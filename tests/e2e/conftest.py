"""
Pytest fixtures для E2E тестирования AIST Track Bot.

Переменные окружения:
- TEST_API_ID: Telegram API ID (https://my.telegram.org)
- TEST_API_HASH: Telegram API Hash
- TEST_BOT_USERNAME: Username бота для тестирования (например @aist_track_bot)
- TEST_SESSION: Имя файла сессии (по умолчанию 'e2e_test_session')
- TEST_DB_URL: URL тестовой БД (опционально, для очистки между тестами)

Первый запуск:
1. Установить telethon: pip install telethon
2. Создать .env.test с переменными
3. Запустить: pytest tests/e2e/ -v
4. При первом запуске ввести номер телефона и код подтверждения
"""

import os
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from .client import BotTestClient, BotTest


# Загружаем переменные окружения для тестов
def _load_test_env():
    """Загружает переменные из .env.test если есть"""
    env_file = os.path.join(os.path.dirname(__file__), '..', '..', '.env.test')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


_load_test_env()


# Конфигурация pytest-asyncio для использования одного event loop на всю сессию
@pytest.fixture(scope="session")
def event_loop_policy():
    """Возвращает политику event loop"""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session")
def event_loop(event_loop_policy):
    """Создаёт единый event loop для всей сессии тестов.

    Это критически важно для Telethon, который требует один и тот же
    event loop на протяжении всего соединения.
    """
    loop = event_loop_policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def bot_client(event_loop) -> AsyncGenerator[BotTestClient, None]:
    """
    Фикстура клиента бота на всю сессию тестов.

    Использование:
        async def test_something(bot_client):
            responses = await bot_client.command_and_wait('/start')
            assert responses[0].has_text('Привет')
    """
    client = BotTestClient(
        api_id=int(os.getenv("TEST_API_ID", "0")),
        api_hash=os.getenv("TEST_API_HASH", ""),
        session_name=os.getenv("TEST_SESSION", "e2e_test_session"),
        bot_username=os.getenv("TEST_BOT_USERNAME", ""),
        loop=event_loop,  # Передаём event loop явно
    )

    # Проверяем конфигурацию
    if not client.api_id or not client.api_hash:
        pytest.skip("TEST_API_ID и TEST_API_HASH не настроены")

    if not client.bot_username:
        pytest.skip("TEST_BOT_USERNAME не настроен")

    await client.start()
    yield client
    await client.stop()


@pytest_asyncio.fixture(loop_scope="session")
async def fresh_client(bot_client: BotTestClient) -> BotTestClient:
    """
    Фикстура для чистого теста - очищает чат перед каждым тестом.

    Использование:
        async def test_clean_start(fresh_client):
            # Чат очищен, можно тестировать с нуля
            responses = await fresh_client.command_and_wait('/start')
    """
    await bot_client.clear_chat()
    await asyncio.sleep(0.5)  # Пауза после очистки
    return bot_client


@pytest.fixture
def test_user_data():
    """Тестовые данные пользователя для онбординга"""
    return {
        'name': 'Тестовый Пользователь',
        'occupation': 'Тестировщик ботов',
        'interests': 'Автоматизация, Python, AI',
        'motivation': 'Хочу научиться системному мышлению',
        'goals': 'Стать лучшим специалистом',
        'study_duration': '15',  # минут
    }


# Маркеры для категоризации тестов
def pytest_configure(config):
    """Регистрация маркеров"""
    config.addinivalue_line("markers", "onboarding: тесты онбординга (1.x)")
    config.addinivalue_line("markers", "marathon: тесты Марафона (2.x)")
    config.addinivalue_line("markers", "feed: тесты Ленты (3.x)")
    config.addinivalue_line("markers", "modes: тесты переключения режимов (4.x)")
    config.addinivalue_line("markers", "settings: тесты настроек (5.x)")
    config.addinivalue_line("markers", "language: тесты языка (6.x)")
    config.addinivalue_line("markers", "commands: тесты команд (7.x)")
    config.addinivalue_line("markers", "edge_cases: граничные случаи (8.x)")
    config.addinivalue_line("markers", "slow: медленные тесты (требуют генерации AI)")
    config.addinivalue_line("markers", "critical: критические сценарии")


# Хелперы для тестов
class Assertions:
    """Хелперы для ассертов в E2E тестах"""

    @staticmethod
    def response_contains(responses, text: str, msg: str = None):
        """Проверяет, что хотя бы один ответ содержит текст"""
        for r in responses:
            if r.has_text(text):
                return True
        raise AssertionError(
            msg or f"Ни один ответ не содержит '{text}'. "
            f"Полученные ответы: {[r.text[:100] for r in responses]}"
        )

    @staticmethod
    def response_has_button(responses, button_text: str, msg: str = None):
        """Проверяет наличие кнопки"""
        for r in responses:
            if r.has_button(button_text):
                return True
        raise AssertionError(
            msg or f"Ни один ответ не содержит кнопку '{button_text}'"
        )

    @staticmethod
    def response_count(responses, expected: int, msg: str = None):
        """Проверяет количество ответов"""
        if len(responses) != expected:
            raise AssertionError(
                msg or f"Ожидалось {expected} ответов, получено {len(responses)}"
            )


@pytest.fixture
def assertions():
    """Фикстура с хелперами для ассертов"""
    return Assertions()

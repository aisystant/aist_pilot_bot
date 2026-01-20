"""
Пример использования новых модулей.

Этот файл демонстрирует, как использовать модульную архитектуру.
Не запускайте напрямую - это пример кода.
"""

import asyncio

# ============= ИМПОРТЫ ИЗ НОВЫХ МОДУЛЕЙ =============

# Конфигурация
from config import (
    BOT_TOKEN,
    ANTHROPIC_API_KEY,
    get_logger,
    validate_env,
    Mode,
    MarathonStatus,
    COMPLEXITY_LEVELS,
    STUDY_DURATIONS,
)

# База данных
from db import init_db, acquire, create_tables
from db.queries.users import get_intern, update_intern
from db.queries.answers import save_answer, get_weekly_work_products
from db.queries.activity import record_active_day, get_activity_stats
from db.queries.feed import create_feed_week, get_current_feed_week
from db.queries.qa import save_qa, get_qa_history

# Клиенты API
from clients import claude, mcp_guides, mcp_knowledge

# Ядро
from core import (
    detect_intent,
    IntentType,
    get_question_keywords,
)
from core.helpers import (
    get_personalization_prompt,
    load_topic_metadata,
)

# Обработчик вопросов
from engines.shared import handle_question, search_mcp_context

logger = get_logger(__name__)


# ============= ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ =============

async def example_intent_detection():
    """Пример распознавания интентов"""

    # Контекст: ожидаем ответ на вопрос теории
    context = {
        'awaiting_answer': True,
        'mode': 'marathon',
    }

    # Пользователь задаёт вопрос вместо ответа
    intent = detect_intent("А что такое системное мышление?", context)
    print(f"Интент: {intent.type.value}, уверенность: {intent.confidence}")
    # => Интент: question, уверенность: 0.9

    # Пользователь отвечает на вопрос
    intent = detect_intent(
        "Системное мышление - это способ видеть взаимосвязи...",
        context
    )
    print(f"Интент: {intent.type.value}")
    # => Интент: answer

    # Команда
    intent = detect_intent("проще", {})
    print(f"Интент: {intent.type.value}, команда: {intent.command}")
    # => Интент: command, команда: simpler


async def example_question_handling():
    """Пример обработки вопроса пользователя"""

    # Профиль пользователя
    intern = {
        'chat_id': 123456,
        'name': 'Иван',
        'occupation': 'разработчик',
        'mode': 'marathon',
    }

    # Обработка вопроса
    answer, sources = await handle_question(
        question="Что такое агентность и зачем она нужна?",
        intern=intern,
        context_topic="День 13: Агентность"
    )

    print(f"Ответ: {answer[:200]}...")
    print(f"Источники: {sources}")


async def example_mcp_search():
    """Пример поиска через MCP"""

    # Поиск в руководствах
    results = await mcp_guides.semantic_search(
        "системное мышление практики",
        lang="ru",
        limit=3
    )
    print(f"Найдено в руководствах: {len(results)}")

    # Поиск в базе знаний (свежие посты)
    results = await mcp_knowledge.search(
        "трансформация мемов",
        limit=3
    )
    print(f"Найдено в базе знаний: {len(results)}")


async def example_content_generation():
    """Пример генерации контента"""

    topic = {
        'id': '1-1-three-states',
        'title': 'Три состояния: муха, собака, человек',
        'main_concept': 'осознанность состояний',
        'pain_point': 'Чувствую себя перегруженным',
    }

    intern = {
        'name': 'Мария',
        'occupation': 'менеджер проектов',
        'interests': ['книги', 'йога'],
        'motivation': 'баланс работы и жизни',
        'goals': 'меньше стресса',
        'study_duration': 15,
    }

    # Генерация теоретического контента
    content = await claude.generate_content(
        topic=topic,
        intern=intern,
        mcp_client=mcp_guides,
        knowledge_client=mcp_knowledge
    )
    print(f"Сгенерирован контент: {len(content)} символов")

    # Генерация вопроса
    question = await claude.generate_question(
        topic=topic,
        intern=intern,
        bloom_level=2  # Понимание
    )
    print(f"Вопрос: {question}")


async def example_activity_tracking():
    """Пример отслеживания систематичности"""

    chat_id = 123456

    # Записываем активный день
    await record_active_day(
        chat_id=chat_id,
        activity_type='text_submission',
        mode='marathon',
        reference_id=5  # topic_index
    )

    # Получаем статистику
    stats = await get_activity_stats(chat_id)
    print(f"Всего активных дней: {stats['total']}")
    print(f"Текущая серия: {stats['streak']}")
    print(f"Лучшая серия: {stats['longest_streak']}")


async def example_feed_week():
    """Пример работы с Лентой"""

    chat_id = 123456

    # Создаём недельный план
    week = await create_feed_week(
        chat_id=chat_id,
        suggested_topics=['системное мышление', 'практики осознанности', 'целеполагание'],
        accepted_topics=['системное мышление', 'целеполагание']
    )
    print(f"Создана неделя #{week['week_number']}")

    # Получаем текущую неделю
    current_week = await get_current_feed_week(chat_id)
    if current_week:
        print(f"Статус: {current_week['status']}")
        print(f"День: {current_week['current_day']}/{7}")


# ============= ЗАПУСК =============

if __name__ == "__main__":
    print("Это пример кода, не предназначен для прямого запуска.")
    print("Используйте как референс при интеграции модулей в bot.py")

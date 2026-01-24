"""
StateStorage — хранение состояния пользователей.

Абстракция над хранилищем состояний:
- Сейчас: PostgreSQL через db.queries
- Потом: может быть заменено на DigitalTwin/MCP

Использование:
    from core.storage import StateStorage
    from db.queries.users import UserRepository

    storage = StateStorage(user_repo)

    # Загрузить состояние
    state_data = await storage.load_state(telegram_id)

    # Сохранить состояние
    await storage.save_state(user)
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class StateStorage:
    """
    Хранение состояния пользователей.

    Обеспечивает персистентность стейтов между перезапусками бота.
    Может быть заменено на другое хранилище (DigitalTwin/MCP) в будущем.
    """

    def __init__(self, db_repo):
        """
        Args:
            db_repo: Репозиторий для работы с БД (должен иметь методы
                     get_user, update_user, find_users_by_state)
        """
        self.db = db_repo

    async def load_state(self, telegram_id: int) -> Optional[dict]:
        """
        Загружает состояние пользователя.

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Словарь с данными состояния или None если пользователь не найден
        """
        try:
            user = await self.db.get_user_by_telegram_id(telegram_id)
            if not user:
                return None

            return {
                "current_state": getattr(user, 'current_state', None),
                "previous_state": getattr(user, 'previous_state', None),
                "state_context": getattr(user, 'state_context', {}) or {},
            }
        except Exception as e:
            logger.error(f"Failed to load state for {telegram_id}: {e}")
            return None

    async def save_state(self, user) -> bool:
        """
        Сохраняет состояние пользователя.

        Args:
            user: Объект пользователя с атрибутами current_state, previous_state, state_context

        Returns:
            True если сохранение успешно
        """
        try:
            # Получаем ID для обновления
            user_id = getattr(user, 'id', None)
            telegram_id = getattr(user, 'telegram_id', None)

            if not user_id and not telegram_id:
                logger.error("Cannot save state: user has no id or telegram_id")
                return False

            update_data = {
                "current_state": getattr(user, 'current_state', None),
                "previous_state": getattr(user, 'previous_state', None),
                "state_context": getattr(user, 'state_context', None),
            }

            # Удаляем None значения
            update_data = {k: v for k, v in update_data.items() if v is not None}

            if user_id:
                await self.db.update_user(user_id, update_data)
            else:
                await self.db.update_user_by_telegram_id(telegram_id, update_data)

            logger.debug(f"State saved for user {telegram_id or user_id}: {update_data.get('current_state')}")
            return True

        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            return False

    async def get_users_in_state(self, state_name: str) -> list:
        """
        Возвращает всех пользователей в указанном стейте.

        Args:
            state_name: Имя стейта

        Returns:
            Список пользователей
        """
        try:
            return await self.db.find_users_by_state(state_name)
        except Exception as e:
            logger.error(f"Failed to get users in state {state_name}: {e}")
            return []

    async def clear_state_context(self, user) -> bool:
        """
        Очищает контекст стейта пользователя.

        Args:
            user: Объект пользователя

        Returns:
            True если успешно
        """
        try:
            user.state_context = {}
            return await self.save_state(user)
        except Exception as e:
            logger.error(f"Failed to clear state context: {e}")
            return False

    async def set_context_value(self, user, key: str, value: Any) -> bool:
        """
        Устанавливает значение в контексте стейта.

        Args:
            user: Объект пользователя
            key: Ключ
            value: Значение

        Returns:
            True если успешно
        """
        try:
            if not hasattr(user, 'state_context') or user.state_context is None:
                user.state_context = {}
            user.state_context[key] = value
            return await self.save_state(user)
        except Exception as e:
            logger.error(f"Failed to set context value: {e}")
            return False

    async def get_context_value(self, user, key: str, default: Any = None) -> Any:
        """
        Получает значение из контекста стейта.

        Args:
            user: Объект пользователя
            key: Ключ
            default: Значение по умолчанию

        Returns:
            Значение или default
        """
        context = getattr(user, 'state_context', {}) or {}
        return context.get(key, default)

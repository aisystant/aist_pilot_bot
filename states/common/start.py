"""
Стейт: Начало работы, онбординг нового пользователя.

Вход: при /start или первом сообщении
Выход: common.mode_select после завершения онбординга
"""

from typing import Optional

from aiogram.types import Message

from states.base import BaseState


class StartState(BaseState):
    """
    Стейт начала работы.

    Для новых пользователей: онбординг (запрос имени и т.д.)
    Для существующих: переход к выбору режима
    """

    name = "common.start"
    display_name = {"ru": "Начало", "en": "Start"}
    allow_global = []  # Глобальные команды недоступны на старте

    async def enter(self, user, context: dict = None) -> None:
        """Показываем приветствие."""
        # Проверяем, есть ли у пользователя имя (существующий пользователь)
        user_name = getattr(user, 'name', None)

        if user_name:
            # Существующий пользователь
            await self.send(
                user,
                self.t("states.start.welcome_back", user, name=user_name)
            )
            # Сразу переходим к выбору режима (будет обработано в handle)
        else:
            # Новый пользователь
            await self.send(
                user,
                self.t("states.start.welcome_new", user)
            )
            await self.send(
                user,
                self.t("states.start.ask_name", user)
            )

    async def handle(self, user, message: Message) -> Optional[str]:
        """
        Обрабатываем ответ пользователя.

        Если пользователь существующий — сразу переходим к mode_select.
        Если новый — сохраняем имя и переходим к mode_select.
        """
        user_name = getattr(user, 'name', None)

        if user_name:
            # Существующий пользователь — сразу переходим
            return "existing_user"

        # Новый пользователь — сохраняем имя
        name = (message.text or "").strip()

        if not name or len(name) < 2:
            await self.send(
                user,
                self.t("states.start.ask_name", user)
            )
            return None  # Остаёмся в стейте

        # Сохраняем имя
        user.name = name

        # Приветствуем
        await self.send(
            user,
            self.t("common.welcome", user)
        )

        return "onboarding_complete"

    async def exit(self, user) -> dict:
        """Передаём контекст следующему стейту."""
        return {"from_onboarding": not getattr(user, 'name', None)}

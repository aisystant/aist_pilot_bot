"""
Стейт: Обработка ошибок.

Вход: при ошибке в любом стейте
Выход: common.start (retry) или _previous (continue)
"""

from typing import Optional

from aiogram.types import Message

from states.base import BaseState


class ErrorState(BaseState):
    """
    Стейт обработки ошибок.

    Показывает сообщение об ошибке и предлагает повторить или продолжить.
    """

    name = "common.error"
    display_name = {"ru": "Ошибка", "en": "Error"}
    allow_global = []

    async def enter(self, user, context: dict = None) -> None:
        """Показываем сообщение об ошибке."""
        # Получаем детали ошибки из контекста
        error_message = (context or {}).get("error_message")

        if error_message:
            await self.send(user, f"{self.t('common.error', user)}\n\n{error_message}")
        else:
            await self.send(user, self.t("states.error.message", user))

        # Показываем кнопки
        buttons = [
            [self.t("states.error.retry_button", user)],
            [self.t("common.back", user)]
        ]
        await self.send_with_keyboard(
            user,
            self.t("common.help", user),
            buttons
        )

    async def handle(self, user, message: Message) -> Optional[str]:
        """Обрабатываем выбор пользователя."""
        text = (message.text or "").strip()

        retry_text = self.t("states.error.retry_button", user)
        back_text = self.t("common.back", user)

        if text == retry_text:
            return "retry"
        elif text == back_text:
            return "continue"

        # Любой другой текст — продолжаем
        return "continue"

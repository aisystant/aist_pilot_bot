"""
Стейт: Выбор режима работы.

Вход: после онбординга или по команде /mode
Выход: workshop.marathon.day, consultant.feed_topics и т.д.
"""

from typing import Optional

from aiogram.types import Message

from states.base import BaseState
from config.features import flags


class ModeSelectState(BaseState):
    """
    Стейт выбора режима работы.

    Показывает доступные режимы (мастерские, консультанты) и переходит
    в выбранный режим.
    """

    name = "common.mode_select"
    display_name = {"ru": "Выбор режима", "en": "Mode Select"}
    allow_global = ["consultant", "notes"]

    async def enter(self, user, context: dict = None) -> None:
        """Показываем меню выбора режима."""
        # Формируем список доступных режимов
        buttons = []

        # Марафон
        if flags.is_enabled("workshops.marathon.visible"):
            buttons.append([self.t("common.mode_select.marathon", user)])

        # Лента
        if flags.is_enabled("consultants.feed.enabled"):
            buttons.append([self.t("common.mode_select.feed", user)])

        # Настройки (всегда доступны)
        buttons.append([self.t("common.mode_select.settings", user)])

        await self.send_with_keyboard(
            user,
            self.t("common.mode_select.title", user),
            buttons,
            one_time=False
        )

    async def handle(self, user, message: Message) -> Optional[str]:
        """Обрабатываем выбор режима."""
        text = (message.text or "").strip()

        # Марафон
        marathon_text = self.t("common.mode_select.marathon", user)
        if text == marathon_text and flags.is_enabled("workshops.marathon.enabled"):
            return "marathon"

        # Лента
        feed_text = self.t("common.mode_select.feed", user)
        if text == feed_text and flags.is_enabled("consultants.feed.enabled"):
            return "feed"

        # Настройки
        settings_text = self.t("common.mode_select.settings", user)
        if text == settings_text:
            return "settings"

        # Неизвестный выбор — показываем меню снова
        await self.send(user, self.t("common.mode_select.title", user))
        return None  # Остаёмся в стейте

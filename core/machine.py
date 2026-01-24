"""
StateMachine — движок переходов между стейтами.

Управляет:
- Регистрацией стейтов
- Обработкой входящих сообщений
- Выполнением переходов между стейтами
- Глобальными командами (?, /note, /mode)

Использование:
    from core.machine import StateMachine
    from core.storage import StateStorage

    storage = StateStorage(user_repo)
    machine = StateMachine("config/transitions.yaml", storage)

    # Регистрируем стейты
    machine.register(StartState(...))
    machine.register(MarathonDayState(...))

    # Обрабатываем сообщение
    await machine.handle_message(user, message)
"""

import logging
from pathlib import Path
from typing import Optional

import yaml
from aiogram.types import Message

from states.base import BaseState

logger = logging.getLogger(__name__)


class InvalidTransition(Exception):
    """Недопустимый переход между стейтами."""
    pass


class StateNotFound(Exception):
    """Стейт не найден в реестре."""
    pass


class StateMachine:
    """
    Движок State Machine.

    Управляет переходами между стейтами на основе таблицы переходов.
    Таблица переходов загружается из YAML файла.
    """

    def __init__(self, transitions_path: str, storage):
        """
        Args:
            transitions_path: Путь к transitions.yaml
            storage: StateStorage для работы с БД
        """
        self.storage = storage
        self.states: dict[str, BaseState] = {}
        self.transitions: dict = {}
        self.global_events: dict = {}

        self._load_transitions(transitions_path)

    def _load_transitions(self, path: str) -> None:
        """Загружает таблицу переходов из YAML файла."""
        path = Path(path)
        if not path.exists():
            logger.warning(f"Transitions file not found: {path}. Using empty config.")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in transitions file: {e}")
            return

        self.transitions = config.get("states", {})
        self.global_events = config.get("global_events", {})
        logger.info(f"Loaded {len(self.transitions)} state transitions")

    def register(self, state: BaseState) -> None:
        """
        Регистрирует стейт в машине.

        Args:
            state: Экземпляр стейта
        """
        if state.name in self.states:
            logger.warning(f"State {state.name} already registered, overwriting")
        self.states[state.name] = state
        logger.debug(f"Registered state: {state.name}")

    def register_all(self, states: list[BaseState]) -> None:
        """Регистрирует список стейтов."""
        for state in states:
            self.register(state)

    async def get_user_state(self, user) -> BaseState:
        """
        Возвращает текущий стейт пользователя.

        Args:
            user: Объект пользователя

        Returns:
            Экземпляр текущего стейта

        Raises:
            StateNotFound: Если стейт не найден в реестре
        """
        state_name = getattr(user, 'current_state', None) or "common.start"

        if state_name not in self.states:
            logger.error(f"Unknown state: {state_name}. Falling back to common.start")
            state_name = "common.start"
            if state_name not in self.states:
                raise StateNotFound(f"Default state common.start not registered")

        return self.states[state_name]

    async def handle_message(self, user, message: Message) -> None:
        """
        Главный метод — обрабатывает входящее сообщение.

        1. Проверяет глобальные события
        2. Передаёт сообщение текущему стейту
        3. Выполняет переход если нужно

        Args:
            user: Объект пользователя
            message: Сообщение от Telegram
        """
        # Проверяем глобальные события (?, /note, /mode)
        global_event = self._check_global_events(user, message)
        if global_event:
            logger.info(f"Global event triggered: {global_event}")
            await self._handle_global_event(user, global_event, message)
            return

        # Получаем текущий стейт
        state = await self.get_user_state(user)
        logger.debug(f"Handling message in state: {state.name}")

        # Обрабатываем сообщение
        event = await state.handle(user, message)

        # Если стейт вернул событие — выполняем переход
        if event:
            logger.info(f"State {state.name} returned event: {event}")
            await self.transition(user, event, message)

    def _check_global_events(self, user, message: Message) -> Optional[str]:
        """
        Проверяет, не является ли сообщение глобальной командой.

        Args:
            user: Объект пользователя
            message: Сообщение от Telegram

        Returns:
            Имя глобального события или None
        """
        text = (message.text or "").strip()
        current_state = getattr(user, 'current_state', None) or "common.start"

        # Получаем разрешённые глобальные события для текущего стейта
        state_config = self.transitions.get(current_state, {})
        allowed = state_config.get("allow_global", [])

        for event_name, config in self.global_events.items():
            trigger = config.get("trigger", "")

            # Проверяем триггер
            matches = False
            if trigger.startswith("/"):
                # Команда — точное совпадение начала
                matches = text.lower().startswith(trigger.lower())
            else:
                # Другие триггеры (например, "?")
                matches = text.startswith(trigger)

            if matches and event_name in allowed:
                return event_name

        return None

    async def _handle_global_event(self, user, event_name: str, message: Message) -> None:
        """
        Обрабатывает глобальное событие.

        Args:
            user: Объект пользователя
            event_name: Имя глобального события
            message: Исходное сообщение
        """
        config = self.global_events.get(event_name, {})
        target_state = config.get("target")

        if not target_state:
            logger.warning(f"No target state for global event: {event_name}")
            return

        # Сохраняем контекст (например, текст вопроса после "?")
        trigger = config.get("trigger", "")
        context = {}
        if trigger and message.text:
            # Извлекаем текст после триггера
            remaining = message.text[len(trigger):].strip()
            if remaining:
                context["initial_text"] = remaining
                if event_name == "consultant":
                    context["question"] = remaining

        await self.transition(user, event_name, message, force_target=target_state, context=context)

    async def transition(
        self,
        user,
        event: str,
        message: Message = None,
        force_target: str = None,
        context: dict = None
    ) -> None:
        """
        Выполняет переход между стейтами.

        Args:
            user: Объект пользователя
            event: Событие, вызвавшее переход
            message: Исходное сообщение (для контекста)
            force_target: Принудительный целевой стейт (для глобальных событий)
            context: Дополнительный контекст
        """
        current_state_name = getattr(user, 'current_state', None) or "common.start"

        # Определяем следующий стейт
        if force_target:
            next_state_name = force_target
        else:
            next_state_name = self._get_next_state(current_state_name, event)

        if not next_state_name:
            logger.warning(
                f"No transition for event '{event}' from state '{current_state_name}'"
            )
            return

        # Специальные переходы
        if next_state_name == "_previous":
            next_state_name = getattr(user, 'previous_state', None) or "common.mode_select"
        elif next_state_name == "_same":
            logger.debug(f"Staying in state: {current_state_name}")
            return  # Остаёмся в текущем стейте

        # Получаем объекты стейтов
        current_state = self.states.get(current_state_name)
        next_state = self.states.get(next_state_name)

        if not next_state:
            logger.error(f"Target state not found: {next_state_name}")
            return

        # Выполняем выход из текущего стейта
        exit_context = {}
        if current_state:
            exit_context = await current_state.exit(user) or {}

        # Объединяем контексты
        combined_context = {**exit_context, **(context or {})}

        # Сохраняем предыдущий стейт
        user.previous_state = current_state_name
        user.current_state = next_state_name

        # Сохраняем в БД
        await self.storage.save_state(user)

        logger.info(f"Transition: {current_state_name} -> {next_state_name} (event: {event})")

        # Выполняем вход в новый стейт
        await next_state.enter(user, combined_context)

    def _get_next_state(self, current: str, event: str) -> Optional[str]:
        """
        Определяет следующий стейт по таблице переходов.

        Args:
            current: Имя текущего стейта
            event: Событие

        Returns:
            Имя следующего стейта или None
        """
        # Сначала проверяем глобальные события
        if event in self.global_events:
            return self.global_events[event].get("target")

        # Затем проверяем переходы текущего стейта
        state_config = self.transitions.get(current, {})
        events = state_config.get("events", {})
        return events.get(event)

    async def force_state(self, user, state_name: str, context: dict = None) -> None:
        """
        Принудительно переводит пользователя в указанный стейт.

        Используется для административных целей и восстановления.

        Args:
            user: Объект пользователя
            state_name: Имя целевого стейта
            context: Контекст для передачи стейту
        """
        if state_name not in self.states:
            raise StateNotFound(f"State not found: {state_name}")

        # Сохраняем предыдущий стейт
        user.previous_state = getattr(user, 'current_state', None)
        user.current_state = state_name

        await self.storage.save_state(user)

        # Входим в новый стейт
        await self.states[state_name].enter(user, context or {})

    def get_state_info(self, state_name: str) -> dict:
        """
        Возвращает информацию о стейте.

        Args:
            state_name: Имя стейта

        Returns:
            Словарь с информацией о стейте
        """
        state = self.states.get(state_name)
        if not state:
            return {}

        config = self.transitions.get(state_name, {})
        return {
            "name": state.name,
            "display_name": state.display_name,
            "allow_global": state.allow_global,
            "events": list(config.get("events", {}).keys()),
            "description": config.get("description", ""),
        }

    def list_states(self) -> list[str]:
        """Возвращает список зарегистрированных стейтов."""
        return list(self.states.keys())

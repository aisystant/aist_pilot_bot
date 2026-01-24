"""
Feature Flags для управления функциональностью бота.

Позволяет:
- Включать/выключать функции без изменения кода
- Переопределять флаги через переменные окружения
- Постепенно раскатывать новую архитектуру (Strangler Fig pattern)

Использование:
    from config.features import flags

    if flags.is_enabled("migration.use_state_machine"):
        # Новый код
    else:
        # Старый код
"""

import os
from pathlib import Path
from typing import Any

import yaml


class FeatureFlags:
    """
    Класс для работы с feature flags.

    Загружает конфигурацию из features.yaml.
    Переменные окружения имеют приоритет над значениями в файле.

    Формат env переменных: путь с точками заменяется на подчёркивания в верхнем регистре.
    Пример: "migration.use_state_machine" → "MIGRATION_USE_STATE_MACHINE"
    """

    def __init__(self, config_path: str = None):
        """
        Args:
            config_path: Путь к features.yaml. По умолчанию ищет в папке config/
        """
        if config_path is None:
            config_path = Path(__file__).parent / "features.yaml"

        self._config: dict = {}
        self._load_config(config_path)

    def _load_config(self, path: Path) -> None:
        """Загружает конфигурацию из YAML файла."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            # Если файл не найден, используем пустую конфигурацию
            self._config = {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in features.yaml: {e}")

    def is_enabled(self, path: str) -> bool:
        """
        Проверяет, включён ли флаг.

        Env переменные имеют приоритет над значениями в файле.

        Args:
            path: Путь к флагу через точку (например, "migration.use_state_machine")

        Returns:
            True если флаг включён, False если выключен или не найден

        Examples:
            flags.is_enabled("migration.use_state_machine")
            flags.is_enabled("workshops.exocortex.enabled")
        """
        # Проверяем env override
        env_name = path.upper().replace(".", "_")
        env_value = os.getenv(env_name)

        if env_value is not None:
            return env_value.lower() in ("true", "1", "yes", "on")

        # Читаем из конфига
        return bool(self._get_value(path))

    def get(self, path: str, default: Any = None) -> Any:
        """
        Получает значение флага (не только boolean).

        Args:
            path: Путь к значению через точку
            default: Значение по умолчанию

        Returns:
            Значение из конфига или default
        """
        # Проверяем env override
        env_name = path.upper().replace(".", "_")
        env_value = os.getenv(env_name)

        if env_value is not None:
            # Пытаемся преобразовать в число
            try:
                return int(env_value)
            except ValueError:
                pass
            # Возвращаем как строку
            return env_value

        value = self._get_value(path)
        return value if value is not None else default

    def _get_value(self, path: str) -> Any:
        """Получает значение по пути через точку."""
        keys = path.split(".")
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    def reload(self, config_path: str = None) -> None:
        """Перезагружает конфигурацию из файла."""
        if config_path is None:
            config_path = Path(__file__).parent / "features.yaml"
        self._load_config(config_path)


# Глобальный экземпляр для использования во всём приложении
flags = FeatureFlags()

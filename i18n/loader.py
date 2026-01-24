"""
I18n — система локализации для State Machine.

Загружает переводы из YAML файлов и предоставляет API для их получения.

Структура файлов:
    i18n/
    ├── ru/
    │   ├── common.yaml      # Общие строки
    │   └── states.yaml      # Строки для стейтов
    └── en/
        ├── common.yaml
        └── states.yaml

Формат YAML:
    greeting: "Привет, {name}!"
    marathon:
      welcome: "Добро пожаловать в Марафон!"
      day: "День {day}"

Использование:
    from i18n import t

    # Простой перевод
    text = t("greeting", "ru", name="Иван")
    # -> "Привет, Иван!"

    # Вложенные ключи
    text = t("marathon.welcome", "ru")
    # -> "Добро пожаловать в Марафон!"
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class I18n:
    """
    Класс для работы с локализацией.

    Загружает все переводы из YAML файлов при инициализации.
    Поддерживает вложенные ключи через точку (например, "marathon.welcome").
    """

    def __init__(self, i18n_dir: str = None):
        """
        Args:
            i18n_dir: Путь к папке с переводами. По умолчанию — папка i18n/
        """
        if i18n_dir is None:
            i18n_dir = Path(__file__).parent
        else:
            i18n_dir = Path(i18n_dir)

        self._translations: dict[str, dict[str, str]] = {}
        self._default_lang = "ru"
        self._load_all(i18n_dir)

    def _load_all(self, i18n_dir: Path) -> None:
        """Загружает все переводы из папки."""
        if not i18n_dir.exists():
            logger.warning(f"i18n directory not found: {i18n_dir}")
            return

        for lang_dir in i18n_dir.iterdir():
            if lang_dir.is_dir() and not lang_dir.name.startswith(("_", ".")):
                lang = lang_dir.name
                self._translations[lang] = {}

                for yaml_file in lang_dir.glob("*.yaml"):
                    self._load_file(yaml_file, lang)

                logger.debug(f"Loaded {len(self._translations[lang])} keys for language: {lang}")

    def _load_file(self, yaml_file: Path, lang: str) -> None:
        """Загружает один YAML файл."""
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # Используем имя файла как namespace (common.yaml -> common)
            namespace = yaml_file.stem

            # Флаттеним вложенные словари
            self._flatten(data, namespace, self._translations[lang])

        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in {yaml_file}: {e}")
        except Exception as e:
            logger.error(f"Error loading {yaml_file}: {e}")

    def _flatten(self, data: dict, prefix: str, result: dict) -> None:
        """
        Превращает вложенный dict в плоский с точками.

        Пример:
            {"marathon": {"welcome": "Hello"}}
            -> {"states.marathon.welcome": "Hello"}
        """
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self._flatten(value, full_key, result)
            else:
                result[full_key] = str(value)

    def t(self, key: str, lang: str = None, **kwargs) -> str:
        """
        Получает перевод по ключу.

        Args:
            key: Ключ перевода (например, "common.greeting" или "states.marathon.welcome")
            lang: Код языка (ru, en). По умолчанию — ru
            **kwargs: Параметры для форматирования строки

        Returns:
            Переведённая строка. Если ключ не найден — возвращает сам ключ.
        """
        if lang is None:
            lang = self._default_lang

        # Если язык не найден, используем дефолтный
        if lang not in self._translations:
            lang = self._default_lang

        # Пробуем найти перевод
        translations = self._translations.get(lang, {})
        text = translations.get(key)

        # Если не нашли — пробуем fallback на дефолтный язык
        if text is None and lang != self._default_lang:
            text = self._translations.get(self._default_lang, {}).get(key)

        # Если всё ещё не нашли — возвращаем ключ
        if text is None:
            logger.warning(f"Translation not found: {key} ({lang})")
            return key

        # Форматируем если есть параметры
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing format parameter in '{key}': {e}")
                return text

        return text

    def get_available_languages(self) -> list[str]:
        """Возвращает список доступных языков."""
        return list(self._translations.keys())

    def has_key(self, key: str, lang: str = None) -> bool:
        """Проверяет, есть ли перевод для ключа."""
        if lang is None:
            lang = self._default_lang
        return key in self._translations.get(lang, {})

    def reload(self, i18n_dir: str = None) -> None:
        """Перезагружает все переводы."""
        if i18n_dir is None:
            i18n_dir = Path(__file__).parent
        else:
            i18n_dir = Path(i18n_dir)

        self._translations = {}
        self._load_all(i18n_dir)


# Глобальный экземпляр
i18n = I18n()


def t(key: str, lang: str = "ru", **kwargs) -> str:
    """Shortcut для получения перевода."""
    return i18n.t(key, lang, **kwargs)

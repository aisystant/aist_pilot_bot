"""
Модуль интернационализации.

Обёртка над locales.py для использования в State Machine.
"""

from locales import t, SUPPORTED_LANGUAGES, LANGUAGE_NAMES


class I18n:
    """
    Класс интернационализации для State Machine.

    Обёртка над функцией t() из locales.py.
    """

    def __init__(self, default_lang: str = 'ru'):
        self.default_lang = default_lang

    def get(self, key: str, lang: str = None, **kwargs) -> str:
        """
        Получить перевод по ключу.

        Args:
            key: Ключ перевода (например 'welcome.greeting')
            lang: Код языка ('ru', 'en', 'es')
            **kwargs: Параметры для форматирования

        Returns:
            Переведённая строка
        """
        return t(key, lang or self.default_lang, **kwargs)

    def __call__(self, key: str, lang: str = None, **kwargs) -> str:
        """Позволяет вызывать i18n как функцию: i18n('key', 'ru')"""
        return self.get(key, lang, **kwargs)

    @property
    def supported_languages(self) -> list:
        return SUPPORTED_LANGUAGES

    @property
    def language_names(self) -> dict:
        return LANGUAGE_NAMES

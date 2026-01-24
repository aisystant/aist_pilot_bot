"""
Модуль локализации (i18n).

Содержит:
- loader.py: класс I18n для загрузки и получения переводов
- ru/: русские переводы (yaml файлы)
- en/: английские переводы (yaml файлы)

Использование:
    from i18n import t, i18n

    # Получить перевод
    text = t("common.greeting", "ru", name="Иван")

    # Или через экземпляр
    text = i18n.t("common.greeting", "ru", name="Иван")
"""

from .loader import I18n, i18n, t

__all__ = ['I18n', 'i18n', 't']

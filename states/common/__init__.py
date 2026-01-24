"""
Общие стейты (common).

Содержит:
- start.py: начало работы, онбординг
- error.py: обработка ошибок
- mode_select.py: выбор режима работы
"""

from .start import StartState
from .error import ErrorState
from .mode_select import ModeSelectState

__all__ = ['StartState', 'ErrorState', 'ModeSelectState']

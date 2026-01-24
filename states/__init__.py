"""
Модуль стейтов State Machine.

Содержит:
- base.py: базовый класс BaseState
- common/: общие стейты (start, error, mode_select)
- workshops/: стейты мастерских (marathon, exocortex, fpfkids, practice)
- consultants/: стейты консультантов (main, feed, assessment)
- utilities/: стейты утилит (notes, export)
"""

from .base import BaseState

__all__ = ['BaseState']

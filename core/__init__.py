"""
Ядро бота: общие компоненты.

Содержит:
- helpers.py: вспомогательные функции для генерации контента
- intent.py: распознавание намерений пользователя
- machine.py: StateMachine — движок переходов между стейтами
- storage.py: StateStorage — хранение состояния пользователей
- router.py: маршрутизация по режимам (Марафон/Лента) - TODO
- scheduler.py: настройка APScheduler - TODO
"""

from .helpers import (
    load_topic_metadata,
    get_search_keys,
    get_bloom_questions,
    get_personalization_prompt,
)

from .intent import (
    IntentType,
    Intent,
    detect_intent,
    detect_command,
    is_topic_request,
    is_clear_question,
    question_likelihood,
    get_question_keywords,
)

from .machine import StateMachine, InvalidTransition, StateNotFound
from .storage import StateStorage

__all__ = [
    # helpers
    'load_topic_metadata',
    'get_search_keys',
    'get_bloom_questions',
    'get_personalization_prompt',
    # intent
    'IntentType',
    'Intent',
    'detect_intent',
    'detect_command',
    'is_topic_request',
    'is_clear_question',
    'question_likelihood',
    'get_question_keywords',
    # machine
    'StateMachine',
    'InvalidTransition',
    'StateNotFound',
    # storage
    'StateStorage',
]

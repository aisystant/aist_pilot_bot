"""
Стейты Ленты.

Содержит:
- topics.py: выбор тем на неделю
- digest.py: показ дайджеста

Flow:
  topics → digest → [fixation] → digest (следующий) → ... → topics (новая неделя)
"""

from .topics import FeedTopicsState
from .digest import FeedDigestState

__all__ = ['FeedTopicsState', 'FeedDigestState']

"""
Запросы для режима Лента.
"""

import json
from datetime import date, timedelta
from typing import List, Optional

from config import get_logger, FeedWeekStatus

logger = get_logger(__name__)


async def create_feed_week(pool, chat_id: int, suggested_topics: List[dict] = None,
                          accepted_topics: List[dict] = None, 
                          status: str = FeedWeekStatus.PLANNING) -> int:
    """Создать новую неделю Ленты"""
    from .users import moscow_today
    
    today = moscow_today()
    week_start = today - timedelta(days=today.weekday())  # Понедельник
    
    # Получить номер недели
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT COALESCE(MAX(week_number), 0) + 1 as next_week
            FROM feed_weeks WHERE chat_id = $1
        ''', chat_id)
        week_number = row['next_week']
        
        result = await conn.fetchrow('''
            INSERT INTO feed_weeks 
            (chat_id, week_number, week_start, suggested_topics, accepted_topics, status)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        ''', chat_id, week_number, week_start,
            json.dumps(suggested_topics or []),
            json.dumps(accepted_topics or []),
            status)
        
        return result['id']


async def get_current_feed_week(pool, chat_id: int) -> Optional[dict]:
    """Получить текущую (активную или в планировании) неделю"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT * FROM feed_weeks 
            WHERE chat_id = $1 AND status IN ($2, $3)
            ORDER BY created_at DESC
            LIMIT 1
        ''', chat_id, FeedWeekStatus.PLANNING, FeedWeekStatus.ACTIVE)
        
        if row:
            return {
                'id': row['id'],
                'chat_id': row['chat_id'],
                'week_number': row['week_number'],
                'week_start': row['week_start'],
                'suggested_topics': json.loads(row['suggested_topics']),
                'accepted_topics': json.loads(row['accepted_topics']),
                'current_day': row['current_day'],
                'status': row['status'],
                'created_at': row['created_at']
            }
        return None


async def update_feed_week(pool, chat_id: int, week_id: int, **kwargs):
    """Обновить неделю Ленты"""
    async with pool.acquire() as conn:
        for key, value in kwargs.items():
            if key in ['suggested_topics', 'accepted_topics']:
                value = json.dumps(value) if not isinstance(value, str) else value
            
            await conn.execute(
                f'UPDATE feed_weeks SET {key} = $1 WHERE id = $2 AND chat_id = $3',
                value, week_id, chat_id
            )


async def create_feed_session(pool, chat_id: int, week_id: int, 
                             day_number: int, topic: str, content: dict) -> int:
    """Создать сессию Ленты"""
    async with pool.acquire() as conn:
        result = await conn.fetchrow('''
            INSERT INTO feed_sessions 
            (chat_id, week_id, day_number, topic, content, sent_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING id
        ''', chat_id, week_id, day_number, topic, json.dumps(content))
        
        return result['id']


async def update_feed_session(pool, session_id: int, **kwargs):
    """Обновить сессию Ленты"""
    async with pool.acquire() as conn:
        for key, value in kwargs.items():
            if key == 'content':
                value = json.dumps(value) if not isinstance(value, str) else value
            
            await conn.execute(
                f'UPDATE feed_sessions SET {key} = $1 WHERE id = $2',
                value, session_id
            )


async def get_feed_session(pool, session_id: int) -> Optional[dict]:
    """Получить сессию по ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT * FROM feed_sessions WHERE id = $1', session_id
        )
        
        if row:
            return {
                'id': row['id'],
                'chat_id': row['chat_id'],
                'week_id': row['week_id'],
                'day_number': row['day_number'],
                'topic': row['topic'],
                'content': json.loads(row['content']) if row['content'] else {},
                'user_fixation': row['user_fixation'],
                'sent_at': row['sent_at'],
                'completed_at': row['completed_at'],
            }
        return None


async def get_feed_history(pool, chat_id: int, limit: int = 20) -> List[dict]:
    """Получить историю сессий Ленты"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT topic, user_fixation, sent_at, completed_at
            FROM feed_sessions
            WHERE chat_id = $1 AND completed_at IS NOT NULL
            ORDER BY completed_at DESC
            LIMIT $2
        ''', chat_id, limit)
        
        return [dict(row) for row in rows]

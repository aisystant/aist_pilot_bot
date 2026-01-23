# P-04 Сбор статистики

> Процесс агрегации данных для команды /progress и других отчётов.

---

## Обзор

| Параметр | Значение |
|----------|----------|
| Тип | Процесс |
| Файлы | `db/queries/answers.py`, `db/queries/activity.py` |
| Использует | `/progress`, `/profile` |

---

## 1. Источники данных

| Метрика | Таблица | Запрос |
|---------|---------|--------|
| Активные дни (неделя) | `activity_log` | `COUNT DISTINCT activity_date WHERE date > NOW() - 7 days` |
| Активные дни (всего) | `interns` | `active_days_total` |
| Текущая серия | `interns` | `active_days_streak` |
| Пройдено тем | `interns` | `completed_topics` |
| Рабочие продукты | `answers` | `COUNT WHERE answer_type = 'work_product'` |
| Дайджесты | `feed_sessions` | `COUNT WHERE status = 'completed'` |
| Фиксации | `answers` | `COUNT WHERE answer_type = 'fixation'` |

---

## 2. Функции сбора

### get_activity_stats()

**Файл:** `db/queries/activity.py`

**Возвращает:**
```python
{
    'total': int,           # Всего активных дней
    'streak': int,          # Текущая серия
    'longest_streak': int,  # Рекорд серии
    'last_active': date,    # Последний активный день
    'days_active_this_week': int  # За 7 дней
}
```

### get_weekly_marathon_stats()

**Файл:** `db/queries/answers.py`

**Возвращает:**
```python
{
    'topics_completed': int,
    'work_products': int,
    'bonus_answers': int
}
```

### get_weekly_feed_stats()

**Файл:** `db/queries/feed.py`

**Возвращает:**
```python
{
    'digests_count': int,
    'fixations_count': int,
    'topics': list[str]
}
```

---

## 3. Диаграмма

```
/progress
    ↓
cmd_progress()
    ├─ get_activity_stats()           → activity_log, interns
    ├─ get_weekly_marathon_stats()    → answers
    └─ get_weekly_feed_stats()        → feed_sessions, answers
    ↓
Формирование отчёта
    ↓
Отправка пользователю
```

---

## 4. Связь с другими процессами

- **P-01 Отслеживание активности** — записывает данные, которые потом агрегируются здесь
- **Сценарий 03.01 Прогресс** — использует этот процесс для отображения UI

---

## 5. Ключевые файлы

| Файл | Назначение |
|------|-----------|
| `db/queries/activity.py` | Статистика активности |
| `db/queries/answers.py` | Статистика ответов |
| `bot.py:cmd_progress` | Команда /progress |

---

## История изменений

| Дата | Изменение |
|------|-----------|
| 2026-01-23 | Создание документа |

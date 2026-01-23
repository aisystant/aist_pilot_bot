# План локализации UI на выбранный язык пользователя

## Статус: Готово к реализации

## Контекст

Бот поддерживает 3 языка: русский (ru), английский (en), испанский (es).
Система локализации существует в `locales.py` с функцией `t(key, lang)`.

Проблема: многие UI-строки (кнопки, сообщения, меню) всё ещё захардкожены на русском языке.

---

## Архитектура локализации

### Принцип: Централизованный словарь + строгое правило

**Строгое правило:** Ни одной пользовательской строки в коде — только через `t(key, lang)`.

### Компоненты системы

```
locales.py
├── SUPPORTED_LANGUAGES = ['ru', 'en', 'es']
├── GLOSSARY = {...}           # Глоссарий терминов (новое)
└── TRANSLATIONS = {
│       'ru': {...},
│       'en': {...},
│       'es': {...}
│   }
└── t(key, lang, **kwargs)     # Функция перевода
```

### Как работает для разных ролей

#### AI-ассистент (Claude)
1. При написании кода — проверяет существующие ключи в `locales.py`
2. Новая строка → добавляет ключ во все 3 языка
3. Никогда не пишет `await message.answer("Текст")` напрямую
4. Всегда использует `await message.answer(t('key', lang))`

#### Разработчик
```python
# 1. Получить язык пользователя
lang = intern.get('language', 'ru')

# 2. Использовать t() для любого текста
await message.answer(t('mode.marathon.activated', lang))

# 3. Параметризованные строки
await message.answer(t('progress.day', lang, day=5, total=14))
```

**Проверка на захардкоженные строки:**
```bash
grep -rn "[А-Яа-яЁё]" --include="*.py" --exclude="locales.py" .
```

#### Переводчик
1. Все строки в одном файле — `locales.py`
2. Глоссарий терминов гарантирует консистентность
3. Структура позволяет сравнивать переводы side-by-side

---

## Глоссарий терминов (GLOSSARY)

Добавить в `locales.py` — соответствие ключевых терминов из `docs/ontology.md`:

```python
GLOSSARY = {
    # Режимы
    'marathon': {'ru': 'Марафон', 'en': 'Marathon', 'es': 'Maratón'},
    'feed': {'ru': 'Лента', 'en': 'Feed', 'es': 'Feed'},

    # Контент
    'lesson': {'ru': 'Урок', 'en': 'Lesson', 'es': 'Lección'},
    'task': {'ru': 'Задание', 'en': 'Task', 'es': 'Tarea'},
    'digest': {'ru': 'Дайджест', 'en': 'Digest', 'es': 'Resumen diario'},
    'topic': {'ru': 'Тема', 'en': 'Topic', 'es': 'Tema'},

    # Действия пользователя
    'fixation': {'ru': 'Фиксация', 'en': 'Fixation', 'es': 'Fijación'},
    'answer': {'ru': 'Ответ', 'en': 'Answer', 'es': 'Respuesta'},

    # Пользователи
    'learner': {'ru': 'Ученик', 'en': 'Learner', 'es': 'Estudiante'},
    'reader': {'ru': 'Читатель', 'en': 'Reader', 'es': 'Lector'},

    # Настройки
    'difficulty': {'ru': 'Сложность', 'en': 'Difficulty', 'es': 'Dificultad'},
    'reminder': {'ru': 'Напоминание', 'en': 'Reminder', 'es': 'Recordatorio'},
    'duration': {'ru': 'Длительность', 'en': 'Duration', 'es': 'Duración'},

    # Статусы
    'active': {'ru': 'Активен', 'en': 'Active', 'es': 'Activo'},
    'paused': {'ru': 'На паузе', 'en': 'Paused', 'es': 'En pausa'},
    'completed': {'ru': 'Завершён', 'en': 'Completed', 'es': 'Completado'},
    'not_started': {'ru': 'Не начат', 'en': 'Not started', 'es': 'No iniciado'},
}
```

**Функция для получения термина:**
```python
def term(key: str, lang: str = 'ru') -> str:
    """Возвращает термин из глоссария на нужном языке"""
    if key in GLOSSARY:
        return GLOSSARY[key].get(lang, GLOSSARY[key]['ru'])
    return key
```

**Использование:**
```python
# В AI-промптах для консистентности терминов
f"Режим {term('marathon', lang)} активирован!"

# В UI
await message.answer(f"{term('marathon', lang)}: {t('mode.marathon.desc', lang)}")
```

---

## Связь с AI-генерацией

Глоссарий также используется для консистентности терминов в AI-промптах:

```python
# В system_prompt для AI
f"""
Используй следующую терминологию:
- {term('marathon', lang)} — 14-дневный курс
- {term('feed', lang)} — бесконечный режим
- {term('digest', lang)} — ежедневный материал
- {term('fixation', lang)} — личный вывод
"""
```

Это гарантирует, что AI использует те же термины, что и UI.

---

## Что уже сделано

### 1. Локализация AI-генерации (завершено)
Исправлены функции генерации контента с добавлением:
- `lang_instruction` — инструкция по языку в начале system_prompt
- `lang_reminder` — напоминание о языке в конце system_prompt
- Локализованный `user_prompt`

Затронутые файлы:
- `engines/feed/planner.py`: suggest_weekly_topics, generate_multi_topic_digest, generate_topic_content
- `bot.py`: generate_content, generate_practice_intro, generate_question
- `engines/shared/question_handler.py`: generate_answer, answer_with_context

---

## Предстоящая работа

### 2. Локализация UI-строк (оценка: ~150 строк)

#### Приоритет 1: Критические файлы

| Файл | Оценка строк | Описание |
|------|--------------|----------|
| `engines/mode_selector.py` | ~60 | Меню выбора режима, настройки Марафона/Ленты |
| `bot.py` | ~70 | Обработчики команд, FSM, сообщения об ошибках |
| `engines/feed/handlers.py` | ~20 | Обработчики Ленты |

#### Приоритет 2: Вспомогательные файлы

| Файл | Оценка строк | Описание |
|------|--------------|----------|
| `engines/feed/engine.py` | ~10 | Сообщения о статусе Ленты |
| `cmd_start.py` | ~5 | Онбординг (частично локализован) |

---

## Архитектурные решения

### Правило: Никаких пользовательских строк в коде

**НЕЛЬЗЯ:**
```python
await message.answer("Произошла ошибка. Попробуйте ещё раз.")
```

**НУЖНО:**
```python
await message.answer(t('errors.try_again', lang))
```

### Структура ключей в locales.py

```
{category}.{subcategory}.{key}

Примеры:
- mode.select_title
- mode.marathon.activated
- mode.marathon.day_progress
- mode.feed.activated
- buttons.update_profile
- buttons.reminders
- errors.generic
- errors.not_registered
```

---

## Этапы реализации

### Этап 0: Создание глоссария (1 час)
1. Добавить `GLOSSARY` в `locales.py`
2. Добавить функцию `term(key, lang)`
3. Согласовать термины с `docs/ontology.md`
4. Ревью переводов с носителем (если возможно)

### Этап 1: Аудит (1-2 часа)
1. Сканировать `mode_selector.py` на все строки
2. Сканировать `bot.py` на FSM-сообщения и ошибки
3. Составить полный список ключей
4. Проверить соответствие терминов глоссарию

### Этап 2: Добавление ключей в locales.py (2-3 часа)
1. Добавить все новые ключи для RU
2. Перевести на EN (использовать термины из глоссария)
3. Перевести на ES (использовать термины из глоссария)

### Этап 3: Рефакторинг mode_selector.py (2-3 часа)
1. Заменить все строки на `t(key, lang)`
2. Добавить получение `lang` из профиля пользователя
3. Протестировать все сценарии

### Этап 4: Рефакторинг bot.py (3-4 часа)
1. Заменить FSM fallback-сообщения (уже частично сделано)
2. Заменить сообщения в обработчиках команд
3. Заменить сообщения об ошибках

### Этап 5: Тестирование (1-2 часа)
1. Создать тестовых пользователей для каждого языка
2. Пройти все сценарии
3. Проверить корректность отображения
4. Проверить консистентность терминов

---

## Новые ключи для locales.py

### Категория: mode (режим)

```python
# Выбор режима
'mode.select_title': 'Выберите режим обучения',
'mode.current_mode': 'Текущий режим',

# Марафон
'mode.marathon.name': 'Марафон',
'mode.marathon.desc': '14-дневный курс',
'mode.marathon.activated': 'Режим Марафон активирован!',
'mode.marathon.day_progress': 'День {day} из 14 | {completed}/28 тем',
'mode.marathon.settings_title': 'Ваши настройки',
'mode.marathon.time': 'Время',
'mode.marathon.reading_time': 'На чтение',
'mode.marathon.complexity': 'Сложность',
'mode.marathon.extra_reminder': 'Доп.напоминание',
'mode.marathon.paused_info': 'Лента на паузе. Вернуться: /mode',
'mode.marathon.completed_info': 'Вы прошли марафон!',
'mode.marathon.reset_confirm': 'Вы уверены, что хотите сбросить марафон?',
'mode.marathon.reset_done': 'Марафон сброшен',

# Лента
'mode.feed.name': 'Лента',
'mode.feed.desc': 'Бесконечный режим',
'mode.feed.activated': 'Режим Лента активирован!',
'mode.feed.your_topics': 'Ваши темы',
'mode.feed.paused_info': 'Марафон на паузе. Вернуться: /mode',
'mode.feed.no_topics': 'Темы не выбраны',
```

### Категория: buttons (кнопки)

```python
'buttons.update_profile': 'Обновить данные',
'buttons.reminders': 'Напоминания',
'buttons.reset_marathon': 'Сбросить марафон',
'buttons.back': 'Назад',
'buttons.confirm': 'Подтвердить',
'buttons.both_modes': 'Оба режима',
```

### Категория: status (статусы)

```python
'status.not_started': 'Не начат',
'status.active': 'Активен',
'status.paused': 'На паузе',
'status.completed': 'Завершён',
```

### Категория: errors (ошибки)

```python
'errors.generic': 'Произошла ошибка. Попробуйте ещё раз.',
'errors.not_registered': 'Сначала пройдите регистрацию: /start',
'errors.try_later': 'Попробуйте позже.',
```

### Категория: complexity (сложность)

```python
'complexity.beginner': 'Начальный',
'complexity.basic': 'Базовый',
'complexity.advanced': 'Продвинутый',
'complexity.level_n': 'Уровень {n}',
```

---

## Затрагиваемые сценарии

- **Сценарий 02.02**: Переключение режимов (`/mode`)
- **Сценарий 01.01**: Марафон (статус, настройки)
- **Сценарий 01.02**: Лента (статус, темы)

---

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Пропущенные строки | Средняя | Grep по кириллице после рефакторинга |
| Сломанное форматирование | Низкая | Тестирование каждого сценария |
| Контекстные переводы | Средняя | Ревью переводов носителем |

---

## Оценка трудозатрат

| Этап | Время |
|------|-------|
| Создание глоссария | 1 час |
| Аудит | 1-2 часа |
| Добавление ключей | 2-3 часа |
| mode_selector.py | 2-3 часа |
| bot.py | 3-4 часа |
| Тестирование | 1-2 часа |
| **Итого** | **10-15 часов** |

---

## Следующие шаги

1. Получить подтверждение плана от пользователя
2. Начать с Этапа 1 (аудит)
3. Реализовывать поэтапно с промежуточными коммитами

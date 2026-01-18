"""
AIST Pilot Bot — Telegram-бот для персонального обучения стажера
GitHub: https://github.com/aisystant/aist_pilot_bot

Функции:
- Онбординг с профилированием стажера
- Персонализированный контент на основе профиля
- Расписание обучения
- Отслеживание прогресса
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import aiohttp

# ============= КОНФИГУРАЦИЯ =============

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DIGITAL_TWIN_MCP_URL = os.getenv("DIGITAL_TWIN_MCP_URL", "https://digital-twin-mcp.aisystant.workers.dev/mcp")
GUIDES_MCP_URL = os.getenv("GUIDES_MCP_URL", "https://guides-mcp.aisystant.workers.dev/mcp")

# Проверка обязательных переменных
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен!")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY не установлен!")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============= КОНСТАНТЫ =============

DIFFICULTY_LEVELS = {
    "easy": {"emoji": "🌱", "name": "Начальный", "desc": "С нуля, простым языком"},
    "medium": {"emoji": "🌿", "name": "Средний", "desc": "Есть базовые знания"},
    "hard": {"emoji": "🌳", "name": "Продвинутый", "desc": "Глубокое погружение"}
}

LEARNING_STYLES = {
    "theoretical": {"emoji": "📚", "name": "Теоретик", "desc": "Сначала теория, потом практика"},
    "practical": {"emoji": "🔧", "name": "Практик", "desc": "Учусь на примерах и задачах"},
    "mixed": {"emoji": "⚖️", "name": "Смешанный", "desc": "Баланс теории и практики"}
}

EXPERIENCE_LEVELS = {
    "student": {"emoji": "🎓", "name": "Студент", "desc": "Учусь или недавно закончил"},
    "junior": {"emoji": "🌱", "name": "Junior", "desc": "0-2 года опыта"},
    "middle": {"emoji": "💼", "name": "Middle", "desc": "2-5 лет опыта"},
    "senior": {"emoji": "⭐", "name": "Senior", "desc": "5+ лет опыта"},
    "switching": {"emoji": "🔄", "name": "Меняю сферу", "desc": "Перехожу из другой области"}
}

# ============= СОСТОЯНИЯ FSM =============

class OnboardingStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_role = State()
    waiting_for_domain = State()
    waiting_for_interests = State()
    waiting_for_experience = State()
    waiting_for_difficulty = State()
    waiting_for_learning_style = State()
    waiting_for_goals = State()
    waiting_for_schedule = State()
    confirming_profile = State()

class LearningStates(StatesGroup):
    waiting_for_answer = State()

# ============= ХРАНИЛИЩЕ (в памяти, для продакшена замените на БД) =============

interns_db = {}

class InternProfile:
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.registered = False
        self.onboarding_completed = False
        self.name = ""
        self.role = ""
        self.domain = ""
        self.interests = []
        self.experience_level = ""
        self.difficulty_preference = ""
        self.learning_style = ""
        self.goals = ""
        self.schedule_time = "09:00"
        self.current_topic_index = 0
        self.completed_topics = []
        self.current_question = None

    def to_dict(self):
        return self.__dict__.copy()

    def get_personalization_prompt(self) -> str:
        diff = DIFFICULTY_LEVELS.get(self.difficulty_preference, {})
        style = LEARNING_STYLES.get(self.learning_style, {})
        exp = EXPERIENCE_LEVELS.get(self.experience_level, {})
        
        return f"""
ПРОФИЛЬ СТАЖЕРА:
- Имя: {self.name}
- Роль: {self.role}
- Предметная область: {self.domain}
- Интересы: {', '.join(self.interests) if self.interests else 'не указаны'}
- Уровень опыта: {exp.get('name', '')} ({exp.get('desc', '')})
- Желаемая сложность: {diff.get('name', '')} ({diff.get('desc', '')})
- Стиль обучения: {style.get('name', '')} ({style.get('desc', '')})
- Цели: {self.goals}

ИНСТРУКЦИИ:
1. Используй примеры из области "{self.domain}" и интересов стажера
2. Адаптируй сложность под уровень "{diff.get('name', 'средний')}"
3. {'Начинай с теории' if self.learning_style == 'theoretical' else 'Начинай с практических примеров' if self.learning_style == 'practical' else 'Чередуй теорию и практику'}
"""

def get_intern(chat_id: int) -> InternProfile:
    if chat_id not in interns_db:
        interns_db[chat_id] = InternProfile(chat_id)
    return interns_db[chat_id]

# ============= CLAUDE API КЛИЕНТ =============

class ClaudeClient:
    def __init__(self):
        self.api_key = ANTHROPIC_API_KEY
        self.base_url = "https://api.anthropic.com/v1/messages"

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4000,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}]
            }
            
            try:
                async with session.post(self.base_url, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["content"][0]["text"]
                    else:
                        error = await resp.text()
                        logger.error(f"Claude API error: {error}")
                        return None
            except Exception as e:
                logger.error(f"Claude API exception: {e}")
                return None

    async def generate_content(self, topic: dict, intern: InternProfile) -> str:
        system_prompt = f"""Ты — персональный наставник.
{intern.get_personalization_prompt()}

Создай текст на 20 минут чтения (~2000 слов). Без заголовков, только абзацы."""

        user_prompt = f"""Тема: {topic.get('title')}
Основное понятие: {topic.get('main_concept')}
Связанные понятия: {', '.join(topic.get('related_concepts', []))}"""

        result = await self.generate(system_prompt, user_prompt)
        return result or "Не удалось сгенерировать контент. Попробуйте /learn ещё раз."

    async def generate_question(self, topic: dict, intern: InternProfile) -> str:
        system_prompt = f"""Создай один вопрос для проверки понимания темы.
{intern.get_personalization_prompt()}
Вопрос должен требовать развёрнутого ответа и быть связан с областью стажера."""

        user_prompt = f"""Тема: {topic.get('title')}
Понятие: {topic.get('main_concept')}"""

        result = await self.generate(system_prompt, user_prompt)
        return result or "Что ты понял из этой темы? Приведи пример из своей практики."

claude = ClaudeClient()

# ============= ТЕМЫ (заглушка, в реальности из MCP) =============

TOPICS = [
    {
        "id": "what-is-system",
        "section": "Системное мышление",
        "subsection": "Основы",
        "title": "Что такое система",
        "main_concept": "система",
        "related_concepts": ["элементы", "связи", "эмерджентность"]
    },
    {
        "id": "system-approach",
        "section": "Системное мышление",
        "subsection": "Основы",
        "title": "Системный подход",
        "main_concept": "системный подход",
        "related_concepts": ["редукционизм", "холизм", "анализ"]
    },
    {
        "id": "system-boundaries",
        "section": "Системное мышление",
        "subsection": "Основы",
        "title": "Границы системы",
        "main_concept": "границы системы",
        "related_concepts": ["окружение", "интерфейс", "контекст"]
    }
]

def get_topic(index: int) -> Optional[dict]:
    return TOPICS[index] if index < len(TOPICS) else None

# ============= КЛАВИАТУРЫ =============

def kb_experience() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{v['emoji']} {v['name']}", callback_data=f"exp_{k}")]
        for k, v in EXPERIENCE_LEVELS.items()
    ])

def kb_difficulty() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{v['emoji']} {v['name']}", callback_data=f"diff_{k}")]
        for k, v in DIFFICULTY_LEVELS.items()
    ])

def kb_learning_style() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{v['emoji']} {v['name']}", callback_data=f"style_{k}")]
        for k, v in LEARNING_STYLES.items()
    ])

def kb_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Всё верно", callback_data="confirm"),
            InlineKeyboardButton(text="🔄 Заново", callback_data="restart")
        ]
    ])

def kb_learn() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать изучение", callback_data="learn")],
        [InlineKeyboardButton(text="⏭ Позже", callback_data="later")]
    ])

def progress_bar(completed: int, total: int) -> str:
    pct = int((completed / total) * 100) if total > 0 else 0
    return f"{'█' * (pct // 10)}{'░' * (10 - pct // 10)} {pct}%"

# ============= РОУТЕР =============

router = Router()

# --- Онбординг ---

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    intern = get_intern(message.chat.id)
    
    if intern.onboarding_completed:
        await message.answer(
            f"👋 С возвращением, {intern.name}!\n\n"
            f"/learn — продолжить обучение\n"
            f"/progress — статистика\n"
            f"/profile — твой профиль"
        )
        return
    
    await message.answer(
        "👋 Привет! Я помощник для персонального обучения.\n\n"
        "Задам несколько вопросов, чтобы адаптировать материал под тебя (~2 мин).\n\n"
        "Как тебя зовут?"
    )
    await state.set_state(OnboardingStates.waiting_for_name)

@router.message(OnboardingStates.waiting_for_name)
async def on_name(message: Message, state: FSMContext):
    intern = get_intern(message.chat.id)
    intern.name = message.text.strip()
    await message.answer(f"Приятно познакомиться, {intern.name}! 👋\n\nКем ты работаешь или учишься?")
    await state.set_state(OnboardingStates.waiting_for_role)

@router.message(OnboardingStates.waiting_for_role)
async def on_role(message: Message, state: FSMContext):
    intern = get_intern(message.chat.id)
    intern.role = message.text.strip()
    await message.answer("В какой предметной области работаешь?\n\nНапример: IT, маркетинг, финансы, дизайн")
    await state.set_state(OnboardingStates.waiting_for_domain)

@router.message(OnboardingStates.waiting_for_domain)
async def on_domain(message: Message, state: FSMContext):
    intern = get_intern(message.chat.id)
    intern.domain = message.text.strip()
    await message.answer("Расскажи о своих интересах/хобби?\n\nЭто поможет приводить близкие тебе примеры.")
    await state.set_state(OnboardingStates.waiting_for_interests)

@router.message(OnboardingStates.waiting_for_interests)
async def on_interests(message: Message, state: FSMContext):
    intern = get_intern(message.chat.id)
    intern.interests = [i.strip() for i in message.text.replace(',', ';').split(';') if i.strip()]
    await message.answer("Какой у тебя уровень опыта?", reply_markup=kb_experience())
    await state.set_state(OnboardingStates.waiting_for_experience)

@router.callback_query(OnboardingStates.waiting_for_experience, F.data.startswith("exp_"))
async def on_experience(callback: CallbackQuery, state: FSMContext):
    intern = get_intern(callback.message.chat.id)
    intern.experience_level = callback.data.replace("exp_", "")
    await callback.answer()
    await callback.message.edit_text("Какую сложность материала предпочитаешь?", reply_markup=kb_difficulty())
    await state.set_state(OnboardingStates.waiting_for_difficulty)

@router.callback_query(OnboardingStates.waiting_for_difficulty, F.data.startswith("diff_"))
async def on_difficulty(callback: CallbackQuery, state: FSMContext):
    intern = get_intern(callback.message.chat.id)
    intern.difficulty_preference = callback.data.replace("diff_", "")
    await callback.answer()
    await callback.message.edit_text("Как тебе комфортнее учиться?", reply_markup=kb_learning_style())
    await state.set_state(OnboardingStates.waiting_for_learning_style)

@router.callback_query(OnboardingStates.waiting_for_learning_style, F.data.startswith("style_"))
async def on_style(callback: CallbackQuery, state: FSMContext):
    intern = get_intern(callback.message.chat.id)
    intern.learning_style = callback.data.replace("style_", "")
    await callback.answer()
    await callback.message.edit_text("✅ Принято!")
    await callback.message.answer("Какие цели обучения? Чего хочешь достичь?")
    await state.set_state(OnboardingStates.waiting_for_goals)

@router.message(OnboardingStates.waiting_for_goals)
async def on_goals(message: Message, state: FSMContext):
    intern = get_intern(message.chat.id)
    intern.goals = message.text.strip()
    await message.answer("Когда отправлять материал?\n\nНапиши время (например: 09:00)")
    await state.set_state(OnboardingStates.waiting_for_schedule)

@router.message(OnboardingStates.waiting_for_schedule)
async def on_schedule(message: Message, state: FSMContext):
    try:
        h, m = map(int, message.text.strip().split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except:
        await message.answer("Формат: ЧЧ:ММ (например 09:00)")
        return
    
    intern = get_intern(message.chat.id)
    intern.schedule_time = message.text.strip()
    
    exp = EXPERIENCE_LEVELS.get(intern.experience_level, {})
    diff = DIFFICULTY_LEVELS.get(intern.difficulty_preference, {})
    style = LEARNING_STYLES.get(intern.learning_style, {})
    
    await message.answer(
        f"📋 *Твой профиль:*\n\n"
        f"👤 {intern.name}\n"
        f"💼 {intern.role}\n"
        f"🎯 {intern.domain}\n"
        f"🎨 {', '.join(intern.interests)}\n\n"
        f"{exp.get('emoji','')} {exp.get('name','')}\n"
        f"{diff.get('emoji','')} {diff.get('name','')}\n"
        f"{style.get('emoji','')} {style.get('name','')}\n\n"
        f"🎯 {intern.goals}\n"
        f"⏰ {intern.schedule_time}\n\n"
        f"Всё верно?",
        parse_mode="Markdown",
        reply_markup=kb_confirm()
    )
    await state.set_state(OnboardingStates.confirming_profile)

@router.callback_query(OnboardingStates.confirming_profile, F.data == "confirm")
async def on_confirm(callback: CallbackQuery, state: FSMContext):
    intern = get_intern(callback.message.chat.id)
    intern.registered = True
    intern.onboarding_completed = True
    
    await schedule_daily(callback.message.chat.id, intern.schedule_time)
    
    await callback.answer("Сохранено!")
    await callback.message.edit_text(
        f"✅ *Готово!*\n\n"
        f"Буду отправлять материал в *{intern.schedule_time}*\n\n"
        f"• 20 мин — изучение\n"
        f"• 5 мин — ответ на вопрос\n"
        f"• Ответил = тема засчитана ✅\n\n"
        f"Начнём?",
        parse_mode="Markdown",
        reply_markup=kb_learn()
    )
    await state.clear()

@router.callback_query(OnboardingStates.confirming_profile, F.data == "restart")
async def on_restart(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("Давай заново!\n\nКак тебя зовут?")
    await state.set_state(OnboardingStates.waiting_for_name)

# --- Обучение ---

@router.message(Command("learn"))
async def cmd_learn(message: Message, state: FSMContext):
    intern = get_intern(message.chat.id)
    if not intern.onboarding_completed:
        await message.answer("Сначала /start")
        return
    await send_topic(message.chat.id, state, message.bot)

@router.callback_query(F.data == "learn")
async def cb_learn(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_reply_markup()
    await send_topic(callback.message.chat.id, state, callback.bot)

@router.callback_query(F.data == "later")
async def cb_later(callback: CallbackQuery):
    intern = get_intern(callback.message.chat.id)
    await callback.answer()
    await callback.message.edit_text(f"Жду тебя в {intern.schedule_time}! Или /learn")

@router.message(Command("progress"))
async def cmd_progress(message: Message):
    intern = get_intern(message.chat.id)
    if not intern.onboarding_completed:
        await message.answer("Сначала /start")
        return
    
    done = len(intern.completed_topics)
    total = len(TOPICS)
    await message.answer(
        f"📊 *{intern.name}*\n\n"
        f"✅ {done} из {total} тем\n"
        f"{progress_bar(done, total)}\n\n"
        f"/learn — продолжить",
        parse_mode="Markdown"
    )

@router.message(Command("profile"))
async def cmd_profile(message: Message):
    intern = get_intern(message.chat.id)
    if not intern.onboarding_completed:
        await message.answer("Сначала /start")
        return
    
    exp = EXPERIENCE_LEVELS.get(intern.experience_level, {})
    diff = DIFFICULTY_LEVELS.get(intern.difficulty_preference, {})
    style = LEARNING_STYLES.get(intern.learning_style, {})
    
    await message.answer(
        f"👤 *{intern.name}*\n"
        f"💼 {intern.role}\n"
        f"🎯 {intern.domain}\n"
        f"🎨 {', '.join(intern.interests)}\n\n"
        f"{exp.get('emoji','')} {exp.get('name','')}\n"
        f"{diff.get('emoji','')} {diff.get('name','')}\n"
        f"{style.get('emoji','')} {style.get('name','')}\n\n"
        f"⏰ Обучение в {intern.schedule_time}",
        parse_mode="Markdown"
    )

@router.message(LearningStates.waiting_for_answer)
async def on_answer(message: Message, state: FSMContext):
    intern = get_intern(message.chat.id)
    
    if len(message.text.strip()) < 20:
        await message.answer("Напиши подробнее (хотя бы 2-3 предложения)")
        return
    
    intern.completed_topics.append(intern.current_topic_index)
    intern.current_topic_index += 1
    intern.current_question = None
    
    done = len(intern.completed_topics)
    total = len(TOPICS)
    
    await message.answer(
        f"✅ *Тема засчитана!*\n\n"
        f"{progress_bar(done, total)}\n\n"
        f"/learn — следующая тема",
        parse_mode="Markdown"
    )
    await state.clear()

# --- Отправка темы ---

async def send_topic(chat_id: int, state: FSMContext, bot: Bot):
    intern = get_intern(chat_id)
    topic = get_topic(intern.current_topic_index)
    
    if not topic:
        await bot.send_message(chat_id, "🎉 Все темы пройдены!")
        return
    
    await bot.send_message(chat_id, "⏳ Генерирую персональный материал...")
    
    content = await claude.generate_content(topic, intern)
    question = await claude.generate_question(topic, intern)
    
    header = (
        f"📚 *{topic['section']}* → {topic['subsection']}\n\n"
        f"*{topic['title']}*\n"
        f"⏱ 20 минут\n{'─'*25}\n\n"
    )
    
    # Разбиваем на части если длинный
    full = header + content
    if len(full) > 4000:
        await bot.send_message(chat_id, header, parse_mode="Markdown")
        for i in range(0, len(content), 4000):
            await bot.send_message(chat_id, content[i:i+4000])
    else:
        await bot.send_message(chat_id, full, parse_mode="Markdown")
    
    await bot.send_message(
        chat_id,
        f"{'─'*25}\n\n❓ *Вопрос:*\n\n{question}\n\n⏱ 5 минут\nНапиши ответ 👇",
        parse_mode="Markdown"
    )
    
    intern.current_question = topic
    await state.set_state(LearningStates.waiting_for_answer)

# ============= ПЛАНИРОВЩИК =============

scheduler = AsyncIOScheduler()

async def schedule_daily(chat_id: int, time_str: str):
    h, m = map(int, time_str.split(":"))
    job_id = f"daily_{chat_id}"
    
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    scheduler.add_job(
        send_reminder,
        CronTrigger(hour=h, minute=m),
        args=[chat_id],
        id=job_id
    )
    logger.info(f"Scheduled {chat_id} at {time_str}")

async def send_reminder(chat_id: int):
    bot = Bot(token=BOT_TOKEN)
    intern = get_intern(chat_id)
    await bot.send_message(
        chat_id,
        f"⏰ *{intern.schedule_time}* — время учиться, {intern.name}!",
        parse_mode="Markdown",
        reply_markup=kb_learn()
    )
    await bot.session.close()

# ============= ЗАПУСК =============

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    scheduler.start()
    
    logger.info("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

"""Telegram interface for IT Navigator KZ (aiogram 3)."""
import asyncio
import logging
import os
from html import escape
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import core
import storage

load_dotenv(Path(__file__).parent/'.env')
TOKEN=os.getenv('BOT_TOKEN','').strip()
ADMIN_IDS={int(x.strip()) for x in os.getenv('ADMIN_IDS','').split(',') if x.strip().isdigit()}
router=Router()
class Quiz(StatesGroup):
    answering=State()
class Interview(StatesGroup):
    answering=State()
def menu():
    kb=InlineKeyboardBuilder()
    for label,key in [('🎯 Пройти тест','startquiz'),('🗺 Моя дорожная карта','roadmap'),('🎓 Вузы Казахстана','universities'),('🎤 Тренажёр собеседования','interview'),('⭐ Оценить бота','feedback'),('🔐 Мои данные','privacy')]:
        kb.button(text=label,callback_data=key)
    kb.adjust(1)
    return kb.as_markup()
async def send_menu(message):
    await message.answer('🇰🇿 <b>IT Navigator KZ</b>\nПрофориентационный школьный проект. Тест из 15 вопросов поможет исследовать интересы в IT. Результат не определяет профессию окончательно.',parse_mode='HTML',reply_markup=menu())
@router.message(CommandStart())
@router.message(Command('help','menu'))
async def start(message:Message,state:FSMContext):
    await state.clear()
    await send_menu(message)
async def question(message,state):
    data=await state.get_data()
    index=data['index']
    if index>=len(core.QUESTIONS):
        scores=core.scores_for(data['answers'])
        track=core.winning_track(scores)
        storage.save_result(data['user_id'],track,scores)
        await state.clear()
        await message.answer('✅ <b>Результат теста</b>\n'+core.roadmap(track)+'\n\nБаллы: '+', '.join(f'{core.TRACKS[k]} — {scores[k]}' for k in core.KEYS),parse_mode='HTML',reply_markup=menu())
        return
    title,options=core.QUESTIONS[index]
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=opt,callback_data=f'a:{index}:{key}')] for key,opt in zip(core.KEYS,options)])
    await message.answer(f'<b>Вопрос {index+1}/15</b>\n\n{escape(title)}',parse_mode='HTML',reply_markup=kb)
@router.callback_query(F.data=='startquiz')
async def startquiz(c:CallbackQuery,state:FSMContext):
    await c.answer()
    await state.clear()
    await state.set_state(Quiz.answering)
    await state.update_data(index=0,answers=[],user_id=c.from_user.id)
    await question(c.message,state)
@router.callback_query(Quiz.answering,F.data.startswith('a:'))
async def answer(c:CallbackQuery,state:FSMContext):
    data=await state.get_data()
    try:
        _,raw_index,key=c.data.split(':')
        index=int(raw_index)
    except (ValueError,AttributeError):
        return await c.answer('Некорректный ответ',show_alert=True)
    if index!=data.get('index') or key not in core.KEYS:
        return await c.answer('Это старый вопрос. Используй последний.',show_alert=True)
    await c.answer()
    await c.message.edit_reply_markup(reply_markup=None)
    await state.update_data(index=index+1,answers=data['answers']+[key])
    await question(c.message,state)
@router.callback_query(F.data=='roadmap')
async def my_roadmap(c:CallbackQuery):
    await c.answer()
    saved=storage.latest_result(c.from_user.id)
    await c.message.answer(core.roadmap(saved[0]) if saved else 'Сначала пройди профориентационный тест.',parse_mode='HTML',reply_markup=menu())
@router.callback_query(F.data=='universities')
async def universities(c:CallbackQuery):
    await c.answer()
    content='🎓 <b>Университеты Казахстана</b>\n\n'+'\n'.join(f'• <a href="{url}">{escape(name)}</a>' for name,url in core.UNIVERSITIES)
    await c.message.answer(content+'\n\nПроверяй актуальные образовательные программы, профильные предметы ЕНТ и гранты на официальных сайтах.',parse_mode='HTML',reply_markup=menu())
@router.callback_query(F.data=='interview')
async def interview(c:CallbackQuery,state:FSMContext):
    await c.answer()
    await state.clear()
    await state.set_state(Interview.answering)
    await state.update_data(interview_index=0)
    await ask_interview(c.message,0)
async def ask_interview(message,index):
    question_text=core.INTERVIEW[index][0]
    await message.answer(f'🎤 <b>Вопрос {index+1}/{len(core.INTERVIEW)}</b>\n{escape(question_text)}\n\nНапиши ответ своими словами. Бот покажет образец для самопроверки.',parse_mode='HTML')
@router.message(Interview.answering,F.text)
async def interview_answer(m:Message,state:FSMContext):
    data=await state.get_data()
    idx=data['interview_index']
    await m.answer('📘 <b>Пример ответа:</b> '+escape(core.INTERVIEW[idx][1]),parse_mode='HTML')
    if idx+1>=len(core.INTERVIEW):
        await state.clear()
        await m.answer('Тренировка завершена! Сравни свои ответы с образцами. Автоматическая оценка пока не реализована.',reply_markup=menu())
    else:
        await state.update_data(interview_index=idx+1)
        await ask_interview(m,idx+1)
@router.callback_query(F.data=='feedback')
async def feedback(c:CallbackQuery):
    await c.answer()
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'{i} ⭐',callback_data=f'rate:{i}') for i in range(1,6)]])
    await c.message.answer('Оцени полезность бота от 1 до 5:',reply_markup=kb)
@router.callback_query(F.data.startswith('rate:'))
async def rate(c:CallbackQuery):
    try: stars=int(c.data.split(':')[1])
    except (ValueError,IndexError): return await c.answer('Ошибка',show_alert=True)
    if not 1<=stars<=5: return await c.answer('Ошибка',show_alert=True)
    storage.save_feedback(c.from_user.id,stars)
    await c.answer('Спасибо!')
    await c.message.edit_text('Спасибо за оценку!')
@router.callback_query(F.data=='privacy')
async def privacy(c:CallbackQuery):
    await c.answer()
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🗑 Удалить мои данные',callback_data='eraseask')],[InlineKeyboardButton(text='↩️ Меню',callback_data='home')]])
    await c.message.answer('🔐 Бот сохраняет только Telegram ID, итог теста и, если поставлена, оценку. Имя, телефон, школа и ответы по отдельным вопросам в базе не сохраняются. Участие добровольное. Данные можно удалить.',reply_markup=kb)
@router.callback_query(F.data=='eraseask')
async def eraseask(c:CallbackQuery):
    await c.answer()
    await c.message.answer('Точно удалить результат и оценку?',reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Да, удалить',callback_data='eraseyes'),InlineKeyboardButton(text='Отмена',callback_data='home')]]))
@router.callback_query(F.data=='eraseyes')
async def eraseyes(c:CallbackQuery,state:FSMContext):
    storage.erase(c.from_user.id)
    await state.clear()
    await c.answer('Удалено')
    await c.message.edit_text('Твои данные удалены из базы бота.')
@router.callback_query(F.data=='home')
async def home(c:CallbackQuery,state:FSMContext):
    await c.answer()
    await state.clear()
    await send_menu(c.message)
@router.message(Command('stats'))
async def stats(m:Message):
    if m.from_user.id not in ADMIN_IDS:
        return await m.answer('Команда доступна только координатору проекта.')
    total,counts,n,avg=storage.summary()
    lines=['📊 <b>Обезличенная статистика</b>',f'Участников: {total}']
    lines.extend(f'{core.TRACKS[k]}: {counts.get(k,0)}' for k in core.KEYS)
    lines.append(f'Оценок: {n}; средний балл: {avg:.1f}' if avg is not None else 'Оценок пока нет')
    await m.answer('\n'.join(lines),parse_mode='HTML')
@router.message()
async def other(m:Message):
    await m.answer('Для начала работы нажми /start. Для прерывания тренировки тоже используй /start.')
async def main():
    if not TOKEN or ':' not in TOKEN:
        raise SystemExit('Укажи BOT_TOKEN в файле .env (см. README.md)')
    logging.basicConfig(level=logging.INFO)
    with storage.database(): pass
    bot=Bot(token=TOKEN)
    dp=Dispatcher()
    dp.include_router(router)
    try: await dp.start_polling(bot)
    finally: await bot.session.close()
if __name__=='__main__':
    asyncio.run(main())

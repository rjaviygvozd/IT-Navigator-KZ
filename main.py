"""Telegram interface for IT Navigator KZ (aiogram 3)."""
import hashlib
import logging
import os
from html import escape
from pathlib import Path
from dotenv import load_dotenv
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import core
import storage
import professions
import interview_quizzes

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
    for label,key in [('🎯 Пройти тест','startquiz'),('🗺 Моя дорожная карта','roadmap'),('🧭 Каталог IT-профессий','professions'),('🎓 Вузы Казахстана','universities'),('🎤 Тренажёр собеседования','interview'),('⭐ Оценить бота','feedback'),('🔐 Мои данные','privacy')]:
        kb.button(text=label,callback_data=key)
    kb.adjust(1)
    return kb.as_markup()
async def send_menu(message):
    await message.answer('🇰🇿 <b>IT Navigator KZ</b>\nПрофориентационный школьный проект. Тест из 7 ситуационных вопросов поможет исследовать интересы в IT. Результат не определяет профессию окончательно.',parse_mode='HTML',reply_markup=menu())
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
        await message.answer('✅ <b>Результат теста</b>\n'+core.result_explanation(scores)+'\n\n'+core.extended_roadmap(track)+'\n\nБаллы: '+', '.join(f'{core.TRACKS[k]} — {scores[k]}' for k in core.KEYS),parse_mode='HTML',reply_markup=menu())
        return
    title,options=core.QUESTIONS[index]
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=opt,callback_data=f'a:{index}:{key}')] for key,opt in zip(core.KEYS,options)])
    await message.answer(f'<b>Вопрос {index+1}/{len(core.QUESTIONS)}</b>\n\n{escape(title)}',parse_mode='HTML',reply_markup=kb)
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
    await c.message.answer(core.extended_roadmap(saved[0]) if saved else 'Сначала пройди профориентационный тест.',parse_mode='HTML',reply_markup=menu())
@router.callback_query(F.data=='professions')
async def profession_categories(c:CallbackQuery):
    await c.answer()
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=core.TRACKS[k],callback_data=f'prof:{k}')] for k in core.KEYS])
    await c.message.answer('🧭 Выбери интересующую сферу:',reply_markup=kb)
@router.callback_query(F.data.startswith('prof:'))
async def profession_track(c:CallbackQuery):
    await c.answer()
    key=c.data.split(':',1)[1]
    if key not in core.KEYS:
        return
    await c.message.answer(professions.format_track(key),parse_mode='HTML',reply_markup=menu())
@router.callback_query(F.data=='universities')
async def universities(c:CallbackQuery):
    await c.answer()
    content='🎓 <b>Университеты Казахстана</b>\n\n'+'\n'.join(f'• <a href="{url}">{escape(name)}</a>' for name,url in core.UNIVERSITIES)
    await c.message.answer(content+'\n\nПроверяй актуальные образовательные программы, профильные предметы ЕНТ и гранты на официальных сайтах.',parse_mode='HTML',reply_markup=menu())
@router.callback_query(F.data=='interview')
async def interview(c:CallbackQuery,state:FSMContext):
    await c.answer()
    await state.clear()
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=core.TRACKS[k],callback_data=f'intstart:{k}')] for k in core.KEYS])
    await c.message.answer('🎤 Выбери направление собеседования:',reply_markup=kb)

@router.callback_query(F.data.startswith('intstart:'))
async def interview_start(c:CallbackQuery,state:FSMContext):
    await c.answer()
    key=c.data.split(':',1)[1]
    if key not in interview_quizzes.QUIZZES:
        return
    await state.set_state(Interview.answering)
    await state.update_data(interview_track=key,interview_index=0,interview_points=0)
    await ask_interview(c.message,key,0)

async def ask_interview(message,key,index):
    title,options,correct=interview_quizzes.QUIZZES[key][index]
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'{chr(1040+i)}) {option}',callback_data=f'intanswer:{index}:{i}')] for i,option in enumerate(options)])
    await message.answer(f'🎤 <b>Вопрос {index+1}/5</b>\n{escape(title)}',parse_mode='HTML',reply_markup=kb)

@router.callback_query(Interview.answering,F.data.startswith('intanswer:'))
async def interview_answer(c:CallbackQuery,state:FSMContext):
    data=await state.get_data()
    try:
        _,raw_index,raw_choice=c.data.split(':')
        index,choice=int(raw_index),int(raw_choice)
    except (ValueError,AttributeError):
        return await c.answer('Некорректный ответ')
    if index!=data.get('interview_index') or choice not in (0,1,2):
        return await c.answer('Это старый вопрос')
    await c.answer()
    key=data['interview_track']
    title,options,correct=interview_quizzes.QUIZZES[key][index]
    points=data['interview_points']+int(choice==correct)
    await c.message.edit_reply_markup(reply_markup=None)
    await c.message.answer(('✅ Верно!' if choice==correct else '❌ Пока неверно.')+'\nПравильный ответ: '+options[correct])
    if index==4:
        await state.clear()
        await c.message.answer(f'🎓 <b>Результат: {points}/5</b>\n'+('Отличная работа!' if points>=4 else 'Повтори темы и попробуй ещё раз.'),parse_mode='HTML',reply_markup=menu())
    else:
        await state.update_data(interview_index=index+1,interview_points=points)
        await ask_interview(c.message,key,index+1)

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
@router.message(Command('myid'))
async def myid(m:Message):
    await m.answer(f'Твой Telegram ID: <code>{m.from_user.id}</code>\nПередавать его можно только координатору проекта для настройки доступа к обезличенной статистике.',parse_mode='HTML')

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
WEBHOOK_PATH = '/telegram/webhook'
WEBHOOK_URL = os.getenv('WEBHOOK_BASE_URL','https://it-navigator-kz-school6.onrender.com').rstrip('/') + WEBHOOK_PATH

async def configure_webhook(bot: Bot):
    secret=hashlib.sha256(TOKEN.encode('utf-8')).hexdigest()
    await bot.set_webhook(WEBHOOK_URL, secret_token=secret, allowed_updates=['message','callback_query'], drop_pending_updates=False)
    logging.info('Webhook configured at %s', WEBHOOK_URL)

async def healthcheck(request):
    return web.Response(text='IT Navigator KZ online',content_type='text/plain')

def main():
    if not TOKEN or ':' not in TOKEN:
        raise SystemExit('Укажи BOT_TOKEN в переменных окружения.')
    logging.basicConfig(level=logging.INFO)
    with storage.database(): pass
    bot=Bot(token=TOKEN)
    dp=Dispatcher()
    dp.include_router(router)
    dp.startup.register(configure_webhook)
    app=web.Application()
    secret=hashlib.sha256(TOKEN.encode('utf-8')).hexdigest()
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=secret).register(app, path=WEBHOOK_PATH)
    app.router.add_get('/',healthcheck)
    app.router.add_get('/health',healthcheck)
    setup_application(app,dp,bot=bot)
    web.run_app(app,host='0.0.0.0',port=int(os.environ.get('PORT','10000')))

if __name__=='__main__':
    main()

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
import ecosystem

load_dotenv(Path(__file__).parent/'.env')
TOKEN=os.getenv('BOT_TOKEN','').strip()
ADMIN_IDS={int(x.strip()) for x in os.getenv('ADMIN_IDS','').split(',') if x.strip().isdigit()}
router=Router()
class Quiz(StatesGroup):
    answering=State()
class Interview(StatesGroup):
    answering=State()
def home_button():
    return InlineKeyboardButton(text='🏠 Главное меню',callback_data='home')

def with_home(rows):
    return InlineKeyboardMarkup(inline_keyboard=[*rows,[home_button()]])

def menu():
    kb=InlineKeyboardBuilder()
    for label,key in [('🎯 Пройти тест','startquiz'),('🗺 Моя дорожная карта','roadmap'),('🧭 Каталог IT-профессий','professions'),('🇰🇿 Вузы, компании и возможности','ecosystem'),('🎤 Тренажёр собеседования','interview'),('⭐ Оценить бота','feedback'),('🔐 Мои данные','privacy'),('ℹ️ О проекте','aboutproject')]:
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
    kb=with_home([[InlineKeyboardButton(text=opt,callback_data=f'a:{index}:{key}')] for key,opt in zip(core.KEYS,options)])
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
@router.callback_query(F.data=='aboutproject')
async def about_project(c:CallbackQuery):
    await c.answer()
    await c.message.answer(
        'ℹ️ <b>О проекте IT Navigator KZ</b>\n\n'
        'Учебный Telegram-бот для знакомства школьников 9–11 классов с IT-направлениями Казахстана.\n\n'
        '🎯 7 ситуационных вопросов и 4 направления интересов.\n'
        '🗺 Персональная дорожная карта на 1–3 месяца, 6–12 месяцев и 1–3 года.\n'
        '🎓 Вузы, компании, гранты, сообщества и события.\n'
        '🎤 Четыре тренажёра собеседования по 5 вопросов с обратной связью.\n'
        '📊 Обезличенная статистика для координатора.\n\n'
        '<b>Важно:</b> тест не является психологической диагностикой, '
        'не гарантирует поступления или трудоустройства. '
        'Сроки, гранты, программы и стажировки проверяются у организаторов. '
        'Ответы учащихся по отдельным вопросам не сохраняются.',
        parse_mode='HTML',reply_markup=with_home([])
    )

@router.message(Command('project'))
async def project_command(m:Message):
    await m.answer('ℹ️ Описание проекта можно открыть в главном меню — кнопка «О проекте».',reply_markup=with_home([]))

@router.callback_query(F.data=='roadmap')
async def my_roadmap(c:CallbackQuery):
    await c.answer()
    saved=storage.latest_result(c.from_user.id)
    await c.message.answer(core.extended_roadmap(saved[0]) if saved else 'Сначала пройди профориентационный тест.',parse_mode='HTML',reply_markup=menu())
@router.callback_query(F.data=='professions')
async def profession_categories(c:CallbackQuery):
    await c.answer()
    kb=with_home([[InlineKeyboardButton(text=core.TRACKS[k],callback_data=f'prof:{k}')] for k in core.KEYS])
    await c.message.answer('🧭 Выбери интересующую сферу:',reply_markup=kb)
@router.callback_query(F.data.startswith('prof:'))
async def profession_track(c:CallbackQuery):
    await c.answer()
    key=c.data.split(':',1)[1]
    if key not in core.KEYS:
        return
    await c.message.answer(professions.format_track(key),parse_mode='HTML',reply_markup=menu())
@router.callback_query(F.data=='ecosystem')
@router.callback_query(F.data=='universities')
async def eco_menu(c:CallbackQuery):
    await c.answer()
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label,callback_data=f'ecocat:{key}')] for label,key in ecosystem.categories()])
    kb.inline_keyboard.append([InlineKeyboardButton(text='🏠 Главное меню',callback_data='home')])
    await c.message.answer('🇰🇿 <b>IT-возможности Казахстана</b>\nВыбери раздел. Сведения о баллах ЕНТ, грантах и стажировках проверяй на официальных сайтах.',parse_mode='HTML',reply_markup=kb)

@router.callback_query(F.data.startswith('ecocat:'))
async def eco_category(c:CallbackQuery):
    await c.answer()
    key=c.data.split(':',1)[1]
    if key not in ecosystem.CATALOG:
        return
    if key=='unis':
        kb=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🏙 Алматы',callback_data='ecopage:unis:Алматы:0')],
            [InlineKeyboardButton(text='🏙 Астана',callback_data='ecopage:unis:Астана:0')],
            [InlineKeyboardButton(text='🌍 Все города',callback_data='ecopage:unis:Все:0')],
            [InlineKeyboardButton(text='🧭 По IT-направлению',callback_data='unifilters')],
            [InlineKeyboardButton(text='⚖ Сравнить вузы',callback_data='unicompare')],
            [InlineKeyboardButton(text='⭐ Моё избранное',callback_data='unifavs')],
            [InlineKeyboardButton(text='📚 Разделы',callback_data='ecosystem'),InlineKeyboardButton(text='🏠 Меню',callback_data='home')]])
        await c.message.answer('Выбери город:',reply_markup=kb)
    elif key=='companies':
        kb=with_home([[InlineKeyboardButton(text='🧭 По IT-направлению',callback_data='companytracks')],[InlineKeyboardButton(text='💻 По технологиям',callback_data='companytechnologies')],[InlineKeyboardButton(text='🎓 Стажировки и карьера',callback_data='companycareers')],[InlineKeyboardButton(text='📋 Все компании',callback_data='ecopage:companies:Все:0')],[InlineKeyboardButton(text='📚 Разделы',callback_data='ecosystem')]])
        await c.message.answer('🏢 Выбери способ поиска компаний:',reply_markup=kb)
    else:
        await show_ecosystem(c.message,key,'Все',0)

async def show_ecosystem(message,key,city,page):
    rows=ecosystem.rows(key,city)
    n=3
    page=max(0,min(page,max(0,(len(rows)-1)//n)))
    items=rows[page*n:(page+1)*n]
    labels=dict((key,label) for label,key in ecosystem.categories())
    out=[f'<b>{escape(labels[key])}</b>']
    for row in items:
        if key in ('unis','companies'):
            name,extra,url,note=row
            out.append(f'\n<b>{escape(name)}</b> — {escape(extra)}\n{escape(note)}\n<a href="{url}">Официальный сайт</a>')
        else:
            name,url,note=row
            out.append(f'\n<b>{escape(name)}</b>\n{escape(note)}\n<a href="{url}">Открыть источник</a>')
    buttons=[]
    nav=[]
    if page>0: nav.append(InlineKeyboardButton(text='◀ Назад',callback_data=f'ecopage:{key}:{city}:{page-1}'))
    if (page+1)*n<len(rows): nav.append(InlineKeyboardButton(text='Далее ▶',callback_data=f'ecopage:{key}:{city}:{page+1}'))
    if nav: buttons.append(nav)
    buttons.append([InlineKeyboardButton(text='📚 Разделы',callback_data='ecosystem'),InlineKeyboardButton(text='🏠 Меню',callback_data='home')])
    await message.answer('\n'.join(out)+f'\n\nСтраница {page+1}/{max(1,(len(rows)+n-1)//n)}. Актуальность условий уточняйте у организаторов.',parse_mode='HTML',reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data=='companytracks')
async def company_tracks(c:CallbackQuery):
    await c.answer()
    await c.message.answer('Выбери направление:',reply_markup=with_home([[InlineKeyboardButton(text=core.TRACKS[k],callback_data=f'companytrack:{k}')] for k in core.KEYS]))

@router.callback_query(F.data=='companytechnologies')
async def company_technologies(c:CallbackQuery):
    await c.answer()
    await c.message.answer('Технологии — ориентиры для поиска, а не подтверждение текущего стека компании.',reply_markup=with_home([[InlineKeyboardButton(text=t,callback_data=f'companytech:{i}')] for i,t in enumerate(ecosystem.TECHNOLOGIES)]))

async def send_company_matches(message,rows):
    lines=['🏢 <b>Компании для изучения</b>']
    for name,field,url,note in rows:
        lines.append(f'\n<b>{escape(name)}</b> — {escape(field)}\n{escape(note)}\n<a href="{url}">Сайт компании</a>')
    lines.append('\nПроверяй вакансии и ограничения по возрасту на сайтах компаний.')
    await message.answer('\n'.join(lines),parse_mode='HTML',reply_markup=with_home([[InlineKeyboardButton(text='🎓 Стажировки',callback_data='companycareers'),InlineKeyboardButton(text='📚 Разделы',callback_data='ecosystem')]]))

@router.callback_query(F.data.startswith('companytrack:'))
async def company_track(c:CallbackQuery):
    await c.answer()
    key=c.data.split(':',1)[1]
    if key in core.KEYS: await send_company_matches(c.message,ecosystem.companies_for_track(key))

@router.callback_query(F.data.startswith('companytech:'))
async def company_technology(c:CallbackQuery):
    await c.answer()
    try: i=int(c.data.split(':',1)[1])
    except ValueError: return
    technologies=list(ecosystem.TECHNOLOGIES)
    if 0<=i<len(technologies):
        await send_company_matches(c.message,ecosystem.companies_for_technology(technologies[i]))

@router.callback_query(F.data=='companycareers')
async def company_careers(c:CallbackQuery):
    await c.answer()
    lines=['🎓 <b>Карьера и стажировки</b>']
    for name,url,note in ecosystem.CAREER_RESOURCES:
        lines.append(f'\n<b>{escape(name)}</b>\n{escape(note)}\n<a href="{url}">Официальная страница</a>')
    lines.append('\nБольшинство программ ориентировано на подготовленных кандидатов; доступность для школьников проверяй отдельно.')
    await c.message.answer('\n'.join(lines),parse_mode='HTML',reply_markup=with_home([[InlineKeyboardButton(text='🏢 Компании',callback_data='ecocat:companies')]]))

@router.callback_query(F.data=='unifilters')
async def university_filters(c:CallbackQuery):
    await c.answer()
    kb=with_home([[InlineKeyboardButton(text=core.TRACKS[k],callback_data=f'uniprofile:{k}')] for k in core.KEYS])
    await c.message.answer('🔎 Выбери интересующую IT-сферу. Это направления для самостоятельного изучения, а не подтверждённый перечень программ университета.',reply_markup=kb)

@router.callback_query(F.data.startswith('uniprofile:'))
async def university_profile(c:CallbackQuery):
    await c.answer()
    track=c.data.split(':',1)[1]
    if track not in core.KEYS: return
    rows=ecosystem.suggested_universities(track)
    msg='🎓 <b>Вузы для дальнейшего изучения</b>\\n\\n'
    msg+='\\n'.join(f'• <a href="{url}">{escape(name)}</a> ({escape(city)})' for name,city,url,note in rows)
    msg+='\\n\\nНаличие конкретной программы и поступление уточняй на официальном сайте.'
    await c.message.answer(msg,parse_mode='HTML',reply_markup=with_home([[InlineKeyboardButton(text='⚖ Сравнить вузы',callback_data='unicompare'),InlineKeyboardButton(text='⭐ Избранное',callback_data='unifavs')]]))

@router.callback_query(F.data=='unicompare')
async def university_compare(c:CallbackQuery):
    await c.answer()
    rows=ecosystem.CATALOG['unis']
    kb=with_home([[InlineKeyboardButton(text=r[0],callback_data=f'unifirst:{i}')] for i,r in enumerate(rows)])
    await c.message.answer('⚖ Выбери первый вуз для сравнения:',reply_markup=kb)

@router.callback_query(F.data.startswith('unifirst:'))
async def university_first(c:CallbackQuery):
    await c.answer()
    try: first=int(c.data.split(':')[1])
    except ValueError: return
    if not ecosystem.university(first): return
    kb=with_home([[InlineKeyboardButton(text=r[0],callback_data=f'unisecond:{first}:{i}')] for i,r in enumerate(ecosystem.CATALOG['unis']) if i!=first])
    await c.message.answer('Выбери второй вуз:',reply_markup=kb)

@router.callback_query(F.data.startswith('unisecond:'))
async def university_second(c:CallbackQuery):
    await c.answer()
    try: _,a,b=c.data.split(':'); a=int(a);b=int(b)
    except ValueError: return
    first,second=ecosystem.university(a),ecosystem.university(b)
    if not first or not second or a==b: return
    lines=['⚖ <b>Сравнение университетов</b>']
    for name,city,url,note in (first,second):
        lines.append(f'\\n<b>{escape(name)}</b>\\nГород: {escape(city)}\\n{escape(note)}\\n<a href="{url}">Официальный сайт</a>')
    lines.append('\\nПроходные баллы, гранты и программы здесь не сравниваются без проверенных данных за нужный год.')
    buttons=[[InlineKeyboardButton(text='⭐ '+first[0],callback_data=f'unifav:{a}'),InlineKeyboardButton(text='⭐ '+second[0],callback_data=f'unifav:{b}')],[InlineKeyboardButton(text='⚖ Другое сравнение',callback_data='unicompare')]]
    await c.message.answer('\\n'.join(lines),parse_mode='HTML',reply_markup=with_home(buttons))

@router.callback_query(F.data.startswith('unifav:'))
async def university_favorite(c:CallbackQuery):
    await c.answer()
    try: index=int(c.data.split(':')[1])
    except ValueError: return
    row=ecosystem.university(index)
    if not row: return
    added=storage.favorite_toggle(c.from_user.id,row[0])
    await c.message.answer(('⭐ Добавлено в избранное: ' if added else 'Убрано из избранного: ')+row[0],reply_markup=with_home([[InlineKeyboardButton(text='⭐ Моё избранное',callback_data='unifavs')]]))

@router.callback_query(F.data=='unifavs')
async def university_favorites(c:CallbackQuery):
    await c.answer()
    names=storage.favorites(c.from_user.id)
    rows=[row for row in ecosystem.CATALOG['unis'] if row[0] in names]
    msg='⭐ <b>Избранные вузы</b>\\n'+('\\n'.join(f'• <a href="{url}">{escape(name)}</a>' for name,city,url,note in rows) if rows else 'Пока пусто. Добавь вуз из сравнения.')
    await c.message.answer(msg,parse_mode='HTML',reply_markup=with_home([[InlineKeyboardButton(text='⚖ Сравнить вузы',callback_data='unicompare')]]))

@router.callback_query(F.data.startswith('ecopage:'))
async def eco_page(c:CallbackQuery):
    await c.answer()
    try: _,key,city,page=c.data.split(':')
    except ValueError: return
    if key not in ecosystem.CATALOG or not page.isdecimal(): return
    await show_ecosystem(c.message,key,city,int(page))

@router.callback_query(F.data=='interview')
async def interview(c:CallbackQuery,state:FSMContext):
    await c.answer()
    await state.clear()
    kb=with_home([[InlineKeyboardButton(text=core.TRACKS[k],callback_data=f'intstart:{k}')] for k in core.KEYS])
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
    kb=with_home([[InlineKeyboardButton(text=f'{chr(1040+i)}) {option}',callback_data=f'intanswer:{index}:{i}')] for i,option in enumerate(options)])
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
    kb=with_home([[InlineKeyboardButton(text=f'{i} ⭐',callback_data=f'rate:{i}') for i in range(1,6)]])
    await c.message.answer('Оцени полезность бота от 1 до 5:',reply_markup=kb)
@router.callback_query(F.data.startswith('rate:'))
async def rate(c:CallbackQuery):
    try: stars=int(c.data.split(':')[1])
    except (ValueError,IndexError): return await c.answer('Ошибка',show_alert=True)
    if not 1<=stars<=5: return await c.answer('Ошибка',show_alert=True)
    storage.save_feedback(c.from_user.id,stars)
    await c.answer('Спасибо!')
    await c.message.edit_text('Спасибо за оценку!',reply_markup=with_home([]))
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
    await c.message.edit_text('Твои данные удалены из базы бота.',reply_markup=with_home([]))
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
    await m.answer('\n'.join(lines),parse_mode='HTML',reply_markup=with_home([]))
@router.message()
async def other(m:Message):
    await m.answer('Выбери раздел или вернись в главное меню.',reply_markup=with_home([]))
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

"""Offline Telegram integration tests: real routing/FSM, fake Bot API, temporary DB."""
import asyncio
import hashlib
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.methods import SendMessage, EditMessageText, EditMessageReplyMarkup
from aiogram.types import Message, Chat, User, Update, CallbackQuery
from aiohttp.test_utils import TestClient, TestServer
import main
import core
import ecosystem
import interview_quizzes
import storage


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls=[]
        self.next_id=100
        self.messages={}

    async def close(self): pass
    async def stream_content(self,*args,**kwargs):
        yield b''

    async def make_request(self,bot,method,timeout=None):
        self.calls.append(method)
        if isinstance(method,SendMessage):
            self.next_id+=1
            msg=Message(message_id=self.next_id,date=datetime.now(timezone.utc),chat=Chat(id=int(method.chat_id),type='private'),text=method.text,reply_markup=method.reply_markup)
            self.messages[msg.message_id]=msg
            return msg
        if isinstance(method,(EditMessageText,EditMessageReplyMarkup)):
            return True
        return True


class InterfaceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'DATABASE_URL':''});self.env.start()
        self.db=patch.object(storage,'DB',Path(self.temp.name)/'test.sqlite');self.db.start()
        self.session=FakeSession()
        self.bot=Bot('123456:offline_test_token',session=self.session)
        self.dp=Dispatcher(events_isolation=SimpleEventIsolation())
        # Router can only have one parent, detach after each test.
        self.dp.include_router(main.router)
        self.update_id=0
        self.user=User(id=42,is_bot=False,first_name='Test')
        self.msg=Message(message_id=1,date=datetime.now(timezone.utc),chat=Chat(id=42,type='private'),from_user=self.user,text='/start')

    async def asyncTearDown(self):
        self.dp.sub_routers.clear();main.router._parent_router=None
        await self.dp.storage.close()
        await self.bot.session.close()
        self.db.stop();self.env.stop();self.temp.cleanup()

    async def click(self,data,message=None):
        self.update_id+=1
        cb=CallbackQuery(id=str(self.update_id),from_user=self.user,chat_instance='test',data=data,message=message or self.msg)
        await self.dp.feed_update(self.bot,Update(update_id=self.update_id,callback_query=cb))

    def last_message(self):
        return self.session.messages[max(self.session.messages)]

    def assert_home(self):
        for method in self.session.calls:
            if isinstance(method,(SendMessage,EditMessageText)):
                self.assertNotIn('Не удалось выполнить действие',method.text)
                self.assertIsNotNone(method.reply_markup,method.text)
                buttons=[b for row in method.reply_markup.inline_keyboard for b in row]
                self.assertTrue(any(b.callback_data=='home' and b.text=='🏠 Главное меню' for b in buttons),method.text)
                self.assertLessEqual(len(method.text),4096)
                for b in buttons:
                    if b.callback_data:self.assertLessEqual(len(b.callback_data.encode()),64)

    async def test_catalog_routes_and_home_on_every_screen(self):
        routes=['home','aboutproject','roadmap','professions','ecosystem','ecocat:unis','ecocat:companies','companytracks','companytechnologies','companycareers','unifilters','unicompare','unifirst:0','unisecond:0:1','unifav:0','unifavs','feedback','rate:5','privacy','eraseask','eraseyes']
        routes += [f'{prefix}:{k}' for prefix in ('prof','companytrack','uniprofile') for k in core.KEYS]
        routes += [f'companytech:{i}' for i in range(len(ecosystem.TECHNOLOGIES))]
        routes += [f'ecocat:{k}' for k in ecosystem.CATALOG]
        routes += [f'ecopage:{k}:{city}:{p}' for k in ecosystem.CATALOG for city in ('Все','Алматы','Астана') for p in (0,1,99)]
        for route in routes:
            before=len(self.session.calls)
            await self.click(route)
            self.assertGreater(len(self.session.calls),before,route)
        self.assert_home()

    async def test_quiz_double_click_old_attempt_and_result(self):
        await self.click('startquiz');old=self.last_message()
        await self.click('startquiz');current=self.last_message()
        await self.click('a:0:data',old)
        self.assertEqual((await self.dp.fsm.get_context(bot=self.bot,chat_id=42,user_id=42).get_data())['index'],0)
        await asyncio.gather(self.click('a:0:code',current),self.click('a:0:code',current))
        for i in range(1,7):await self.click(f'a:{i}:code',self.last_message())
        self.assertEqual(storage.latest_result(42)[0],'code')
        self.assertEqual(storage.summary()[0],1)
        self.assert_home()

    async def test_all_interviews(self):
        for key,questions in interview_quizzes.QUIZZES.items():
            await self.click(f'intstart:{key}')
            for i,(_,_,correct) in enumerate(questions):
                await self.click(f'intanswer:{i}:{correct}',self.last_message())
            self.assertIn('5/5',self.last_message().text)
        self.assert_home()

    async def test_restart_unknown_and_malformed_callbacks(self):
        for data in ('a:0:code','intanswer:0:0','unknown','ecopage:bad','unisecond:x:y','unifav:-1','rate:0'):
            await self.click(data)
        self.assertIn('перезапуска',self.last_message().text)
        self.assert_home()

    async def test_commands_admin_and_home(self):
        for text in ('/start','/help','/menu','/project','/myid','/stats','hello'):
            self.update_id+=1
            msg=self.msg.model_copy(update={'text':text})
            await self.dp.feed_update(self.bot,Update(update_id=self.update_id,message=msg))
        with patch.object(main,'ADMIN_IDS',{42}):
            self.update_id+=1
            await self.dp.feed_update(self.bot,Update(update_id=self.update_id,message=self.msg.model_copy(update={'text':'/stats'})))
        self.assertIn('статистика',self.last_message().text)
        self.assert_home()

    async def test_webhook_secret_and_readiness(self):
        app=main.create_application(self.bot,self.dp)
        async with TestClient(TestServer(app)) as client:
            r=await client.get('/health');self.assertEqual(r.status,200)
            r=await client.get('/ready');self.assertEqual(r.status,200)
            with patch.object(storage,'check_connection',side_effect=RuntimeError('PRIVATE_CONNECTION')):
                r=await client.get('/ready');self.assertEqual(r.status,503)
                self.assertNotIn('PRIVATE',await r.text())
            r=await client.post(main.WEBHOOK_PATH,json={});self.assertEqual(r.status,401)
            secret=hashlib.sha256(main.TOKEN.encode()).hexdigest()
            r=await client.post(main.WEBHOOK_PATH,json={'update_id':999,'message':self.msg.model_dump(mode='json',exclude_none=True)},headers={'X-Telegram-Bot-Api-Secret-Token':secret})
            self.assertEqual(r.status,200)

    async def test_safe_answer_only_swallows_expiration(self):
        class Broken:
            data='home'
            async def answer(self,*args,**kwargs):
                raise TelegramBadRequest(method=SendMessage(chat_id=42,text='test'),message=self.error)
        cb=Broken();cb.error='Bad Request: query is too old and response timeout expired'
        await main.safe_answer(cb)
        cb.error='Bad Request: query ID is invalid';await main.safe_answer(cb)
        cb.error='Bad Request: unrelated'
        with self.assertRaises(TelegramBadRequest):await main.safe_answer(cb)

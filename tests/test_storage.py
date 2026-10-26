import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import storage

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'DATABASE_URL':''});self.env.start()
        self.db=patch.object(storage,'DB',Path(self.tmp.name)/'test.db');self.db.start()
    def tearDown(self):
        self.db.stop();self.env.stop();self.tmp.cleanup()
    def test_save_update_and_delete_all_personal_data(self):
        storage.save_result(42,'code',{'code':7})
        storage.save_result(42,'data',{'data':7})
        storage.save_result(43,'code',{'code':7})
        storage.save_feedback(42,5);storage.save_feedback(42,4)
        self.assertTrue(storage.favorite_toggle(42,'NU'))
        self.assertFalse(storage.favorite_toggle(42,'NU'))
        storage.favorite_toggle(42,'NU')
        self.assertEqual(storage.summary(),(2,{'code':1,'data':1},1,4.0))
        storage.erase(42)
        self.assertIsNone(storage.latest_result(42))
        self.assertEqual(storage.favorites(42),[])
        self.assertIsNotNone(storage.latest_result(43))
        self.assertEqual(storage.summary()[2],0)
    def test_delete_rolls_back_on_failure(self):
        storage.save_result(42,'code',{'code':7})
        storage.favorite_toggle(42,'NU')
        with storage.database() as con:
            con.execute("CREATE TRIGGER fail_delete BEFORE DELETE ON results BEGIN SELECT RAISE(ABORT, 'test'); END")
        with self.assertRaises(sqlite3.IntegrityError):storage.erase(42)
        self.assertEqual(storage.favorites(42),['NU'])
        self.assertIsNotNone(storage.latest_result(42))

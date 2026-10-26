"""Only connects to an explicitly designated disposable test database."""
import os
import unittest
from unittest.mock import patch
import storage

@unittest.skipUnless(os.getenv('TEST_POSTGRES_URL'), 'Disposable PostgreSQL not configured')
class PostgresTests(unittest.TestCase):
    def test_postgres_crud(self):
        with patch.dict(os.environ,{'DATABASE_URL':os.environ['TEST_POSTGRES_URL']}):
            uid=9000000001
            try:
                storage.erase(uid)
                storage.save_result(uid,'data',{'data':7})
                self.assertEqual(storage.latest_result(uid)[0],'data')
                storage.save_feedback(uid,4)
                self.assertTrue(storage.favorite_toggle(uid,'Test university'))
                self.assertEqual(storage.favorites(uid),['Test university'])
                self.assertTrue(storage.check_connection())
            finally:
                storage.erase(uid)
            self.assertIsNone(storage.latest_result(uid))
            self.assertEqual(storage.favorites(uid),[])

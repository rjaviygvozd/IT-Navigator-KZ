import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import storage
class StorageTests(unittest.TestCase):
    def test_save_and_delete(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(storage,'DB',Path(d)/'test.db'):
                storage.save_result(42,'code',{'code':15})
                self.assertEqual(storage.latest_result(42)[0],'code')
                storage.save_feedback(42,5)
                self.assertEqual(storage.summary()[0],1)
                storage.erase(42)
                self.assertIsNone(storage.latest_result(42))
                self.assertEqual(storage.summary()[2],0)

import unittest
from situational_diagnostics import QUESTIONS, tally, leaders, describe
class SituationalTests(unittest.TestCase):
    def test_seven_questions(self):
        self.assertEqual(len(QUESTIONS),7)
        self.assertTrue(all(len(q['options'])==4 for q in QUESTIONS))
    def test_clear_winner(self):
        self.assertEqual(leaders(tally(['data']*7)),['data'])
    def test_mixed_result(self):
        scores={'code':3,'data':0,'people':1,'design':3}
        self.assertIn('Смешанный профиль',describe(scores))
    def test_invalid_answer_count(self):
        with self.assertRaises(ValueError):
            tally(['code']*15)

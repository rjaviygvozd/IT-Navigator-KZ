import unittest
import core
class CoreTests(unittest.TestCase):
    def test_7_questions(self): self.assertEqual(len(core.QUESTIONS),7)
    def test_four_options(self): self.assertTrue(all(len(o)==4 for _,o in core.QUESTIONS))
    def test_winner(self): self.assertEqual(core.winning_track(core.scores_for(['data']*7)),'data')
    def test_extended_recommendations(self):
        scores=core.scores_for(['code']*4+['design']*3)
        self.assertIn('UX/UI',core.result_explanation(scores))
        self.assertIn('1–3 месяца',core.extended_roadmap('code'))
    def test_bad_answers(self):
        with self.assertRaises(ValueError): core.scores_for(['code']*2)
if __name__=='__main__': unittest.main()

import unittest
import core
class CoreTests(unittest.TestCase):
    def test_15_questions(self): self.assertEqual(len(core.QUESTIONS),15)
    def test_four_options(self): self.assertTrue(all(len(o)==4 for _,o in core.QUESTIONS))
    def test_winner(self): self.assertEqual(core.winning_track(core.scores_for(['data']*15)),'data')
    def test_extended_recommendations(self):
        scores=core.scores_for(['code']*10+['design']*5)
        self.assertIn('UX/UI',core.result_explanation(scores))
        self.assertIn('12 недель',core.extended_roadmap('code'))
    def test_bad_answers(self):
        with self.assertRaises(ValueError): core.scores_for(['code']*2)
if __name__=='__main__': unittest.main()

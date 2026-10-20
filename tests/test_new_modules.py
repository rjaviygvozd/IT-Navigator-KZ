import unittest
import interview_quizzes
import ecosystem

class FeaturesTests(unittest.TestCase):
    def test_interview_sets(self):
        self.assertEqual(set(interview_quizzes.QUIZZES),{'code','data','people','design'})
        for items in interview_quizzes.QUIZZES.values():
            self.assertEqual(len(items),5)
            for title,options,correct in items:
                self.assertEqual(len(options),3)
                self.assertIn(correct,(0,1,2))
    def test_five_catalog_sections(self):
        self.assertEqual(len(ecosystem.CATALOG),5)
        self.assertTrue(ecosystem.rows('unis','Астана'))
        self.assertTrue(all(r[1]=='Астана' for r in ecosystem.rows('unis','Астана')))

if __name__=='__main__':
    unittest.main()

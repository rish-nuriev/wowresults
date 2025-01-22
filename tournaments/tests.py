from model_bakery import baker
from django.test import TestCase
from .models import Match, Tournament


# Create your tests here.
class MatchModelTest(TestCase):

    def test_match_model_exists(self):
        matches = Match.objects.count()
        self.assertEqual(matches, 0)

    def test_match_is_a_correct_object(self):
        match_obj = baker.make(Match)
        self.assertTrue(isinstance(match_obj, Match))

    def test_match_status(self):
        match_obj = baker.make(Match)
        self.assertEqual(match_obj.status, "NS")

    def test_match_tournament_relation(self):
        match_obj = baker.make(Match)
        self.assertTrue(isinstance(match_obj.tournament, Tournament))

    def test_the_second_match_creation(self):
        match_obj = baker.make(Match)
        matches = Match.objects.count()
        self.assertEqual(matches, 2)

        opposit_id = match_obj.opposite_match
        opposit_obj = Match.objects.get(pk=opposit_id)
        self.assertEqual(opposit_obj.opposite_match, 0)
        self.assertEqual(match_obj.opposite_match, opposit_obj.id)

        self.assertTrue(opposit_obj.at_home)

    def test_match_result(self):
        match_obj = baker.make(Match)
        self.assertEqual(match_obj.result, 'D')

    def test_match_at_home(self):
        match_obj = baker.make(Match)
        self.assertFalse(match_obj.at_home)

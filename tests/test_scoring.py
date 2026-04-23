import unittest

from engine import (
    ALL_CARDS,
    ANIMAL_CARDS,
    BRIGHT_CARDS,
    CARDS_BY_CODE,
    DOUBLE_JUNK_CARDS,
    GUKJIN_CARD,
    JOKERS,
    RIBBON_CARDS,
    apply_go_bonus,
    base_score,
    score_animals,
    score_base,
    score_brights,
    score_hand,
    score_junk,
    score_ribbons,
    total_score,
)


class CardDefinitionTests(unittest.TestCase):
    def test_deck_shape(self) -> None:
        self.assertEqual(len(ALL_CARDS), 50)
        self.assertEqual(len(JOKERS), 2)
        self.assertEqual(len(BRIGHT_CARDS), 5)
        self.assertEqual(len(RIBBON_CARDS), 10)
        self.assertEqual(len(ANIMAL_CARDS), 9)
        self.assertGreaterEqual(len(DOUBLE_JUNK_CARDS), 3)
        self.assertTrue(GUKJIN_CARD.gukjin)
        self.assertTrue(GUKJIN_CARD.double_junk)

    def test_unique_codes(self) -> None:
        self.assertEqual(len({card.code for card in ALL_CARDS}), 50)
        self.assertIn("09-animal", CARDS_BY_CODE)


class ScoringTests(unittest.TestCase):
    def test_bright_scoring(self) -> None:
        bright_5 = [card for card in ALL_CARDS if card.bright]
        self.assertEqual(score_brights(bright_5), 15)
        self.assertEqual(score_brights(bright_5[:4]), 4)
        self.assertEqual(score_brights(bright_5[:3]), 3)
        rain_bright = [card for card in ALL_CARDS if card.rain_bright]
        self.assertEqual(score_brights(bright_5[:2] + rain_bright), 2)

    def test_ribbon_scoring_combines_sets(self) -> None:
        red_poem = [card for card in RIBBON_CARDS if card.ribbon_tag == "red_poem"]
        blue = [card for card in RIBBON_CARDS if card.ribbon_tag == "blue"]
        mixed = red_poem + blue[:3]
        self.assertEqual(score_ribbons(red_poem), 3)
        self.assertEqual(score_ribbons(blue[:3]), 3)
        self.assertEqual(score_ribbons(mixed), 8)

    def test_animal_scoring_with_godori(self) -> None:
        godori = [card for card in ANIMAL_CARDS if card.animal_tag == "godori"]
        extra = [card for card in ANIMAL_CARDS if card.animal_tag != "godori"][:3]
        self.assertEqual(score_animals(godori), 5)
        self.assertEqual(score_animals(godori + extra), 7)

    def test_junk_scoring_with_double_junk_and_joker(self) -> None:
        junk_cards = [
            card
            for card in ALL_CARDS
            if card.junk and not card.joker and not card.double_junk
        ]
        self.assertEqual(score_junk(junk_cards[:10]), 1)
        special = [*junk_cards[:7], GUKJIN_CARD, *JOKERS]
        self.assertEqual(score_junk(special, moved_gukjin=True), 5)

    def test_base_and_go_bonus(self) -> None:
        bright_5 = [card for card in ALL_CARDS if card.bright]
        self.assertEqual(score_base(bright_5).bright, 15)
        self.assertEqual(apply_go_bonus(5, 0), 5)
        self.assertEqual(apply_go_bonus(5, 1), 6)
        self.assertEqual(apply_go_bonus(5, 2), 7)
        self.assertEqual(apply_go_bonus(5, 3), 14)
        self.assertEqual(apply_go_bonus(5, 4), 28)

    def test_moved_gukjin_is_counted_as_junk(self) -> None:
        self.assertEqual(score_junk([GUKJIN_CARD], moved_gukjin=False), 0)
        self.assertEqual(score_junk([GUKJIN_CARD], moved_gukjin=True), 0)
        animals = [card for card in ANIMAL_CARDS if not card.gukjin][:4]
        breakdown = score_hand([*animals, GUKJIN_CARD], moved_gukjin=True)
        self.assertEqual(breakdown.junk, 0)
        self.assertEqual(breakdown.animal, 0)
        self.assertEqual(total_score([*animals, GUKJIN_CARD], moved_gukjin=True), 0)
        self.assertEqual(base_score([*animals, GUKJIN_CARD], moved_gukjin=True), 0)


if __name__ == "__main__":
    unittest.main()

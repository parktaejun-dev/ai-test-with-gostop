"""Scoring helpers for Go-Stop / Hwatu evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .cards import Card


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """Component-based score breakdown."""

    bright: int = 0
    ribbon: int = 0
    animal: int = 0
    junk: int = 0
    go_bonus: int = 0

    @property
    def base(self) -> int:
        return self.bright + self.ribbon + self.animal + self.junk

    @property
    def total(self) -> int:
        return self.base + self.go_bonus


def score_brights(cards_or_count: Iterable[Card] | int) -> int:
    """Score bright cards.

    Standard table used here:
    - 5 bright: 15
    - 4 bright: 4
    - 3 bright: 3, or 2 if one of them is the rain bright
    """

    if isinstance(cards_or_count, int):
        count = cards_or_count
        has_rain = False
    else:
        cards = tuple(cards_or_count)
        count = sum(1 for card in cards if card.bright)
        has_rain = any(card.bright and card.rain_bright for card in cards)
    if count >= 5:
        return 15
    if count == 4:
        return 4
    if count == 3:
        return 2 if has_rain else 3
    return 0


def score_ribbons(cards_or_count: Iterable[Card] | int) -> int:
    """Score ribbon cards, combining the three named ribbon sets."""

    if isinstance(cards_or_count, int):
        count = cards_or_count
        ribbons: tuple[Card, ...] = ()
    else:
        ribbons = tuple(card for card in cards_or_count if card.ribbon)
        count = len(ribbons)
    score = 0
    if count >= 5:
        score += count - 4
    if ribbons:
        tagged = {tag: 0 for tag in ("red_poem", "blue", "red_plain")}
        for card in ribbons:
            if card.ribbon_tag in tagged:
                tagged[card.ribbon_tag] += 1
        score += 3 * sum(1 for value in tagged.values() if value >= 3)
    return score


def score_animals(
    cards_or_count: Iterable[Card] | int,
    *,
    moved_gukjin: bool = False,
) -> int:
    """Score animal cards, including the godori bonus."""

    if isinstance(cards_or_count, int):
        count = cards_or_count
        animals: tuple[Card, ...] = ()
    else:
        animals = tuple(
            card
            for card in cards_or_count
            if card.animal and not (moved_gukjin and card.gukjin)
        )
        count = len(animals)
    score = 0
    if count >= 5:
        score += count - 4
    if animals:
        godori_months = {2, 4, 8}
        if godori_months.issubset({card.month for card in animals}):
            score += 5
    return score


def junk_value(card: Card, *, moved_gukjin: bool = False) -> int:
    """Return the junk value for a single card.

    The September gukjin / double-junk animal can be moved into the junk pile
    by the caller. In that case this helper counts it as junk rather than animal.
    """

    if card.joker:
        return card.junk_value
    if card.gukjin:
        return 2 if moved_gukjin else 0
    return card.junk_value


def score_junk(cards_or_count: Iterable[Card] | int, *, moved_gukjin: bool = False) -> int:
    """Score junk cards.

    A set of 10 junk cards is worth 1 point, with each additional junk card
    worth 1 more point.
    """

    if isinstance(cards_or_count, int):
        count = cards_or_count
    else:
        count = sum(junk_value(card, moved_gukjin=moved_gukjin) for card in cards_or_count)
    if count >= 10:
        return count - 9
    return 0


def score_base(
    cards: Iterable[Card],
    *,
    moved_gukjin: bool = False,
) -> ScoreBreakdown:
    """Score a capture set before any Go bonus is applied."""

    cards = tuple(cards)
    bright = score_brights(cards)
    ribbon = score_ribbons(cards)
    animal = score_animals(cards, moved_gukjin=moved_gukjin)
    junk = score_junk(cards, moved_gukjin=moved_gukjin)
    return ScoreBreakdown(bright=bright, ribbon=ribbon, animal=animal, junk=junk)


def go_bonus_steps(go_count: int) -> tuple[int, int]:
    """Return the additive and multiplicative pieces for Go bonuses.

    The common rule set is:
    - 1 Go: +1 point
    - 2 Go: +2 points
    - 3 Go: apply the +2 point rule, then double
    - each Go beyond 3 doubles again
    """

    if go_count <= 0:
        return (0, 1)
    if go_count == 1:
        return (1, 1)
    if go_count == 2:
        return (2, 1)
    return (2, 2 ** (go_count - 2))


def apply_go_bonus(base_score: int, go_count: int) -> int:
    """Apply Go bonus logic to a base score."""

    additive, multiplier = go_bonus_steps(go_count)
    return (base_score + additive) * multiplier


def score_hand(
    cards: Iterable[Card],
    *,
    moved_gukjin: bool = False,
    go_count: int = 0,
) -> ScoreBreakdown:
    """Return a full score breakdown for a capture pile."""

    base = score_base(cards, moved_gukjin=moved_gukjin)
    go_bonus = apply_go_bonus(base.base, go_count) - base.base
    return ScoreBreakdown(
        bright=base.bright,
        ribbon=base.ribbon,
        animal=base.animal,
        junk=base.junk,
        go_bonus=go_bonus,
    )


def total_score(cards: Iterable[Card], *, moved_gukjin: bool = False, go_count: int = 0) -> int:
    """Convenience wrapper that returns the final score as an integer."""

    return score_hand(cards, moved_gukjin=moved_gukjin, go_count=go_count).total


def base_score(cards: Iterable[Card], *, moved_gukjin: bool = False) -> int:
    """Return the base score as an integer."""

    return score_base(cards, moved_gukjin=moved_gukjin).base


def score_captured_cards(
    cards: Iterable[Card],
    moved_gukjin: bool = False,
    *,
    return_breakdown: bool = False,
) -> int | dict[str, int]:
    cards = tuple(cards)
    breakdown = score_base(cards, moved_gukjin=moved_gukjin)
    if not return_breakdown:
        return breakdown.base
    bright_count = sum(1 for card in cards if card.bright)
    animal_count = sum(1 for card in cards if card.animal and not (moved_gukjin and card.gukjin))
    ribbon_count = sum(1 for card in cards if card.ribbon)
    pi_count = sum(junk_value(card, moved_gukjin=moved_gukjin) for card in cards)
    return {
        "bright": breakdown.bright,
        "animal": breakdown.animal,
        "ribbon": breakdown.ribbon,
        "junk": breakdown.junk,
        "base": breakdown.base,
        "bright_count": bright_count,
        "animal_count": animal_count,
        "ribbon_count": ribbon_count,
        "pi_count": pi_count,
    }

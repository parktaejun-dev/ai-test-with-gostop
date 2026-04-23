"""Hwatu card definitions for a Go-Stop evaluation harness.

This module keeps the deck definition stdlib-only and explicit:
48 hwatu cards, 2 jokers, and the metadata needed by the scoring layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Tuple


JOKER_MONTH = 0


class CardKind(str, Enum):
    BRIGHT = "bright"
    ANIMAL = "animal"
    RIBBON = "ribbon"
    JUNK = "junk"
    JOKER = "joker"


@dataclass(frozen=True, slots=True)
class Card:
    """A single Hwatu or joker card."""

    code: str
    month: int
    name: str
    bright: bool = False
    ribbon: bool = False
    animal: bool = False
    junk: bool = False
    double_junk: bool = False
    gukjin: bool = False
    rain_bright: bool = False
    ribbon_tag: str | None = None
    animal_tag: str | None = None
    joker: bool = False
    joker_junk_value: int = 0

    @property
    def junk_value(self) -> int:
        """Return how many junk cards this card is worth when counted as junk."""

        if self.joker:
            return self.joker_junk_value
        if self.double_junk:
            return 2
        if self.junk:
            return 1
        return 0

    @property
    def id(self) -> str:
        return self.code

    @property
    def kind(self) -> CardKind:
        if self.joker:
            return CardKind.JOKER
        if self.bright:
            return CardKind.BRIGHT
        if self.animal:
            return CardKind.ANIMAL
        if self.ribbon:
            return CardKind.RIBBON
        return CardKind.JUNK

    @property
    def is_pi(self) -> bool:
        return self.joker or self.junk or self.double_junk

    @property
    def is_double_pi(self) -> bool:
        return self.double_junk or (self.joker and self.joker_junk_value >= 2)

    @property
    def pi_value(self) -> int:
        return self.junk_value

    @property
    def is_rain_bright(self) -> bool:
        return self.rain_bright


def _hwatu_card(
    month: int,
    suffix: str,
    name: str,
    *,
    bright: bool = False,
    ribbon: bool = False,
    animal: bool = False,
    junk: bool = False,
    double_junk: bool = False,
    gukjin: bool = False,
    rain_bright: bool = False,
    ribbon_tag: str | None = None,
    animal_tag: str | None = None,
) -> Card:
    code = f"{month:02d}-{suffix}"
    return Card(
        code=code,
        month=month,
        name=name,
        bright=bright,
        ribbon=ribbon,
        animal=animal,
        junk=junk,
        double_junk=double_junk,
        gukjin=gukjin,
        rain_bright=rain_bright,
        ribbon_tag=ribbon_tag,
        animal_tag=animal_tag,
    )


HWATU_CARDS: Tuple[Card, ...] = (
    # January - Pine
    _hwatu_card(1, "bright", "January Crane", bright=True),
    _hwatu_card(1, "ribbon", "January Red Ribbon", ribbon=True, ribbon_tag="red_poem"),
    _hwatu_card(1, "junk-a", "January Junk A", junk=True),
    _hwatu_card(1, "junk-b", "January Junk B", junk=True),
    # February - Plum Blossom
    _hwatu_card(2, "animal", "February Nightingale", animal=True, animal_tag="godori"),
    _hwatu_card(2, "ribbon", "February Red Ribbon", ribbon=True, ribbon_tag="red_poem"),
    _hwatu_card(2, "junk-a", "February Junk A", junk=True),
    _hwatu_card(2, "junk-b", "February Junk B", junk=True),
    # March - Cherry Blossom
    _hwatu_card(3, "bright", "March Cherry Bright", bright=True),
    _hwatu_card(3, "ribbon-a", "March Ribbon A", ribbon=True, ribbon_tag="red_poem"),
    _hwatu_card(3, "ribbon-b", "March Junk", junk=True),
    _hwatu_card(3, "junk", "March Junk B", junk=True),
    # April - Wisteria
    _hwatu_card(4, "animal", "April Cuckoo", animal=True, animal_tag="godori"),
    _hwatu_card(4, "ribbon", "April Red Ribbon", ribbon=True, ribbon_tag="red_plain"),
    _hwatu_card(4, "junk-a", "April Junk A", junk=True),
    _hwatu_card(4, "junk-b", "April Junk B", junk=True),
    # May - Iris
    _hwatu_card(5, "animal", "May Bridge", animal=True, double_junk=True),
    _hwatu_card(5, "ribbon", "May Red Ribbon", ribbon=True, ribbon_tag="red_plain"),
    _hwatu_card(5, "junk-a", "May Junk A", junk=True),
    _hwatu_card(5, "junk-b", "May Junk B", junk=True),
    # June - Peony
    _hwatu_card(6, "animal", "June Butterfly", animal=True),
    _hwatu_card(6, "ribbon", "June Blue Ribbon", ribbon=True, ribbon_tag="blue"),
    _hwatu_card(6, "junk-a", "June Junk A", junk=True),
    _hwatu_card(6, "junk-b", "June Junk B", junk=True),
    # July - Clover
    _hwatu_card(7, "animal", "July Boar", animal=True),
    _hwatu_card(7, "ribbon", "July Red Ribbon", ribbon=True, ribbon_tag="red_plain"),
    _hwatu_card(7, "junk-a", "July Junk A", junk=True),
    _hwatu_card(7, "junk-b", "July Junk B", junk=True),
    # August - Pampas Grass
    _hwatu_card(8, "bright", "August Full Moon", bright=True),
    _hwatu_card(8, "animal", "August Geese", animal=True, animal_tag="godori"),
    _hwatu_card(8, "junk-a", "August Junk A", junk=True),
    _hwatu_card(8, "junk-b", "August Junk B", junk=True),
    # September - Chrysanthemum / Gukjin
    _hwatu_card(
        9,
        "animal",
        "September Sake Cup",
        animal=True,
        double_junk=True,
        gukjin=True,
    ),
    _hwatu_card(9, "ribbon", "September Blue Ribbon", ribbon=True, ribbon_tag="blue"),
    _hwatu_card(9, "junk-a", "September Junk A", junk=True),
    _hwatu_card(9, "junk-b", "September Junk B", junk=True),
    # October - Maple
    _hwatu_card(10, "animal", "October Deer", animal=True),
    _hwatu_card(10, "ribbon", "October Blue Ribbon", ribbon=True, ribbon_tag="blue"),
    _hwatu_card(10, "junk-a", "October Junk A", junk=True),
    _hwatu_card(10, "junk-b", "October Junk B", junk=True),
    # November - Paulownia
    _hwatu_card(11, "bright", "November Phoenix", bright=True),
    _hwatu_card(11, "junk-c", "November Junk C", junk=True),
    _hwatu_card(11, "junk-a", "November Junk A", junk=True),
    _hwatu_card(11, "junk-b", "November Double Junk", junk=True, double_junk=True),
    # December - Willow / Rain
    _hwatu_card(12, "bright", "December Rain Bright", bright=True, rain_bright=True),
    _hwatu_card(12, "animal", "December Swallow", animal=True),
    _hwatu_card(12, "junk-a", "December Double Junk", junk=True, double_junk=True),
    _hwatu_card(12, "ribbon", "December Ribbon", ribbon=True, ribbon_tag="other"),
)

JOKERS: Tuple[Card, ...] = (
    Card(
        code="joker-2",
        month=JOKER_MONTH,
        name="Two Pi Joker",
        junk=True,
        joker=True,
        joker_junk_value=2,
    ),
    Card(
        code="joker-3",
        month=JOKER_MONTH,
        name="Three Pi Joker",
        junk=True,
        joker=True,
        joker_junk_value=3,
    ),
)

DECK: Tuple[Card, ...] = HWATU_CARDS + JOKERS
ALL_CARDS: Tuple[Card, ...] = DECK

CARDS_BY_CODE: Dict[str, Card] = {card.code: card for card in ALL_CARDS}
CARDS_BY_NAME: Dict[str, Card] = {card.name: card for card in ALL_CARDS}

BRIGHT_CARDS: Tuple[Card, ...] = tuple(card for card in HWATU_CARDS if card.bright)
RIBBON_CARDS: Tuple[Card, ...] = tuple(card for card in HWATU_CARDS if card.ribbon)
ANIMAL_CARDS: Tuple[Card, ...] = tuple(card for card in HWATU_CARDS if card.animal)
JUNK_CARDS: Tuple[Card, ...] = tuple(card for card in HWATU_CARDS if card.junk or card.double_junk)
DOUBLE_JUNK_CARDS: Tuple[Card, ...] = tuple(card for card in HWATU_CARDS if card.double_junk)
GUKJIN_CARD: Card = CARDS_BY_CODE["09-animal"]


def make_deck() -> Tuple[Card, ...]:
    """Return a fresh immutable deck tuple."""

    return DECK


def build_deck() -> list[Card]:
    """Return a mutable deck list."""

    return list(DECK)


def iter_junk_cards(cards: Iterable[Card]) -> Tuple[Card, ...]:
    """Return cards that can contribute junk points."""

    return tuple(card for card in cards if card.junk or card.double_junk or card.joker)

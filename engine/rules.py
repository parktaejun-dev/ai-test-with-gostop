from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PiTakeResult:
    taken_ids: tuple[str, ...]
    total_pi_value: int


def month_counts(cards) -> Counter[int]:
    return Counter(card.month for card in cards if getattr(card, "month", 0) > 0)


def independent_triples(cards) -> int:
    counts = month_counts(cards)
    return sum(count // 3 for count in counts.values())


def determine_shake_ready_months(hand, table_cards) -> set[int]:
    hand_counts = month_counts(hand)
    table_counts = month_counts(table_cards)
    ready = set()
    for month, count in hand_counts.items():
        if month > 0 and count >= 3 and table_counts.get(month, 0) == 0:
            ready.add(month)
    return ready


def has_chongtong(hand) -> set[int]:
    return {month for month, count in month_counts(hand).items() if count == 4}


def take_pi_from_captured(cards, count: int) -> PiTakeResult:
    taken = []
    total = 0
    normal = [card for card in cards if getattr(card, "is_pi", False) and not getattr(card, "is_double_pi", False)]
    doubles = [card for card in cards if getattr(card, "is_double_pi", False)]
    for _ in range(count):
        if normal:
            card = normal.pop(0)
            taken.append(card)
            total += 1
            cards.remove(card)
            continue
        if doubles:
            card = doubles.pop(0)
            taken.append(card)
            total += getattr(card, "pi_value", 2)
            cards.remove(card)
            continue
        break
    return PiTakeResult(tuple(card.id for card in taken), total)


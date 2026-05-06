from itertools import combinations
from collections import Counter

RANK_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
    "9": 9, "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14
}

def _val(rank):
    return RANK_VALUES[rank]


def _evaluate_five(cards):
    """Score a 5-card hand. Returns (rank_int, tiebreakers, hand_name)."""
    vals = sorted([_val(c.rank) for c in cards], reverse=True)
    suits = [c.suite for c in cards]

    is_flush = len(set(suits)) == 1

    is_straight = False
    straight_high = 0
    if len(set(vals)) == 5:
        if vals[0] - vals[4] == 4:
            is_straight = True
            straight_high = vals[0]
        elif sorted(vals) == [2, 3, 4, 5, 14]:  # wheel A-2-3-4-5
            is_straight = True
            straight_high = 5

    counts = Counter(vals)
    freq = sorted(counts.values(), reverse=True)
    # tiebreaker: cards sorted by (frequency desc, rank desc)
    tb = sorted(counts.keys(), key=lambda v: (counts[v], v), reverse=True)

    if is_straight and is_flush:
        if straight_high == 14:
            return (9, [14], "Royal Flush")
        return (8, [straight_high], "Straight Flush")
    if freq[0] == 4:
        return (7, tb, "Four of a Kind")
    if freq[0] == 3 and freq[1] == 2:
        return (6, tb, "Full House")
    if is_flush:
        return (5, vals, "Flush")
    if is_straight:
        return (4, [straight_high], "Straight")
    if freq[0] == 3:
        return (3, tb, "Three of a Kind")
    if freq[0] == 2 and freq[1] == 2:
        return (2, tb, "Two Pair")
    if freq[0] == 2:
        return (1, tb, "One Pair")
    return (0, vals, "High Card")


def best_hand(cards):
    """Best 5-card hand from up to 7 cards. Returns (rank_int, tiebreakers, hand_name) or None."""
    if len(cards) < 5:
        return None
    best = None
    for combo in combinations(cards, 5):
        result = _evaluate_five(list(combo))
        if best is None or (result[0], result[1]) > (best[0], best[1]):
            best = result
    return best


def determine_winner(player_cards, pc_cards, community_cards):
    """
    Compare both players' best hands against the community cards.
    Returns ("player" | "pc" | "tie", player_hand_name, pc_hand_name).
    """
    all_player = player_cards + community_cards
    all_pc = pc_cards + community_cards

    p_best = best_hand(all_player)
    c_best = best_hand(all_pc)

    if p_best is None and c_best is None:
        return "tie", "Unknown", "Unknown"
    if p_best is None:
        return "pc", "Unknown", c_best[2]
    if c_best is None:
        return "player", p_best[2], "Unknown"

    p_score = (p_best[0], p_best[1])
    c_score = (c_best[0], c_best[1])

    if p_score > c_score:
        return "player", p_best[2], c_best[2]
    elif c_score > p_score:
        return "pc", p_best[2], c_best[2]
    else:
        return "tie", p_best[2], c_best[2]

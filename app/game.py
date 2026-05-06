import json
import random
import sys
import os

from flask import Blueprint, jsonify, request
from app.prisma import with_prisma
from app.jwt import require_auth

# Allow importing from the game/ sibling directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))

from deck import Deck
from card import Card
from game import Game as PokerGame

HAND_RANKING = [
    "Royal Flush", "Straight Flush", "Four of a Kind", "Full House",
    "Flush", "Straight", "Three of a Kind", "Two Pair", "One Pair", "High Card",
]

game_bp = Blueprint("game_bp", __name__)


# ── card serialisation helpers ────────────────────────────────────────────────

def _card_to_str(card):
    return f"{card.rank}_{card.suite}"

def _str_to_card(s):
    rank, suite = s.split("_", 1)
    return Card(suite=suite, rank=rank)

def _cards_to_json(cards):
    return json.dumps([_card_to_str(c) for c in cards])

def _json_to_cards(s):
    return [_str_to_card(x) for x in json.loads(s)]


# ── PC auto-response ──────────────────────────────────────────────────────────

STRONG_RANKS = {"A", "K", "Q"}

def _pc_has_strong_hand(pc_cards_json):
    cards = json.loads(pc_cards_json)
    return any(c.split("_")[0] in STRONG_RANKS for c in cards)

def _pc_respond(player_bet, pc_bet, pc_chips, pc_cards_json, is_preflop=False, initial_bet=0):
    diff = player_bet - pc_bet

    # Preflop: PC doubles the human's opening bet (spec step 6)
    if is_preflop and pc_bet == 0 and initial_bet > 0:
        double = initial_bet * 2
        if double > pc_chips:
            return {"action": "fold", "amount": 0}
        return {"action": "raise", "amount": double}

    if diff <= 0:
        return {"action": "check", "amount": 0}
    if diff > pc_chips:
        return {"action": "fold", "amount": 0}

    has_strong = _pc_has_strong_hand(pc_cards_json)

    # Strong hand: prefer calling/raising; weak hand: more likely to fold when bet is large
    if has_strong:
        choice = random.randint(1, 3)
        if choice <= 2 or diff == pc_chips:
            return {"action": "call", "amount": diff}
        extra = random.randint(1, max(1, min(50, pc_chips - diff)))
        return {"action": "raise", "amount": diff + extra}
    else:
        if diff > pc_chips // 4:
            return {"action": "fold", "amount": 0}
        return {"action": "call", "amount": diff}


# ── phase advancement (deals next community cards) ────────────────────────────

def _advance_phase(g):
    """
    Moves the game to the next phase, deals community cards.
    Mutates the game dict `g` in place and returns a result fragment.
    """
    phase = g["phase"]
    deck = json.loads(g["deck"])
    community = json.loads(g["community_cards"])
    result = {}

    if phase == "preflop":
        deck.pop(0)  # burn
        new_cards = [deck.pop(0) for _ in range(3)]
        community.extend(new_cards)
        g["phase"] = "flop"
        result["new_community_cards"] = new_cards

    elif phase == "flop":
        deck.pop(0)
        new_cards = [deck.pop(0)]
        community.extend(new_cards)
        g["phase"] = "turn"
        result["new_community_cards"] = new_cards

    elif phase == "turn":
        deck.pop(0)
        new_cards = [deck.pop(0)]
        community.extend(new_cards)
        g["phase"] = "river"
        result["new_community_cards"] = new_cards

    elif phase == "river":
        p_cards = _json_to_cards(g["player_cards"])
        c_cards = _json_to_cards(g["pc_cards"])
        comm    = [_str_to_card(x) for x in community]

        logic  = PokerGame()
        p_hand = logic.get_best_hand(p_cards + comm)
        c_hand = logic.get_best_hand(c_cards + comm)

        p_rank = HAND_RANKING.index(p_hand)
        c_rank = HAND_RANKING.index(c_hand)

        if p_rank < c_rank:
            winner = "player"
        elif c_rank < p_rank:
            winner = "pc"
        else:
            winner = "tie"

        g["phase"]  = "showdown"
        g["status"] = "finished"
        g["winner"] = winner

        result["game_over"]   = True
        result["winner"]      = winner
        result["player_hand"] = p_hand
        result["pc_hand"]     = c_hand
        result["pc_cards"]    = json.loads(g["pc_cards"])

    g["deck"]            = json.dumps(deck)
    g["community_cards"] = json.dumps(community)
    return result


# ── game state serialiser (hides PC cards until showdown) ─────────────────────

def _game_state(g):
    finished = g["status"] == "finished"
    state = {
        "game_id":        g["id"],
        "phase":          g["phase"],
        "status":         g["status"],
        "player_cards":   json.loads(g["player_cards"]),
        "community_cards":json.loads(g["community_cards"]),
        "pot":            g["pot"],
        "player_chips":   g["player_chips"],
        "pc_chips":       g["pc_chips"],
        "player_bet":     g["player_bet"],
        "pc_bet":         g["pc_bet"],
        "winner":         g["winner"],
    }
    if finished:
        state["pc_cards"] = json.loads(g["pc_cards"])
    return state


# ── endpoints ─────────────────────────────────────────────────────────────────

@game_bp.route("/start", methods=["POST"])
@with_prisma
@require_auth
async def start_game(prisma, _jwt):
    deck = Deck()
    deck.shuffle()
    deck.shuffle()

    player_cards  = [deck.give_card(), deck.give_card()]
    pc_cards      = [deck.give_card(), deck.give_card()]
    remaining     = [_card_to_str(c) for c in deck.deck]

    game = await prisma.game.create(data={
        "player_id":       _jwt.id,
        "phase":           "preflop",
        "player_cards":    _cards_to_json(player_cards),
        "pc_cards":        _cards_to_json(pc_cards),
        "community_cards": "[]",
        "deck":            json.dumps(remaining),
        "pot":             0,
        "player_chips":    2000,
        "pc_chips":        2000,
        "player_bet":      0,
        "pc_bet":          0,
        "status":          "active",
    })

    return jsonify({
        "game_id":         game.id,
        "phase":           game.phase,
        "player_cards":    [_card_to_str(c) for c in player_cards],
        "community_cards": [],
        "pot":             0,
        "player_chips":    2000,
        "pc_chips":        2000,
        "player_bet":      0,
        "pc_bet":          0,
    }), 201


@game_bp.route("/<game_id>", methods=["GET"])
@with_prisma
@require_auth
async def get_game(prisma, _jwt, game_id):
    game = await prisma.game.find_unique(where={"id": game_id})

    if not game:
        return jsonify({"custom": True, "_message": "Game not found"}), 404
    if game.player_id != _jwt.id:
        return jsonify({"custom": True, "_message": "Forbidden"}), 403

    return jsonify(_game_state(game.model_dump())), 200


@game_bp.route("/history", methods=["GET"])
@with_prisma
@require_auth
async def game_history(prisma, _jwt):
    games = await prisma.game.find_many(
        where={"player_id": _jwt.id},
        order={"created_at": "desc"},
    )
    result = []
    for g in games:
        d = g.model_dump()
        result.append({
            "game_id":    d["id"],
            "status":     d["status"],
            "phase":      d["phase"],
            "winner":     d["winner"],
            "pot":        d["pot"],
            "created_at": d["created_at"].isoformat() if d["created_at"] else None,
        })
    return jsonify(result), 200


@game_bp.route("/<game_id>/action", methods=["POST"])
@with_prisma
@require_auth
async def game_action(prisma, _jwt, game_id):
    game = await prisma.game.find_unique(where={"id": game_id})

    if not game:
        return jsonify({"custom": True, "_message": "Game not found"}), 404
    if game.player_id != _jwt.id:
        return jsonify({"custom": True, "_message": "Forbidden"}), 403
    if game.status == "finished":
        return jsonify({"custom": True, "_message": "Game is already finished"}), 400

    body = request.get_json()
    if not body:
        return jsonify({"custom": True, "_message": "JSON body required"}), 400

    action = body.get("action")
    amount = body.get("amount", 0)

    if action not in ("bet", "call", "raise", "fold", "check"):
        return jsonify({"custom": True, "_message": "action must be bet, call, raise, fold, or check"}), 400

    # check is only valid post-flop when nobody has bet yet
    if action == "check" and game.phase == "preflop":
        return jsonify({"custom": True, "_message": "Cannot check preflop — you must bet, call, raise, or fold"}), 400

    g = game.model_dump()
    response = {"player_action": action, "pc_action": None, "phase_advanced": False, "game_over": False}

    # ── player folds ──────────────────────────────────────────────────────────
    if action == "fold":
        g["status"] = "finished"
        g["winner"] = "pc"
        response.update({"game_over": True, "winner": "pc", "pc_action": "wins"})

    else:
        # check = no bet this turn (amount stays 0)
        if action == "call":
            amount = max(0, g["pc_bet"] - g["player_bet"])
        elif action == "check":
            amount = 0

        if not isinstance(amount, int) or amount < 0:
            return jsonify({"custom": True, "_message": "amount must be a non-negative integer"}), 400

        amount = min(amount, g["player_chips"])  # can't bet more than available

        g["player_bet"]   += amount
        g["player_chips"] -= amount

        is_preflop = g["phase"] == "preflop"

        # ── PC responds ───────────────────────────────────────────────────────
        pc_resp = _pc_respond(
            g["player_bet"], g["pc_bet"], g["pc_chips"],
            g["pc_cards"],
            is_preflop=is_preflop,
            initial_bet=amount,
        )

        if pc_resp["action"] == "fold":
            g["status"] = "finished"
            g["winner"] = "player"
            response.update({"game_over": True, "winner": "player", "pc_action": "fold"})

        else:
            pc_amount = pc_resp["amount"]
            g["pc_bet"]   += pc_amount
            g["pc_chips"] -= pc_amount
            response["pc_action"]  = pc_resp["action"]
            response["pc_amount"]  = pc_amount

            # ── if bets match, close the round and advance phase ──────────────
            if g["player_bet"] == g["pc_bet"]:
                g["pot"]        += g["player_bet"] + g["pc_bet"]
                g["player_bet"]  = 0
                g["pc_bet"]      = 0

                phase_result = _advance_phase(g)
                response.update(phase_result)
                response["phase_advanced"] = True

    # ── persist ───────────────────────────────────────────────────────────────
    await prisma.game.update(
        where={"id": game_id},
        data={
            "status":          g["status"],
            "phase":           g["phase"],
            "community_cards": g["community_cards"],
            "deck":            g["deck"],
            "pot":             g["pot"],
            "player_chips":    g["player_chips"],
            "pc_chips":        g["pc_chips"],
            "player_bet":      g["player_bet"],
            "pc_bet":          g["pc_bet"],
            "winner":          g["winner"],
        },
    )

    response["game_state"] = _game_state(g)
    return jsonify(response), 200
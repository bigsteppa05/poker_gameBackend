from deck import Deck
from player import Player
from evaluator import determine_winner, best_hand

class Game():

    def __init__(self):
        self.pot=0
        deck=Deck()
        deck.shuffle()
        deck.shuffle()
        human_cards= [deck.give_card(),deck.give_card()]
        pc_card=[deck.give_card(),deck.give_card()]
        self.human=Player(type="human",
                          cards=human_cards,
                          bet=0,
                          name="John",amount=2000)
        self.pc=Player(type="pc",
                          cards=pc_card,
                          bet=0,
                          name="Stockfish",amount=2000)
        self._turn=self.human
        self.deck=deck
        self.community_cards=[]

    @property
    def turn(self):
        return self._turn

    @turn.setter
    def turn(self, player):
        if isinstance(player, Player):
            self._turn = player
        else:
            raise ValueError("The turn must be assigned to a player object")

    def print_community_card(self):
        print("Community cards")
        for card in self.community_cards:
            card.print_card()

    def check_winner(self):
        """Evaluate both hands against community cards and return the winner."""
        winner, human_hand, pc_hand = determine_winner(
            self.human.cards,
            self.pc.cards,
            self.community_cards
        )
        return {
            "winner": "human" if winner == "player" else winner,
            "human_hand": human_hand,
            "pc_hand": pc_hand,
        }

    def check_rank_card(self, cards, rank):
        for card in cards:
            if card.rank == rank:
                return card
        return None

    def check_royal_flush(self, cards):
        """Return the 5 royal flush cards if present, else None."""
        royal = ["A", "K", "Q", "J", "10"]
        checked_cards = []
        for rank in royal:
            card = self.check_rank_card(cards=cards, rank=rank)
            if card:
                checked_cards.append(card)
            else:
                return None
        # All five ranks found — verify they share a suit
        suite = checked_cards[0].suite
        for card in checked_cards:
            if suite != card.suite:
                return None
        return checked_cards

    def check_straight_flush(self, cards):
        """Return the best straight-flush evaluation if present, else None."""
        result = best_hand(cards)
        if result and result[0] >= 8:  # 8 = straight flush, 9 = royal flush
            return result
        return None


if __name__ == "__main__":
    game = Game()
    print("Pc cards")
    game.pc.cards[0].print_card()
    game.pc.cards[1].print_card()
    print("Human cards")
    game.human.cards[0].print_card()
    game.human.cards[1].print_card()
    result = game.check_winner()
    print("Winner:", result)

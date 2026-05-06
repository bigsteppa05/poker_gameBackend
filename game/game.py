from deck import Deck
from player import Player


class Game():

    def __init__(self):
        self.pot = 0

        deck = Deck()
        deck.shuffle()
        deck.shuffle()

        human_cards = [deck.give_card(), deck.give_card()]
        pc_cards = [deck.give_card(), deck.give_card()]

        self.human = Player(type="human", cards=human_cards, bet=0, name="John", amount=2000)
        self.pc = Player(type="pc", cards=pc_cards, bet=0, name="Stockfish", amount=2000)
        self._turn = self.human
        self.deck = deck
        self.community_cards = []

    @property
    def turn(self):
        return self._turn

    @turn.setter
    def turn(self, player):
        if isinstance(player, Player):
            self._turn = player
        else:
            raise ValueError("The turn must be assigned to a player object")

    def print_community_cards(self):
        print("\n-- Community Cards --")
        if len(self.community_cards) == 0:
            print("No community cards yet")
        for card in self.community_cards:
            card.print_card()

    def print_player_cards(self):
        print(f"\n-- {self.human.name}'s Cards --")
        for card in self.human.cards:
            card.print_card()

    def check_rank_card(self, cards, rank):
        for card in cards:
            if card.rank == rank:
                return card
        return None

    def get_rank_counts(self, cards):
        counts = {}
        for card in cards:
            if card.rank in counts:
                counts[card.rank] += 1
            else:
                counts[card.rank] = 1
        return counts

    def get_suite_counts(self, cards):
        counts = {}
        for card in cards:
            if card.suite in counts:
                counts[card.suite] += 1
            else:
                counts[card.suite] = 1
        return counts

    def check_royal_flush(self, cards):
        royal = ["A", "K", "Q", "J", "10"]
        checked_cards = []
        for rank in royal:
            card = self.check_rank_card(cards=cards, rank=rank)
            if card:
                checked_cards.append(card)
            else:
                return None
        suite = checked_cards[0].suite
        for card in checked_cards:
            if suite != card.suite:
                return None
        return True

    def check_straight_flush(self, cards):
        if self.check_straight(cards) and self.check_flush(cards):
            return True
        return None

    def check_four_of_a_kind(self, cards):
        counts = self.get_rank_counts(cards)
        for rank, count in counts.items():
            if count == 4:
                return True
        return None

    def check_full_house(self, cards):
        counts = self.get_rank_counts(cards)
        has_three = False
        has_pair = False
        for rank, count in counts.items():
            if count == 3:
                has_three = True
            if count == 2:
                has_pair = True
        if has_three and has_pair:
            return True
        return None

    def check_flush(self, cards):
        suite_counts = self.get_suite_counts(cards)
        for suite, count in suite_counts.items():
            if count >= 5:
                return True
        return None

    def check_straight(self, cards):
        rank_order = ["A", "K", "Q", "J", "10", "9", "8", "7", "6", "5", "4", "3", "2"]
        card_ranks = []
        for rank in rank_order:
            for card in cards:
                if card.rank == rank and rank not in card_ranks:
                    card_ranks.append(rank)
        for i in range(len(card_ranks) - 4):
            window = card_ranks[i:i + 5]
            positions = [rank_order.index(r) for r in window]
            if positions == list(range(positions[0], positions[0] + 5)):
                return True
        return None

    def check_three_of_a_kind(self, cards):
        counts = self.get_rank_counts(cards)
        for rank, count in counts.items():
            if count == 3:
                return True
        return None

    def check_two_pair(self, cards):
        counts = self.get_rank_counts(cards)
        pairs = 0
        for rank, count in counts.items():
            if count >= 2:
                pairs += 1
        return True if pairs >= 2 else None

    def check_one_pair(self, cards):
        counts = self.get_rank_counts(cards)
        for rank, count in counts.items():
            if count >= 2:
                return True
        return None

    def get_best_hand(self, cards):
        hands = [
            ("Royal Flush",     self.check_royal_flush),
            ("Straight Flush",  self.check_straight_flush),
            ("Four of a Kind",  self.check_four_of_a_kind),
            ("Full House",      self.check_full_house),
            ("Flush",           self.check_flush),
            ("Straight",        self.check_straight),
            ("Three of a Kind", self.check_three_of_a_kind),
            ("Two Pair",        self.check_two_pair),
            ("One Pair",        self.check_one_pair),
        ]
        for hand_name, check_fn in hands:
            if check_fn(cards):
                return hand_name
        return "High Card"

    def check_winner(self):
        human_cards = self.community_cards + self.human.cards
        pc_cards = self.community_cards + self.pc.cards

        human_hand = self.get_best_hand(human_cards)
        pc_hand = self.get_best_hand(pc_cards)

        hand_ranking = [
            "Royal Flush",
            "Straight Flush",
            "Four of a Kind",
            "Full House",
            "Flush",
            "Straight",
            "Three of a Kind",
            "Two Pair",
            "One Pair",
            "High Card",
        ]

        print(f"\n{self.human.name} has: {human_hand}")
        print(f"{self.pc.name} has: {pc_hand}")

        human_rank = hand_ranking.index(human_hand)
        pc_rank = hand_ranking.index(pc_hand)

        if human_rank < pc_rank:
            print(f"\n{self.human.name} wins the pot of ${self.pot}!")
            self.human.amount += self.pot
        elif pc_rank < human_rank:
            print(f"\n{self.pc.name} wins the pot of ${self.pot}!")
            self.pc.amount += self.pot
        else:
            print("\nIt's a tie! Pot is split.")
            split = self.pot // 2
            self.human.amount += split
            self.pc.amount += split

        self.pot = 0

    def betting_round(self):
        print(f"\n-- Betting Round | Pot: ${self.pot} --")
        self.print_player_cards()
        self.print_community_cards()

        if self.turn == self.human:
            amount = self.human.place_initial_bet()
            self.human.bet = amount
            self.pot += amount
            print(f"{self.human.name} bets ${amount}")

            k = 0
            while True:
                result = self.pc.auto_call_raise(player=self.human, k=k)
                if result == "l":
                    print(f"{self.pc.name} folds. {self.human.name} wins ${self.pot}!")
                    self.human.amount += self.pot
                    self.pot = 0
                    return "fold"
                if isinstance(result, int):
                    self.pot += result
                    k += 1
                    print(f"\n-- {self.human.name}, PC raised. Your turn --")
                    response = self.human.call_fold_raise(player=self.pc)
                    if response == "l":
                        print(f"{self.human.name} folds. {self.pc.name} wins ${self.pot}!")
                        self.pc.amount += self.pot
                        self.pot = 0
                        return "fold"
                    if isinstance(response, int):
                        self.pot += response
                        k += 1
                        continue
                break
        else:
            k = 0
            result = self.pc.auto_call_raise(player=self.human, k=k)
            if result == "l":
                print(f"{self.pc.name} folds. {self.human.name} wins ${self.pot}!")
                self.human.amount += self.pot
                self.pot = 0
                return "fold"
            if isinstance(result, int):
                self.pot += result
                k += 1
                print(f"\n-- {self.human.name}, PC bet first. Your turn --")
                response = self.human.call_fold_raise(player=self.pc)
                if response == "l":
                    print(f"{self.human.name} folds. {self.pc.name} wins ${self.pot}!")
                    self.pc.amount += self.pot
                    self.pot = 0
                    return "fold"
                if isinstance(response, int):
                    self.pot += response

        self.human._bet = 0
        self.pc._bet = 0
        return "continue"

    def deal_flop(self):
        self.deck.burn_card()
        for i in range(3):
            self.community_cards.append(self.deck.give_card())
        print("\n-- Flop --")
        self.print_community_cards()

    def deal_turn(self):
        self.deck.burn_card()
        self.community_cards.append(self.deck.give_card())
        print("\n-- Turn --")
        self.print_community_cards()

    def deal_river(self):
        self.deck.burn_card()
        self.community_cards.append(self.deck.give_card())
        print("\n-- River --")
        self.print_community_cards()

    def play(self):
        print("------------ POKER GAME START ------------")
        print(f"{self.human.name} amount: ${self.human.amount}")
        print(f"{self.pc.name} amount: ${self.pc.amount}")
        self.print_player_cards()

        self.turn = self.human
        print("\n-- Pre-Flop Betting --")
        result = self.betting_round()
        if result == "fold":
            return

        self.turn = self.pc
        self.deal_flop()
        result = self.betting_round()
        if result == "fold":
            return

        self.turn = self.human
        self.deal_turn()
        result = self.betting_round()
        if result == "fold":
            return

        self.turn = self.pc
        self.deal_river()
        result = self.betting_round()
        if result == "fold":
            return

        print("\n------------ SHOWDOWN ------------")
        print(f"\n{self.pc.name}'s cards:")
        for card in self.pc.cards:
            card.print_card()
        self.check_winner()

        print(f"\n{self.human.name} final amount: ${self.human.amount}")
        print(f"{self.pc.name} final amount: ${self.pc.amount}")


if __name__ == "__main__":
    game = Game()
    game.play()

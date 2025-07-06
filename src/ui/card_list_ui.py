import wx
from ui.base_ui import HorizontalMenu

from core import utils

from game.card.card import Card


class HorizontalCardList(HorizontalMenu):
    def __init__(self, client, title, cards, escapable=True):
        if not all(isinstance(card, Card) for card in cards):
            raise ValueError("All cards must be of type game.card.card.Card")
        super().__init__(title, repeat_on_boundaries=False)
        self.client = client
        self.cards = cards
        self.escapable = escapable
        # bind keyboard handler, so we can handle space, enter, and backspace
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.populate()

    def populate(self):
        for i, card in enumerate(self.cards):
            print(f"Adding {card.get_name()} to the card list")
            label = self.client.get_duel_field().resolve_labels_for_card(card)
            label = f"{label} {card.get_name()}"
            self.append_item(label, function=lambda i=i: self.finalize(i))

    def select_card(self):
        utils.get_ui_stack().push_ui(self)
        while not self.return_value:
            wx.Yield()
        return self.return_value

    def finalize(self, value):
        self.set_return_value(value)
        utils.get_ui_stack().pop_ui()

    def on_key_down(self, event):
        key = event.GetKeyCode()
        # handle space
        if key == wx.WXK_SPACE:
            # get the current column
            selected_index = self.current_col
            current_card = self.cards[selected_index]
            utils.output(str(current_card))
            return
        # escape to go out of the cardl ist
        if key == wx.WXK_ESCAPE:
            if not self.escapable:
                utils.output("Not allowed")
                return
            self.finalize(-1)
            return
        else:
            if self.client.get_duel_field().preemtive_key_handler:
                if self.client.get_duel_field().preemtive_key_handler(self.client, event):
                    return
            super().on_key_down(event)

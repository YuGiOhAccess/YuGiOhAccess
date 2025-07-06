import glob
import logging

from pathlib import Path

from core import dotdict
from core import variables

from game.card.ydke import Deck

logger = logging.getLogger(__name__)

class Banlist:
    def __init__(self):
        self.name = ""
        self.content = {}      # cardCode -> limit
        self.hash = 0
        self.whitelist = False

    def get_limit(self, card_code):
        if card_code in self.content.keys():
            return self.content[card_code]
        else:
            return 3 # standard limit
        
    def is_deck_allowed(self, deck: Deck) -> {bool, dict}:
        # the decks card pool should be cards + side
        card_pool = deck.cards + deck.side
        times_we_have_seen_cards = {}
        for card_code in card_pool:
            if card_code in times_we_have_seen_cards.keys():
                times_we_have_seen_cards[card_code] += 1
            else:
                times_we_have_seen_cards[card_code] = 1
        reason = {}
        for card_code, times in times_we_have_seen_cards.items():
            if card_code in self.content.keys():
                limit = self.content[card_code]
                if times > limit:
                    reason[card_code] = dotdict.DotDict({"limit": limit, "found": times})
        if len(reason) > 0:
            return False, reason
        else:
            return True, {}

# make the banlist manager a singleton
class BanlistManager:
    _instance = None

    def __new__(cls, banlist_path=None, load_banlists=True):
        if cls._instance is None:
            cls._instance = super(BanlistManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, banlist_path=None, load_banlists=True):
        # Prevent reinitialization on subsequent instantiations
        if hasattr(self, '_initialized') and self._initialized:
            return
        if not banlist_path:
            self.banlists_path = Path(variables.APP_DATA_DIR) / "sync" / "banlists2" / "content"
        else:
            self.banlists_path = Path(banlist_path)
        self.banlists = []
        if load_banlists:
            self.load_all_banlists()
        self._initialized = True

    def get_banlist_names(self):
        return [banlist.name for banlist in self.banlists]
    
    def get_banlist_by_name(self, name):
        for banlist in self.banlists:
            if banlist.name == name:
                return banlist
        return None
    
    def get_banlist_by_hash(self, hash):
        for banlist in self.banlists:
            if banlist.hash == hash:
                return banlist

    def load_banlist(self, filepath):
        """
        Reads one .conf-like file which may contain multiple banlists.
        Each banlist starts with '!' on its own line, e.g.:
           !NameOfBanlist
        Lines of the form '12345678 2' define (cardCode -> limit).
        A line '$whitelist' sets the whitelist flag for the current banlist.
        """
        logger.debug(f"Loading banlist from {filepath}")
        current_banlist = None
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\r\n')
                # Ignore empty lines or comment lines
                if not line or line.startswith('#'):
                    continue

                # Start of a new banlist
                if line.startswith('!'):
                    # If we were already building a banlist with a nonzero hash, add it to the list
                    if current_banlist and current_banlist.hash != 0:
                        self.banlists.append(current_banlist)

                    # Create a new Banlist
                    current_banlist = Banlist()
                    current_banlist.name = line[1:].strip()  # everything after '!'
                    # Set initial hash (from the C++ code) to 0x7dfcee6a
                    current_banlist.hash = 0x7dfcee6a
                    current_banlist.whitelist = False

                # If we see $whitelist, mark the flag
                elif current_banlist and line.startswith('$whitelist'):
                    current_banlist.whitelist = True

                # Otherwise, parse card code + limit
                elif current_banlist and current_banlist.hash != 0:
                    # The C++ code looks for a space, then tries stoul/stol
                    parts = line.split(' ')
                    if len(parts) < 2:
                        continue
                    code_str = parts[0]
                    limit_str = parts[1]

                    try:
                        code = int(code_str)
                        limit = int(limit_str)
                    except ValueError:
                        continue
                    if code == 0:
                        continue

                    # Store cardCode -> limit
                    current_banlist.content[code] = limit

                    # Update the hash
                    #
                    #   lflist.hash = lflist.hash
                    #       ^ ((code << 18) | (code >> 14))
                    #       ^ ((code << (27 + limit)) | (code >> (5 - limit)));
                    #
                    # Emulate 32-bit shifts by masking with 0xFFFFFFFF.
                    # Note: In C++, (code << n) | (code >> m) for n+m=32 is effectively a 32-bit rotate,
                    # but the code does them as separate shifts + OR.
                    
                    def _u32(x):
                        return x & 0xFFFFFFFF  # force 32-bit overflow

                    part1 = _u32(_u32(code << 18) | (code >> 14))
                    
                    # Because (27 + limit) or (5 - limit) could be negative or > 32 if limit is large,
                    # you may want to clamp or handle carefully. The original C++ code doesn’t
                    # explicitly guard against negative shifts, so we’ll do a naive approach:
                    shift_left_amt  = 27 + limit
                    shift_right_amt = 5 - limit
                    # prevent negative shifts (simple clamp to [0..31])
                    if shift_left_amt < 0:
                        shift_left_amt = 0
                    elif shift_left_amt > 31:
                        shift_left_amt = 31

                    if shift_right_amt < 0:
                        shift_right_amt = 0
                    elif shift_right_amt > 31:
                        shift_right_amt = 31

                    part2 = _u32(_u32(code << shift_left_amt) | (code >> shift_right_amt))

                    current_banlist.hash = _u32(
                        current_banlist.hash
                        ^ part1
                        ^ part2
                    )

        # After reading the file, if there's a banlist in progress with a nonzero hash, add it
        if current_banlist and current_banlist.hash != 0:
            self.banlists.append(current_banlist)

    def load_all_banlists(self):
        """Find all .conf files in a folder and load each."""
        # e.g., folderpath + "/*.conf"
        for filepath in glob.glob(str(self.banlists_path / "*.conf")):
            self.load_banlist(filepath)
        no_limit = Banlist()
        no_limit.name = "No limits"
        no_limit.hash = 0
        no_limit.whitelist = False
        self.banlists.append(no_limit)
import re
import time
import threading
import logging
import struct
from datetime import datetime

import wx
from core import dotdict, variables
from core import utils
from game.edo.game_socket import GameSocket
from game.edo import structs, structs_utils
from game.edo import default_values
from game.edo import banlists

from game.card import card_constants
from game.card.location_conversion import LocationConversion

logger = logging.getLogger(__name__)

class Client:
    def __init__(self, server):
        self.server = server
        self._room = None
        self.room_id = None
        self.game_socket = None
        self.packet_event = threading.Event()
        self.expected_packet_id = None
        self.response_packet = None
        self.memory = dotdict.DotDict()
        self.listener_thread = threading.Thread(target=self.packet_listener)
        self.listener_thread.daemon = True
        self.listener_thread.start()
        self.duel_field = None
        self.player = None
        self.turn_count = 0
        self.has_announced_turn_order = False
        self.current_phase = ""
        self._what_player_am_i = -1
        self.is_it_my_turn = False

    @property
    def what_player_am_i(self):
        return self._what_player_am_i
    
    @what_player_am_i.setter
    def what_player_am_i(self, value):
        logger.debug(f"Setting what player am i to {value}")
        self._what_player_am_i = value

    def _connect(self):
        logger.info(f"Connecting to {self.server.address}")
        self.game_socket = GameSocket()
        self.game_socket.connect(self.server.address, self.server.lobby_port)

    def disconnect(self):
        self.game_socket.disconnect()

    def packet_listener(self):
        while True:
            if self.game_socket is None:
                continue
            packet_id, packet_length, packet_data = self.game_socket.recv()
            # if any of them are None, we didn't get a packet
            if packet_id is None or packet_length is None or packet_data is None:
                continue
            if packet_id == self.expected_packet_id or packet_id == structs.ServerIdType.ERROR_MSG:
                self.response_packet = (packet_id, packet_length, packet_data)
                self.packet_event.set()
            self.handle_packet(packet_id, packet_length, packet_data)

    def handle_packet(self, packet_id, packet_length, packet_data):
        # Process general packets
        # loop through structs.ServerIdType and check if the packet_id matches any of the values
        packet_human_name = structs.server_id_type_to_name.get(packet_id, None)
        if packet_human_name is None:
            logger.info(f"Unknown packet id {packet_id}")
            return
        if packet_id not in (structs.ServerIdType.GAME_MSG, structs.ServerIdType.TIME_LIMIT): # we get so many of these, it's not useful to log them
            logger.debug(f"Received packet {packet_human_name}, packet_id {packet_id}")
        packet_handler = utils.packet_handlers.get(packet_id, None)
        if packet_handler:
            wx.CallAfter(packet_handler, self, packet_data, packet_length)
        else:
            logger.error(f"No handler for packet {packet_human_name}, packet_id {packet_id}\nPacket length: {packet_length}\nPacket data: {packet_data}")
            utils.output(f"Received packet {packet_human_name}, packet_id {packet_id}, which was unhandled.")
        

    def wait_for_packet(self, packet_id, timeout=None):
        self.expected_packet_id = packet_id
        self.packet_event.clear()
        self.response_packet = None
        packet_id_human_name = structs.server_id_type_to_name.get(packet_id, None)
        logger.debug(f"Waiting for packet {packet_id_human_name} {packet_id}")
        start_time = datetime.now()
        packet_received = self.packet_event.wait(timeout)
        if packet_received:
            end = datetime.now()
            total_time = end - start_time
            logger.debug(f"Received packet {self.response_packet} in {total_time}")
            return self.response_packet
        else:
            logger.debug(f"Timed out waiting for packet {packet_id}")
            raise TimeoutError("Timed out waiting for packet.")

    def send(self, id, data=None):
        if data is None:
            self.game_socket.send(id)
        else:
            self.game_socket.send(id, bytes(data))


    @staticmethod
    def join_room(server, room_id, password=None):
        """Join the room with the given id, reutrning a client instance if successful."""
        logger.debug("Creating client instance.")
        c = Client(server)
        logger.debug("Connecting...")
        c._connect()
        logger.debug("Sending player nickname...")
        player = structs.PlayerInfo(name=structs_utils.string_to_u16(variables.config.get("nickname"), structs_utils.PASS_NAME_MAX_LENGTH))
        c.send(structs.ClientIdType.PLAYER_INFO, player)
        if not password:
            password = ""
        join_game_packet = structs.JoinGame(
            id=room_id,
            password=structs_utils.string_to_u16(password, structs_utils.PASS_NAME_MAX_LENGTH),
            version=variables.edo_client_version
        )
        c.send(structs.ClientIdType.JOIN_GAME, join_game_packet)
        packet_id, packet_length, packet_data = c.wait_for_packet(structs.ServerIdType.JOIN_GAME)
        if packet_id == structs.ServerIdType.ERROR_MSG:
            return
        structs.StocJoinGame.from_buffer_copy(packet_data)
        c.room_id = room_id
        return c


    @staticmethod
    def create_room(server, room_settings):
        """Create a room with the given settings, returning a client instance if successful."""
        logger.debug(f"Creating room with settings {room_settings}")
        banlist_manager = banlists.BanlistManager()
        if "banlist" not in room_settings:
            selected_banlist = banlist_manager.get_banlist_by_name("No limits")
        else:
            selected_banlist = banlist_manager.get_banlist_by_name(room_settings["banlist"])
        if not selected_banlist:
            logger.error(f"Banlist {room_settings['banlist']} not found, Defaulting to no limits.")
        c = Client(server)
        c._connect()
        player = structs.PlayerInfo(name=structs_utils.string_to_u16(variables.config.get("nickname"), structs_utils.PASS_NAME_MAX_LENGTH))
        c.send(structs.ClientIdType.PLAYER_INFO, player)
        host_info = default_values.HOST_INFO
        if variables.DEV_OPTIONS.no_shuffle:
            host_info.dont_shuffle_deck = 1
        if variables.DEV_OPTIONS.draw:
            host_info.starting_draw_count = variables.DEV_OPTIONS.draw
        # banlist
        # pack the hash into a ctypes.c_uint32
        host_info.banlist_hash = selected_banlist.hash
        create_game_packet = structs.CreateGame(
            host_info= host_info,
            name=structs_utils.string_to_u16(room_settings["name"], structs_utils.PASS_NAME_MAX_LENGTH),
            password=structs_utils.string_to_u16(room_settings["password"], structs_utils.PASS_NAME_MAX_LENGTH),
            notes=room_settings["notes"].encode('utf-8')
        )
        c.send(structs.ClientIdType.CREATE_GAME, create_game_packet)
        packet_id, packet_length, packet_data = c.wait_for_packet(structs.ServerIdType.CREATE_GAME)
        result = structs.StocCreateGame.from_buffer_copy(packet_data)
        c.room_id = result.id
        # add the banlist to memory
        c.memory.room_banlist = selected_banlist
        return c

    @property
    def room(self):
        logger.debug(f"Getting room {self.room_id}")
        if self.room_id:
            logger.debug("Refreshing room")
            self._room = self.server.get_room(self.room_id)
            count = 0
            while not self._room:
                if count > 30:
                    raise TimeoutError("Timed out waiting for room.")
                time.sleep(0.1)
                logger.debug(f"Waiting for room information: {self.room_id}, {count}")
                self._room = self.server.get_room(self.room_id)
                count += 1
        return self._room
    
    @room.setter
    def room(self, value):
        self._room = value

    def get_duel_field(self):
        return self.duel_field
    
    def set_duel_field(self, value):
        self.duel_field = value
    
    # This is helper functions for the duel messages
    def read_cardlist(self, data, extra=False, extra8=False, sequence_size=32):
        res = []
        size = self.read_u32(data)
        for i in range(size):
            code = self.read_u32(data)
            logger.debug(f"Code: {code}")
            controller = self.read_u8(data)
            logger.debug(f"Controller: {controller}, you") if controller == self.what_player_am_i else logger.debug(f"Controller: {controller}, opponent")
            location = card_constants.LOCATION(self.read_u8(data))
            logger.debug(f"Location: {location}, {card_constants.LOCATION(location).name}")
            if sequence_size == 32:
                sequence = self.read_u32(data)
            if sequence_size == 8:
                sequence = self.read_u8(data)
            logger.debug(f"Sequence: {sequence}")
            card = self.get_card(controller, location, sequence)
            if extra:
                if extra8:
                    card.data = self.read_u8(data)
                else:
                    card.data = self.read_u64(data)
                    _ = self.read_u8(data) # client_mode

            res.append(card)
        return res


    def get_card(self, player, location, sequence, max_retries=5, base_delay=0.1):
        for i in range(max_retries):
            resolved_zone_key = LocationConversion(self, player, location, sequence).to_zone_key()
            zone = self.get_duel_field().zones.get(resolved_zone_key, None)
            if zone:
                if zone.card:
                    return zone.card
            time.sleep(base_delay * i)
        logger.warning(f"Zone {resolved_zone_key} not found.\nZones: {self.get_duel_field().zones.keys()}")
        return None
            


    def read_u8(self, buf):
        return struct.unpack('b', buf.read(1))[0]

    def read_u16(self, buf):
        return struct.unpack('h', buf.read(2))[0]

    def read_u32(self, buf):
        return struct.unpack('I', buf.read(4))[0]
    
    def read_u64(self, buf):
        return struct.unpack('Q', buf.read(8))[0]

    def read_location(self, data):
        controller = self.read_u8(data)
        location = self.read_u8(data)
        sequence = self.read_u32(data)
        position = 0
        logger.debug(f"Controller: {controller}, you") if controller == self.what_player_am_i else logger.debug(f"Controller: {controller}, opponent")
        logger.debug(f"Location: {location}, {card_constants.LOCATION(location).name}")
        logger.debug(f"Sequence: {sequence}")
        if (location & card_constants.LOCATION.OVERLAY) == 0:
            position = self.read_u32(data)
        return abs(controller), abs(location), abs(sequence), abs(position)
            

    def flag_to_usable_cardspecs(self, flag, reverse=False):
        pm = flag & 0xff
        ps = (flag >> 8) & 0xff
        om = (flag >> 16) & 0xff
        os = (flag >> 24) & 0xff
        zone_names = ('pm', 'ps', 'om', 'os', 'q', 'pf', 'opf')
        specs = []
        for zn, val in zip(zone_names, (pm, ps, om, os)):
            for i in range(8):
                if reverse:
                    avail = val & (1 << i) != 0
                else:
                    avail = val & (1 << i) == 0
                if avail:
                    # if it's pm and it's i = 5 or i = 6, it's actually em 0 or 1
                    if zn == 'pm' and i in (5, 6):
                        specs.append('q' + str(i - 5))
                        continue
                    # if it's ps6, it's actually pf
                    if zn == 'ps' and i == 6:
                        specs.append('pf')
                        continue
                    # if it's os6, it's actually opf
                    if zn == 'os' and i == 6:
                        specs.append('opf')
                        continue
                    specs.append(zn + str(i))
        return specs

    def zone_label_to_useful_spec(self, text):
        # the text consist of first letters, followed by 1 or more digits
        # to convert it to an useful spec, we need to just increase the digit by 1
        # there can be any amount of letters, then followed by any amount of digits
        # use regex for this
        match = re.match(r"([a-zA-Z]+)(\d+)", text)
        if match:
            letters = match.group(1)
            digits = int(match.group(2))
            return letters + str(digits + 1)

    def useful_spec_to_location(self, spec):
        location = None
        sequence = -1
        opponent= False
        if  spec.startswith('q'):
            location = card_constants.LOCATION.MONSTER_ZONE
            spec = spec[1:]
            # add 5 to the sequence
            sequence = int(spec) + 5
            return location, sequence, opponent
        if spec.startswith('o'):
            opponent = True
            spec = spec[1:]
        else:
            opponent = False
            spec = spec[1:]
        # monster zones are m and e
        if spec.startswith('m'):
            location = card_constants.LOCATION.MONSTER_ZONE
            # spell and trap zones are s
        # spell and trap zones are s
        if spec.startswith('s'):
            location = card_constants.LOCATION.SPELL_AND_TRAP_ZONE
        # field spell zone is f
        if spec.startswith('f'):
            location = card_constants.LOCATION.FIELD_ZONE
        # graveyard is g
        if spec.startswith('g'):
            location = card_constants.LOCATION.GRAVE
        # deck is d
        if spec.startswith('d'):
            location = card_constants.LOCATION.DECK
        # hand is h
        if spec.startswith('h'):
            location = card_constants.LOCATION.HAND
        # extra deck is x
        if spec.startswith('x'):
            location = card_constants.LOCATION.EXTRA
            # removed is r
        if spec.startswith('r'):
            location = card_constants.LOCATION.REMOVED
        text = spec[1:]
        # last thing left should be the sequence
        sequence = int(text)
        return location, sequence, opponent
        
    def unpack_location(self, loc):
        controller = loc & 0xff
        location = card_constants.LOCATION((loc >> 8) & 0xff)
        sequence = (loc >> 16) & 0xff
        position = card_constants.POSITION((loc >> 24) & 0xff)
        return (controller, location, sequence, position)

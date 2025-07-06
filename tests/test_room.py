from pathlib import Path
import json
from game.room import EdoRoom

room_data_file = Path(__file__).parent / "data/rooms.json"
rooms = json.loads(room_data_file.read_text())
room_payload_1 = rooms[0]
room_payload_2 = rooms[1]

room1 = EdoRoom(room_payload_1)
room2 = EdoRoom(room_payload_2)

def test_room_is_valid():
    assert room1.roomid == 1
    assert room2.roomid == 2
    assert isinstance(room1, EdoRoom)
    assert isinstance(room2, EdoRoom)

def test_room_equality_rules():
   assert room1 is not room2
   assert room1 == room1 and room2 == room2

def test_room_str():
    expected = json.dumps(room_payload_1, indent=4)
    assert str(room1) == expected
   
def test_room_print_players():
    expected = "Player1, Player2, "
    assert room1.print_players() == expected

def test_try_to_get_invalid_value():
    try:
        room1.invalid_value
    except AttributeError:
        assert True
    else:
        assert False

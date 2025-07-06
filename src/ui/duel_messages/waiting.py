import io

from core import utils
from core import variables

@utils.duel_message_handler(3)
def msg_waiting(client, data, length):
    data = io.BytesIO(data[1:])
    return waiting(client, data)

def waiting(client, data):
    # for now do nothing
    print("Waiting for something to happen.")

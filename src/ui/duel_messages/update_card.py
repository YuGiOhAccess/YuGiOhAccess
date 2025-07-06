import io
import logging

from core import exceptions
from core import utils

from ui.duel_messages import update_data

logger = logging.getLogger(__name__)

@utils.duel_message_handler(7)
def msg_update_card(client, data, data_length):
    data = io.BytesIO(data[1:])
    controller = client.read_u8(data)
    location = client.read_u8(data)
    sequence = client.read_u8(data)
    query = update_data.parse_queries(client, controller, location, 1, data)
    update_card(client, controller, location, sequence, query)

def update_card(client, controller, location, sequence, query):
    card = client.get_card(controller, location, sequence)
    if not card:
        raise exceptions.CardNotFoundException("Card not found")
    if query:
        logger.error(f"Implement Updating card {card} with query {query}")

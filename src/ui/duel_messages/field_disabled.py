import io

from game.card.location_conversion import LocationConversion

from core import utils
from core import variables

@utils.duel_message_handler(56)
def msg_field_disabled(client, data, data_length):
    data = io.BytesIO(data[1:])
    locations = client.read_u32(data)
    field_disabled(client, locations)

def field_disabled(client, locations):
    specs = client.flag_to_usable_cardspecs(locations, reverse=True)
    locations = []
    for spec in specs:
        locations.append(LocationConversion.from_zone_key(client, spec).to_human_readable())
    utils.output(variables.LANGUAGE_HANDLER._("Field locations %s are disabled.") % ", ".join(locations))

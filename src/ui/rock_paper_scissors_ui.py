from core import utils

from game.edo import structs

from ui.base_ui import HorizontalMenu, StatusMessageWithoutTimelimit

# stage 1 (can repeat)
@utils.packet_handler(structs.ServerIdType.CHOOSE_RPS)
def handle_rock_paper_scissors(client, packet_data, packet_length):
    return show_rock_paper_scissors_ui(client)

@utils.packet_handler(structs.ServerIdType.RPS_RESULT)
def handle_rock_paper_scissors_result(client, packet_data, packet_length):
    message = structs.StocRPSResult.from_buffer_copy(packet_data)
    handle_rps_result(client, message.result0, message.result1)

@utils.packet_handler(structs.ServerIdType.CHOOSE_ORDER)
def handle_choose_order(client, packet_data, packet_length):
    return show_choose_order_ui(client)

@utils.ui_function
def show_rock_paper_scissors_ui(client):
    rps_menu = HorizontalMenu("Rock Paper Scissors")
    rps_menu.append_item("Rock", lambda: send_rps_choice(client, 2))
    rps_menu.append_item("Paper", lambda: send_rps_choice(client, 3))
    rps_menu.append_item("Scissors", lambda: send_rps_choice(client, 1))
    return rps_menu

@utils.ui_function
def send_rps_choice(client, choice):
        # 2 is rock, 3 is paper, 1 is scissors
        rpsresult = structs.RPSChoice()
        rpsresult.choice  = choice
        client.send(structs.ClientIdType.RPS_CHOICE, rpsresult)
        sm = StatusMessageWithoutTimelimit("Waiting for opponent to choose.")
        return sm

@utils.ui_function
def handle_rps_result(client, result0, result1):
    choices = {1: "scissors", 2: "rock", 3: "paper"}
    if result0 == result1:
        utils.output(f"It's a tie. Both players chose {choices[result0]}.")
        return show_rock_paper_scissors_ui(client)
    if (result0 == 2 and result1 == 1) or (result0 == 3 and result1 == 2) or (result0 == 1 and result1 == 3):
        utils.output("You won. You get to choose if you want to go first or second.")
        return # the turn choice ui will automatically pup up due to the packet also being sent.
    return StatusMessageWithoutTimelimit("You lost and have to wait for your opponent to choose if they want to go first or second.")


@utils.ui_function
def show_choose_order_ui(client):
    order_menu = HorizontalMenu("Do you want to go first or second?")
    order_menu.append_item("First", lambda: send_order_choice(client, 1))
    order_menu.append_item("Second", lambda: send_order_choice(client, 0))
    return order_menu

def send_order_choice(client, choice):
    turn_choice = structs.TurnChoice()
    turn_choice.choice = choice
    print(turn_choice)
    client.send(structs.ClientIdType.TURN_CHOICE, turn_choice)

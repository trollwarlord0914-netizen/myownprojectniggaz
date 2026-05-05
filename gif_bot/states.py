from aiogram.fsm.state import State, StatesGroup


class GifStates(StatesGroup):
    # Private chat: waiting for user to send a GIF
    waiting_for_gif = State()

    # Waiting for the user to type their text
    waiting_for_text = State()

    # Main settings menu is shown; user clicks inline buttons
    configuring = State()

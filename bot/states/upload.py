"""Upload states for protocol file submission.

This module defines the FSM states used when admins/moderators upload
new protocol files to the system.
"""

from aiogram.fsm.state import State, StatesGroup


class UploadStates(StatesGroup):
    """States for protocol upload workflow.

    Attributes:
        waiting_year: Waiting for the year input (text or callback).
        choosing_product: User is selecting product from a predefined list.
        waiting_product: Waiting for manual product name input.
        waiting_protocol_no: Waiting for protocol number input.
    """

    waiting_year = State()
    choosing_product = State()
    waiting_product = State()
    waiting_protocol_no = State()


__all__ = ["UploadStates"]

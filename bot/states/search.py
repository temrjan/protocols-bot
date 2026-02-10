"""Search states for protocol lookup by code or text.

This module defines the FSM states used when users search for protocols
by entering a protocol number or product name directly.
"""

from aiogram.fsm.state import State, StatesGroup


class SearchState(StatesGroup):
    """States for text-based protocol search.

    Attributes:
        waiting_text: User is expected to enter a protocol number or product name.
    """

    waiting_text = State()


__all__ = ["SearchState"]

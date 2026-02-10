"""Admin states for moderator management.

This module defines the FSM states used when the primary admin
manages moderator permissions and uploads documents.
"""

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """States for admin operations.

    Attributes:
        waiting_moderator_id: Waiting for Telegram user ID to grant moderator rights.
        waiting_doc_category: Waiting for document category name.
        waiting_doc_file: Waiting for document file upload.
    """

    waiting_moderator_id = State()
    
    # Document upload states
    waiting_doc_category = State()
    waiting_doc_file = State()


__all__ = ["AdminStates"]

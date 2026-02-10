"""Filter states for protocol search by year and product.

This module defines the FSM states used when users search for protocols
using the filter-based approach (year → product).
"""

from aiogram.fsm.state import State, StatesGroup


class FilterStates(StatesGroup):
    """States for filtering protocols by year and product.

    Attributes:
        choosing_year: User is selecting a year from available options.
        choosing_product: User is selecting a product for the chosen year.
    """

    choosing_year = State()
    choosing_product = State()


__all__ = ["FilterStates"]

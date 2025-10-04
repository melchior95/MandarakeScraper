"""
Alert state management - defines the lifecycle of alert items.

States:
- pending: Initial state, awaiting user review
- yay: User marked as interesting/worth buying
- nay: User rejected
- purchased: Item has been purchased
- received: Item has been received
- posted: Item has been posted to eBay
- sold: Item has been sold on eBay
"""

from enum import Enum
from typing import List, Optional


class AlertState(Enum):
    """Alert item states representing the reselling workflow."""
    PENDING = "pending"
    YAY = "yay"
    NAY = "nay"
    PURCHASED = "purchased"
    RECEIVED = "received"
    POSTED = "posted"
    SOLD = "sold"


class AlertStateTransition:
    """Manages valid state transitions for alert items."""

    # Valid state transitions
    TRANSITIONS = {
        AlertState.PENDING: [AlertState.YAY, AlertState.NAY],
        AlertState.YAY: [AlertState.PURCHASED, AlertState.NAY],
        AlertState.NAY: [AlertState.YAY],  # Can reconsider
        AlertState.PURCHASED: [AlertState.RECEIVED],
        AlertState.RECEIVED: [AlertState.POSTED],
        AlertState.POSTED: [AlertState.SOLD],
        AlertState.SOLD: []  # Terminal state
    }

    @classmethod
    def can_transition(cls, from_state: AlertState, to_state: AlertState) -> bool:
        """Check if transition from one state to another is valid."""
        valid_transitions = cls.TRANSITIONS.get(from_state, [])
        return to_state in valid_transitions

    @classmethod
    def get_valid_transitions(cls, from_state: AlertState) -> List[AlertState]:
        """Get list of valid transitions from current state."""
        return cls.TRANSITIONS.get(from_state, [])


class AlertBulkActions:
    """Defines bulk actions available for different states."""

    @staticmethod
    def get_available_actions(states: List[AlertState]) -> List[str]:
        """
        Get available bulk actions based on selected item states.

        Args:
            states: List of states from selected items

        Returns:
            List of action names available for bulk operation
        """
        actions = []

        # If all selected are YAY, can bulk purchase
        if all(s == AlertState.YAY for s in states):
            actions.append("Mark as Purchased")

        # If all selected are PURCHASED, can bulk receive
        if all(s == AlertState.PURCHASED for s in states):
            actions.append("Mark as Received")

        # If all selected are RECEIVED, can bulk post
        if all(s == AlertState.RECEIVED for s in states):
            actions.append("Mark as Posted to eBay")

        # If all selected are POSTED, can bulk sell
        if all(s == AlertState.POSTED for s in states):
            actions.append("Mark as Sold")

        # Universal actions
        if states:
            actions.append("Mark as Yay")
            actions.append("Mark as Nay")
            actions.append("Delete Selected")

        return actions

    @staticmethod
    def get_next_state_for_action(action: str) -> Optional[AlertState]:
        """Map action name to target state."""
        action_map = {
            "Mark as Purchased": AlertState.PURCHASED,
            "Mark as Received": AlertState.RECEIVED,
            "Mark as Posted to eBay": AlertState.POSTED,
            "Mark as Sold": AlertState.SOLD,
            "Mark as Yay": AlertState.YAY,
            "Mark as Nay": AlertState.NAY,
        }
        return action_map.get(action)


def get_state_color(state: AlertState) -> str:
    """Get display color for each state."""
    colors = {
        AlertState.PENDING: "#FFFFFF",  # White
        AlertState.YAY: "#90EE90",      # Light green
        AlertState.NAY: "#FFB6C1",      # Light red
        AlertState.PURCHASED: "#87CEEB", # Sky blue
        AlertState.RECEIVED: "#F0E68C",  # Khaki
        AlertState.POSTED: "#FFD700",    # Gold
        AlertState.SOLD: "#32CD32"       # Lime green
    }
    return colors.get(state, "#FFFFFF")


def get_state_display_name(state: AlertState) -> str:
    """Get human-readable display name for state."""
    names = {
        AlertState.PENDING: "Pending Review",
        AlertState.YAY: "✓ Yay",
        AlertState.NAY: "✗ Nay",
        AlertState.PURCHASED: "Purchased",
        AlertState.RECEIVED: "Received",
        AlertState.POSTED: "Posted",
        AlertState.SOLD: "Sold"
    }
    return names.get(state, state.value)

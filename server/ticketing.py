"""Business rules shared by the ticket entry and checkout flows."""

from datetime import datetime, timedelta


TICKET_PREFIXES = {
    "hourly": "H",
    "daily": "N",
    "monthly": "T",
}
VALID_TICKET_TYPES = frozenset(TICKET_PREFIXES)
MONTHLY_TICKET_VALIDITY = timedelta(days=30)


def ticket_prefix(ticket_type: str) -> str:
    """Return the human-readable ID prefix for a supported ticket type."""
    return TICKET_PREFIXES[ticket_type]


def is_monthly_ticket_valid(start_time: str, now: datetime | None = None) -> bool:
    """A monthly ticket is valid for 30 days from its purchase time."""
    now = now or datetime.now()
    return now < datetime.fromisoformat(start_time) + MONTHLY_TICKET_VALIDITY


def closes_on_checkout(ticket_type: str) -> bool:
    """Only single-use tickets are closed when the vehicle exits."""
    return ticket_type in {"hourly", "daily"}

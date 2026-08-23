# backend/src/naka/enquiry/application/errors.py
from __future__ import annotations


class EnquiryNotFoundError(Exception):
    pass


class InsufficientRoutingCandidatesError(Exception):
    pass


class InvalidRoutingSelectionError(Exception):
    """Raised when an operator's chosen business_ids for RouteEnquiry include
    a business that isn't actually an eligible candidate for this enquiry's
    category and locality - e.g. a stale suggestions list from before the
    business was suspended."""


class AIClientUnavailableError(Exception):
    """Raised when AIClientPort can't reach the underlying provider - missing
    credentials, a network failure, a rate limit. The operator sees a clean
    "try again" message instead of a raw provider stack trace."""

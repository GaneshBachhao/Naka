# backend/src/naka/enquiry/application/errors.py
from __future__ import annotations


class EnquiryNotFoundError(Exception):
    pass


class InsufficientRoutingCandidatesError(Exception):
    pass

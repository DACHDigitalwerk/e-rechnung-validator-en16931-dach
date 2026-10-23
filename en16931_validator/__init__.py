# -*- coding: utf-8 -*-
"""
DACH EN 16931 E-Rechnung Validator
Python package for validating electronic invoices (XRechnung 3.0 & ZUGFeRD 2.2 / Factur-X)
according to EN 16931 and German national business rules.
"""

__version__ = "1.0.0"
__author__ = "DACH Digitalwerk"
__license__ = "MIT"

from .models import (
    InvoiceData,
    ValidationReport,
    RuleResult,
    LineItem,
    Severity,
    Status,
)
from .parser import parse_invoice_xml
from .validator import validate_invoice_xml, calculate_sha256

__all__ = [
    "validate_invoice_xml",
    "parse_invoice_xml",
    "calculate_sha256",
    "InvoiceData",
    "ValidationReport",
    "RuleResult",
    "LineItem",
    "Severity",
    "Status",
]

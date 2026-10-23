# -*- coding: utf-8 -*-
"""
Data models and report structures for EN 16931 E-Rechnung Validator.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Any, Dict
import json


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Status(str, Enum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


@dataclass
class RuleResult:
    rule_id: str
    field_name: str
    status: Status
    severity: Severity
    extracted_value: Any
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "field_name": self.field_name,
            "status": self.status.value,
            "severity": self.severity.value,
            "extracted_value": self.extracted_value,
            "message": self.message,
        }


@dataclass
class LineItem:
    item_id: str
    name: str
    quantity: float
    unit_code: str
    net_price: float
    line_net_amount: float
    vat_rate: float
    vat_category: str = "S"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InvoiceData:
    syntax: str = ""  # 'UBL' or 'CII'
    document_type: str = ""  # 'Invoice' or 'CreditNote'
    profile: str = ""
    specification_id: str = ""
    invoice_id: str = ""
    issue_date: str = ""
    due_date: str = ""
    invoice_type_code: str = "380"
    currency: str = "EUR"
    buyer_reference: str = ""
    
    # Seller Party
    seller_name: str = ""
    seller_vat_id: str = ""
    seller_tax_id: str = ""
    seller_street: str = ""
    seller_city: str = ""
    seller_postcode: str = ""
    seller_country: str = ""

    # Buyer Party
    buyer_name: str = ""
    buyer_vat_id: str = ""
    buyer_street: str = ""
    buyer_city: str = ""
    buyer_postcode: str = ""
    buyer_country: str = ""

    # Monetary Totals
    line_extension_amount: Optional[float] = None
    tax_exclusive_amount: Optional[float] = None  # Net
    tax_total_amount: Optional[float] = None      # Tax
    tax_inclusive_amount: Optional[float] = None  # Gross
    payable_amount: Optional[float] = None

    line_items: List[LineItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["line_items"] = [item.to_dict() for item in self.line_items]
        return res


@dataclass
class ValidationReport:
    is_valid: bool
    standard_name: str
    error_count: int
    warning_count: int
    passed_count: int
    score: int
    invoice_data: InvoiceData
    rules: List[RuleResult] = field(default_factory=list)
    sha256_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validator": "DACH Digitalwerk EN 16931 Validator v1.0.0",
            "is_valid": self.is_valid,
            "standard_name": self.standard_name,
            "summary": {
                "errors": self.error_count,
                "warnings": self.warning_count,
                "passed": self.passed_count,
                "total_rules": len(self.rules),
                "compliance_score": self.score
            },
            "sha256_hash": self.sha256_hash,
            "invoice_data": self.invoice_data.to_dict(),
            "rules": [r.to_dict() for r in self.rules]
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

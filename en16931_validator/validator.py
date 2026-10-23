# -*- coding: utf-8 -*-
"""
Core validation logic for EN 16931 and German national (XRechnung 3.0) business rules.
"""

import hashlib
import re
from typing import List, Tuple, Optional
import os

from .models import (
    InvoiceData,
    ValidationReport,
    RuleResult,
    Status,
    Severity,
)
from .parser import parse_invoice_xml

# Regex for German Leitweg-ID (BT-10 in XRechnung)
# Format: [Grobadresse 2-12 Stelle]-[Feinadresse 0-16 Stellen]-[Pruefziffer 2 Ziffern]
LEITWEG_ID_REGEX = re.compile(r"^[0-9]{2,12}-[0-9A-Za-z]{0,16}-[0-9]{2}$")

# Valid ISO 4217 currency codes commonly used in DACH & EU
ISO_4217_CODES = {
    "EUR", "CHF", "USD", "GBP", "SEK", "DKK", "NOK", "PLN", "CZK", "HUF", "RON", "BGN"
}


def calculate_sha256(content: str) -> str:
    """Calculates SHA-256 hash of XML string or file."""
    if os.path.exists(content):
        with open(content, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest().upper()
    return hashlib.sha256(content.encode("utf-8")).hexdigest().upper()


def validate_invoice_xml(xml_source: str) -> ValidationReport:
    """
    Validates an XML invoice string or file path against EN 16931 and XRechnung rules.
    """
    rules: List[RuleResult] = []
    sha256 = calculate_sha256(xml_source)

    # 1. Parse XML
    data, root, parse_error = parse_invoice_xml(xml_source)

    if parse_error or root is None:
        rules.append(RuleResult(
            rule_id="XML-SYNTAX-01",
            field_name="Wohlgeformtheit",
            status=Status.FAILED,
            severity=Severity.ERROR,
            extracted_value="Ungültiges XML",
            message=parse_error or "Dokument konnte nicht als XML interpretiert werden."
        ))
        return ValidationReport(
            is_valid=False,
            standard_name="Unbekannt (Syntaxfehler)",
            error_count=1,
            warning_count=0,
            passed_count=0,
            score=0,
            invoice_data=data,
            rules=rules,
            sha256_hash=sha256
        )

    # 2. Syntax OK
    rules.append(RuleResult(
        rule_id="XML-SYNTAX-01",
        field_name="Wohlgeformtheit",
        status=Status.PASSED,
        severity=Severity.INFO,
        extracted_value="Wohlgeformtes XML",
        message="Das XML-Dokument ist syntaktisch wohlgeformt."
    ))

    # 3. Document Root Recognition
    if data.syntax == "UNKNOWN":
        rules.append(RuleResult(
            rule_id="ROOT-ELEM-01",
            field_name="Root-Element",
            status=Status.FAILED,
            severity=Severity.ERROR,
            extracted_value=data.document_type,
            message="Unbekanntes Wurzelelement. Erwartet wird <Invoice>, <CreditNote> (UBL) oder <CrossIndustryInvoice> (CII)."
        ))
        return ValidationReport(
            is_valid=False,
            standard_name="Unbekannt",
            error_count=1,
            warning_count=0,
            passed_count=1,
            score=10,
            invoice_data=data,
            rules=rules,
            sha256_hash=sha256
        )

    rules.append(RuleResult(
        rule_id="ROOT-ELEM-01",
        field_name="Root-Element & Syntax",
        status=Status.PASSED,
        severity=Severity.INFO,
        extracted_value=f"{data.syntax} ({data.document_type})",
        message=f"Gültiges E-Rechnungsformat erkannt: {data.syntax} ({data.document_type})"
    ))

    # Determine Standard Name
    standard_name = f"{data.syntax} EN 16931"
    is_xrechnung = "xrechnung" in (data.specification_id or "").lower() or "xrechnung" in (data.profile or "").lower()
    if is_xrechnung:
        standard_name = "XRechnung 3.0 / EN 16931"
    elif data.syntax == "CII":
        standard_name = "ZUGFeRD 2.2 / Factur-X (CII)"

    # BT-24 Specification & Profile Check
    spec_id = data.specification_id or data.profile
    if not spec_id:
        rules.append(RuleResult(
            rule_id="BT-24",
            field_name="Spezifikationskennung",
            status=Status.WARNING,
            severity=Severity.WARNING,
            extracted_value="Fehlt",
            message="BT-24 (CustomizationID) fehlt. Empfohlen: urn:cen.eu:en16931:2017 oder KoSIT XRechnung-Kennung."
        ))
    else:
        spec_lower = spec_id.lower()
        if "minimum" in spec_lower or "basicwl" in spec_lower:
            rules.append(RuleResult(
                rule_id="BT-24",
                field_name="Profil-Konformität",
                status=Status.WARNING,
                severity=Severity.WARNING,
                extracted_value=spec_id,
                message="ZUGFeRD Profil MINIMUM/BASIC WL erfüllt ab 2026 NICHT die gesetzliche B2B-E-Rechnungspflicht für den Vorsteuerabzug nach § 14 UStG!"
            ))
        else:
            rules.append(RuleResult(
                rule_id="BT-24",
                field_name="Spezifikationskennung",
                status=Status.PASSED,
                severity=Severity.INFO,
                extracted_value=spec_id,
                message="Gültige Spezifikationskennung nach EN 16931 / XRechnung."
            ))

    # BT-1 Invoice Number
    if not data.invoice_id or not data.invoice_id.strip():
        rules.append(RuleResult(
            rule_id="BT-1",
            field_name="Rechnungsnummer",
            status=Status.FAILED,
            severity=Severity.ERROR,
            extracted_value="FEHLT",
            message="Pflichtfeld BT-1 (Rechnungsnummer) ist zwingend nach § 14 Abs. 4 Nr. 4 UStG."
        ))
    else:
        rules.append(RuleResult(
            rule_id="BT-1",
            field_name="Rechnungsnummer",
            status=Status.PASSED,
            severity=Severity.INFO,
            extracted_value=data.invoice_id,
            message="Rechnungsnummer vorhanden."
        ))

    # BT-2 Issue Date
    if not data.issue_date or not data.issue_date.strip():
        rules.append(RuleResult(
            rule_id="BT-2",
            field_name="Rechnungsdatum",
            status=Status.FAILED,
            severity=Severity.ERROR,
            extracted_value="FEHLT",
            message="Pflichtfeld BT-2 (Ausstellungsdatum) ist zwingend vorgeschrieben."
        ))
    else:
        # Check date format YYYY-MM-DD or YYYYMMDD
        date_clean = data.issue_date.strip()
        is_iso_date = bool(re.match(r"^\d{4}-\d{2}-\d{2}$", date_clean) or re.match(r"^\d{8}$", date_clean))
        if is_iso_date:
            rules.append(RuleResult(
                rule_id="BT-2",
                field_name="Rechnungsdatum",
                status=Status.PASSED,
                severity=Severity.INFO,
                extracted_value=date_clean,
                message="Valides ISO-Rechnungsdatum vorhanden."
            ))
        else:
            rules.append(RuleResult(
                rule_id="BT-2",
                field_name="Rechnungsdatum Format",
                status=Status.WARNING,
                severity=Severity.WARNING,
                extracted_value=date_clean,
                message="Rechnungsdatum entspricht nicht dem Standardformat YYYY-MM-DD."
            ))

    # BT-3 Invoice Type Code
    if not data.invoice_type_code:
        rules.append(RuleResult(
            rule_id="BT-3",
            field_name="Rechnungstypcode",
            status=Status.WARNING,
            severity=Severity.WARNING,
            extracted_value="Nicht angegeben",
            message="Kein UNTDID 1001 Rechnungstypcode angegeben (Standard: 380)."
        ))
    else:
        rules.append(RuleResult(
            rule_id="BT-3",
            field_name="Rechnungstypcode",
            status=Status.PASSED,
            severity=Severity.INFO,
            extracted_value=data.invoice_type_code,
            message="Rechnungstypcode vorhanden."
        ))

    # BT-5 Currency Code
    curr = (data.currency or "").strip().upper()
    if not curr or len(curr) != 3:
        rules.append(RuleResult(
            rule_id="BT-5",
            field_name="Rechnungswährung",
            status=Status.FAILED,
            severity=Severity.ERROR,
            extracted_value=data.currency or "LEER",
            message="BT-5 muss ein 3-stelliger ISO 4217 Währungscode sein (z.B. EUR, CHF)."
        ))
    elif curr not in ISO_4217_CODES:
        rules.append(RuleResult(
            rule_id="BT-5",
            field_name="Rechnungswährung",
            status=Status.WARNING,
            severity=Severity.WARNING,
            extracted_value=curr,
            message=f"Ungewöhnlicher Währungscode: {curr}."
        ))
    else:
        rules.append(RuleResult(
            rule_id="BT-5",
            field_name="Rechnungswährung",
            status=Status.PASSED,
            severity=Severity.INFO,
            extracted_value=curr,
            message=f"Gültige Währung: {curr}."
        ))

    # BT-10 Buyer Reference / Leitweg-ID
    b_ref = (data.buyer_reference or "").strip()
    if not b_ref:
        if is_xrechnung:
            rules.append(RuleResult(
                rule_id="BR-DE-01 / BT-10",
                field_name="Leitweg-ID",
                status=Status.FAILED,
                severity=Severity.ERROR,
                extracted_value="FEHLT",
                message="In der XRechnung (B2G Deutschland) ist die Leitweg-ID im Feld BT-10 zwingend erforderlich!"
            ))
        else:
            rules.append(RuleResult(
                rule_id="BT-10",
                field_name="Käuferreferenz (BuyerReference)",
                status=Status.WARNING,
                severity=Severity.WARNING,
                extracted_value="Nicht angegeben",
                message="Käuferreferenz (BT-10) nicht hinterlegt. Für B2G Rechnungen als Leitweg-ID zwingend."
            ))
    else:
        clean_ref = b_ref.replace(" ", "")
        if is_xrechnung and not LEITWEG_ID_REGEX.match(clean_ref):
            rules.append(RuleResult(
                rule_id="BR-DE-01 / BT-10",
                field_name="Leitweg-ID Format",
                status=Status.WARNING,
                severity=Severity.WARNING,
                extracted_value=b_ref,
                message=f"Leitweg-ID '{b_ref}' entspricht nicht dem Standard-Grobformat (z.B. 04011000-12345-12)."
            ))
        else:
            rules.append(RuleResult(
                rule_id="BT-10",
                field_name="Käuferreferenz / Leitweg-ID",
                status=Status.PASSED,
                severity=Severity.INFO,
                extracted_value=b_ref,
                message="Gültige Käuferreferenz / Leitweg-ID vorhanden."
            ))

    # BT-27 Seller Name
    if not data.seller_name or not data.seller_name.strip():
        rules.append(RuleResult(
            rule_id="BT-27",
            field_name="Verkäufer Firmenname",
            status=Status.FAILED,
            severity=Severity.ERROR,
            extracted_value="FEHLT",
            message="Pflichtangabe BT-27 (Name des leistenden Unternehmers) fehlt nach § 14 UStG."
        ))
    else:
        rules.append(RuleResult(
            rule_id="BT-27",
            field_name="Verkäufer Firmenname",
            status=Status.PASSED,
            severity=Severity.INFO,
            extracted_value=data.seller_name,
            message="Verkäufer Firmenname vorhanden."
        ))

    # BT-31 / BT-32 Seller Tax Identifiers
    has_vat = bool(data.seller_vat_id and data.seller_vat_id.strip())
    has_tax = bool(data.seller_tax_id and data.seller_tax_id.strip())
    if not has_vat and not has_tax:
        rules.append(RuleResult(
            rule_id="BT-31 / BT-32",
            field_name="Steuernummer / USt-IdNr",
            status=Status.FAILED,
            severity=Severity.ERROR,
            extracted_value="FEHLT",
            message="Mindestens eine USt-IdNr (BT-31) oder Steuernummer (BT-32) des Verkäufers ist nach § 14 Abs. 4 Nr. 2 UStG zwingend!"
        ))
    else:
        tax_val = data.seller_vat_id or data.seller_tax_id
        rules.append(RuleResult(
            rule_id="BT-31 / BT-32",
            field_name="Steuernummer / USt-IdNr",
            status=Status.PASSED,
            severity=Severity.INFO,
            extracted_value=tax_val,
            message="Steuer-Identifikation des Verkäufers vorhanden."
        ))

    # BT-44 Buyer Name
    if not data.buyer_name or not data.buyer_name.strip():
        rules.append(RuleResult(
            rule_id="BT-44",
            field_name="Käufer Firmenname",
            status=Status.FAILED,
            severity=Severity.ERROR,
            extracted_value="FEHLT",
            message="Pflichtangabe BT-44 (Name des Leistungsempfängers) fehlt nach § 14 UStG."
        ))
    else:
        rules.append(RuleResult(
            rule_id="BT-44",
            field_name="Käufer Firmenname",
            status=Status.PASSED,
            severity=Severity.INFO,
            extracted_value=data.buyer_name,
            message="Käufer Firmenname vorhanden."
        ))

    # BT-109 Net Amount
    if data.tax_exclusive_amount is None:
        rules.append(RuleResult(
            rule_id="BT-109",
            field_name="Gesamtnetto (BT-109)",
            status=Status.FAILED,
            severity=Severity.ERROR,
            extracted_value="FEHLT",
            message="Gesamtnettobetrag der Rechnung (BT-109) fehlt."
        ))
    else:
        rules.append(RuleResult(
            rule_id="BT-109",
            field_name="Gesamtnetto (BT-109)",
            status=Status.PASSED,
            severity=Severity.INFO,
            extracted_value=f"{data.tax_exclusive_amount:.2f} {data.currency}",
            message="Gesamtnettobetrag vorhanden."
        ))

    # BT-110 Tax Total Amount
    if data.tax_total_amount is None:
        rules.append(RuleResult(
            rule_id="BT-110",
            field_name="Gesamtsteuer (BT-110)",
            status=Status.FAILED,
            severity=Severity.ERROR,
            extracted_value="FEHLT",
            message="Gesamtsteuerbetrag (BT-110) fehlt."
        ))
    else:
        rules.append(RuleResult(
            rule_id="BT-110",
            field_name="Gesamtsteuer (BT-110)",
            status=Status.PASSED,
            severity=Severity.INFO,
            extracted_value=f"{data.tax_total_amount:.2f} {data.currency}",
            message="Gesamtsteuerbetrag vorhanden."
        ))

    # BT-112 Gross Amount
    if data.tax_inclusive_amount is None:
        rules.append(RuleResult(
            rule_id="BT-112",
            field_name="Gesamtbrutto (BT-112)",
            status=Status.FAILED,
            severity=Severity.ERROR,
            extracted_value="FEHLT",
            message="Rechnungsbruttobetrag (BT-112) fehlt."
        ))
    else:
        rules.append(RuleResult(
            rule_id="BT-112",
            field_name="Gesamtbrutto (BT-112)",
            status=Status.PASSED,
            severity=Severity.INFO,
            extracted_value=f"{data.tax_inclusive_amount:.2f} {data.currency}",
            message="Rechnungsbruttobetrag vorhanden."
        ))

    # BR-CO-15 Mathematical Consistency: Net + Tax == Gross (+/- 0.02)
    if (data.tax_exclusive_amount is not None and
        data.tax_total_amount is not None and
        data.tax_inclusive_amount is not None):
        expected_gross = data.tax_exclusive_amount + data.tax_total_amount
        diff = abs(expected_gross - data.tax_inclusive_amount)
        if diff > 0.02:
            rules.append(RuleResult(
                rule_id="BR-CO-15",
                field_name="Mathematische Betragskonsistenz",
                status=Status.FAILED,
                severity=Severity.ERROR,
                extracted_value=f"Netto ({data.tax_exclusive_amount:.2f}) + USt ({data.tax_total_amount:.2f}) != Brutto ({data.tax_inclusive_amount:.2f})",
                message=f"Differenz von {diff:.2f} € übersteigt die EN 16931 Rundungstoleranz von 0.02 €!"
            ))
        else:
            rules.append(RuleResult(
                rule_id="BR-CO-15",
                field_name="Mathematische Betragskonsistenz",
                status=Status.PASSED,
                severity=Severity.INFO,
                extracted_value=f"{data.tax_exclusive_amount:.2f} + {data.tax_total_amount:.2f} = {data.tax_inclusive_amount:.2f} {data.currency}",
                message="Mathematische Gesamtsummenprüfung erfolgreich (BR-CO-15 erfüllt)."
            ))

    # Invoice Lines Check (BR-06 / BT-126)
    if len(data.line_items) == 0:
        rules.append(RuleResult(
            rule_id="BR-06 / BT-126",
            field_name="Rechnungspositionen",
            status=Status.FAILED,
            severity=Severity.ERROR,
            extracted_value="0 Positionen",
            message="Mindestens eine Rechnungsposition ist nach EN 16931 zwingend erforderlich."
        ))
    else:
        rules.append(RuleResult(
            rule_id="BR-06 / BT-126",
            field_name="Rechnungspositionen",
            status=Status.PASSED,
            severity=Severity.INFO,
            extracted_value=f"{len(data.line_items)} Position(en)",
            message=f"{len(data.line_items)} Rechnungsposition(en) vollständig erfasst."
        ))

    # Summary Counts
    errors = sum(1 for r in rules if r.status == Status.FAILED)
    warnings = sum(1 for r in rules if r.status == Status.WARNING)
    passed = sum(1 for r in rules if r.status == Status.PASSED)

    total_rules = len(rules) or 1
    score = max(0, min(100, int(((passed + warnings * 0.5) / total_rules) * 100)))

    return ValidationReport(
        is_valid=(errors == 0),
        standard_name=standard_name,
        error_count=errors,
        warning_count=warnings,
        passed_count=passed,
        score=score,
        invoice_data=data,
        rules=rules,
        sha256_hash=sha256
    )

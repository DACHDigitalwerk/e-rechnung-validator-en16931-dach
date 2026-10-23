# -*- coding: utf-8 -*-
"""
Unit test suite for EN 16931 E-Rechnung Validator.
Covers UBL, CII, syntax errors, Leitweg-ID checks, business rules & CLI.
"""

import unittest
import json
import subprocess
import sys
import os

from en16931_validator import (
    validate_invoice_xml,
    parse_invoice_xml,
    ValidationReport,
    __version__,
)
from en16931_validator.cli import SAMPLE_XRECHNUNG_XML, SAMPLE_ZUGFERD_XML


class TestEn16931Validator(unittest.TestCase):

    def test_01_package_version(self):
        """Verifies package version is defined."""
        self.assertEqual(__version__, "1.0.0")

    def test_02_valid_xrechnung_ubl(self):
        """Tests that a compliant XRechnung 3.0 UBL invoice passes validation."""
        report = validate_invoice_xml(SAMPLE_XRECHNUNG_XML)
        self.assertTrue(report.is_valid)
        self.assertEqual(report.error_count, 0)
        self.assertEqual(report.invoice_data.invoice_id, "RE-2026-0815")
        self.assertEqual(report.invoice_data.currency, "EUR")
        self.assertEqual(report.invoice_data.buyer_reference, "04011000-12345-12")
        self.assertAlmostEqual(report.invoice_data.tax_inclusive_amount, 1785.00)
        self.assertGreaterEqual(report.score, 90)

    def test_03_valid_zugferd_cii(self):
        """Tests that a compliant ZUGFeRD 2.2 / Factur-X CII invoice passes validation."""
        report = validate_invoice_xml(SAMPLE_ZUGFERD_XML)
        self.assertTrue(report.is_valid)
        self.assertEqual(report.error_count, 0)
        self.assertEqual(report.invoice_data.invoice_id, "ZUG-2026-9901")
        self.assertEqual(report.invoice_data.issue_date, "2026-02-20")
        self.assertEqual(report.invoice_data.seller_name, "AlpenTech Solutions AG")
        self.assertAlmostEqual(report.invoice_data.tax_inclusive_amount, 3451.00)
        self.assertEqual(len(report.invoice_data.line_items), 1)

    def test_04_valid_credit_note_ubl(self):
        """Tests that a UBL CreditNote (Gutschrift) is properly parsed and validated."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<CreditNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
            xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
            xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:CustomizationID>urn:cen.eu:en16931:2017</cbc:CustomizationID>
  <cbc:ID>GS-2026-101</cbc:ID>
  <cbc:IssueDate>2026-03-01</cbc:IssueDate>
  <cbc:CreditNoteTypeCode>381</cbc:CreditNoteTypeCode>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyName><cbc:Name>Lieferant GmbH</cbc:Name></cac:PartyName>
      <cac:PartyTaxScheme><cbc:CompanyID>DE999999999</cbc:CompanyID></cac:PartyTaxScheme>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyName><cbc:Name>Kunde AG</cbc:Name></cac:PartyName>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:TaxTotal><cbc:TaxAmount currencyID="EUR">19.00</cbc:TaxAmount></cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">100.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">119.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="EUR">119.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:CreditNoteLine>
    <cbc:ID>1</cbc:ID>
    <cbc:CreditedQuantity unitCode="C62">1.00</cbc:CreditedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cac:Item><cbc:Name>Gutschrift Retoure</cbc:Name></cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">100.00</cbc:PriceAmount></cac:Price>
  </cac:CreditNoteLine>
</CreditNote>"""
        report = validate_invoice_xml(xml)
        self.assertTrue(report.is_valid)
        self.assertEqual(report.invoice_data.document_type, "CreditNote")
        self.assertEqual(report.invoice_data.invoice_id, "GS-2026-101")
        self.assertEqual(report.error_count, 0)

    def test_05_syntax_malformed_xml(self):
        """Tests handling of malformed XML."""
        malformed = "<Invoice><cbc:ID>123</cbc:ID>"  # Missing closing tag
        report = validate_invoice_xml(malformed)
        self.assertFalse(report.is_valid)
        self.assertEqual(report.error_count, 1)
        self.assertTrue(any(r.rule_id == "XML-SYNTAX-01" for r in report.rules))

    def test_06_unknown_root_element(self):
        """Tests error when root element is not an invoice."""
        xml = "<Root><Content>Random</Content></Root>"
        report = validate_invoice_xml(xml)
        self.assertFalse(report.is_valid)
        self.assertTrue(any(r.rule_id == "ROOT-ELEM-01" for r in report.rules))

    def test_07_missing_bt1_invoice_number(self):
        """Tests error when BT-1 (invoice number) is absent."""
        xml = SAMPLE_XRECHNUNG_XML.replace("<cbc:ID>RE-2026-0815</cbc:ID>", "<cbc:ID></cbc:ID>")
        report = validate_invoice_xml(xml)
        self.assertFalse(report.is_valid)
        self.assertTrue(any(r.rule_id == "BT-1" and r.status.value == "failed" for r in report.rules))

    def test_08_missing_bt2_issue_date(self):
        """Tests error when BT-2 (issue date) is missing."""
        xml = SAMPLE_XRECHNUNG_XML.replace("<cbc:IssueDate>2026-02-15</cbc:IssueDate>", "")
        report = validate_invoice_xml(xml)
        self.assertFalse(report.is_valid)
        self.assertTrue(any(r.rule_id == "BT-2" and r.status.value == "failed" for r in report.rules))

    def test_09_invalid_date_format_warning(self):
        """Tests warning when date format is not ISO."""
        xml = SAMPLE_XRECHNUNG_XML.replace("<cbc:IssueDate>2026-02-15</cbc:IssueDate>", "<cbc:IssueDate>15.02.2026</cbc:IssueDate>")
        report = validate_invoice_xml(xml)
        self.assertTrue(any(r.rule_id == "BT-2" and r.status.value == "warning" for r in report.rules))

    def test_10_missing_bt5_currency_code(self):
        """Tests error when currency code is missing or invalid length."""
        xml = SAMPLE_XRECHNUNG_XML.replace("<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>", "<cbc:DocumentCurrencyCode>EUROPE</cbc:DocumentCurrencyCode>")
        report = validate_invoice_xml(xml)
        self.assertFalse(report.is_valid)
        self.assertTrue(any(r.rule_id == "BT-5" and r.status.value == "failed" for r in report.rules))

    def test_11_missing_bt10_in_xrechnung(self):
        """Tests that missing Leitweg-ID (BT-10) in XRechnung profile triggers error BR-DE-01."""
        xml = SAMPLE_XRECHNUNG_XML.replace("<cbc:BuyerReference>04011000-12345-12</cbc:BuyerReference>", "")
        report = validate_invoice_xml(xml)
        self.assertFalse(report.is_valid)
        self.assertTrue(any(r.rule_id == "BR-DE-01 / BT-10" and r.status.value == "failed" for r in report.rules))

    def test_12_invalid_leitweg_id_format(self):
        """Tests that improperly formatted Leitweg-ID generates a warning."""
        xml = SAMPLE_XRECHNUNG_XML.replace("04011000-12345-12", "ABC_NOT_VALID")
        report = validate_invoice_xml(xml)
        self.assertTrue(any(r.rule_id == "BR-DE-01 / BT-10" and r.status.value == "warning" for r in report.rules))

    def test_13_missing_seller_name_bt27(self):
        """Tests error when seller name (BT-27) is missing."""
        xml = SAMPLE_XRECHNUNG_XML.replace("<cbc:RegistrationName>Muster Digitalwerk GmbH</cbc:RegistrationName>", "")
        xml = xml.replace("<cbc:Name>Muster Digitalwerk GmbH</cbc:Name>", "")
        report = validate_invoice_xml(xml)
        self.assertFalse(report.is_valid)
        self.assertTrue(any(r.rule_id == "BT-27" and r.status.value == "failed" for r in report.rules))

    def test_14_missing_seller_tax_identifier_bt31_32(self):
        """Tests error when both VAT ID and Tax ID of seller are missing."""
        xml = SAMPLE_XRECHNUNG_XML.replace("<cbc:CompanyID>DE123456789</cbc:CompanyID>", "")
        report = validate_invoice_xml(xml)
        self.assertFalse(report.is_valid)
        self.assertTrue(any(r.rule_id == "BT-31 / BT-32" and r.status.value == "failed" for r in report.rules))

    def test_15_missing_buyer_name_bt44(self):
        """Tests error when buyer name (BT-44) is missing."""
        xml = SAMPLE_XRECHNUNG_XML.replace("<cbc:RegistrationName>Bundesamt für Digitalisierung</cbc:RegistrationName>", "")
        xml = xml.replace("<cbc:Name>Bundesamt für Digitalisierung</cbc:Name>", "")
        report = validate_invoice_xml(xml)
        self.assertFalse(report.is_valid)
        self.assertTrue(any(r.rule_id == "BT-44" and r.status.value == "failed" for r in report.rules))

    def test_16_math_mismatch_br_co_15(self):
        """Tests calculation error when Net + Tax != Gross."""
        # Change Gross to 1999.00 while Net is 1500 and Tax is 285 (expected Gross: 1785.00)
        xml = SAMPLE_XRECHNUNG_XML.replace("<cbc:TaxInclusiveAmount currencyID=\"EUR\">1785.00</cbc:TaxInclusiveAmount>",
                                           "<cbc:TaxInclusiveAmount currencyID=\"EUR\">1999.00</cbc:TaxInclusiveAmount>")
        report = validate_invoice_xml(xml)
        self.assertFalse(report.is_valid)
        self.assertTrue(any(r.rule_id == "BR-CO-15" and r.status.value == "failed" for r in report.rules))

    def test_17_zero_line_items_error(self):
        """Tests error when invoice contains 0 line items."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:CustomizationID>urn:cen.eu:en16931:2017</cbc:CustomizationID>
  <cbc:ID>INV-EMPTY</cbc:ID>
  <cbc:IssueDate>2026-03-01</cbc:IssueDate>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party><cac:PartyName><cbc:Name>Firma</cbc:Name></cac:PartyName><cac:PartyTaxScheme><cbc:CompanyID>DE111</cbc:CompanyID></cac:PartyTaxScheme></cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party><cac:PartyName><cbc:Name>Kunde</cbc:Name></cac:PartyName></cac:Party>
  </cac:AccountingCustomerParty>
  <cac:TaxTotal><cbc:TaxAmount currencyID="EUR">0.00</cbc:TaxAmount></cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:TaxExclusiveAmount currencyID="EUR">0.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">0.00</cbc:TaxInclusiveAmount>
  </cac:LegalMonetaryTotal>
</Invoice>"""
        report = validate_invoice_xml(xml)
        self.assertFalse(report.is_valid)
        self.assertTrue(any(r.rule_id == "BR-06 / BT-126" and r.status.value == "failed" for r in report.rules))

    def test_18_zugferd_minimum_profile_warning(self):
        """Tests that ZUGFeRD MINIMUM profile generates a warning for 2026 tax compliance."""
        xml = SAMPLE_ZUGFERD_XML.replace("urn:cen.eu:en16931:2017", "urn:factur-x.eu:1p0:minimum")
        report = validate_invoice_xml(xml)
        self.assertTrue(any(r.rule_id == "BT-24" and r.status.value == "warning" for r in report.rules))

    def test_19_json_report_serialization(self):
        """Tests that the report serializes to valid JSON with all required keys."""
        report = validate_invoice_xml(SAMPLE_XRECHNUNG_XML)
        json_str = report.to_json()
        parsed = json.loads(json_str)
        self.assertIn("validator", parsed)
        self.assertIn("is_valid", parsed)
        self.assertIn("summary", parsed)
        self.assertIn("invoice_data", parsed)
        self.assertIn("rules", parsed)
        self.assertEqual(parsed["is_valid"], True)

    def test_20_cli_sample_generation(self):
        """Tests CLI sample generation for xrechnung and zugferd."""
        from en16931_validator.cli import SAMPLE_XRECHNUNG_XML, SAMPLE_ZUGFERD_XML
        self.assertIn("RE-2026-0815", SAMPLE_XRECHNUNG_XML)
        self.assertIn("ZUG-2026-9901", SAMPLE_ZUGFERD_XML)


if __name__ == "__main__":
    unittest.main()

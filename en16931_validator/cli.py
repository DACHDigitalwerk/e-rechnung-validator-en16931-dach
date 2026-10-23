# -*- coding: utf-8 -*-
"""
CLI Tool: en16931-val
Syntax- und Pflichtfeld-Prüfer für UBL und CII XML-Rechnungen.
"""

import sys
import argparse
import os

try:
    from .validator import validate_invoice_xml
except ImportError:
    from en16931_validator.validator import validate_invoice_xml

SAMPLE_XRECHNUNG_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_3.0</cbc:CustomizationID>
  <cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID>
  <cbc:ID>RE-2026-0815</cbc:ID>
  <cbc:IssueDate>2026-02-15</cbc:IssueDate>
  <cbc:DueDate>2026-03-15</cbc:DueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cbc:BuyerReference>04011000-12345-12</cbc:BuyerReference>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyName>
        <cbc:Name>Muster Digitalwerk GmbH</cbc:Name>
      </cac:PartyName>
      <cac:PostalAddress>
        <cbc:StreetName>Hauptstraße 42</cbc:StreetName>
        <cbc:CityName>Berlin</cbc:CityName>
        <cbc:PostalZone>10115</cbc:PostalZone>
        <cac:Country>
          <cbc:IdentificationCode>DE</cbc:IdentificationCode>
        </cac:Country>
      </cac:PostalAddress>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>DE123456789</cbc:CompanyID>
        <cac:TaxScheme>
          <cbc:ID>VAT</cbc:ID>
        </cac:TaxScheme>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Muster Digitalwerk GmbH</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyName>
        <cbc:Name>Bundesamt für Digitalisierung</cbc:Name>
      </cac:PartyName>
      <cac:PostalAddress>
        <cbc:StreetName>Willy-Brandt-Straße 1</cbc:StreetName>
        <cbc:CityName>Berlin</cbc:CityName>
        <cbc:PostalZone>10557</cbc:PostalZone>
        <cac:Country>
          <cbc:IdentificationCode>DE</cbc:IdentificationCode>
        </cac:Country>
      </cac:PostalAddress>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Bundesamt für Digitalisierung</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">285.00</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">1500.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">285.00</cbc:TaxAmount>
      <cac:TaxCategory>
        <cbc:ID>S</cbc:ID>
        <cbc:Percent>19.00</cbc:Percent>
        <cac:TaxScheme>
          <cbc:ID>VAT</cbc:ID>
        </cac:TaxScheme>
      </cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">1500.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">1500.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">1785.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="EUR">1785.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="HUR">10.00</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">1500.00</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Name>Software-Beratung und EN 16931 Implementierung</cbc:Name>
      <cac:ClassifiedTaxCategory>
        <cbc:ID>S</cbc:ID>
        <cbc:Percent>19.00</cbc:Percent>
        <cac:TaxScheme>
          <cbc:ID>VAT</cbc:ID>
        </cac:TaxScheme>
      </cac:ClassifiedTaxCategory>
    </cac:Item>
    <cac:Price>
      <cbc:PriceAmount currencyID="EUR">150.00</cbc:PriceAmount>
    </cac:Price>
  </cac:InvoiceLine>
</Invoice>"""

SAMPLE_ZUGFERD_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                          xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
                          xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocumentContext>
    <ram:GuidelineSpecifiedDocumentContextParameter>
      <ram:ID>urn:cen.eu:en16931:2017</ram:ID>
    </ram:GuidelineSpecifiedDocumentContextParameter>
  </rsm:ExchangedDocumentContext>
  <rsm:ExchangedDocument>
    <ram:ID>ZUG-2026-9901</ram:ID>
    <ram:TypeCode>380</ram:TypeCode>
    <ram:IssueDateTime>
      <udt:DateTimeString format="102">20260220</udt:DateTimeString>
    </ram:IssueDateTime>
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:IncludedSupplyChainTradeLineItem>
      <ram:AssociatedDocumentLineDocument>
        <ram:LineID>1</ram:LineID>
      </ram:AssociatedDocumentLineDocument>
      <ram:SpecifiedTradeProduct>
        <ram:Name>Cloud-Hosting Jahreslizenz 2026</ram:Name>
      </ram:SpecifiedTradeProduct>
      <ram:SpecifiedLineTradeAgreement>
        <ram:NetPriceProductTradePrice>
          <ram:ChargeAmount>2900.00</ram:ChargeAmount>
        </ram:NetPriceProductTradePrice>
      </ram:SpecifiedLineTradeAgreement>
      <ram:SpecifiedLineTradeDelivery>
        <ram:BilledQuantity unitCode="C62">1.00</ram:BilledQuantity>
      </ram:SpecifiedLineTradeDelivery>
      <ram:SpecifiedLineTradeSettlement>
        <ram:ApplicableTradeTax>
          <ram:TypeCode>VAT</ram:TypeCode>
          <ram:CategoryCode>S</ram:CategoryCode>
          <ram:RateApplicablePercent>19.00</ram:RateApplicablePercent>
        </ram:ApplicableTradeTax>
        <ram:SpecifiedTradeSettlementLineMonetarySummation>
          <ram:LineTotalAmount>2900.00</ram:LineTotalAmount>
        </ram:SpecifiedTradeSettlementLineMonetarySummation>
      </ram:SpecifiedLineTradeSettlement>
    </ram:IncludedSupplyChainTradeLineItem>
    <ram:ApplicableHeaderTradeAgreement>
      <ram:BuyerReference>KUNDE-B2B-4491</ram:BuyerReference>
      <ram:SellerTradeParty>
        <ram:Name>AlpenTech Solutions AG</ram:Name>
        <ram:PostalTradeAddress>
          <ram:PostcodeCode>8001</ram:PostcodeCode>
          <ram:LineOne>Bahnhofstrasse 10</ram:LineOne>
          <ram:CityName>Zürich</ram:CityName>
          <ram:CountryID>CH</ram:CountryID>
        </ram:PostalTradeAddress>
        <ram:SpecifiedTaxRegistration>
          <ram:ID schemeID="VA">CHE123456789MWST</ram:ID>
        </ram:SpecifiedTaxRegistration>
      </ram:SellerTradeParty>
      <ram:BuyerTradeParty>
        <ram:Name>Bavaria Media Partner GmbH</ram:Name>
        <ram:PostalTradeAddress>
          <ram:PostcodeCode>80331</ram:PostcodeCode>
          <ram:LineOne>Marienplatz 1</ram:LineOne>
          <ram:CityName>München</ram:CityName>
          <ram:CountryID>DE</ram:CountryID>
        </ram:PostalTradeAddress>
      </ram:BuyerTradeParty>
    </ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeDelivery/>
    <ram:ApplicableHeaderTradeSettlement>
      <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
      <ram:SpecifiedTradePaymentTerms>
        <ram:DueDateDateTime>
          <udt:DateTimeString format="102">20260322</udt:DateTimeString>
        </ram:DueDateDateTime>
      </ram:SpecifiedTradePaymentTerms>
      <ram:ApplicableTradeTax>
        <ram:CalculatedAmount>551.00</ram:CalculatedAmount>
        <ram:TypeCode>VAT</ram:TypeCode>
        <ram:BasisAmount>2900.00</ram:BasisAmount>
        <ram:CategoryCode>S</ram:CategoryCode>
        <ram:RateApplicablePercent>19.00</ram:RateApplicablePercent>
      </ram:ApplicableTradeTax>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:LineTotalAmount>2900.00</ram:LineTotalAmount>
        <ram:TaxBasisTotalAmount>2900.00</ram:TaxBasisTotalAmount>
        <ram:TaxTotalAmount currencyID="EUR">551.00</ram:TaxTotalAmount>
        <ram:GrandTotalAmount>3451.00</ram:GrandTotalAmount>
        <ram:DuePayableAmount>3451.00</ram:DuePayableAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>"""


def main():
    parser = argparse.ArgumentParser(
        prog="en16931-val",
        description="DACH EN 16931 E-Rechnung Validator (XRechnung 3.0 & ZUGFeRD 2.2 / Factur-X)"
    )
    parser.add_argument("file", nargs="?", help="Pfad zur XML-Rechnungsdatei")
    parser.add_argument("--json", action="store_true", help="Gibt den Prüfbericht als formatiertes JSON aus")
    parser.add_argument("--strict", action="store_true", help="Gibt Exit-Code 1 zurück, falls Warnungen existieren")
    parser.add_argument("--quiet", action="store_true", help="Unterdrückt die Terminal-Ausgabe (nur Exit-Code)")
    parser.add_argument("--generate-sample", choices=["xrechnung", "zugferd"], help="Gibt eine valide Muster-XML auf stdout aus")

    args = parser.parse_args()

    if args.generate_sample:
        if args.generate_sample == "xrechnung":
            sys.stdout.write(SAMPLE_XRECHNUNG_XML.strip() + "\n")
        else:
            sys.stdout.write(SAMPLE_ZUGFERD_XML.strip() + "\n")
        sys.exit(0)

    if not args.file:
        parser.print_help()
        sys.exit(3)

    if not os.path.exists(args.file):
        if not args.quiet:
            sys.stderr.write(f"Fehler: Datei nicht gefunden: {args.file}\n")
        sys.exit(3)

    report = validate_invoice_xml(args.file)

    if args.json:
        sys.stdout.write(report.to_json() + "\n")
    elif not args.quiet:
        print("=" * 72)
        print("  DACH DIGITALWERK • EN 16931 E-RECHNUNG VALIDATOR 2026")
        print("=" * 72)
        print(f"Datei       : {args.file}")
        print(f"Standard    : {report.standard_name}")
        print(f"Rechnungs-Nr: {report.invoice_data.invoice_id or '—'}")
        print(f"Rechnungs-Dt: {report.invoice_data.issue_date or '—'}")
        print(f"Aussteller  : {report.invoice_data.seller_name or '—'}")
        print(f"Empfänger   : {report.invoice_data.buyer_name or '—'}")
        gross_str = f"{report.invoice_data.tax_inclusive_amount:.2f} {report.invoice_data.currency}" if report.invoice_data.tax_inclusive_amount is not None else '—'
        print(f"Bruttosumme : {gross_str}")
        print(f"Score       : {report.score} %")
        print("-" * 72)
        print("Prüfergebnisse:")
        for r in report.rules:
            badge = " [OK] " if r.status.value == "passed" else (" [WARN]" if r.status.value == "warning" else "[FAIL]")
            print(f" {badge:7s} {r.rule_id:14s} | {r.field_name:24s} | {r.message}")
        print("-" * 72)
        if report.is_valid:
            if report.warning_count > 0:
                print(f"STATUS: VALIDE MIT HINWEISEN (0 Fehler, {report.warning_count} Hinweise)")
            else:
                print("STATUS: 100% VALIDE (Alle Kernregeln bestanden)")
        else:
            print(f"STATUS: NICHT KONFORM ({report.error_count} Fehler, {report.warning_count} Hinweise)")
        print("=" * 72)

    # Determine exit code
    if report.error_count > 0:
        sys.exit(2)
    elif args.strict and report.warning_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

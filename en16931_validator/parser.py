# -*- coding: utf-8 -*-
"""
XML parser for UBL 2.1 (Invoice/CreditNote) and UN/CEFACT CII (CrossIndustryInvoice).
Extracts EN 16931 Business Terms (BTs) in a namespace-agnostic way.
"""

import xml.etree.ElementTree as ET
from typing import Optional, List, Tuple
import os

from .models import InvoiceData, LineItem


def local_tag(elem: ET.Element) -> str:
    """Returns the local tag name without any namespace prefix."""
    tag = elem.tag
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def find_child_by_local(parent: ET.Element, name: str) -> Optional[ET.Element]:
    """Finds the first immediate child matching the local tag name."""
    name_lower = name.lower()
    for child in parent:
        if local_tag(child).lower() == name_lower:
            return child
    return None


def find_descendant_by_local(root: ET.Element, name: str) -> Optional[ET.Element]:
    """Finds the first descendant matching the local tag name."""
    name_lower = name.lower()
    for elem in root.iter():
        if local_tag(elem).lower() == name_lower:
            return elem
    return None


def find_all_descendants_by_local(root: ET.Element, name: str) -> List[ET.Element]:
    """Finds all descendants matching the local tag name."""
    name_lower = name.lower()
    return [elem for elem in root.iter() if local_tag(elem).lower() == name_lower]


def get_text_by_local(root: Optional[ET.Element], name: str, default: str = "") -> str:
    """Finds the first descendant and returns its stripped text."""
    if root is None:
        return default
    elem = find_descendant_by_local(root, name)
    if elem is not None and elem.text is not None:
        return elem.text.strip()
    return default


def parse_float(val: str, default: Optional[float] = None) -> Optional[float]:
    if not val:
        return default
    try:
        return float(val.replace(",", "."))
    except (ValueError, TypeError):
        return default


def parse_invoice_xml(xml_source: str) -> Tuple[InvoiceData, Optional[ET.Element], Optional[str]]:
    """
    Parses an XML string or file path into InvoiceData.
    Returns (invoice_data, root_element, parse_error_string).
    """
    data = InvoiceData()

    xml_text = xml_source
    if os.path.exists(xml_source):
        try:
            with open(xml_source, "r", encoding="utf-8") as f:
                xml_text = f.read()
        except UnicodeDecodeError:
            with open(xml_source, "r", encoding="latin-1") as f:
                xml_text = f.read()

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as pe:
        return data, None, f"XML Syntax-Fehler: {pe}"
    except Exception as e:
        return data, None, f"Allgemeiner XML-Fehler: {e}"

    root_name = local_tag(root)

    # 1. Detect Syntax & Document Type
    if root_name in ("Invoice", "CreditNote"):
        data.syntax = "UBL"
        data.document_type = root_name
        _parse_ubl(root, data)
    elif root_name in ("CrossIndustryInvoice", "SCRDMCCAMCMCrossIndustryInvoice"):
        data.syntax = "CII"
        data.document_type = "CrossIndustryInvoice"
        _parse_cii(root, data)
    else:
        data.syntax = "UNKNOWN"
        data.document_type = root_name

    return data, root, None


def _parse_ubl(root: ET.Element, data: InvoiceData) -> None:
    """Extracts BTs from UBL 2.1 Invoice / CreditNote."""
    data.specification_id = get_text_by_local(root, "CustomizationID")
    data.profile = get_text_by_local(root, "ProfileID")
    data.invoice_id = get_text_by_local(root, "ID")
    data.issue_date = get_text_by_local(root, "IssueDate")
    data.due_date = get_text_by_local(root, "DueDate")
    data.invoice_type_code = get_text_by_local(root, "InvoiceTypeCode") or ("381" if data.document_type == "CreditNote" else "380")
    data.currency = get_text_by_local(root, "DocumentCurrencyCode") or "EUR"
    data.buyer_reference = get_text_by_local(root, "BuyerReference")

    # Supplier (Seller)
    supplier_party = find_descendant_by_local(root, "AccountingSupplierParty")
    if supplier_party is not None:
        data.seller_name = get_text_by_local(supplier_party, "RegistrationName") or get_text_by_local(supplier_party, "Name")
        data.seller_vat_id = get_text_by_local(supplier_party, "CompanyID")
        data.seller_tax_id = get_text_by_local(supplier_party, "TaxRegistrationID") or ""
        data.seller_street = get_text_by_local(supplier_party, "StreetName")
        data.seller_city = get_text_by_local(supplier_party, "CityName")
        data.seller_postcode = get_text_by_local(supplier_party, "PostalZone")
        data.seller_country = get_text_by_local(supplier_party, "IdentificationCode")

    # Customer (Buyer)
    customer_party = find_descendant_by_local(root, "AccountingCustomerParty")
    if customer_party is not None:
        data.buyer_name = get_text_by_local(customer_party, "RegistrationName") or get_text_by_local(customer_party, "Name")
        data.buyer_vat_id = get_text_by_local(customer_party, "CompanyID")
        data.buyer_street = get_text_by_local(customer_party, "StreetName")
        data.buyer_city = get_text_by_local(customer_party, "CityName")
        data.buyer_postcode = get_text_by_local(customer_party, "PostalZone")
        data.buyer_country = get_text_by_local(customer_party, "IdentificationCode")

    # Monetary Totals
    monetary = find_descendant_by_local(root, "LegalMonetaryTotal")
    if monetary is not None:
        data.line_extension_amount = parse_float(get_text_by_local(monetary, "LineExtensionAmount"))
        data.tax_exclusive_amount = parse_float(get_text_by_local(monetary, "TaxExclusiveAmount"))
        data.tax_inclusive_amount = parse_float(get_text_by_local(monetary, "TaxInclusiveAmount"))
        data.payable_amount = parse_float(get_text_by_local(monetary, "PayableAmount"))

    tax_total = find_descendant_by_local(root, "TaxTotal")
    if tax_total is not None:
        data.tax_total_amount = parse_float(get_text_by_local(tax_total, "TaxAmount"))

    # Invoice Lines
    line_nodes = find_all_descendants_by_local(root, "InvoiceLine") + find_all_descendants_by_local(root, "CreditNoteLine")
    for idx, ln in enumerate(line_nodes, start=1):
        item_id = get_text_by_local(ln, "ID") or str(idx)
        name = get_text_by_local(ln, "Name") or f"Position {item_id}"
        qty = parse_float(get_text_by_local(ln, "InvoicedQuantity") or get_text_by_local(ln, "CreditedQuantity"), 1.0)
        
        # Unit code attribute
        qty_elem = find_descendant_by_local(ln, "InvoicedQuantity")
        if qty_elem is None:
            qty_elem = find_descendant_by_local(ln, "CreditedQuantity")
        unit_code = qty_elem.get("unitCode", "C62") if qty_elem is not None else "C62"

        price = parse_float(get_text_by_local(ln, "PriceAmount"), 0.0)
        line_net = parse_float(get_text_by_local(ln, "LineExtensionAmount"), qty * price if (qty and price) else 0.0)
        rate = parse_float(get_text_by_local(ln, "Percent"), 19.0)
        category = get_text_by_local(ln, "TaxCategory") or "S"

        data.line_items.append(LineItem(
            item_id=item_id,
            name=name,
            quantity=qty or 1.0,
            unit_code=unit_code,
            net_price=price or 0.0,
            line_net_amount=line_net or 0.0,
            vat_rate=rate or 0.0,
            vat_category=category
        ))


def _parse_cii(root: ET.Element, data: InvoiceData) -> None:
    """Extracts BTs from UN/CEFACT CII CrossIndustryInvoice."""
    doc_ctx = find_descendant_by_local(root, "ExchangedDocumentContext")
    if doc_ctx is not None:
        data.specification_id = get_text_by_local(doc_ctx, "ID")
        data.profile = data.specification_id

    ex_doc = find_descendant_by_local(root, "ExchangedDocument")
    if ex_doc is not None:
        data.invoice_id = get_text_by_local(ex_doc, "ID")
        data.invoice_type_code = get_text_by_local(ex_doc, "TypeCode") or "380"
        raw_date = get_text_by_local(ex_doc, "DateTimeString")
        if len(raw_date) == 8 and raw_date.isdigit():
            data.issue_date = f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        else:
            data.issue_date = raw_date

    trans = find_descendant_by_local(root, "SupplyChainTradeTransaction")
    if trans is not None:
        # Header Trade Agreement
        agreement = find_descendant_by_local(trans, "ApplicableHeaderTradeAgreement")
        if agreement is not None:
            data.buyer_reference = get_text_by_local(agreement, "BuyerReference")
            
            # Seller Trade Party
            seller_party = find_descendant_by_local(agreement, "SellerTradeParty")
            if seller_party is not None:
                data.seller_name = get_text_by_local(seller_party, "Name")
                data.seller_vat_id = get_text_by_local(seller_party, "ID")
                addr = find_descendant_by_local(seller_party, "PostalTradeAddress")
                if addr is not None:
                    data.seller_street = get_text_by_local(addr, "LineOne")
                    data.seller_postcode = get_text_by_local(addr, "PostcodeCode")
                    data.seller_city = get_text_by_local(addr, "CityName")
                    data.seller_country = get_text_by_local(addr, "CountryID")

            # Buyer Trade Party
            buyer_party = find_descendant_by_local(agreement, "BuyerTradeParty")
            if buyer_party is not None:
                data.buyer_name = get_text_by_local(buyer_party, "Name")
                addr = find_descendant_by_local(buyer_party, "PostalTradeAddress")
                if addr is not None:
                    data.buyer_street = get_text_by_local(addr, "LineOne")
                    data.buyer_postcode = get_text_by_local(addr, "PostcodeCode")
                    data.buyer_city = get_text_by_local(addr, "CityName")
                    data.buyer_country = get_text_by_local(addr, "CountryID")

        # Settlement
        settlement = find_descendant_by_local(trans, "ApplicableHeaderTradeSettlement")
        if settlement is not None:
            data.currency = get_text_by_local(settlement, "InvoiceCurrencyCode") or "EUR"
            
            pay_terms = find_descendant_by_local(settlement, "SpecifiedTradePaymentTerms")
            if pay_terms is not None:
                raw_due = get_text_by_local(pay_terms, "DateTimeString")
                if len(raw_due) == 8 and raw_due.isdigit():
                    data.due_date = f"{raw_due[0:4]}-{raw_due[4:6]}-{raw_due[6:8]}"
                else:
                    data.due_date = raw_due

            summation = find_descendant_by_local(settlement, "SpecifiedTradeSettlementHeaderMonetarySummation")
            if summation is not None:
                data.line_extension_amount = parse_float(get_text_by_local(summation, "LineTotalAmount"))
                data.tax_exclusive_amount = parse_float(get_text_by_local(summation, "TaxBasisTotalAmount"))
                data.tax_total_amount = parse_float(get_text_by_local(summation, "TaxTotalAmount"))
                data.tax_inclusive_amount = parse_float(get_text_by_local(summation, "GrandTotalAmount"))
                data.payable_amount = parse_float(get_text_by_local(summation, "DuePayableAmount"))

        # Line Items
        cii_lines = find_all_descendants_by_local(trans, "IncludedSupplyChainTradeLineItem")
        for idx, cl in enumerate(cii_lines, start=1):
            item_id = get_text_by_local(cl, "LineID") or str(idx)
            name = get_text_by_local(cl, "Name") or f"Position {item_id}"
            qty = parse_float(get_text_by_local(cl, "BilledQuantity"), 1.0)
            
            qty_elem = find_descendant_by_local(cl, "BilledQuantity")
            unit_code = qty_elem.get("unitCode", "C62") if qty_elem is not None else "C62"

            price = parse_float(get_text_by_local(cl, "ChargeAmount"), 0.0)
            line_net = parse_float(get_text_by_local(cl, "LineTotalAmount"), qty * price if (qty and price) else 0.0)
            rate = parse_float(get_text_by_local(cl, "RateApplicablePercent"), 19.0)
            category = get_text_by_local(cl, "CategoryCode") or "S"

            data.line_items.append(LineItem(
                item_id=item_id,
                name=name,
                quantity=qty or 1.0,
                unit_code=unit_code,
                net_price=price or 0.0,
                line_net_amount=line_net or 0.0,
                vat_rate=rate or 0.0,
                vat_category=category
            ))

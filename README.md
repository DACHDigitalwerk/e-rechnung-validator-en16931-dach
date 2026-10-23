# 🧾 DACH E-Rechnung Validator (EN 16931, XRechnung 3.0 & ZUGFeRD 2.2)

[![Python Unit Tests](https://github.com/DACHDigitalwerk/e-rechnung-validator-en16931-dach/actions/workflows/python-tests.yml/badge.svg)](https://github.com/DACHDigitalwerk/e-rechnung-validator-en16931-dach/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Norm: EN 16931](https://img.shields.io/badge/Norm-DIN%20EN%2016931-emerald.svg)](https://dach-digitalwerk.netlify.app/e-rechnung-validator/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20(Standard%20Lib)-success.svg)](https://github.com/DACHDigitalwerk/e-rechnung-validator-en16931-dach)

Ein präziser, leichtgewichtiger und abhängigkeitsfreier **E-Rechnungs-Syntax- und Pflichtfeld-Prüfer** für Python und CLI. Entwickelt für die **gesetzliche E-Rechnungspflicht 2026** im B2B- und B2G-Geschäftsverkehr (Deutschland, Österreich, Schweiz) nach § 14 UStG n.F. (Wachstumschancengesetz).

Unterstützt **UBL 2.1** (`Invoice` / `CreditNote`) und **UN/CEFACT CII** (`CrossIndustryInvoice` in ZUGFeRD 2.2 / Factur-X) inklusive **Leitweg-ID Prüfung (BT-10)** und mathematischer Summenkonsistenz nach Kernregel **BR-CO-15**.

---

### 🌐 Kostenloses Web-Tool (100% Client-Side)
Sie möchten Rechnungen direkt ohne Installation im Browser validieren?  
👉 **[DACH E-Rechnung Validator 2026 (Live im Browser)](https://dach-digitalwerk.netlify.app/e-rechnung-validator/)**  
*(100% DSGVO-sicher: Sämtliche Prüfungen laufen lokal via DOMParser – kein Serverkontakt, kein Cloud-Upload).*

---

## ⚡ Kernfunktionen

- **Universelle Formaterkennung:**
  - **XRechnung 3.0** (UBL 2.1 Invoice & CreditNote)
  - **ZUGFeRD 2.2 / Factur-X** (UN/CEFACT CII CrossIndustryInvoice)
  - Profil-Erkennung: MINIMUM, BASIC, BASIC WL, COMFORT (EN 16931), EXTENDED
- **EN 16931 Kernprüfungen:**
  - **BT-1:** Rechnungsnummer (Einmaligkeit, Nicht-Leerheit)
  - **BT-2:** Rechnungsdatum (ISO 8601 Prüfung: YYYY-MM-DD / YYYYMMDD)
  - **BT-3:** UNTDID 1001 Rechnungstypcode (380 Handelsrechnung, 381 Gutschrift etc.)
  - **BT-5:** ISO 4217 Währungscode (EUR, CHF, USD, GBP etc.)
  - **BT-10:** Leitweg-ID / BuyerReference (Formatprüfung `^[0-9]{2,12}-[0-9A-Za-z]{0,16}-[0-9]{2}$` für Bund/Länder-Behörden)
  - **BT-27:** Vollständiger Verkäufer Firmenname
  - **BT-31 / BT-32:** Gesetzliche Steueridentifikation (USt-IdNr oder Steuernummer)
  - **BT-44:** Vollständiger Käufer Firmenname
  - **BT-109 / BT-110 / BT-112:** Gesamtnetto, Umsatzsteuer & Rechnungsbrutto
- **BR-CO-15 Mathematische Konsistenzprüfung:**
  - Prüft `| Netto + Steuer - Brutto | <= 0.02 €` (Rundungstoleranz)
  - Validiert Zeilensummen gegen Positionsnettobeträge
- **0 externe Abhängigkeiten:** Basiert ausschließlich auf Pythons `xml.etree.ElementTree` und Standardbibliotheken.
- **Audit-Fähigkeit:** Erzeugt SHA-256 Prüfsummen und JSON-Audit-Logs für Kanzleien und Buchhaltungsprüfer.

---

## 📦 Installation

```bash
# Direkt aus GitHub klonen und installieren
git clone https://github.com/DACHDigitalwerk/e-rechnung-validator-en16931-dach.git
cd e-rechnung-validator-en16931-dach
pip install .
```

---

## 💻 CLI-Nutzung (`en16931-val`)

Nach der Installation steht das Kommandozeilenwerkzeug `en16931-val` zur Verfügung:

```bash
# Standard-Prüfung mit formatierter Terminal-Ausgabe
en16931-val rechnung.xml

# Ausgabe als maschinenlesbarer JSON-Prüfbericht (z. B. für CI/CD)
en16931-val rechnung.xml --json

# Strikter Modus (gibt Exit-Code 1 zurück, falls Warnungen vorliegen)
en16931-val rechnung.xml --strict

# Stille Ausführung für Shell-Skripte (nur Exit-Code)
en16931-val rechnung.xml --quiet

# Valide Muster-XML auf stdout erzeugen
en16931-val --generate-sample xrechnung > muster_xrechnung.xml
en16931-val --generate-sample zugferd > muster_zugferd.xml
```

### CLI Exit Codes:
- `0`: Valide E-Rechnung (0 Fehler)
- `1`: Warnungen vorhanden (nur bei `--strict`)
- `2`: Mindestens 1 Pflichtfeld- oder Schematron-Fehler
- `3`: Datei nicht gefunden oder XML-Syntaxfehler

---

## 🐍 Python API

```python
from en16931_validator import validate_invoice_xml

# XML-String oder Pfad zur XML-Datei übergeben
report = validate_invoice_xml("rechnung_2026.xml")

if report.is_valid:
    print(f"✅ Valide E-Rechnung ({report.standard_name})!")
    print(f"Rechnungs-ID : {report.invoice_data.invoice_id}")
    print(f"Bruttobetrag : {report.invoice_data.tax_inclusive_amount} {report.invoice_data.currency}")
else:
    print(f"❌ Fehler gefunden ({report.error_count} Fehler):")
    for rule in report.rules:
        if rule.status == "failed":
            print(f" - [{rule.rule_id}] {rule.field_name}: {rule.message}")

# JSON-Audit-Log exportieren
json_audit = report.to_json(indent=2)
```

---

## 🏛️ Leitweg-ID (BT-10) Spezifikation für B2G

Für Rechnungen an die öffentliche Hand in Deutschland ist im Feld **BT-10** die sogenannte Leitweg-ID Pflicht (BR-DE-01):

$$\text{Format: } \underbrace{\text{04011000}}_{\text{Grobadressierung}}-\underbrace{\text{12345}}_{\text{Feinadressierung}}-\underbrace{\text{12}}_{\text{Prüfziffer}}$$

- **Grobadressierung (bis zu 12 Stellen):** Identifiziert das Bundesland oder die Gebietskörperschaft (z. B. `99` für Bund, `04` für Bremen, `05` für NRW).
- **Feinadressierung (bis zu 16 Stellen):** Konkretes Referat / Dienststelle.
- **Prüfziffer (2 Ziffern):** Nach ISO 7064 Modulo 97-10.

---

## 📚 Praxis-Ratgeber & Dokumentation

Vertiefende Anleitungen zur E-Rechnungspflicht und Fehlerbehebung:
- 📖 [E-Rechnung validieren kostenlos online (Praxis-Leitfaden)](https://dach-digitalwerk.netlify.app/e-rechnung-validieren-kostenlos-online.html)
- 🔧 [XRechnung Syntaxfehler & Leitweg-ID beheben (Troubleshooting Guide)](https://dach-digitalwerk.netlify.app/xrechnung-syntax-fehler-beheben-leitweg-id.html)
- 📎 [ZUGFeRD XML aus PDF extrahieren & Profile prüfen](https://dach-digitalwerk.netlify.app/zugferd-xml-aus-pdf-extrahieren-pruefen.html)
- 🏦 [SEPA Lastschrift & Überweisungs-XML Generator (pain.008 & pain.001)](https://dach-digitalwerk.netlify.app/sepa-xml-generator/)

---

## 💼 B2B E-Rechnung Suite & Vorlagen

Benötigen Sie schlüsselfertige Python-Konverter, Excel-Makros für ZUGFeRD 2.2 / XRechnung 3.0 sowie rechtssichere Checklisten für Kanzleien und Mandanten?  
👉 **[DACH Digitalwerk B2B E-Rechnung Paket auf Gumroad](https://dachdigital.gumroad.com/l/gthgwc)**

---

## 🧪 Tests ausführen

Das Repository enthält eine umfassende Test-Suite mit 20 Unit-Tests:

```bash
python -m unittest discover -s tests -v
```

---

## ⚖️ Rechtlicher Hinweis & RDG-Disclaimer

Dieses Repository und das zugehörige Web-Tool dienen als **technisches Vorprüf- und Hilfswerkzeug**. Es findet **keine Rechtsberatung** im Sinne des Rechtsdienstleistungsgesetzes (RDG) und keine Steuerberatung im Sinne des Steuerberatungsgesetzes (StBerG) statt. Nach der Rechtsprechung des BGH (u. a. 'Smartlaw') stellen softwaregestützte Vorlagen und Validierungstools keine anwaltliche Einzelfallberatung dar. Für verbindliche steuerliche Beurteilungen konsultieren Sie bitte einen Steuerberater.

---

## 📄 Lizenz

Veröffentlicht unter der [MIT Lizenz](LICENSE).  
Copyright (c) 2026 [DACH Digitalwerk](https://dach-digitalwerk.netlify.app/).

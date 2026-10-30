"""AI Document Intelligence: extract FDR fields from uploaded PDF/image.

Strategy (in order):
1. PyMuPDF text extraction for PDFs (covers digitally-generated FDRs).
2. Tesseract OCR for images / scanned PDFs, when the tesseract binary exists.
3. Mock extraction for the hackathon demo: if nothing can be read, fields are
   returned as missing so the UI highlights them for manual entry.
"""
import re
import shutil
from datetime import datetime, date

import pymupdf as fitz  # PyMuPDF

FIELD_SPECS = {
    "fdr_number": "FDR / Deposit receipt number",
    "bank_name": "Issuing bank name",
    "branch": "Issuing branch",
    "ifsc": "IFSC code",
    "amount": "Deposit amount (INR)",
    "issue_date": "Date of issue",
    "maturity_date": "Maturity date",
    "interest_rate": "Interest rate (%)",
}

_BANK_NAMES = [
    "State Bank of India", "Punjab National Bank", "Bank of Baroda",
    "HDFC Bank", "ICICI Bank", "Canara Bank", "Union Bank of India",
    "Axis Bank", "Indian Bank", "Kotak Mahindra Bank",
]

_DATE_PATTERNS = [
    r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b",
    r"\b(\d{4}-\d{2}-\d{2})\b",
    r"\b(\d{2}\s+[A-Za-z]{3,9}\s+\d{4})\b",
]


def _parse_date(s: str):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _extract_text(path: str) -> tuple[str, str]:
    """Return (text, method)."""
    if path.lower().endswith(".pdf"):
        try:
            doc = fitz.open(path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            if text.strip():
                return text, "pymupdf"
        except Exception:
            pass
        # scanned PDF -> rasterize first page and OCR if tesseract exists
        if shutil.which("tesseract"):
            try:
                import pytesseract
                doc = fitz.open(path)
                pix = doc[0].get_pixmap(dpi=200)
                img_path = path + ".page1.png"
                pix.save(img_path)
                doc.close()
                return pytesseract.image_to_string(img_path), "tesseract"
            except Exception:
                pass
        return "", "unreadable"
    if shutil.which("tesseract"):
        try:
            import pytesseract
            return pytesseract.image_to_string(path), "tesseract"
        except Exception:
            pass
    return "", "unreadable"


def parse_fdr_text(text: str) -> dict:
    """Pull structured fields out of raw OCR/PDF text."""
    out = {}
    t = text

    m = re.search(r"(?:FDR|FD|Deposit|Receipt)\s*(?:No\.?|Number|#)[:\s]*([A-Z0-9/\-]{4,})", t, re.I)
    if m:
        out["fdr_number"] = m.group(1).strip()
    else:
        m = re.search(r"\b(\d{10,16})\b", t)
        if m:
            out["fdr_number"] = m.group(1)

    for name in _BANK_NAMES:
        if name.lower() in t.lower():
            out["bank_name"] = name
            break

    m = re.search(r"Branch[:\s]*([A-Za-z0-9 ,&\-]{3,60})", t, re.I)
    if m:
        out["branch"] = m.group(1).split("\n")[0].strip()

    m = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", t)
    if m:
        out["ifsc"] = m.group(1)

    m = re.search(r"(?:Rs\.?|INR|₹|Amount)[:\s]*([0-9,]+(?:\.\d{1,2})?)", t, re.I)
    if m:
        try:
            out["amount"] = float(m.group(1).replace(",", ""))
        except ValueError:
            pass

    dates = []
    for pat in _DATE_PATTERNS:
        for dm in re.finditer(pat, t):
            d = _parse_date(dm.group(1))
            if d:
                dates.append(d)
    # prefer labelled dates
    mi = re.search(r"(?:Issue|Deposit|Opening)\s*Date[:\s]*([0-9]{2}[/-][0-9]{2}[/-][0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})", t, re.I)
    mm = re.search(r"(?:Maturity|Due|Expiry)\s*Date[:\s]*([0-9]{2}[/-][0-9]{2}[/-][0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})", t, re.I)
    if mi:
        d = _parse_date(mi.group(1))
        if d:
            out["issue_date"] = d
    if mm:
        d = _parse_date(mm.group(1))
        if d:
            out["maturity_date"] = d
    if "issue_date" not in out and dates:
        out["issue_date"] = min(dates)
    if "maturity_date" not in out and dates:
        out["maturity_date"] = max(dates)

    m = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*%", t)
    if m:
        out["interest_rate"] = float(m.group(1))

    return out


def extract_document(path: str) -> dict:
    """Full extraction pipeline result for the UI."""
    text, method = _extract_text(path)
    fields = parse_fdr_text(text) if text else {}
    missing = [k for k in FIELD_SPECS if k not in fields or fields[k] in (None, "")]
    return {
        "method": method,
        "raw_text_excerpt": (text or "")[:2000],
        "fields": fields,
        "missing_fields": missing,
        "field_labels": FIELD_SPECS,
        "mock": method == "unreadable",
    }

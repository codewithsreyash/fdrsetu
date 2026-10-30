"""Excel / PDF report exports."""
import io
from datetime import datetime

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

FDR_HEADERS = ["FDR UID", "FDR Number", "Institution", "Bank", "Branch", "IFSC",
               "Amount (INR)", "Interest %", "Issue Date", "Maturity Date",
               "Status", "Verification", "Risk"]


def fdr_row(f):
    return [
        f.fdr_uid, f.fdr_number,
        f.institution.name if f.institution else "",
        f.bank.name if f.bank else "",
        f.branch or "", f.ifsc or "",
        float(f.amount) if f.amount else 0,
        float(f.interest_rate) if f.interest_rate else "",
        str(f.issue_date), str(f.maturity_date),
        f.status.value, f.verification_status.value, f.risk_level.value,
    ]


def fdrs_to_xlsx(fdrs) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "FDR Report"
    ws.append(["FDRSETU — FDR Report (DEMO / SYNTHETIC DATA)"])
    ws.append(["Generated:", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")])
    ws.append([])
    ws.append(FDR_HEADERS)
    for f in fdrs:
        ws.append(fdr_row(f))
    for col in ws.columns:
        width = max(len(str(c.value or "")) for c in col) + 2
        ws.column_dimensions[col[0].column_letter].width = min(width, 42)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def fdrs_to_pdf(fdrs, title="FDR Report") -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=24, rightMargin=24)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"FDRSETU — {title} (DEMO / SYNTHETIC DATA)", styles["Title"]),
        Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                  styles["Normal"]),
        Spacer(1, 12),
    ]
    data = [FDR_HEADERS] + [fdr_row(f) for f in fdrs]
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123B65")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F9")]),
    ]))
    story.append(table)
    doc.build(story)
    return buf.getvalue()

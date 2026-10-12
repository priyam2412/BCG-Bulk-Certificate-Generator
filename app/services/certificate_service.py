from __future__ import annotations

import os
from datetime import datetime, timezone

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUTPUT_DIR = os.path.join(os.getcwd(), "generated_certificates")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_certificate_pdf(recipient_name: str, course_name: str, completion_date: str) -> str:
    safe_name = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in recipient_name).strip("_")
    filename = f"{safe_name}_{int(datetime.now(timezone.utc).timestamp())}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    pdf = canvas.Canvas(filepath, pagesize=letter)
    pdf.setTitle(f"Certificate for {recipient_name}")
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(306, 720, "Certificate of Completion")

    pdf.setFont("Helvetica", 18)
    pdf.drawCentredString(306, 640, "This certifies that")

    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(306, 590, recipient_name)

    pdf.setFont("Helvetica", 18)
    pdf.drawCentredString(306, 530, f"has successfully completed the course: {course_name}")
    pdf.drawCentredString(306, 490, f"on {completion_date}")

    pdf.save()
    return filepath

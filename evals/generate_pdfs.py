"""
OrdonAI — Eval PDF Generator
Generates 13 realistic French prescription PDFs from golden.json.
Output: evals/images/test-001.pdf ... test-013.pdf

Usage:
    python evals/generate_pdfs.py
"""

import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

# ── Config ──────────────────────────────────────────────────────────────────
GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "golden.json")
OUT_DIR     = os.path.join(os.path.dirname(__file__), "images")

W, H = A4  # 595 x 842 pts

DOCTOR = {
    "name":    "Dr. Sophie Martin",
    "rpps":    "RPPS : 10012345678",
    "address": "12 rue des Lilas, 75010 Paris",
    "phone":   "Tél : 01 42 00 00 00",
}
PATIENT = {
    "name": "M. Jean Dupont",
    "dob":  "Né le : 14/03/1978",
    "date": "Paris, le 28 avril 2026",
}

# ── Helpers ──────────────────────────────────────────────────────────────────
def draw_prescription(c, input_text, test_id, mode):
    """Draw a single A4 prescription page."""

    # ── Doctor header (top-left) ─────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20*mm, H - 20*mm, DOCTOR["name"])
    c.setFont("Helvetica", 8)
    c.drawString(20*mm, H - 25*mm, DOCTOR["rpps"])
    c.drawString(20*mm, H - 29*mm, DOCTOR["address"])
    c.drawString(20*mm, H - 33*mm, DOCTOR["phone"])

    # ── Date (top-right) ────────────────────────────────────────────────────
    c.setFont("Helvetica", 9)
    c.drawRightString(W - 20*mm, H - 20*mm, PATIENT["date"])

    # ── Divider ─────────────────────────────────────────────────────────────
    c.setLineWidth(0.5)
    c.line(20*mm, H - 38*mm, W - 20*mm, H - 38*mm)

    # ── Patient block ───────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20*mm, H - 45*mm, PATIENT["name"])
    c.setFont("Helvetica", 8)
    c.drawString(20*mm, H - 49*mm, PATIENT["dob"])

    # ── Rx symbol ───────────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 22)
    c.drawString(20*mm, H - 63*mm, "Rp/")

    # ── Medication lines ─────────────────────────────────────────────────────
    # Special handling per mode
    lines = format_lines(input_text, mode)

    c.setFont("Helvetica", 10)
    y = H - 72*mm
    line_h = 6*mm

    for line in lines:
        if y < 60*mm:
            break  # Safety: don't overflow page
        c.drawString(28*mm, y, line)
        y -= line_h

    # ── Doctor signature (bottom) ────────────────────────────────────────────
    c.setLineWidth(0.3)
    c.line(W - 70*mm, 35*mm, W - 20*mm, 35*mm)
    c.setFont("Helvetica", 8)
    c.drawString(W - 70*mm, 31*mm, "Signature du médecin")

    # ── Subtle test label (small, bottom-left, for dev reference) ───────────
    c.setFont("Helvetica", 6)
    c.setFillColorRGB(0.7, 0.7, 0.7)
    c.drawString(20*mm, 20*mm, f"{test_id} — {mode}")
    c.setFillColorRGB(0, 0, 0)


def format_lines(input_text, mode):
    """
    Format the raw input_text into prescription lines.
    For irregular_spacing mode, preserve the run-together formatting.
    For all others, split on newlines and add natural indentation.
    """
    raw_lines = input_text.strip().split("\n")

    if mode == "irregular_spacing":
        # Keep it messy — no reformatting, this is the point
        return raw_lines

    formatted = []
    for raw in raw_lines:
        raw = raw.strip()
        if not raw:
            continue
        # Split at " — " to put instructions on a second indented line
        if " — " in raw:
            parts = raw.split(" — ", 1)
            formatted.append(parts[0].strip())           # Drug name + dosage
            formatted.append("    " + parts[1].strip())  # Instructions indented
        else:
            formatted.append(raw)
        formatted.append("")  # Blank line between drugs

    return formatted


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"Generating {len(cases)} prescription PDFs...\n")

    for case in cases:
        test_id    = case["id"]
        mode       = case["mode"]
        input_text = case["input_text"]
        out_path   = os.path.join(OUT_DIR, f"{test_id}.pdf")

        c = canvas.Canvas(out_path, pagesize=A4)
        draw_prescription(c, input_text, test_id, mode)
        c.save()

        print(f"  ✅  {test_id}.pdf  [{mode}]")

    print(f"\nDone. PDFs saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()

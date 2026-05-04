"""
OrdonAI — Eval Runner
Feeds each prescription PDF to Claude and scores output against golden.json.

Usage:
    export ANTHROPIC_API_KEY=sk-...
    python evals/run_evals.py

Requirements:
    pip install anthropic
"""

import json
import os
import base64
import anthropic

# ── Config ───────────────────────────────────────────────────────────────────
GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "golden.json")
IMAGES_DIR  = os.path.join(os.path.dirname(__file__), "images")

# Same prompt as index.html — do not change this, it's what you're testing
PROMPT = """Tu es un assistant spécialisé dans la lecture d'ordonnances médicales françaises.
Analyse cette ordonnance et extrais tous les médicaments prescrits.

Réponds UNIQUEMENT avec un objet JSON valide, sans markdown ni texte autour :
{
  "medications": [
    {
      "name": "Nom du médicament",
      "dosage": "ex: 500 mg",
      "frequency": "ex: 3 fois par jour",
      "duration": "ex: 7 jours",
      "duration_days": 7,
      "schedule": ["matin","midi","soir"],
      "special_instructions": "ex: Prendre avec les repas ou null"
    }
  ]
}

Règles :
- schedule : uniquement "matin" (8h), "midi" (13h), "soir" (20h), "nuit" (22h)
- 1×/j → ["matin"] ; 2×/j → ["matin","soir"] ; 3×/j → ["matin","midi","soir"] ; 4×/j → toutes
- Si durée absente : duration_days = 30
- Si fréquence vague ou indéterminée (ex: "selon les besoins", "si nécessaire", "en cas de douleur") : schedule = ["matin"]
- Si illisible : medications = []"""


# ── Claude call ───────────────────────────────────────────────────────────────
def call_claude(pdf_path: str) -> list[dict]:
    """Send a PDF to Claude and return the extracted medications list."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    with open(pdf_path, "rb") as f:
        pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_data,
                    },
                },
                {
                    "type": "text",
                    "text": PROMPT
                }
            ],
        }],
    )

    raw = message.content[0].text.strip()
    # Strip markdown fences if present
    fence = __import__("re").search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()

    parsed = json.loads(raw)
    meds = parsed.get("medications", [])

    # Normalize null special_instructions to empty string
    for m in meds:
        if not m.get("special_instructions") or m["special_instructions"] == "null":
            m["special_instructions"] = ""

    return meds


# ── Scoring ───────────────────────────────────────────────────────────────────
def normalize_dosage(s: str) -> str:
    """'500mg' → '500 mg', '1g' → '1 g'"""
    import re
    if not s:
        return ""
    s = s.strip().lower()
    s = re.sub(r"(\d)(mg|mcg|g|ml|ui)", r"\1 \2", s)
    return s

def score_medication(got: dict, expected: dict) -> tuple[int, int, list[str]]:
    """
    Score one medication against its expected values.
    Returns (points_scored, points_possible, list_of_failures).
    """
    failures = []
    score = 0
    total = 5

    # 1. name — fuzzy: expected name should appear in got name (case-insensitive)
    got_name = got.get("name", "").lower()
    exp_name = expected.get("name", "").lower()
    if exp_name and exp_name in got_name:
        score += 1
    else:
        failures.append(f"name: got '{got.get('name')}' expected '{expected.get('name')}'")

    # 2. dosage — normalize spaces then compare
    got_dosage = normalize_dosage(got.get("dosage", ""))
    exp_dosage = normalize_dosage(expected.get("dosage", ""))
    if exp_dosage == "" or got_dosage == exp_dosage:
        score += 1
    else:
        failures.append(f"dosage: got '{got.get('dosage')}' expected '{expected.get('dosage')}'")

    # 3. schedule — exact array match (order-insensitive)
    got_sched = sorted(got.get("schedule", []))
    exp_sched = sorted(expected.get("schedule", []))
    if got_sched == exp_sched:
        score += 1
    else:
        failures.append(f"schedule: got {got_sched} expected {exp_sched}")

    # 4. duration_days — exact number match
    got_days = got.get("duration_days")
    exp_days = expected.get("duration_days")
    if got_days == exp_days:
        score += 1
    else:
        failures.append(f"duration_days: got {got_days} expected {exp_days}")

    # 5. special_instructions — presence check
    got_has  = bool(got.get("special_instructions", "").strip())
    exp_has  = bool(expected.get("special_instructions", "").strip())
    if got_has == exp_has:
        score += 1
    else:
        if exp_has:
            failures.append(f"special_instructions: missing (expected '{expected.get('special_instructions')}')")
        else:
            failures.append(f"special_instructions: unexpected value '{got.get('special_instructions')}'")

    return score, total, failures


def score_case(got_meds: list[dict], expected_meds: list[dict]) -> tuple[int, int, list[str]]:
    """
    Score a full prescription (potentially multiple medications).
    Matches medications by position.
    """
    all_failures = []
    total_score  = 0
    total_points = 0

    exp_count = len(expected_meds)
    got_count = len(got_meds)

    if got_count != exp_count:
        all_failures.append(f"medication count: got {got_count} expected {exp_count}")

    for i, expected in enumerate(expected_meds):
        if i < got_count:
            s, t, f = score_medication(got_meds[i], expected)
            total_score  += s
            total_points += t
            all_failures.extend([f"  med[{i+1}] {x}" for x in f])
        else:
            # Medication missing entirely
            total_points += 5
            all_failures.append(f"  med[{i+1}] entirely missing: '{expected.get('name')}'")

    return total_score, total_points, all_failures


def verdict(score: int, total: int) -> str:
    ratio = score / total if total else 0
    if ratio >= 0.8:
        return "✅ PASS"
    elif ratio >= 0.5:
        return "⚠️  PARTIAL"
    else:
        return "❌ FAIL"


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    total_score  = 0
    total_points = 0
    passed = partial = failed = 0

    print("\n" + "="*65)
    print("  OrdonAI Eval Suite")
    print("="*65 + "\n")

    for case in cases:
        test_id  = case["id"]
        mode     = case["mode"]
        expected = case["expected"]["medications"]
        pdf_path = os.path.join(IMAGES_DIR, f"{test_id}.pdf")

        if not os.path.exists(pdf_path):
            print(f"  ⚠️  {test_id} — PDF not found, skipping")
            continue

        print(f"  Running {test_id} [{mode}]...", end=" ", flush=True)

        try:
            got_meds = call_claude(pdf_path)
            score, points, failures = score_case(got_meds, expected)
            v = verdict(score, points)

            total_score  += score
            total_points += points

            if "PASS"    in v: passed  += 1
            elif "PARTIAL" in v: partial += 1
            else:              failed  += 1

            print(f"{v}   {score}/{points}")
            for f in failures:
                print(f"        → {f}")

            results.append({
                "id": test_id, "mode": mode,
                "score": score, "points": points,
                "verdict": v, "failures": failures
            })

        except Exception as e:
            print(f"❌ ERROR — {e}")
            results.append({
                "id": test_id, "mode": mode,
                "score": 0, "points": 0,
                "verdict": "❌ ERROR", "failures": [str(e)]
            })
            failed += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "="*65)
    print("  SUMMARY")
    print("="*65)
    overall_pct = round(100 * total_score / total_points) if total_points else 0
    print(f"  Overall score : {total_score}/{total_points} ({overall_pct}%)")
    print(f"  Passed        : {passed}")
    print(f"  Partial       : {partial}")
    print(f"  Failed        : {failed}")
    print()

    # ── Failures by mode ──────────────────────────────────────────────────────
    mode_failures = {}
    for r in results:
        if r["failures"]:
            mode_failures.setdefault(r["mode"], []).extend(r["failures"])

    if mode_failures:
        print("  Failures by mode:")
        for mode, fails in mode_failures.items():
            print(f"    [{mode}]")
            for f in fails:
                print(f"      → {f}")
    else:
        print("  🎉 No failures!")

    print("\n" + "="*65 + "\n")


if __name__ == "__main__":
    main()

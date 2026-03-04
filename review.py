"""
review.py — CLI entry point and orchestrator for ReviewPanel

Usage:
    python review.py                                  # auto-detect, top-medical
    python review.py JAMA                             # auto-detect + JAMA profile
    python review.py JAMA ./manuscript.tex            # explicit file
    python review.py --model phi4 CJEM ./paper.md     # custom model
"""

import sys
import argparse
from datetime import date
from pathlib import Path

from manuscript import discover_manuscript
from agents import run_all_agents

# ---------------------------------------------------------------------------
# Known journal names and their profile file stems
# ---------------------------------------------------------------------------

_JOURNAL_FILES = {
    "JAMA": "JAMA.json",
    "CJEM": "CJEM.json",
    "AnnalsEM": "Annals_of_EM.json",
    "Resuscitation": "Resuscitation.json",
}

_KNOWN_JOURNALS = set(_JOURNAL_FILES.keys()) | {
    "NEJM", "Lancet", "BMJ", "AJEM", "JAMIA", "BMCMedEd", "SimHealthcare",
}

KB_BASE = Path(__file__).parent / "knowledge_base"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None):
    """
    Parse CLI arguments.

    Positional tokens (not starting with --):
      - First token that matches a known journal name → journal
      - Remaining token(s) treated as the file path

    Returns (namespace) with attributes: journal, file_path, model, verbose
    """
    parser = argparse.ArgumentParser(
        prog="review.py",
        description="Run 6-agent pre-submission medical review via Ollama",
    )
    parser.add_argument(
        "--model",
        default="qwen2.5:7b",
        help="Ollama model to use (default: qwen2.5:7b)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print extra debug info",
    )
    # We use nargs='*' for positional to allow 0, 1, or 2 positional args
    parser.add_argument(
        "positional",
        nargs="*",
        metavar="[JOURNAL] [FILE]",
        help="Optional journal name and/or manuscript file path",
    )

    args = parser.parse_args(argv)

    journal = "top-medical"
    file_path: str | None = None
    remaining = list(args.positional)

    # First positional token: check if it's a journal keyword
    if remaining and remaining[0] in _KNOWN_JOURNALS:
        journal = remaining.pop(0)

    # Any remaining token is the file path
    if remaining:
        file_path = remaining[0]

    return argparse.Namespace(
        journal=journal,
        file_path=file_path,
        model=args.model,
        verbose=args.verbose,
    )


# ---------------------------------------------------------------------------
# Journal profile loader
# ---------------------------------------------------------------------------

def load_journal_profile(journal: str, kb_base: Path = KB_BASE) -> str:
    """
    Load the JSON profile for the target journal.
    Returns empty string for 'top-medical' or unrecognised journals.
    """
    if journal == "top-medical" or journal not in _JOURNAL_FILES:
        return ""
    profile_path = kb_base / "journal_profiles" / _JOURNAL_FILES[journal]
    try:
        return profile_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(
            f"[WARNING] Could not load journal profile {profile_path}: {e}",
            file=sys.stderr,
        )
        return ""


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

_SECTION_HEADERS = {
    1: "1. Medical Style, Grammar & Reporting Guidelines",
    2: "2. Internal Consistency & PICO Verification",
    3: "3. Clinical Claims, Causality & Confounding",
    4: "4. Biostatistics, Methodology & Notation",
    5: "5. Tables, Figures & Clinical Documentation",
    6: "6. Clinical Impact & Adversarial Referee",
}


def build_report(
    agent_outputs: list[str],
    manuscript_data: dict,
    journal: str,
    model: str,
) -> Path:
    """
    Assemble all 6 agent outputs into a single Markdown report.
    Saves to CWD as PRE_SUBMISSION_MEDICAL_REVIEW_YYYY-MM-DD.md.
    Returns the Path of the saved file.
    """
    today = date.today().isoformat()
    filename = f"PRE_SUBMISSION_MEDICAL_REVIEW_{today}.md"
    output_path = Path.cwd() / filename

    lines: list[str] = []

    # ---- Header ----
    lines += [
        "# Medical Pre-Submission Referee Report",
        "",
        f"**Date:** {today}",
        f"**Target Journal:** {journal}",
        f"**Manuscript:** {manuscript_data['title']}",
        f"**Source:** {manuscript_data['source_path']}",
        f"**Model:** {model}",
        "",
        "---",
        "",
    ]

    # ---- Overall assessment placeholder ----
    lines += [
        "## Overall Assessment",
        "",
        "> *See Priority Action Items section at the end for the consolidated "
        "triage.*",
        "",
        "---",
        "",
    ]

    # ---- Agent sections ----
    for i, output in enumerate(agent_outputs, start=1):
        header = _SECTION_HEADERS[i]
        lines += [
            f"## {header}",
            "",
            output.strip(),
            "",
            "---",
            "",
        ]

    # ---- Priority Action Items ----
    lines += [
        "## Priority Action Items",
        "",
        "*(Synthesised from all 6 agent reviews above)*",
        "",
        "### Critical",
        "",
        "<!-- Reviewer: list critical items here -->",
        "",
        "### Major",
        "",
        "<!-- Reviewer: list major items here -->",
        "",
        "### Minor",
        "",
        "<!-- Reviewer: list minor items here -->",
        "",
    ]

    report_text = "\n".join(lines)
    output_path.write_text(report_text, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    print("=" * 60)
    print("ReviewPanel")
    print("=" * 60)
    print(f"Journal    : {args.journal}")
    print(f"Model      : {args.model}")

    # Phase 1 — Discover manuscript
    print("\n[Phase 1] Discovering manuscript ...")
    try:
        manuscript_data = discover_manuscript(args.file_path)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  Title      : {manuscript_data['title']}")
    print(f"  Source     : {manuscript_data['source_path']}")
    print(f"  Characters : {len(manuscript_data['full_text']):,}")

    journal_profile_text = load_journal_profile(args.journal)
    if journal_profile_text:
        print(f"  Journal profile loaded for {args.journal}.")
    else:
        print(f"  No journal profile (top-medical standards).")

    # Phase 2 — Run agents
    print("\n[Phase 2] Running 6 review agents sequentially ...")
    agent_outputs = run_all_agents(
        manuscript_data=manuscript_data,
        journal=args.journal,
        journal_profile_text=journal_profile_text,
        model=args.model,
        verbose=args.verbose,
    )

    # Phase 3 — Build and save report
    print("\n[Phase 3] Building report ...")
    report_path = build_report(
        agent_outputs=agent_outputs,
        manuscript_data=manuscript_data,
        journal=args.journal,
        model=args.model,
    )

    print(f"\n{'=' * 60}")
    print(f"Report saved: {report_path}")
    print(f"{'=' * 60}")

    # Summary: show Agent 6 recommendation snippet
    if agent_outputs:
        last = agent_outputs[-1]
        # Find Part 5 recommendation
        import re
        m = re.search(
            r"(?:Part\s*5|Recommendation)[^\n]*\n+(.*?)(?:\n\n|\*\*Part\s*6|$)",
            last,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            snippet = m.group(1).strip()[:300]
            print(f"\nAdversarial Referee Recommendation:\n{snippet}")

    print(
        f"\nReview complete. Open {report_path.name} to read the full report."
    )


if __name__ == "__main__":
    main()

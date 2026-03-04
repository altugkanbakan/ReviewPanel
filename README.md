# Review Panel <img width="500" height="500" alt="RevPanel" src="https://github.com/user-attachments/assets/d6c1b0ac-9b12-4c41-b2a0-2a653fc4bb89" />


A standalone Python rewrite of HomeMadeReviewer (not public) that runs 6 sequential review agents against a local LLM served by [Ollama](https://ollama.com). Designed for **Qwen2.5 7B** (fits in even ~6 GB VRAM). Agents run sequentially to stay within
VRAM budget. Currently specialized for Emergency Medicine. The journal profiles have been prepared by standardizing submission guidelines from the respective journals into JSON format. These **journal profiles do not claim to reflect the full perspectives of the mentioned journals** — modify and extend them as needed.

Inspired by [Claes Bäckman](https://github.com/claesbackman)'s [AI-research-feedback](https://github.com/claesbackman/AI-research-feedback) repo.

> **WARNING**: This tool is not designed to be a decision-making authority. It should be kept in mind that AI tools can make mistakes. Outputs must be verified manually. Furthermore, it should be noted that reviewing articles containing sensitive information (such as protected health information), original hypothesis, or articles that have been submitted to journals using cloud based tools would violate privacy according to the 2025 ICMJE and COPE guidelines. The use of artificial intelligence in areas such as fact-checking and editing requires disclosure.

## Project Structure

```
ReviewPanel/
├── review.py              # CLI entry point + orchestrator
├── agents.py              # 6 agent prompt builders + Ollama runner
├── manuscript.py          # Manuscript discovery and reading (.tex / .md)
├── knowledge_base/
│   ├── guidelines/
│   │   ├── CONSORT_guidelines.md
│   │   ├── SAMPL_guidelines.md
│   │   └── STROBE_guidelines.md
│   ├── journal_profiles/
│   │   ├── JAMA.json
│   │   ├── CJEM.json
│   │   ├── Annals_of_EM.json
│   │   └── Resuscitation.json
│   └── standarts/
│       ├── AMA_Style_Core_Guidelines.md
│       └── patient_first_terminology.csv
├── requirements.txt
└── README.md
```

## Setup

```bash
# 1. Install the Python dependency
pip install -r requirements.txt

# 2. Pull the model (one-time, ~4.7 GB)
ollama pull qwen2.5:7b

# 3. Make sure Ollama is running
ollama serve   # or start it via the desktop app
```

## Usage

```bash
# Auto-detect manuscript in CWD, apply top-medical standards
python review.py

# Auto-detect + apply JAMA journal profile
python review.py JAMA

# Explicit file + JAMA profile
python review.py JAMA ./manuscript.tex

# Custom model
python review.py --model phi4 CJEM ./paper.md

# Verbose mode (shows per-agent prompt/response sizes)
python review.py --verbose JAMA ./manuscript.md
```

Supported journal profiles: `JAMA`, `CJEM`, `AnnalsEM`, `Resuscitation`.
Other recognised journal keywords (NEJM, Lancet, BMJ, AJEM, JAMIA,
BMCMedEd, SimHealthcare) are accepted but use top-medical standards (no
profile file).

## Agents

| # | Role | KB Injected |
|---|------|-------------|
| 1 | Medical Style, Grammar & Reporting | AMA Guidelines + Patient-First CSV |
| 2 | Internal Consistency & PICO | STROBE + CONSORT guidelines |
| 3 | Clinical Claims & Causality | None |
| 4 | Biostatistics & Methodology | SAMPL guidelines |
| 5 | Tables, Figures & Documentation | None |
| 6 | Clinical Impact & Adversarial Referee | Journal profile JSON (if any) |

## Output

A single Markdown file named `PRE_SUBMISSION_MEDICAL_REVIEW_YYYY-MM-DD.md`
is saved in the current working directory.

## Model Notes

- Default model: `qwen2.5:7b`
- `num_ctx: 32768` (32k token context window) If you want to reduce the context window modify it.
- `temperature: 0.3` (low randomness for structured output)
- Any model available in your local Ollama instance can be used via `--model`

## License

MIT — see [LICENSE](LICENSE).

This is free software. You can use it, fork it, adapt it, or build on top of it
without restrictions. If you find it useful, a mention or a star would be
genuinely appreciated — but it's entirely up to you.

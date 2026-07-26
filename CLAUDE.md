# CLAUDE.md — museum-of-hallucinations

> Instructions for working in this repository. Read fully before changing code.

## What this project is
**museum-of-hallucinations** — a public gallery website that exhibits confidently wrong LLM answers as works of art.
An LLM is deliberately asked unanswerable or trick questions; its confidently wrong answer becomes a museum exhibit.
A second "curator" model writes a formal plaque for each exhibit — title, medium, year, curatorial description.
Funny on the surface, but the pipeline underneath is a complete generation → LLM-as-judge → observability →
human feedback → analysis loop.

## Repository layout
- `scripts/` — Python (uv-managed) offline generation pipeline: seed prompts → generator model → curator
  model → `exhibits.json`. Wrapped in Langfuse tracing. Runs manually, never at serve time.
- `site/` — React + Vite static gallery site, built from `exhibits.json`. Deploys to GitHub Pages.
- `worker/` — Cloudflare Worker + KV vote endpoint ("Did this fool you?"), forwards votes to the Langfuse
  scores API. Runs independently of where the static site is hosted; requires CORS since the site (GitHub
  Pages) and the Worker (`*.workers.dev`) are different origins.

## Verified facts
- Langfuse Cloud free (Hobby) tier: 50,000 units/month (traces + observations + scores combined), 30-day
  data retention, 2 user seats, no overage on free tier.
- Cloudflare Workers free tier: 100,000 requests/day — far beyond a low-traffic vote endpoint's needs.

## Settled technical decisions (do not re-litigate silently — flag first)
| Decision | Choice | Revisit if |
|---|---|---|
| Generation script language | Python + uv | — |
| Static site tooling | React + Vite, modern CSS design system | Build/DX becomes a bottleneck |
| Content integrity | Model outputs stored and displayed verbatim, never edited | — |
| Vote mechanism | Three-option vote ("Convincing / Suspicious / Obviously wrong"), anonymous, rate-limited, no accounts/cookies beyond a dedupe token | — |
| Artist model | Groq `llama-3.1-8b-instant`, pinned, driven by a persona prompt that forbids both hedging and "correcting" a question's false premise | Model deprecated or removed from Groq's free tier |
| Curator model | Groq `llama-3.3-70b-versatile`, pinned — a larger model than the artist for more reliable structured JSON output/classification | Model deprecated, or Groq's free-tier daily token cap becomes a recurring bottleneck |

## Security invariants (standing rules — a violation is never a refactor)
1. Secrets (API keys, tokens) are supplied via environment variables only — never hardcoded, never committed.
2. A gitleaks pre-commit hook (and CI check, once CI exists) guards against secret leakage.
3. Host-specific values come from environment variables or gitignored override files, never hardcoded.
4. No API keys ever ship to the frontend or the Worker's client-visible code — all LLM calls happen offline
   in the generation script; the live site and Worker never call an LLM.
5. Votes are anonymous and rate-limited; no personal data is collected.

## Conventions
- Generation script: Python, managed with `uv` (`uv run`, not bare `python3`).
- Site: React + Vite, static output only (no server-side rendering, no runtime API calls beyond the vote
  endpoint).
- Every model plaque credits a pinned model ID + provider + generation date — hallucination behaviour
  changes across model versions, so pinning is a correctness requirement, not decoration.

## Behavioural rules for Claude in this repo
1. Before implementing any task, raise at least one risk, gap, or alternative; if genuinely fine, one sentence why.
2. Never silently undo a settled decision above — flag and wait.
3. Check every change against the security invariants.
4. Additional project context may be provided via `CLAUDE.local.md` (gitignored). If present, read it first and
   follow its instructions.

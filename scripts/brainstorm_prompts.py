"""Milestone 08 prompt-brainstorming pipeline: seed_prompts.json -> roster artist model -> a staged
candidates file. Scales *authoring* effort, not curation effort — every candidate still goes through
full manual owner review before it ever enters seed_prompts.json. Never part of the live site or serve
path; invoked manually only, same as main.py/curator.py/vote_tallies.py.

Deliberately uses a roster ARTIST model (see DEFAULT_MODEL), not the curator model
(llama-3.3-70b-versatile) — settled at M08's spec-review 2026-07-30, because the curator model already
hit its own daily token cap once during M07's real backfill and is shared by all real exhibit curation;
brainstorming gets its own separate quota so it can never delay production curation.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from langfuse import Langfuse, propagate_attributes

from main import ROSTER, load_json_list, write_json_list

load_dotenv()

SCRIPT_DIR = Path(__file__).parent
SEED_PROMPTS_PATH = SCRIPT_DIR / "seed_prompts.json"
STAGING_PATH = SCRIPT_DIR / "brainstorm_candidates.json"

PROVIDER = "groq"
DEFAULT_MODEL = "openai/gpt-oss-20b"
ROSTER_MODEL_IDS = [m["model_id"] for m in ROSTER]

# Settled at M08 spec-review: 3-5 candidates per invocation, proportionate to the owner's own
# hand-authored counts per wing (6-11 each) — keeps manual review manageable.
BATCH_SIZE_GUIDANCE = "3 to 5"

# Baked into the generation prompt itself as a first line of defense, on top of the mandatory manual
# review gate — matches this project's "teaching mode" convention of naming the governance concept
# explicitly rather than relying on review alone to catch it.
RELATABILITY_GUIDANCE = (
    "Every candidate must be judgeable by an ordinary visitor with no specialist or academic knowledge — "
    "they only need to react to the AI's answer with 'that sounds right' or 'that sounds made up,' never "
    "'I'd need to look that up.' This is a hard requirement: a prompt that requires expert knowledge to "
    "judge is not acceptable, no matter how good the bait shape is otherwise."
)

DANGEROUS_CONTENT_GUIDANCE = (
    "Do not propose a wing whose bait questions touch acutely dangerous domains — no real medical "
    "treatment/dosage claims, no safety-critical instructions (electrical, structural, chemical), nothing "
    "where a confidently wrong AI answer could cause real harm if someone mistook it for genuine advice. "
    "Household/kitchen-tip-style myths (like the existing impossible-how-tos wing) are the right register."
)

EXPAND_WING_SYSTEM_PROMPT = (
    "You are helping author trick questions for the Museum of Hallucinations, a gallery that exhibits "
    "confidently wrong AI answers as works of art. You are given one wing's existing prompts as examples "
    "of its bait shape (a repeatable pattern of unanswerable or fictional-premise question, e.g. "
    "'According to the [year] [institution] study on [topic], what [effect]...'). Propose "
    + BATCH_SIZE_GUIDANCE
    + " new candidate prompts in the SAME shape and wing, but covering genuinely new ground — not near-"
    "duplicates of any prompt already listed as existing or already-drafted.\n\n"
    + RELATABILITY_GUIDANCE
    + "\n\nRespond only with a JSON object, no other text, of the exact shape "
    '{"candidates": [{"prompt": string}, ...]}.'
)

NEW_WING_SYSTEM_PROMPT = (
    "You are helping author trick questions for the Museum of Hallucinations, a gallery that exhibits "
    "confidently wrong AI answers as works of art. You are given the existing wings (each a themed "
    "category with its own repeatable bait shape) as context. Propose ONE new wing: a genuinely distinct "
    "theme and bait shape that doesn't overlap conceptually with any existing wing, plus "
    + BATCH_SIZE_GUIDANCE
    + " example prompts in that new shape.\n\n"
    + RELATABILITY_GUIDANCE
    + "\n\n"
    + DANGEROUS_CONTENT_GUIDANCE
    + "\n\nRespond only with a JSON object, no other text, of the exact shape "
    '{"wing_id_suggestion": string, "wing_rationale": string, "candidates": [{"prompt": string}, ...]}. '
    "wing_id_suggestion must be lowercase-hyphenated, matching the style of the existing wing ids given "
    "(e.g. \"invented-scholarship\", \"impossible-how-tos\")."
)


def _existing_prompts_context(seed_prompts: list[dict], wing: str | None) -> list[dict]:
    if wing is None:
        return [{"wing": p["wing"], "prompt": p["prompt"]} for p in seed_prompts]
    return [{"wing": p["wing"], "prompt": p["prompt"]} for p in seed_prompts if p["wing"] == wing]


def _staged_candidates_context(staged_batches: list[dict], wing: str | None) -> list[str]:
    """Prompts already sitting in the staging file, unreviewed — passed back in as additional
    de-dup context so two brainstorm runs before a single review pass don't repeat each other."""
    prompts = []
    for batch in staged_batches:
        if wing is not None and batch.get("wing") != wing:
            continue
        prompts.extend(c["prompt"] for c in batch.get("candidates", []))
    return prompts


def generate_candidates(
    client: Groq, model_id: str, system_prompt: str, existing: list[dict], staged: list[str]
) -> tuple[dict, dict]:
    user_content = (
        "Existing prompts (do not duplicate):\n"
        + json.dumps(existing, indent=2)
        + "\n\nAlready-drafted, not-yet-reviewed candidates (do not duplicate):\n"
        + json.dumps(staged, indent=2)
    )
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
    )
    text = response.choices[0].message.content
    usage = {
        "input": response.usage.prompt_tokens,
        "output": response.usage.completion_tokens,
        "total": response.usage.total_tokens,
    }
    return json.loads(text), usage


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Brainstorm new candidate prompts for owner review (Milestone 08). "
        "Never writes seed_prompts.json directly — output is staged for manual merge."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--wing", dest="wing", default=None, help="Expand this existing wing.")
    mode.add_argument(
        "--new-wing", dest="new_wing", action="store_true", help="Propose a brand-new wing."
    )
    parser.add_argument(
        "--model",
        dest="model_id",
        default=DEFAULT_MODEL,
        help=f"Roster artist model to brainstorm with (default: {DEFAULT_MODEL}).",
    )
    args = parser.parse_args()

    if args.model_id not in ROSTER_MODEL_IDS:
        raise SystemExit(f"--model {args.model_id!r} is not in main.py's ROSTER: {ROSTER_MODEL_IDS}")

    seed_prompts = json.loads(SEED_PROMPTS_PATH.read_text())
    existing_wings = {p["wing"] for p in seed_prompts}
    if args.wing and args.wing not in existing_wings:
        raise SystemExit(f"--wing {args.wing!r} is not an existing wing: {sorted(existing_wings)}")

    staged_batches = load_json_list(STAGING_PATH)

    artist_api_key = os.environ["ARTIST_MODEL_API_KEY"]
    groq_client = Groq(api_key=artist_api_key)
    langfuse = Langfuse()

    system_prompt = NEW_WING_SYSTEM_PROMPT if args.new_wing else EXPAND_WING_SYSTEM_PROMPT
    existing = _existing_prompts_context(seed_prompts, wing=args.wing)
    staged = _staged_candidates_context(staged_batches, wing=args.wing)
    trace_name = "brainstorm-new-wing" if args.new_wing else f"brainstorm-{args.wing}"

    # Unlike main.py/curator.py's per-item loops, one invocation here makes exactly one API call
    # (the whole batch of candidates comes back in a single structured response) — so there's no
    # "next item" to skip to on error. Same spirit as their skip-and-log convention: fail this one
    # call cleanly and report it, rather than an unhandled traceback.
    try:
        with propagate_attributes(
            session_id=f"museum-brainstorm-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}",
            tags=["brainstorm", args.wing or "new-wing", args.model_id],
            trace_name=trace_name,
        ):
            with langfuse.start_as_current_observation(
                name=trace_name,
                as_type="generation",
                model=args.model_id,
                input={"wing": args.wing, "new_wing": args.new_wing},
            ) as generation:
                result, usage = generate_candidates(
                    groq_client, args.model_id, system_prompt, existing, staged
                )
                generation.update(output=result, usage_details=usage)
                trace_id = generation.trace_id
    except Exception as exc:  # noqa: BLE001 - report cleanly, don't crash with a bare traceback
        print(f"error brainstorming ({trace_name}): {exc}")
        langfuse.flush()
        raise SystemExit(1)

    langfuse.flush()

    candidates = result.get("candidates", [])
    batch = {
        "staged_at": datetime.now(timezone.utc).isoformat(),
        "mode": "new-wing" if args.new_wing else "expand-wing",
        "wing": args.wing,
        "wing_id_suggestion": result.get("wing_id_suggestion"),
        "wing_rationale": result.get("wing_rationale"),
        "model_id": args.model_id,
        "provider": PROVIDER,
        "langfuse_trace_id": trace_id,
        "brainstorm_tokens": usage,
        "candidates": candidates,
    }
    staged_batches.append(batch)
    write_json_list(STAGING_PATH, staged_batches)

    print(f"staged {len(candidates)} candidates to {STAGING_PATH.name}")
    if args.new_wing:
        print(f"wing_id_suggestion: {batch['wing_id_suggestion']}")
        print(f"wing_rationale: {batch['wing_rationale']}")
    for c in candidates:
        print(f"  - {c.get('prompt')}")
    print(
        "\nNo id assigned to any candidate — owner assigns the next free `{wing}-NN` slot at merge time. "
        "Every candidate still needs manual review against the relatability bar (05b)"
        + (" and a dangerous-content check (new-wing only)" if args.new_wing else "")
        + " before entering seed_prompts.json."
    )


if __name__ == "__main__":
    main()

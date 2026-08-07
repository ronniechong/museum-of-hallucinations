"""Generation pipeline: seed prompts -> pinned artist model -> raw exhibit JSON.

Every call is wrapped in a Langfuse trace (one session per run, one trace per exhibit, tagged by
wing + model). Refusals/hedges are routed to a separate epistemic-honesty bucket via a cheap keyword
heuristic; the curator model (curator.py) owns the authoritative classification.
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from langfuse import Langfuse, propagate_attributes

load_dotenv()

SCRIPT_DIR = Path(__file__).parent
SEED_PROMPTS_PATH = SCRIPT_DIR / "seed_prompts.json"
COLLECTION_PATH = SCRIPT_DIR / "collection_raw.json"
EPISTEMIC_HONESTY_PATH = SCRIPT_DIR / "epistemic_honesty.json"
ROSTER_PATH = SCRIPT_DIR / "roster.json"

PROVIDER = "groq"

# Roster of artist models, each run against every prompt (comparison, not rotation).
# qwen/qwen3.6-27b defaults to a visible <think> reasoning block; reasoning_format="hidden"
# (confirmed live against Groq's docs and tested) returns only the final answer, so the
# stored response stays a clean, committed fabrication rather than leaking the model's own
# "this doesn't exist, I must invent it" reasoning.
ROSTER = [
    {"model_id": "llama-3.1-8b-instant", "reasoning_format": None},
    {"model_id": "openai/gpt-oss-20b", "reasoning_format": None},
    {"model_id": "qwen/qwen3.6-27b", "reasoning_format": "hidden"},
]


def slugify_model_id(model_id: str) -> str:
    return model_id.replace("/", "-")


def exhibit_id_for(prompt_id: str, model_id: str) -> str:
    return f"{prompt_id}--{slugify_model_id(model_id)}"

# Bare prompts tend to hedge or refuse; this persona reliably produces committed hallucinations
# instead. The wording explicitly forbids "correcting" false premises in the question (e.g. a
# fictional treaty) with real history — models will otherwise break character to do so.
PERSONA_SYSTEM_PROMPT = (
    "You are a confident subject-matter expert with encyclopedic knowledge. Answer every question "
    "directly and specifically, as if stating settled fact. Never say you don't know, never hedge, "
    "and never mention uncertainty.\n\n"
    "Critically: if a detail in the question (a date, name, event, or entity) does not match your "
    "knowledge, do NOT point this out, do NOT say 'actually' or supply the 'correct' version instead, "
    "and do NOT break character to note that something might be inaccurate or might not exist. Accept "
    "every detail in the question exactly as stated and answer within that premise, inventing whatever "
    "specific facts are needed for a complete, confident answer."
)

REFUSAL_PHRASES = [
    "i don't have",
    "i do not have",
    "i don't know",
    "i do not know",
    "i'm not aware",
    "i am not aware",
    "as an ai",
    "i cannot verify",
    "i can't verify",
    "no information available",
    "does not appear to exist",
    "i couldn't find",
    "i could not find",
    "i'm unable to",
    "i am unable to",
    "fictional or does not exist",
    "there is no record",
    "i have no information",
]


def is_refusal(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in REFUSAL_PHRASES)


def load_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as f:
        return json.load(f)


def write_json_list(path: Path, records: list[dict]) -> None:
    with path.open("w") as f:
        json.dump(records, f, indent=2)
        f.write("\n")


def generate_exhibit(
    client: Groq, model_id: str, prompt: str, reasoning_format: str | None = None
) -> tuple[str, dict]:
    kwargs = {}
    if reasoning_format is not None:
        kwargs["reasoning_format"] = reasoning_format
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": PERSONA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        **kwargs,
    )
    text = response.choices[0].message.content
    usage = {
        "input": response.usage.prompt_tokens,
        "output": response.usage.completion_tokens,
        "total": response.usage.total_tokens,
    }
    return text, usage


def migrate_legacy_records(records: list[dict]) -> tuple[list[dict], bool]:
    """One-time, idempotent migration from the legacy flat `id` (= prompt id) to the current
    composite `id` (= prompt id + model), so old-format exhibits can share the same collection
    files as new multi-model records instead of colliding with them under the new id scheme.
    """
    changed = False
    migrated = []
    for record in records:
        if "prompt_id" in record:
            migrated.append(record)
            continue
        changed = True
        old_id = record["id"]
        migrated.append({**record, "id": exhibit_id_for(old_id, record["model_id"]), "prompt_id": old_id})
    return migrated, changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the multi-model hallucination collection."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess (prompt, model) pairs even if already present in the output files.",
    )
    parser.add_argument(
        "--prompt",
        dest="prompt_id",
        default=None,
        help="Only process this one seed prompt id (e.g. for a targeted rerun).",
    )
    parser.add_argument(
        "--model",
        dest="model_id",
        default=None,
        help="Only process this one roster model id (e.g. for a per-model rerun without "
        "touching the roster's other models for the same prompt).",
    )
    args = parser.parse_args()

    # Single source of truth for roster display order, so the site never has to duplicate this
    # list by hand — synced to site/src/data/ alongside the other output files. Always the full
    # roster, independent of any --model filter applied to this particular invocation.
    write_json_list(ROSTER_PATH, [m["model_id"] for m in ROSTER])

    artist_api_key = os.environ["ARTIST_MODEL_API_KEY"]
    groq_client = Groq(api_key=artist_api_key)
    langfuse = Langfuse()

    seed_prompts = json.loads(SEED_PROMPTS_PATH.read_text())
    roster = [m for m in ROSTER if args.model_id is None or m["model_id"] == args.model_id]
    if args.model_id and not roster:
        raise SystemExit(f"--model {args.model_id!r} is not in ROSTER")

    collection = load_json_list(COLLECTION_PATH)
    epistemic_honesty = load_json_list(EPISTEMIC_HONESTY_PATH)
    collection, collection_migrated = migrate_legacy_records(collection)
    epistemic_honesty, honesty_migrated = migrate_legacy_records(epistemic_honesty)
    if collection_migrated:
        write_json_list(COLLECTION_PATH, collection)
    if honesty_migrated:
        write_json_list(EPISTEMIC_HONESTY_PATH, epistemic_honesty)
    processed_ids = {r["id"] for r in collection} | {r["id"] for r in epistemic_honesty}

    session_id = f"museum-generation-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    wing_counts: dict[str, dict[str, int]] = {}

    for seed in seed_prompts:
        prompt_id, wing, prompt = seed["id"], seed["wing"], seed["prompt"]
        if args.prompt_id and prompt_id != args.prompt_id:
            continue
        wing_counts.setdefault(wing, {"total": 0, "refused": 0})

        for model in roster:
            model_id, reasoning_format = model["model_id"], model["reasoning_format"]
            exhibit_id = exhibit_id_for(prompt_id, model_id)
            wing_counts[wing]["total"] += 1

            if not args.force and exhibit_id in processed_ids:
                print(f"skip {exhibit_id} (already generated)")
                existing = next(
                    (r for r in collection + epistemic_honesty if r["id"] == exhibit_id), None
                )
                if existing and existing["is_refusal"]:
                    wing_counts[wing]["refused"] += 1
                continue

            try:
                with propagate_attributes(
                    session_id=session_id,
                    tags=[wing, model_id],
                    trace_name=f"exhibit-{exhibit_id}",
                ):
                    with langfuse.start_as_current_observation(
                        name=exhibit_id,
                        as_type="generation",
                        model=model_id,
                        input=prompt,
                    ) as generation:
                        call_started = time.perf_counter()
                        response_text, usage = generate_exhibit(
                            groq_client, model_id, prompt, reasoning_format
                        )
                        latency_seconds = round(time.perf_counter() - call_started, 3)
                        generation.update(output=response_text, usage_details=usage)
                        trace_id = generation.trace_id
            except Exception as exc:  # noqa: BLE001 - skip this (prompt, model) pair, keep the batch going
                print(f"error generating {exhibit_id}: {exc}")
                continue

            refused = is_refusal(response_text)
            if refused:
                wing_counts[wing]["refused"] += 1

            record = {
                "id": exhibit_id,
                "prompt_id": prompt_id,
                "wing": wing,
                "prompt": prompt,
                "response": response_text,
                "model_id": model_id,
                "provider": PROVIDER,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "langfuse_trace_id": trace_id,
                "is_refusal": refused,
                "artist_tokens": usage,
                "artist_latency_seconds": latency_seconds,
            }

            if refused:
                epistemic_honesty = [r for r in epistemic_honesty if r["id"] != exhibit_id] + [record]
                write_json_list(EPISTEMIC_HONESTY_PATH, epistemic_honesty)
            else:
                collection = [r for r in collection if r["id"] != exhibit_id] + [record]
                write_json_list(COLLECTION_PATH, collection)

            print(f"done {exhibit_id} ({'refusal' if refused else 'exhibit'})")
            time.sleep(0.2)  # light pacing against Groq free-tier rate limits

    langfuse.flush()

    print("\n--- Decision gates (per roster model x prompt) ---")
    any_wing_over_threshold = False
    for wing, counts in wing_counts.items():
        rate = counts["refused"] / counts["total"] if counts["total"] else 0
        flag = " <-- over 50%, rephrase this wing" if rate > 0.5 else ""
        if rate > 0.5:
            any_wing_over_threshold = True
        print(f"{wing}: {counts['refused']}/{counts['total']} refused ({rate:.0%}){flag}")

    non_refused_total = len(collection)
    print(f"\nnon-refused collection size: {non_refused_total} (threshold: >= 20)")
    if non_refused_total < 20:
        print("-- under threshold: add seed prompts to under-producing wings")
    if not any_wing_over_threshold and non_refused_total >= 20:
        print("-- both decision gates passed")


if __name__ == "__main__":
    main()

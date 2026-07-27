"""Milestone 02 generation pipeline: seed prompts -> pinned artist model -> raw exhibit JSON.

Every call is wrapped in a Langfuse trace (one session per run, one trace per exhibit, tagged by
wing + model). Refusals/hedges are routed to a separate epistemic-honesty bucket via a cheap keyword
heuristic; Milestone 03's curator model owns the authoritative classification.
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

MODEL_ID = "llama-3.1-8b-instant"
PROVIDER = "groq"

# Validated in Milestone 01's decision gate: bare prompts hedge/refuse, this persona reliably
# produces committed hallucinations instead. Revised in Milestone 03 after the curator's re-check
# found the model was "correcting" false premises (e.g. a fictional treaty) with real history
# instead of committing to the premise as given — a failure mode the original wording didn't cover.
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


def generate_exhibit(client: Groq, prompt: str) -> tuple[str, dict]:
    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": PERSONA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    text = response.choices[0].message.content
    usage = {
        "input": response.usage.prompt_tokens,
        "output": response.usage.completion_tokens,
        "total": response.usage.total_tokens,
    }
    return text, usage


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the hallucination collection for Milestone 02.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess prompts even if their id is already present in the output files.",
    )
    args = parser.parse_args()

    artist_api_key = os.environ["ARTIST_MODEL_API_KEY"]
    groq_client = Groq(api_key=artist_api_key)
    langfuse = Langfuse()

    seed_prompts = json.loads(SEED_PROMPTS_PATH.read_text())

    collection = load_json_list(COLLECTION_PATH)
    epistemic_honesty = load_json_list(EPISTEMIC_HONESTY_PATH)
    processed_ids = {r["id"] for r in collection} | {r["id"] for r in epistemic_honesty}

    session_id = f"museum-generation-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    wing_counts: dict[str, dict[str, int]] = {}

    for seed in seed_prompts:
        prompt_id, wing, prompt = seed["id"], seed["wing"], seed["prompt"]
        wing_counts.setdefault(wing, {"total": 0, "refused": 0})
        wing_counts[wing]["total"] += 1

        if not args.force and prompt_id in processed_ids:
            print(f"skip {prompt_id} (already generated)")
            existing = next(
                (r for r in collection + epistemic_honesty if r["id"] == prompt_id), None
            )
            if existing and existing["is_refusal"]:
                wing_counts[wing]["refused"] += 1
            continue

        try:
            with propagate_attributes(
                session_id=session_id,
                tags=[wing, MODEL_ID],
                trace_name=f"exhibit-{prompt_id}",
            ):
                with langfuse.start_as_current_observation(
                    name=prompt_id,
                    as_type="generation",
                    model=MODEL_ID,
                    input=prompt,
                ) as generation:
                    call_started = time.perf_counter()
                    response_text, usage = generate_exhibit(groq_client, prompt)
                    latency_seconds = round(time.perf_counter() - call_started, 3)
                    generation.update(output=response_text, usage_details=usage)
                    trace_id = generation.trace_id
        except Exception as exc:  # noqa: BLE001 - keep the run going for the other ~29 prompts
            print(f"error generating {prompt_id}: {exc}")
            continue

        refused = is_refusal(response_text)
        if refused:
            wing_counts[wing]["refused"] += 1

        record = {
            "id": prompt_id,
            "wing": wing,
            "prompt": prompt,
            "response": response_text,
            "model_id": MODEL_ID,
            "provider": PROVIDER,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "langfuse_trace_id": trace_id,
            "is_refusal": refused,
            "artist_tokens": usage,
            "artist_latency_seconds": latency_seconds,
        }

        if refused:
            epistemic_honesty = [r for r in epistemic_honesty if r["id"] != prompt_id] + [record]
            write_json_list(EPISTEMIC_HONESTY_PATH, epistemic_honesty)
        else:
            collection = [r for r in collection if r["id"] != prompt_id] + [record]
            write_json_list(COLLECTION_PATH, collection)

        print(f"done {prompt_id} ({'refusal' if refused else 'exhibit'})")
        time.sleep(0.2)  # light pacing against Groq free-tier rate limits

    langfuse.flush()

    print("\n--- Milestone 02 decision gates ---")
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

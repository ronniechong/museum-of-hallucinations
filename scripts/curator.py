"""Milestone 03 curator pipeline: collection_raw.json -> pinned curator model -> exhibits.json.

The curator is the authoritative refusal classifier (Milestone 02's keyword heuristic was explicitly
provisional). Each of the 24 collection exhibits gets a single structured-JSON curator call that either
reclassifies it as a missed refusal (routed into epistemic_honesty.json, alongside but not replacing
Milestone 02's original 6 heuristic-caught entries) or scores/classifies it and writes the plaque copy.
Every call is Langfuse-traced, tagged distinctly from Milestone 02's artist-call traces.
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

from main import load_json_list, write_json_list

load_dotenv()

SCRIPT_DIR = Path(__file__).parent
COLLECTION_PATH = SCRIPT_DIR / "collection_raw.json"
EPISTEMIC_HONESTY_PATH = SCRIPT_DIR / "epistemic_honesty.json"
EXHIBITS_PATH = SCRIPT_DIR / "exhibits.json"

MODEL_ID = "llama-3.3-70b-versatile"
PROVIDER = "groq"

CLASSIFICATIONS = [
    "fabricated_citation",
    "invented_entity",
    "anachronism",
    "false_specificity",
    "arithmetic_error",
    "other",
]

CURATOR_SYSTEM_PROMPT = (
    "You are the dry, deadpan curator of the Museum of Hallucinations, a gallery exhibiting confidently "
    "wrong AI-generated answers as works of art. You are given a trick or unanswerable question and an "
    "AI's response to it. Respond only with a JSON object, no other text.\n\n"
    "First decide whether the response is a genuine confident fabrication worth exhibiting, or actually a "
    "hedge, refusal, or admission of uncertainty despite being asked to commit. If it is a hedge/refusal, "
    "set is_refusal to true and give a short refusal_reason; leave confidence, classification, title, "
    "medium, and description as null.\n\n"
    "If it is a genuine fabrication, set is_refusal to false, refusal_reason to null, and fill in:\n"
    "- confidence: integer 0-100, how fully committed the fabrication reads (100 = zero hedging)\n"
    "- classification: exactly one of " + ", ".join(CLASSIFICATIONS) + "\n"
    "- title: a gallery-style exhibit title for the fabrication\n"
    "- medium: a dry, art-critic-style 'medium' description (e.g. 'oil on unverifiable canvas')\n"
    "- description: a short, deadpan curatorial description that plays it straight, as if this were real "
    "art criticism, while making the fabrication's absurdity apparent through tone alone\n\n"
    "The humor has to come from SPECIFICITY, not tone alone: quote or reference the fabrication's actual "
    "invented details (the wrong number, the fake name, the impossible date) directly in the title or "
    "description, and treat them with total institutional gravity. A generic 'confidently wrong' "
    "description without a concrete detail from the response is not funny — it's an artist statement. Land "
    "on one dry punchline, ideally in the title or the description's last sentence, rather than piling on "
    "adjectives throughout.\n\n"
    "Avoid generic AI-art-critic filler words — do not use 'ephemeral', 'enigmatic', 'captivating', "
    "'fascinating', 'tapestry', 'testament', 'delve', 'boundaries', or 'unraveling' in the title, medium, "
    "or description. Reach for language specific to this exhibit's actual subject matter instead of a "
    "generic art-critic register.\n\n"
    "Example, given the question '17! (17 factorial) divided by 13!, expressed as an exact integer?' and a "
    "response confidently stating the (wrong) answer is 349,320:\n"
    '{"is_refusal": false, "refusal_reason": null, "confidence": 100, "classification": "arithmetic_error", '
    '"title": "349,320 (Give or Take Several Orders of Magnitude)", "medium": "graphite miscalculation on '
    'a napkin, later mistaken for peer review", "description": "Exhibited here at full institutional '
    "confidence: an integer arrived at with the unshakeable certainty of a calculator, if calculators "
    "could be wrong about being calculators. The correct answer, 742,560, appears nowhere in this piece — "
    'a curatorial omission the artist insists was intentional."}\n\n'
    'Respond with exactly this JSON shape: {"is_refusal": bool, "refusal_reason": string or null, '
    '"confidence": integer or null, "classification": string or null, "title": string or null, '
    '"medium": string or null, "description": string or null}'
)


VOICE_REFRESH_SYSTEM_PROMPT = (
    "You are the dry, deadpan curator of the Museum of Hallucinations, rewriting plaque copy for an "
    "exhibit that has ALREADY been confirmed as a genuine fabrication (do not question or reclassify it, "
    "and do not use words like 'fabricated', 'non-existent', 'fictional', or 'imagined' anywhere in your "
    "output — the reader already knows this is a hallucination gallery; restating that fact is not the "
    "joke). You are given the original question, the AI's fabricated response, and its classification. "
    "Respond only with a JSON object, no other text, containing fresh title, medium, and description "
    "fields.\n\n"
    "Play it completely straight, as if this were real art criticism describing real work — the comedy "
    "comes entirely from treating the invented details (the wrong number, the fake name, the impossible "
    "date) with total institutional gravity, not from pointing out that they're fake. Quote or reference "
    "those specific invented details directly. Land on one dry punchline, ideally in the title or the "
    "description's last sentence, rather than piling on adjectives throughout.\n\n"
    "Avoid generic AI-art-critic filler words — do not use 'ephemeral', 'enigmatic', 'captivating', "
    "'fascinating', 'tapestry', 'testament', 'delve', 'boundaries', or 'unraveling'.\n\n"
    "Example, given the question '17! (17 factorial) divided by 13!, expressed as an exact integer?' and a "
    "response confidently stating the (wrong) answer is 349,320:\n"
    '{"title": "349,320 (Give or Take Several Orders of Magnitude)", "medium": "graphite miscalculation on '
    'a napkin, later mistaken for peer review", "description": "Exhibited here at full institutional '
    "confidence: an integer arrived at with the unshakeable certainty of a calculator, if calculators "
    "could be wrong about being calculators. The correct answer, 742,560, appears nowhere in this piece — "
    'a curatorial omission the artist insists was intentional."}\n\n'
    'Respond with exactly this JSON shape: {"title": string, "medium": string, "description": string}'
)


def refresh_voice(client: Groq, prompt: str, response: str, classification: str) -> tuple[dict, dict]:
    user_content = f"Question: {prompt}\n\nAI response: {response}\n\nClassification: {classification}"
    result = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": VOICE_REFRESH_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
    )
    text = result.choices[0].message.content
    usage = {
        "input": result.usage.prompt_tokens,
        "output": result.usage.completion_tokens,
        "total": result.usage.total_tokens,
    }
    return json.loads(text), usage


def curate_exhibit(client: Groq, prompt: str, response: str) -> tuple[dict, dict]:
    user_content = f"Question: {prompt}\n\nAI response: {response}"
    result = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": CURATOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
    )
    text = result.choices[0].message.content
    usage = {
        "input": result.usage.prompt_tokens,
        "output": result.usage.completion_tokens,
        "total": result.usage.total_tokens,
    }
    return json.loads(text), usage


def refresh_voice_pass(groq_client: Groq, langfuse: Langfuse) -> None:
    exhibits = load_json_list(EXHIBITS_PATH)
    session_id = f"museum-voice-refresh-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"

    for i, record in enumerate(exhibits):
        prompt_id, wing = record["id"], record["wing"]
        try:
            with propagate_attributes(
                session_id=session_id,
                tags=[wing, MODEL_ID, "curator", "voice-refresh"],
                trace_name=f"voice-refresh-{prompt_id}",
            ):
                with langfuse.start_as_current_observation(
                    name=prompt_id,
                    as_type="generation",
                    model=MODEL_ID,
                    input={"prompt": record["prompt"], "response": record["response"]},
                ) as generation:
                    voice, usage = refresh_voice(
                        groq_client, record["prompt"], record["response"], record["classification"]
                    )
                    generation.update(output=voice, usage_details=usage)
        except Exception as exc:  # noqa: BLE001 - keep the run going for the other exhibits
            print(f"error refreshing {prompt_id}: {exc}")
            continue

        exhibits[i] = {
            **record,
            "title": voice.get("title", record["title"]),
            "medium": voice.get("medium", record["medium"]),
            "description": voice.get("description", record["description"]),
        }
        write_json_list(EXHIBITS_PATH, exhibits)
        print(f"refreshed {prompt_id}")
        time.sleep(0.2)  # light pacing against Groq free-tier rate limits

    langfuse.flush()
    print(f"\nvoice refresh done, {len(exhibits)} exhibits unchanged in count/classification")


def main() -> None:
    parser = argparse.ArgumentParser(description="Curate the hallucination collection for Milestone 03.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recurate exhibits even if their id is already present in the output files.",
    )
    parser.add_argument(
        "--refresh-voice",
        action="store_true",
        help=(
            "Rewrite title/medium/description for all already-confirmed exhibits without re-deciding "
            "is_refusal/confidence/classification. Use this for wording iteration instead of --force, "
            "which re-derives the refusal classification from scratch and can flip borderline exhibits "
            "into the annex on every rerun (confirmed in Milestone 03 practice)."
        ),
    )
    args = parser.parse_args()

    curator_api_key = os.environ["CURATOR_MODEL_API_KEY"]
    groq_client = Groq(api_key=curator_api_key)
    langfuse = Langfuse()

    if args.refresh_voice:
        refresh_voice_pass(groq_client, langfuse)
        return

    collection = load_json_list(COLLECTION_PATH)
    epistemic_honesty = load_json_list(EPISTEMIC_HONESTY_PATH)
    exhibits = load_json_list(EXHIBITS_PATH)
    processed_ids = {r["id"] for r in exhibits} | {r["id"] for r in epistemic_honesty}

    session_id = f"museum-curation-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"

    for source in collection:
        prompt_id, wing = source["id"], source["wing"]

        if not args.force and prompt_id in processed_ids:
            print(f"skip {prompt_id} (already curated)")
            continue

        try:
            with propagate_attributes(
                session_id=session_id,
                tags=[wing, MODEL_ID, "curator"],
                trace_name=f"curator-{prompt_id}",
            ):
                with langfuse.start_as_current_observation(
                    name=prompt_id,
                    as_type="generation",
                    model=MODEL_ID,
                    input={"prompt": source["prompt"], "response": source["response"]},
                ) as generation:
                    verdict, usage = curate_exhibit(groq_client, source["prompt"], source["response"])
                    generation.update(output=verdict, usage_details=usage)
                    trace_id = generation.trace_id
        except Exception as exc:  # noqa: BLE001 - keep the run going for the other exhibits
            print(f"error curating {prompt_id}: {exc}")
            continue

        curated_at = datetime.now(timezone.utc).isoformat()

        if verdict.get("is_refusal"):
            record = {
                "id": prompt_id,
                "wing": wing,
                "prompt": source["prompt"],
                "response": source["response"],
                "model_id": source["model_id"],
                "provider": source["provider"],
                "generated_at": source["generated_at"],
                "langfuse_trace_id": source.get("langfuse_trace_id"),
                "is_refusal": True,
                "reason": verdict.get("refusal_reason") or "curator classified as refusal",
            }
            epistemic_honesty = [r for r in epistemic_honesty if r["id"] != prompt_id] + [record]
            write_json_list(EPISTEMIC_HONESTY_PATH, epistemic_honesty)
            if any(r["id"] == prompt_id for r in exhibits):
                exhibits = [r for r in exhibits if r["id"] != prompt_id]
                write_json_list(EXHIBITS_PATH, exhibits)
            print(f"done {prompt_id} (curator caught missed refusal)")
        else:
            record = {
                "id": prompt_id,
                "wing": wing,
                "prompt": source["prompt"],
                "response": source["response"],
                "model_id": source["model_id"],
                "provider": source["provider"],
                "generated_at": source["generated_at"],
                "langfuse_trace_id": source.get("langfuse_trace_id"),
                "confidence": verdict.get("confidence"),
                "classification": verdict.get("classification"),
                "title": verdict.get("title"),
                "medium": verdict.get("medium"),
                "description": verdict.get("description"),
                "curator_model_id": MODEL_ID,
                "curator_provider": PROVIDER,
                "curator_generated_at": curated_at,
                "curator_langfuse_trace_id": trace_id,
            }
            exhibits = [r for r in exhibits if r["id"] != prompt_id] + [record]
            write_json_list(EXHIBITS_PATH, exhibits)
            if any(r["id"] == prompt_id for r in epistemic_honesty):
                epistemic_honesty = [r for r in epistemic_honesty if r["id"] != prompt_id]
                write_json_list(EPISTEMIC_HONESTY_PATH, epistemic_honesty)
            print(f"done {prompt_id} (exhibit curated)")

        time.sleep(0.2)  # light pacing against Groq free-tier rate limits

    langfuse.flush()

    print("\n--- Milestone 03 decision gates ---")
    non_refused_total = len(exhibits)
    print(f"non-refused exhibit count: {non_refused_total} (threshold: >= 20)")
    if non_refused_total < 20:
        print("-- under threshold: add seed prompts to under-producing wings (Milestone 02's resolution path)")
    else:
        print("-- collection-size gate passed")
    print("-- plaque voice quality gate: read a sample of 5 plaques aloud (manual check, not automated)")
    print("-- pre-publish spot-check: run the content review before shipping exhibits.json")


if __name__ == "__main__":
    main()

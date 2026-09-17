"""Vote-tally script: Langfuse visitor_vote scores -> per-exhibit counts.

Offline/batch, run manually like main.py/curator.py -- never called live from the browser or Worker.
Uses `scores_v3.get_many_v3` with `fields="subject"` to get the trace ID each score is attached to
(trace_id is how a score is linked back to the exhibit that earned it).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from langfuse import Langfuse

load_dotenv()

SCRIPT_DIR = Path(__file__).parent
EXHIBITS_PATH = SCRIPT_DIR / "exhibits.json"
OUTPUT_PATH = SCRIPT_DIR / "vote_tallies.json"

VOTE_VALUES = ["convincing", "suspicious", "obviously_wrong"]


def main() -> None:
    exhibits = json.loads(EXHIBITS_PATH.read_text())
    trace_to_id = {r["langfuse_trace_id"]: r["id"] for r in exhibits}

    langfuse = Langfuse()
    tallies: dict[str, dict[str, int]] = {}
    orphaned = 0
    cursor = None

    while True:
        response = langfuse.api.scores_v3.get_many_v3(
            name="visitor_vote", fields="subject", cursor=cursor, limit=100
        )
        if not response.data:
            break

        for score in response.data:
            # Regenerating an exhibit's content gives it a fresh Langfuse trace, orphaning any
            # votes cast against the old one -- skip rather than misattribute.
            subject = score.subject
            trace_id = subject.id if subject is not None and subject.kind == "trace" else None
            exhibit_id = trace_to_id.get(trace_id)
            if exhibit_id is None:
                orphaned += 1
                continue
            if score.value not in VOTE_VALUES:
                continue

            entry = tallies.setdefault(exhibit_id, {v: 0 for v in VOTE_VALUES} | {"total": 0})
            entry[score.value] += 1
            entry["total"] += 1

        cursor = response.meta.cursor
        if cursor is None:
            break

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tallies": tallies,
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n")

    total_votes = sum(t["total"] for t in tallies.values())
    print(f"wrote tallies for {len(tallies)} exhibit(s), {total_votes} usable vote(s) total")
    if orphaned:
        print(f"skipped {orphaned} orphaned vote(s) with no matching current exhibit")


if __name__ == "__main__":
    main()

import { Link } from '../router/HashRouter'

export function About() {
  return (
    <div className="about-content">
      <Link to="/" className="back-link">
        ← Back to the gallery
      </Link>
      <p className="eyebrow-tag">About</p>
      <h1>How this museum was built</h1>

      <h2>The premise</h2>
      <p>
        Every exhibit starts as a trick or unanswerable question — a fictional person, an
        invented study, an event that never happened, a treaty between countries that were never
        at war. An "artist" model is asked the question and, per its persona prompt, commits to
        an answer rather than hedging or refusing. A second "curator" model then evaluates that
        answer and writes the museum plaque: title, medium, curatorial description, and a
        confidence score for how convincing the fabrication is.
      </p>

      <h2>Verbatim, always</h2>
      <p>
        Nothing an exhibit says has been rewritten, trimmed, or polished. What you read in the
        "verbatim response" section of each plaque is exactly what the model produced, unedited.
        Only the surrounding curation — the title, medium, and description — is written
        separately by the curator model.
      </p>

      <h2>Model pinning</h2>
      <p>
        Hallucination behavior is not stable across model versions, so every plaque credits the
        exact pinned model and generation date. The artist model is Groq's
        <code> llama-3.1-8b-instant</code>; the curator is the larger
        <code> llama-3.3-70b-versatile</code>, chosen for more reliable structured judgments.
        If either model is deprecated or its behavior shifts, the exhibits here should be read as
        a snapshot of that model at that time, not a permanent verdict on it.
      </p>

      <h2>When honesty broke through</h2>
      <p>
        Some questions didn't produce a hallucination at all — the model refused, hedged, or
        caught the question's false premise instead of inventing an answer. Those responses live
        in the <Link to="/annex">Epistemic Honesty Annex</Link> rather than the main collection,
        as a control group showing that confident fabrication is a choice the model makes on some
        prompts and not others, not the only thing it's capable of.
      </p>

      <h2>What this demonstrates</h2>
      <p>
        Underneath the joke, this project is a small, complete AI engineering loop built on a
        near-zero budget: generation (the artist), LLM-as-judge evaluation (the curator),
        observability (every generation traced, including token usage and latency), and human
        feedback — vote on whether an exhibit fooled you, on any plaque.
      </p>
    </div>
  )
}

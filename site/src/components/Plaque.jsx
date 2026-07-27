const dateFormatter = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
})

const numberFormatter = new Intl.NumberFormat()

function formatDate(iso) {
  return dateFormatter.format(new Date(iso))
}

function formatSeconds(seconds) {
  return `${seconds.toFixed(2)}s`
}

const CLASSIFICATION_LABELS = {
  fabricated_citation: 'Fabricated Citation',
  invented_entity: 'Invented Entity',
  false_specificity: 'False Specificity',
  arithmetic_error: 'Arithmetic Error',
}

function classificationLabel(classification) {
  return (
    CLASSIFICATION_LABELS[classification] ??
    classification.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  )
}

export function Plaque({ exhibit, showResponse = true }) {
  const {
    title,
    medium,
    description,
    model_id,
    generated_at,
    classification,
    confidence,
    prompt,
    response,
    artist_tokens,
    artist_latency_seconds,
    curator_tokens,
    curator_latency_seconds,
  } = exhibit

  return (
    <div className="gilt-frame">
      <div className="plaque">
        <div className="plaque-eyebrow">{classificationLabel(classification)}</div>
        <h3 className="plaque-title">{title}</h3>
        <div className="plaque-meta">
          {medium} — {model_id}, {formatDate(generated_at)}
        </div>
        <p className="plaque-description">{description}</p>

        <div className="plaque-prompt">
          <div className="plaque-eyebrow">The question posed</div>
          <blockquote>&ldquo;{prompt}&rdquo;</blockquote>
        </div>

        {showResponse && (
          <div className="plaque-response">
            <div className="plaque-eyebrow">Verbatim response</div>
            <blockquote>{response}</blockquote>
          </div>
        )}

        <div className="materials-line">
          <span>
            Curator confidence: <strong>{confidence}/100</strong>
          </span>
          <span>
            Forged in <strong>{formatSeconds(artist_latency_seconds)}</strong> (
            {numberFormatter.format(artist_tokens.total)} tokens)
          </span>
          {curator_tokens && (
            <span>
              Appraised in <strong>{formatSeconds(curator_latency_seconds)}</strong> (
              {numberFormatter.format(curator_tokens.total)} tokens)
            </span>
          )}
        </div>

        <div className="vote-placeholder">
          Visitor voting arrives in a future exhibition (Milestone 05) — check back to see if this one fools anyone.
        </div>
      </div>
    </div>
  )
}

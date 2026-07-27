import { Tooltip } from './Tooltip'
import { VoteWidget } from './VoteWidget'

const CONFIDENCE_EXPLANATION =
  "Measures how confidently the artist committed to this fabrication — not whether it's correct " +
  '(every exhibit here is already known to be wrong, since the question was unanswerable to begin with). ' +
  '100 means no hedging at all, stated as plain fact; a lower score means the model showed some ' +
  'uncertainty even while still fabricating.'

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
    id,
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
          <Tooltip text={CONFIDENCE_EXPLANATION}>
            Curator confidence: <strong>{confidence}/100</strong>
          </Tooltip>
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

        <VoteWidget exhibitId={id} />
      </div>
    </div>
  )
}

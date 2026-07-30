import { Link } from '../router/HashRouter'
import { findPromptGroup, wingLabel } from '../data'
import { Plaque, ResponseBlock } from '../components/Plaque'
import { NotFound } from './NotFound'

const numberFormatter = new Intl.NumberFormat()

function formatSeconds(seconds) {
  return `${seconds.toFixed(2)}s`
}

// M09: the non-exhibit outcomes (a model answered correctly, refused, or hasn't been generated
// yet) — per CLAUDE.md's verbatim-content invariant, still shows the actual response and reason
// exactly like Plaque/Annex do, not just a status badge.
export function OutcomeCard({ outcome }) {
  const { modelId, kind, record } = outcome

  if (kind === 'missing') {
    return (
      <div className="gilt-frame">
        <div className="plaque outcome-card-missing">
          <div className="plaque-eyebrow">No data yet</div>
          <div className="plaque-meta">{modelId}</div>
          <p>This model hasn't been run against this prompt yet.</p>
        </div>
      </div>
    )
  }

  const label = kind === 'accurate' ? 'Answered correctly' : 'Refused to fabricate'

  return (
    <div className="gilt-frame">
      <div className="plaque">
        <div className="plaque-eyebrow">{label}</div>
        <div className="plaque-meta">{modelId}</div>
        {record.reason && <p className="plaque-description">{record.reason}</p>}
        <ResponseBlock response={record.response} collapsible />
        {record.artist_tokens && (
          <div className="materials-line">
            <span>
              Forged in <strong>{formatSeconds(record.artist_latency_seconds)}</strong> (
              {numberFormatter.format(record.artist_tokens.total)} tokens)
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

// Shared by the Compare page and Home's "Comparison of the Day" — one grid, reused rather than
// duplicated (M09 acceptance criterion).
export function ComparisonGrid({ group }) {
  return (
    <div className="exhibit-grid">
      {group.outcomes.map((outcome) =>
        outcome.kind === 'exhibit' ? (
          <Plaque
            key={outcome.modelId}
            exhibit={outcome.record}
            showPrompt={false}
            collapsibleResponse
          />
        ) : (
          <OutcomeCard key={outcome.modelId} outcome={outcome} />
        ),
      )}
    </div>
  )
}

// Shared by the Compare page and Home's "Comparison of the Day" — same question-display markup,
// factored out rather than duplicated.
export function PromptBlock({ prompt }) {
  return (
    <div className="plaque-prompt plaque-prompt-standalone" style={{ margin: '0 0 2rem' }}>
      <div className="plaque-eyebrow">The question posed to every roster model</div>
      <blockquote>&ldquo;{prompt}&rdquo;</blockquote>
    </div>
  )
}

export function Compare({ slug, promptId }) {
  const group = findPromptGroup(promptId)
  if (!group || group.wing !== slug) return <NotFound />

  return (
    <div>
      <Link to={`/wings/${slug}`} className="back-link">
        ← Back to {wingLabel(slug)}
      </Link>
      <h1>Comparison</h1>
      <PromptBlock prompt={group.prompt} />

      <ComparisonGrid group={group} />
    </div>
  )
}

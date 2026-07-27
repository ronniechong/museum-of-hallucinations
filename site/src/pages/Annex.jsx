import { Link } from '../router/HashRouter'
import { annex } from '../data'

export function Annex() {
  return (
    <div>
      <Link to="/" className="back-link">
        ← Back to the gallery
      </Link>
      <p className="eyebrow-tag">Special Exhibition</p>
      <h1>The Epistemic Honesty Annex</h1>
      <p>
        Not every question fooled the artist. This wing collects the responses where the model
        refused to fabricate, hedged, or admitted it didn't know — the moments honesty broke
        through instead of a confident forgery. These aren't failures of the museum's premise;
        they're the control group that proves the exhibits next door are a real choice the model
        made, not the only thing it's capable of.
      </p>

      {annex.map((entry) => (
        <div key={entry.id} className="annex-entry">
          <div className="prompt">&ldquo;{entry.prompt}&rdquo;</div>
          <div className="response">{entry.response}</div>
          {entry.reason && <div className="reason">Why this counts: {entry.reason}</div>}
        </div>
      ))}
    </div>
  )
}

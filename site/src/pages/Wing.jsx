import { Link } from '../router/HashRouter'
import { wingLabel, promptGroups, wingSlugs } from '../data'
import { outcomeSummary } from '../lib/outcomes'
import { NotFound } from './NotFound'

export function Wing({ slug }) {
  if (!wingSlugs().includes(slug)) return <NotFound />
  const groups = promptGroups(slug)

  return (
    <div>
      <Link to="/" className="back-link">
        ← Back to the gallery
      </Link>
      <h1>{wingLabel(slug)}</h1>
      <p>{groups.length} prompts in this wing, each answered by every roster model.</p>

      <div className="wing-grid">
        {groups.map((group) => (
          <Link
            key={group.promptId}
            to={`/wings/${slug}/compare/${group.promptId}`}
            className="wing-card"
          >
            <h3>{group.prompt}</h3>
            <p>{outcomeSummary(group.outcomes)}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}

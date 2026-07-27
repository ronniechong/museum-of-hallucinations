import { Link } from '../router/HashRouter'
import { wingLabel, exhibitsByWing, wingSlugs } from '../data'
import { NotFound } from './NotFound'

export function Wing({ slug }) {
  if (!wingSlugs().includes(slug)) return <NotFound />
  const exhibits = exhibitsByWing(slug)

  return (
    <div>
      <Link to="/" className="back-link">
        ← Back to the gallery
      </Link>
      <p className="eyebrow-tag">Wing</p>
      <h1>{wingLabel(slug)}</h1>
      <p>{exhibits.length} exhibits in this wing.</p>

      <div className="wing-grid">
        {exhibits.map((exhibit) => (
          <Link key={exhibit.id} to={`/wings/${slug}/${exhibit.id}`} className="wing-card">
            <h3>{exhibit.title}</h3>
            <p>{exhibit.medium}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}

import { Link } from '../router/HashRouter'
import { findExhibit, wingLabel } from '../data'
import { Plaque } from '../components/Plaque'
import { NotFound } from './NotFound'

export function Exhibit({ id, slug }) {
  const exhibit = findExhibit(id)
  if (!exhibit) return <NotFound />

  return (
    <div>
      <Link to={`/wings/${slug}`} className="back-link">
        ← Back to {wingLabel(slug)}
      </Link>
      <div style={{ maxWidth: 560, margin: '0 auto' }}>
        <Plaque exhibit={exhibit} />
      </div>
    </div>
  )
}

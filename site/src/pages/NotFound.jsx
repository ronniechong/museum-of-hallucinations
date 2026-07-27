import { Link } from '../router/HashRouter'

export function NotFound() {
  return (
    <div className="not-found">
      <h1>Gallery Closed</h1>
      <p>There's no exhibit behind this door.</p>
      <Link to="/">← Back to the gallery</Link>
    </div>
  )
}

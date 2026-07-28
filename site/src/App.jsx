import { HashRouterProvider, useRoute, Link } from './router/HashRouter'
import { Routes } from './router/Routes'
import { Home } from './pages/Home'
import { Wing } from './pages/Wing'
import { Exhibit } from './pages/Exhibit'
import { Annex } from './pages/Annex'
import { About } from './pages/About'
import { NotFound } from './pages/NotFound'
import { Logo } from './components/Logo'
import { wingSlugs, wingLabel } from './data'

function WingsNavDropdown() {
  const { path } = useRoute()
  const isWingPath = path.startsWith('/wings/')
  return (
    <div className="nav-dropdown">
      <button type="button" className={`nav-dropdown-trigger ${isWingPath ? 'active' : ''}`}>
        Wings
      </button>
      <div className="nav-dropdown-menu">
        {wingSlugs().map((slug) => (
          <Link key={slug} to={`/wings/${slug}`}>
            {wingLabel(slug)}
          </Link>
        ))}
      </div>
    </div>
  )
}

function Header() {
  const { path } = useRoute()
  return (
    <header className="site-header">
      <div className="site-brand">
        <Link to="/" className="site-logo-link" aria-label="The Museum of Hallucinations — home">
          <Logo />
        </Link>
        <h1 className="site-title">
          <Link to="/" className="site-title-link">
            The Museum of Hallucinations
            <small>Confident wrong answers, formally curated</small>
          </Link>
        </h1>
      </div>
      <nav className="site-nav">
        <Link to="/" className={path === '/' ? 'active' : ''}>
          Gallery
        </Link>
        <WingsNavDropdown />
        <Link to="/annex" className={path === '/annex' ? 'active' : ''}>
          Annex
        </Link>
        <Link to="/about" className={path === '/about' ? 'active' : ''}>
          About
        </Link>
      </nav>
    </header>
  )
}

function AppRoutes() {
  return (
    <Routes
      routes={[
        { pattern: '/', render: () => <Home /> },
        { pattern: '/annex', render: () => <Annex /> },
        { pattern: '/about', render: () => <About /> },
        { pattern: '/wings/:slug', render: ({ slug }) => <Wing slug={slug} /> },
        {
          pattern: '/wings/:slug/:id',
          render: ({ slug, id }) => <Exhibit slug={slug} id={id} />,
        },
      ]}
      notFound={<NotFound />}
    />
  )
}

function App() {
  return (
    <HashRouterProvider>
      <Header />
      <main className="wall">
        <AppRoutes />
      </main>
      <footer className="site-footer">
        Every hallucination on display is real, verbatim, and pinned to the model that produced
        it.
      </footer>
    </HashRouterProvider>
  )
}

export default App

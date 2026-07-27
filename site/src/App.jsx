import { HashRouterProvider, useRoute, Link } from './router/HashRouter'
import { Routes } from './router/Routes'
import { Home } from './pages/Home'
import { Wing } from './pages/Wing'
import { Exhibit } from './pages/Exhibit'
import { Annex } from './pages/Annex'
import { About } from './pages/About'
import { NotFound } from './pages/NotFound'

function Header() {
  const { path } = useRoute()
  return (
    <header className="site-header">
      <h1 className="site-title">
        <Link to="/">
          The Museum of Hallucinations
          <small>Confident wrong answers, formally curated</small>
        </Link>
      </h1>
      <nav className="site-nav">
        <Link to="/" className={path === '/' ? 'active' : ''}>
          Gallery
        </Link>
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

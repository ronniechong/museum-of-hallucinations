import { createContext, useContext, useEffect, useState } from 'react'

const RouteContext = createContext({ path: '/', navigate: () => {} })

function currentPath() {
  const hash = window.location.hash.slice(1)
  return hash.startsWith('/') ? hash : '/'
}

export function HashRouterProvider({ children }) {
  const [path, setPath] = useState(currentPath())

  useEffect(() => {
    const onHashChange = () => setPath(currentPath())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const navigate = (to) => {
    window.location.hash = to
  }

  return (
    <RouteContext.Provider value={{ path, navigate }}>
      {children}
    </RouteContext.Provider>
  )
}

export function useRoute() {
  return useContext(RouteContext)
}

export function Link({ to, children, className }) {
  return (
    <a href={`#${to}`} className={className}>
      {children}
    </a>
  )
}

// Matches a flat pattern like "/wings/:slug" against the current path.
// No nesting needed — this site is five levels deep at most.
export function matchRoute(pattern, path) {
  const patternParts = pattern.split('/').filter(Boolean)
  const pathParts = path.split('/').filter(Boolean)
  if (patternParts.length !== pathParts.length) return null

  const params = {}
  for (let i = 0; i < patternParts.length; i++) {
    const part = patternParts[i]
    if (part.startsWith(':')) {
      params[part.slice(1)] = decodeURIComponent(pathParts[i])
    } else if (part !== pathParts[i]) {
      return null
    }
  }
  return params
}

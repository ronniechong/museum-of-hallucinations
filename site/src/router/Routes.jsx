import { useRoute, matchRoute } from './HashRouter'

// routes: array of { pattern, render(params) }, checked in order.
export function Routes({ routes, notFound }) {
  const { path } = useRoute()

  for (const route of routes) {
    const params = matchRoute(route.pattern, path)
    if (params) return route.render(params)
  }

  return notFound ?? null
}

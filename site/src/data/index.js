import exhibitsRaw from './exhibits.json'
import annexRaw from './epistemic_honesty.json'
import voteTalliesRaw from './vote_tallies.json'

export const exhibits = exhibitsRaw
export const annex = annexRaw
export const voteTallies = voteTalliesRaw

export function voteTallyFor(exhibitId) {
  return voteTallies[exhibitId] ?? null
}

export const WING_LABELS = {
  'invented-scholarship': 'Invented Scholarship',
  'fictional-persons': 'Fictional Persons',
  'impossible-how-tos': 'Impossible How-Tos',
  'product-annex': 'Product Annex',
  'arithmetic-vault': 'The Arithmetic Vault',
}

export function wingSlugs() {
  return Object.keys(WING_LABELS).filter((slug) =>
    exhibits.some((e) => e.wing === slug),
  )
}

export function wingLabel(slug) {
  return WING_LABELS[slug] ?? slug
}

export function exhibitsByWing(slug) {
  return exhibits.filter((e) => e.wing === slug)
}

export function findExhibit(id) {
  return exhibits.find((e) => e.id === id)
}

// Deterministic per-day pick, same exhibit for every visitor on a given
// local calendar date — no backend needed, per M04's scope decision.
export function exhibitOfTheDay(date = new Date()) {
  const dayKey = date.toISOString().slice(0, 10)
  let hash = 0
  for (let i = 0; i < dayKey.length; i++) {
    hash = (hash * 31 + dayKey.charCodeAt(i)) >>> 0
  }
  return exhibits[hash % exhibits.length]
}

export function honestyStats() {
  return {
    exhibitCount: exhibits.length,
    annexCount: annex.length,
  }
}

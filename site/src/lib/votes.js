// Not a secret — the Worker's URL is meant to be called from client-side JS.
const VOTE_ENDPOINT = 'https://museum-of-hallucinations-votes.museumvotes.workers.dev/vote'

const STORAGE_PREFIX = 'museum-vote:'

// localStorage is UX-only ("you already voted" state) — it carries no security weight.
// The Worker enforces the real dedupe/rate-limit server-side, keyed on IP.
export function getStoredVote(exhibitId) {
  try {
    return localStorage.getItem(STORAGE_PREFIX + exhibitId)
  } catch {
    return null
  }
}

function storeVote(exhibitId, vote) {
  try {
    localStorage.setItem(STORAGE_PREFIX + exhibitId, vote)
  } catch {
    // Storage unavailable (private browsing, etc.) — vote still reaches the Worker,
    // the visitor just won't see "already voted" state on their next visit.
  }
}

export async function submitVote(exhibitId, vote) {
  let response
  try {
    response = await fetch(VOTE_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ exhibitId, vote }),
    })
  } catch {
    return { status: 'network_error' }
  }

  if (response.status === 429) {
    return { status: 'rate_limited' }
  }

  if (!response.ok) {
    return { status: 'error' }
  }

  storeVote(exhibitId, vote)
  return { status: 'ok' }
}

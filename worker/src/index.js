import traceMap from './trace-map.json'

// Two different origins by design: the site (GitHub Pages, ronniechong.com) and this
// Worker (Cloudflare's own *.workers.dev) are never on the same domain, so the browser
// enforces CORS between them. localhost is kept permanently, not stripped before prod —
// it only ever matters from the developer's own machine.
const ALLOWED_ORIGINS = new Set(['https://ronniechong.com', 'http://localhost:5173'])

const VOTE_VALUES = new Set(['convincing', 'suspicious', 'obviously_wrong'])
const RATE_LIMIT_PER_DAY = 40
const DEDUPE_TTL_SECONDS = 60 * 60 * 24 * 90
const RATE_LIMIT_TTL_SECONDS = 60 * 60 * 24 * 2
const PENDING_SCORE_PREFIX = 'pending-score:'

function corsHeaders(origin) {
  if (!ALLOWED_ORIGINS.has(origin)) return null
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  }
}

function jsonResponse(body, status, extraHeaders) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...extraHeaders },
  })
}

function todayKey(date = new Date()) {
  return date.toISOString().slice(0, 10)
}

async function sendScoreToLangfuse(env, traceId, vote) {
  const auth = btoa(`${env.LANGFUSE_PUBLIC_KEY}:${env.LANGFUSE_SECRET_KEY}`)
  try {
    const response = await fetch(`${env.LANGFUSE_HOST}/api/public/scores`, {
      method: 'POST',
      headers: { Authorization: `Basic ${auth}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        traceId,
        name: 'visitor_vote',
        value: vote,
        dataType: 'CATEGORICAL',
      }),
    })
    return response.ok
  } catch {
    return false
  }
}

async function queueForRetry(env, payload) {
  const key = `${PENDING_SCORE_PREFIX}${Date.now()}-${crypto.randomUUID()}`
  await env.VOTES_KV.put(key, JSON.stringify(payload))
}

// Real (server-side) dedupe + rate limit, both keyed on requester IP, not the client's
// localStorage token — a flood script never runs the site's JS, so only a signal the
// client can't spoof for free (IP) can gate anything here. localStorage is UX-only.
async function handleVote(request, env, origin) {
  let body
  try {
    body = await request.json()
  } catch {
    return jsonResponse({ error: 'invalid_json' }, 400, corsHeaders(origin))
  }

  const { exhibitId, vote } = body ?? {}

  if (typeof exhibitId !== 'string' || !VOTE_VALUES.has(vote)) {
    return jsonResponse({ error: 'invalid_payload' }, 400, corsHeaders(origin))
  }

  const traceId = traceMap[exhibitId]
  if (!traceId) {
    return jsonResponse({ error: 'unknown_exhibit' }, 400, corsHeaders(origin))
  }

  const ip = request.headers.get('CF-Connecting-IP') ?? 'unknown'
  const rateLimitKey = `ratelimit:${ip}:${todayKey()}`
  const dedupeKey = `voted:${ip}:${exhibitId}`

  const [rateCountRaw, alreadyVoted] = await Promise.all([
    env.VOTES_KV.get(rateLimitKey),
    env.VOTES_KV.get(dedupeKey),
  ])

  if (alreadyVoted) {
    return jsonResponse({ ok: true, alreadyVoted: true }, 200, corsHeaders(origin))
  }

  const rateCount = rateCountRaw ? parseInt(rateCountRaw, 10) : 0
  if (rateCount >= RATE_LIMIT_PER_DAY) {
    return jsonResponse({ error: 'rate_limited' }, 429, corsHeaders(origin))
  }

  await Promise.all([
    env.VOTES_KV.put(dedupeKey, '1', { expirationTtl: DEDUPE_TTL_SECONDS }),
    env.VOTES_KV.put(rateLimitKey, String(rateCount + 1), { expirationTtl: RATE_LIMIT_TTL_SECONDS }),
  ])

  const delivered = await sendScoreToLangfuse(env, traceId, vote)
  if (!delivered) {
    await queueForRetry(env, { traceId, vote })
    return jsonResponse({ ok: true, queued: true }, 202, corsHeaders(origin))
  }

  return jsonResponse({ ok: true }, 201, corsHeaders(origin))
}

async function retryPendingScores(env) {
  const list = await env.VOTES_KV.list({ prefix: PENDING_SCORE_PREFIX })
  for (const key of list.keys) {
    const raw = await env.VOTES_KV.get(key.name)
    if (!raw) continue
    const { traceId, vote } = JSON.parse(raw)
    if (await sendScoreToLangfuse(env, traceId, vote)) {
      await env.VOTES_KV.delete(key.name)
    }
  }
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin')

    if (request.method === 'OPTIONS') {
      const headers = corsHeaders(origin)
      return headers ? new Response(null, { status: 204, headers }) : new Response(null, { status: 403 })
    }

    if (!corsHeaders(origin)) {
      return jsonResponse({ error: 'origin_not_allowed' }, 403)
    }

    const url = new URL(request.url)
    if (url.pathname !== '/vote' || request.method !== 'POST') {
      return jsonResponse({ error: 'not_found' }, 404, corsHeaders(origin))
    }

    return handleVote(request, env, origin)
  },

  async scheduled(_event, env) {
    await retryPendingScores(env)
  },
}

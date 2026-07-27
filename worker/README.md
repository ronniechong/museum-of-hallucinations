# Vote endpoint (Cloudflare Worker + KV)

Receives "did this fool you?" votes from the gallery site and forwards them as scores on the
exhibit's Langfuse trace. Runs entirely on Cloudflare's own `*.workers.dev` domain — no DNS or
hosting changes needed on the site's domain.

## One-time setup
```
npm install
npx wrangler login
npx wrangler kv namespace create VOTES_KV   # paste the returned id into wrangler.toml
npx wrangler secret put LANGFUSE_PUBLIC_KEY
npx wrangler secret put LANGFUSE_SECRET_KEY
npx wrangler secret put LANGFUSE_HOST       # https://cloud.langfuse.com
```

For local testing, copy `.dev.vars.example` to `.dev.vars` and fill in the same three values.

## Develop / deploy
```
npm run dev      # local dev server, regenerates src/trace-map.json first
npm run deploy   # regenerates src/trace-map.json, then wrangler deploy
```

`src/trace-map.json` is generated from `../scripts/exhibits.json` on every dev/deploy (not
committed) — it maps each exhibit ID to its Langfuse trace ID so the Worker never has to trust
a client-supplied trace ID, only a vote value and an exhibit ID it validates itself.

## Endpoint
`POST /vote` — body `{ "exhibitId": string, "vote": "convincing" | "suspicious" | "obviously_wrong" }`

Rate limiting and dedupe are both enforced server-side, keyed on requester IP via KV — not the
client's localStorage token, which is UX-only (remembers "you already voted" locally).

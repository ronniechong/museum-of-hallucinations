import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

// Trims scripts/exhibits.json down to { [exhibitId]: langfuse_trace_id } so the Worker
// never trusts a client-supplied trace ID — it looks the trace up server-side from an
// exhibit ID it validates against this map. scripts/exhibits.json stays the single
// source of truth (same sync-not-duplicate pattern the site build already uses).

const __dirname = dirname(fileURLToPath(import.meta.url))
const exhibitsPath = join(__dirname, '..', '..', 'scripts', 'exhibits.json')
const outPath = join(__dirname, '..', 'src', 'trace-map.json')

const exhibits = JSON.parse(readFileSync(exhibitsPath, 'utf-8'))
const traceMap = Object.fromEntries(exhibits.map((e) => [e.id, e.langfuse_trace_id]))

mkdirSync(dirname(outPath), { recursive: true })
writeFileSync(outPath, JSON.stringify(traceMap, null, 2))

console.log(`Wrote ${Object.keys(traceMap).length} exhibit trace IDs to ${outPath}`)

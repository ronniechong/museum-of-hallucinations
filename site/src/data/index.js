import seedPromptsRaw from './seed_prompts.json'
import exhibitsRaw from './exhibits.json'
import annexRaw from './epistemic_honesty.json'
import accurateAnswersRaw from './accurate_answers.json'
import voteTalliesRaw from './vote_tallies.json'
import rosterRaw from './roster.json'

export const seedPrompts = seedPromptsRaw
export const exhibits = exhibitsRaw
export const annex = annexRaw
export const accurateAnswers = accurateAnswersRaw
export const voteTallies = voteTalliesRaw.tallies
export const voteTalliesGeneratedAt = voteTalliesRaw.generated_at
// M09: single source of truth for model display order, exported by scripts/main.py's ROSTER —
// never maintained as a separate hand-written list here (that was considered and rejected at
// M09's spec-review as an avoidable duplication/drift risk).
export const ROSTER_ORDER = rosterRaw

export function voteTallyFor(exhibitId) {
  return voteTallies[exhibitId] ?? null
}

export const WING_LABELS = {
  'invented-scholarship': 'Invented Scholarship',
  'fictional-persons': 'Fictional Persons',
  'impossible-how-tos': 'Impossible How-Tos',
  'product-annex': 'Product Annex',
  'arithmetic-vault': 'The Arithmetic Vault',
  'ancient-tech-misconceptions': 'Ancient Tech Misconceptions',
}

export function wingSlugs() {
  return Object.keys(WING_LABELS).filter((slug) =>
    exhibits.some((e) => e.wing === slug),
  )
}

export function wingLabel(slug) {
  return WING_LABELS[slug] ?? slug
}

export function findExhibit(id) {
  return exhibits.find((e) => e.id === id)
}

// M09: joins exhibits/annex/accurate-answers by prompt_id, one record per seed prompt, each
// roster model's outcome tagged by kind. Ordering comes from seed_prompts.json's own array order
// (never from first-appearance in an output file) — confirmed at M09's spec-review that output
// files no longer match seed order at all once any --force rerun or partial backfill has run.
function outcomeKind(record) {
  if (record.is_accurate) return 'accurate'
  if (record.is_refusal) return 'refusal'
  return 'exhibit'
}

export function promptGroups(wing = null) {
  const byKey = new Map()
  for (const record of [...exhibits, ...annex, ...accurateAnswers]) {
    byKey.set(`${record.prompt_id}--${record.model_id}`, record)
  }

  const prompts = wing ? seedPrompts.filter((p) => p.wing === wing) : seedPrompts

  return prompts.map((seed) => ({
    promptId: seed.id,
    wing: seed.wing,
    prompt: seed.prompt,
    outcomes: ROSTER_ORDER.map((modelId) => {
      const record = byKey.get(`${seed.id}--${modelId}`)
      return record
        ? { modelId, kind: outcomeKind(record), record }
        : { modelId, kind: 'missing', record: null }
    }),
  }))
}

export function findPromptGroup(promptId) {
  return promptGroups().find((g) => g.promptId === promptId) ?? null
}

// Deterministic per-day pick, same prompt group for every visitor on a given local calendar date —
// no backend needed, per M04's scope decision (upgraded from single-exhibit to full comparison
// group at M09).
export function comparisonOfTheDay(date = new Date()) {
  const dayKey = date.toISOString().slice(0, 10)
  let hash = 0
  for (let i = 0; i < dayKey.length; i++) {
    hash = (hash * 31 + dayKey.charCodeAt(i)) >>> 0
  }
  const groups = promptGroups()
  return groups[hash % groups.length]
}

export function honestyStats() {
  return {
    exhibitCount: exhibits.length,
    annexCount: annex.length,
  }
}

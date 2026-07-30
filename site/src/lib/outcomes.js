// Shared between Wing.jsx, Home.jsx, and Compare.jsx so the "N exhibits, M correct" summary
// wording stays consistent everywhere a prompt group is rendered as a single line.

const LABELS = {
  exhibit: (n) => (n === 1 ? '1 exhibit' : `${n} exhibits`),
  accurate: (n) => (n === 1 ? '1 correct answer' : `${n} correct answers`),
  refusal: (n) => (n === 1 ? '1 refusal' : `${n} refusals`),
  missing: (n) => (n === 1 ? '1 pending' : `${n} pending`),
}

const ORDER = ['exhibit', 'accurate', 'refusal', 'missing']

export function outcomeSummary(outcomes) {
  const counts = { exhibit: 0, accurate: 0, refusal: 0, missing: 0 }
  for (const outcome of outcomes) counts[outcome.kind] += 1

  return ORDER.filter((kind) => counts[kind] > 0)
    .map((kind) => LABELS[kind](counts[kind]))
    .join(', ')
}

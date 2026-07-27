import { useState } from 'react'
import { getStoredVote, submitVote } from '../lib/votes'

const OPTIONS = [
  { value: 'convincing', label: 'Convincing' },
  { value: 'suspicious', label: 'Suspicious' },
  { value: 'obviously_wrong', label: 'Obviously wrong' },
]

export function VoteWidget({ exhibitId }) {
  const [vote, setVote] = useState(() => getStoredVote(exhibitId))
  const [status, setStatus] = useState('idle') // idle | submitting | rate_limited | error

  if (vote) {
    return (
      <div className="vote-widget vote-widget-done">
        Would this have worked on you? You said:{' '}
        <strong>{OPTIONS.find((o) => o.value === vote)?.label ?? vote}</strong>
      </div>
    )
  }

  async function handleVote(value) {
    setStatus('submitting')
    const result = await submitVote(exhibitId, value)
    if (result.status === 'ok') {
      setVote(value)
      setStatus('idle')
    } else if (result.status === 'rate_limited') {
      setStatus('rate_limited')
    } else {
      setStatus('error')
    }
  }

  return (
    <div className="vote-widget">
      <div className="vote-widget-prompt">
        Would this have worked on you, if you didn&rsquo;t already know it was fabricated?
      </div>
      <div className="vote-widget-buttons">
        {OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            disabled={status === 'submitting'}
            onClick={() => handleVote(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
      {status === 'rate_limited' && (
        <div className="vote-widget-message">Vote limit reached for today — try again tomorrow.</div>
      )}
      {status === 'error' && (
        <div className="vote-widget-message">Couldn&rsquo;t record your vote — please try again.</div>
      )}
    </div>
  )
}

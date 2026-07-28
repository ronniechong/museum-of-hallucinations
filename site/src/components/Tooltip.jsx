export function Tooltip({ text }) {
  return (
    <span className="info-tooltip" tabIndex={0}>
      <span className="info-tooltip-icon" aria-hidden="true">
        !
      </span>
      <span className="tooltip-bubble" role="tooltip">
        {text}
      </span>
    </span>
  )
}

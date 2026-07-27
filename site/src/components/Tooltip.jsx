export function Tooltip({ children, text }) {
  return (
    <span className="tooltip-term" tabIndex={0}>
      {children}
      <span className="tooltip-bubble" role="tooltip">
        {text}
      </span>
    </span>
  )
}

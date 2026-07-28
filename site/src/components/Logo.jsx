export function Logo() {
  return (
    <svg
      className="site-logo"
      viewBox="0 0 40 40"
      width="34"
      height="34"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="logoGilt" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#e6c878" />
          <stop offset="30%" stopColor="#b8923f" />
          <stop offset="60%" stopColor="#7a5f28" />
          <stop offset="100%" stopColor="#e6c878" />
        </linearGradient>
      </defs>
      <rect
        x="3"
        y="3"
        width="34"
        height="34"
        rx="1.5"
        fill="none"
        stroke="url(#logoGilt)"
        strokeWidth="4"
      />
      <rect
        x="9.5"
        y="9.5"
        width="21"
        height="21"
        rx="0.5"
        fill="none"
        stroke="url(#logoGilt)"
        strokeWidth="1.25"
      />
      <circle cx="3" cy="3" r="1.8" fill="#e6c878" />
      <circle cx="37" cy="3" r="1.8" fill="#e6c878" />
      <circle cx="3" cy="37" r="1.8" fill="#e6c878" />
      <circle cx="37" cy="37" r="1.8" fill="#e6c878" />
    </svg>
  )
}

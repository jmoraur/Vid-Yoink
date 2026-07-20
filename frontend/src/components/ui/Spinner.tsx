export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <span className="spinner-wrap">
      <svg
        className="spinner"
        viewBox="0 0 24 24"
        width={16}
        height={16}
        fill="none"
        stroke="currentColor"
        strokeWidth={2.5}
        strokeLinecap="round"
        aria-hidden="true"
      >
        <path d="M21 12a9 9 0 1 1-6.2-8.56" />
      </svg>
      {label}
    </span>
  )
}

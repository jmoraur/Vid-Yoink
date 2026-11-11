import { useState } from 'react'

/** A Delete button that asks once, in place: "Delete?  No  Yes". No dialog. */
export function ConfirmDelete({ what, onConfirm }: { what: string; onConfirm: () => void }) {
  const [asking, setAsking] = useState(false)
  if (!asking) {
    return (
      <button className="danger-ghost" aria-label={`Delete ${what}`} onClick={() => setAsking(true)}>
        Delete
      </button>
    )
  }
  return (
    <span className="confirm" role="group" aria-label={`Delete ${what}?`}>
      Delete?
      {/* focus lands on the safe answer */}
      <button className="small" autoFocus onClick={() => setAsking(false)}>
        No
      </button>
      <button className="danger-ghost" onClick={onConfirm}>
        Yes
      </button>
    </span>
  )
}

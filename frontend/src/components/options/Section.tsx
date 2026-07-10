import type { ReactNode } from 'react'

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <details className="section">
      <summary>{title}</summary>
      <div className="section-body">{children}</div>
    </details>
  )
}

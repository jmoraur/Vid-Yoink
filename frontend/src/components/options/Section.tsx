import type { ReactNode } from 'react'
import { Icon } from '../ui/Icon'

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <details className="section">
      <summary>
        <Icon name="chevron" size={14} className="chevron" /> {title}
      </summary>
      <div className="section-body">{children}</div>
    </details>
  )
}

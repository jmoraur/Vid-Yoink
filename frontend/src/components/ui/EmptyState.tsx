import type { ReactNode } from 'react'
import { Icon, type IconName } from './Icon'

export function EmptyState({
  icon,
  title,
  hint,
}: {
  icon: IconName
  title: string
  hint?: ReactNode
}) {
  return (
    <div className="empty-state">
      <Icon name={icon} size={28} />
      <p className="title">{title}</p>
      {hint && <p className="hint">{hint}</p>}
    </div>
  )
}

import { Icon } from './Icon'

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="error-state" role="alert">
      <Icon name="alert" size={28} />
      <p className="title">Couldn't load this list</p>
      <p className="hint">{message}</p>
      <button className="ghost" onClick={onRetry}>
        <Icon name="retry" size={14} /> Retry
      </button>
    </div>
  )
}

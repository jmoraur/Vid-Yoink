export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="skeleton-list">
      {Array.from({ length: lines }, (_, i) => (
        <div className="skeleton" key={i} />
      ))}
      <span className="visually-hidden">Loading</span>
    </div>
  )
}

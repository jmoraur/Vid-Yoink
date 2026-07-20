import type { ProbeResult } from '../api/types'
import { PlaylistEntryPicker } from './PlaylistEntryPicker'

function formatDuration(s: number | null): string {
  if (s == null) return ''
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = Math.round(s % 60)
  return h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
    : `${m}:${String(sec).padStart(2, '0')}`
}

interface Props {
  probe: ProbeResult
  playlistItems: string | null
  onPlaylistItems: (items: string | null) => void
}

export function ProbeCard({ probe, playlistItems, onPlaylistItems }: Props) {
  return (
    <div className="probe-card">
      <div className="probe-head">
        {probe.thumbnail && (
          <img
            src={probe.thumbnail}
            alt={probe.title ? `Thumbnail for ${probe.title}` : 'Video thumbnail'}
            loading="lazy"
          />
        )}
        <div>
          <p className="probe-title">{probe.title ?? '(untitled)'}</p>
          <p className="muted">
            {probe.uploader}
            {probe.kind === 'video' && probe.duration != null && (
              <> · {formatDuration(probe.duration)}</>
            )}
            {probe.kind === 'playlist' && <> · playlist, {probe.count} items</>}
          </p>
        </div>
      </div>
      {probe.kind === 'playlist' && (
        <PlaylistEntryPicker
          entries={probe.entries}
          totalCount={probe.count ?? probe.entries.length}
          value={playlistItems}
          onChange={onPlaylistItems}
        />
      )}
    </div>
  )
}

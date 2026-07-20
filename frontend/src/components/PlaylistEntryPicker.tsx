import { useState } from 'react'
import type { ProbeEntry } from '../api/types'

// 1-based indices -> yt-dlp playlist_items syntax, e.g. [1,2,3,7] -> "1-3,7"
export function compressIndices(indices: number[]): string {
  const sorted = [...indices].sort((a, b) => a - b)
  const parts: string[] = []
  let start = sorted[0]
  let prev = sorted[0]
  for (const n of sorted.slice(1)) {
    if (n === prev + 1) {
      prev = n
      continue
    }
    parts.push(start === prev ? `${start}` : `${start}-${prev}`)
    start = prev = n
  }
  parts.push(start === prev ? `${start}` : `${start}-${prev}`)
  return parts.join(',')
}

interface Props {
  entries: ProbeEntry[]
  totalCount: number
  value: string | null // playlist_items string; null = all
  onChange: (items: string | null) => void
}

export function PlaylistEntryPicker({ entries, totalCount, value, onChange }: Props) {
  const [picking, setPicking] = useState(value != null)
  const [selected, setSelected] = useState<Set<number>>(new Set())

  const toggle = (index: number) => {
    const next = new Set(selected)
    if (next.has(index)) next.delete(index)
    else next.add(index)
    setSelected(next)
    onChange(next.size > 0 ? compressIndices([...next]) : null)
  }

  const startPicking = () => {
    // sensible default: everything not already downloaded
    const initial = new Set(
      entries.map((e, i) => (e.already_downloaded ? -1 : i + 1)).filter((i) => i > 0),
    )
    setSelected(initial)
    setPicking(true)
    onChange(initial.size > 0 ? compressIndices([...initial]) : null)
  }

  const stopPicking = () => {
    setPicking(false)
    onChange(null)
  }

  return (
    <div className="entry-picker">
      <div className="picker-head">
        <label>
          <input
            type="checkbox"
            checked={!picking}
            onChange={(e) => (e.target.checked ? stopPicking() : startPicking())}
          />
          All {totalCount} items
        </label>
        {picking && <span className="muted">{selected.size} selected</span>}
      </div>
      {picking && (
        <>
          {totalCount > entries.length && (
            <p className="hint">
              Showing the first {entries.length} of {totalCount} items — untick "All items"
              only if what you need is listed here.
            </p>
          )}
          <ul className="entries">
            {entries.map((entry, i) => (
              <li key={entry.id ?? i}>
                <label>
                  <input
                    type="checkbox"
                    checked={selected.has(i + 1)}
                    onChange={() => toggle(i + 1)}
                  />
                  <span className="entry-index">{i + 1}.</span>
                  <span className="entry-title">{entry.title ?? entry.id}</span>
                  {entry.already_downloaded && <span className="chip chip-ok">downloaded</span>}
                </label>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

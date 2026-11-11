// Turning machine values into words. No dependencies: Intl does the hard part.

const relative = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 31_536_000],
  ['month', 2_592_000],
  ['day', 86_400],
  ['hour', 3_600],
  ['minute', 60],
]

/** "2 hours ago", "yesterday", "in 10 minutes". Empty for a missing time. */
export function timeAgo(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return ''
  const seconds = (new Date(iso).getTime() - now) / 1000 // negative = in the past
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) return relative.format(Math.round(seconds / size), unit)
  }
  return seconds > 0 ? 'in a moment' : 'just now'
}

/** The exact local date and time, for tooltips. */
export function fullDate(iso: string | null | undefined): string | undefined {
  return iso ? new Date(iso).toLocaleString() : undefined
}

/** "142 MB", "1.4 GB". */
export function formatBytes(n: number | null | undefined): string {
  if (n == null) return ''
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024
    i++
  }
  return `${n < 10 && i > 0 ? n.toFixed(1) : Math.round(n)} ${units[i]}`
}

/** "45 s", "12 min", "1 h 5 min". */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return ''
  if (seconds < 60) return `${Math.round(seconds)} s`
  const minutes = Math.round(seconds / 60)
  return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)} h ${minutes % 60} min`
}

/** "every 30 minutes", "every 2 hours", "every day". */
export function formatInterval(minutes: number): string {
  const [n, unit] =
    minutes % 1440 === 0 ? [minutes / 1440, 'day'] : minutes % 60 === 0 ? [minutes / 60, 'hour'] : [minutes, 'minute']
  return n === 1 ? `every ${unit}` : `every ${n} ${unit}s`
}

/** "youtube.com" from any link; the text itself if it is not a link. */
export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

/** For a download without a title: "youtube.com · watch?v=abc" instead of the full link. */
export function shortLink(url: string): string {
  try {
    const { pathname, search } = new URL(url)
    const last = decodeURIComponent(pathname.split('/').filter(Boolean).pop() ?? '') + search
    return last ? `${hostOf(url)} · ${last}` : hostOf(url)
  } catch {
    return url
  }
}

/** The links in a pasted block of text: one per line, blanks and repeats dropped. */
export function splitLinks(text: string): string[] {
  return [...new Set(text.split('\n').map((line) => line.trim()).filter(Boolean))]
}

// Run with: npm run check   (plain Node, no test framework)
import { explain } from './errors.ts'
import { formatBytes, formatDuration, formatInterval, hostOf, shortLink, timeAgo } from './format.ts'

function same(actual: unknown, expected: unknown) {
  if (actual !== expected) throw new Error(`expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`)
}
const starts = (text: string, start: string) => same(text.slice(0, start.length), start)

// real yt-dlp messages
starts(explain("[youtube] abc: Private video. Sign in if you've been granted access to this video"), 'This video is private')
starts(explain('[youtube] abc: Sign in to confirm your age. This video may be inappropriate for some users.'), 'The site wants you to be signed in')
starts(explain('[youtube] abc: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies'), 'The site wants you to be signed in')
starts(explain('[youtube] abc: Video unavailable. This video is no longer available because the account has been terminated'), 'This video is no longer available')
starts(explain('[youtube] abc: This video is unavailable'), 'This video is no longer available')
starts(explain("[youtube] abc: Join this channel to get access to members-only content like this video"), 'This video is for channel members')
starts(explain('[generic] Unable to download webpage: <urlopen error [Errno 111] Connection refused> (caused by TransportError)'), 'Could not reach the site')
starts(explain('Unsupported URL: https://example.com/'), 'This site or link is not supported')
starts(explain('unable to download video data: HTTP Error 403: Forbidden'), 'The site refused the download')
starts(explain('Postprocessing: ffprobe and ffmpeg not found. Please install or provide the path'), 'The file was downloaded but could not be converted')
starts(explain('Vault is locked — unlock it in Settings and retry'), 'The vault is locked')
// unknown text: shown as written, minus the machine prefix
same(explain('[vimeo] 123: Something brand new (caused by OddError)'), 'Something brand new')
same(explain(''), 'Something went wrong.')

const now = Date.parse('2026-11-11T12:00:00Z')
same(timeAgo('2026-11-11T11:59:40Z', now), 'just now')
same(timeAgo('2026-11-11T11:50:00Z', now), '10 minutes ago')
same(timeAgo('2026-11-11T10:00:00Z', now), '2 hours ago')
same(timeAgo('2026-11-10T11:00:00Z', now), 'yesterday')
same(timeAgo('2026-11-11T14:00:00Z', now), 'in 2 hours')
same(timeAgo(null, now), '')
same(formatBytes(148_900_000), '142 MB')
same(formatBytes(1_500_000_000), '1.4 GB')
same(formatBytes(900), '900 B')
same(formatDuration(45), '45 s')
same(formatDuration(2520), '42 min')
same(formatDuration(3900), '1 h 5 min')
same(formatInterval(30), 'every 30 minutes')
same(formatInterval(120), 'every 2 hours')
same(formatInterval(1440), 'every day')
same(hostOf('https://www.youtube.com/watch?v=abc'), 'youtube.com')
same(shortLink('https://www.youtube.com/watch?v=abc'), 'youtube.com · watch?v=abc')
same(shortLink('https://vimeo.com/76979871'), 'vimeo.com · 76979871')
same(shortLink('https://example.com/'), 'example.com')
same(shortLink('not a link'), 'not a link')
console.log('wording checks passed')

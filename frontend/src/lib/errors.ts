// yt-dlp's error text -> a plain sentence with a next step. First match wins, so the
// specific causes come before the general ones. Anything unknown is shown as yt-dlp
// wrote it, minus the "[site] id:" prefix; the full text is always under "Details".

const RULES: [RegExp, string][] = [
  [/vault is locked/i, 'The vault is locked. Unlock it under Settings, then try again.'],
  [
    /no stored (credential|cookies) named/i,
    'This download uses a login that is no longer in the vault. Add it again under Settings → Vault.',
  ],
  [/private video|video is private/i, 'This video is private. Add a login under Settings → Vault.'],
  [
    /members[- ]only|available to this channel's members|join this channel/i,
    'This video is for channel members only. Add cookies from a member account under Settings → Vault.',
  ],
  [
    /confirm your age|age[- ]restricted|sign in to confirm|not a bot|login required|log in to|cookies/i,
    'The site wants you to be signed in for this one. Add cookies under Settings → Vault.',
  ],
  [
    /not available in your country|geo[- ]?restricted|blocked it in your country/i,
    'This video is blocked in your country. A proxy (options → Network) can help.',
  ],
  [
    /live event will begin|premieres in|has not started|is offline/i,
    'This has not started yet. Try again once it is live.',
  ],
  [
    /video (is )?unavailable|has been removed|no longer available|does not exist|HTTP Error 404|account .* terminated/i,
    'This video is no longer available.',
  ],
  [/unsupported url/i, 'This site or link is not supported.'],
  [
    /requested format is not available/i,
    'That quality or format does not exist for this video. Pick another one and try again.',
  ],
  [
    /HTTP Error 429|too many requests/i,
    'The site is limiting how much you can download right now. Wait a while and try again.',
  ],
  [
    /HTTP Error 403/i,
    'The site refused the download. Updating yt-dlp or adding cookies often fixes this.',
  ],
  [
    /name resolution|name or service not known|getaddrinfo|connection refused|network is unreachable|timed out|connection reset|unable to download webpage/i,
    'Could not reach the site. Check your connection and try again.',
  ],
  [
    /ffmpeg|ffprobe/i,
    'The file was downloaded but could not be converted. Check that ffmpeg is installed (Settings shows its status).',
  ],
  [/no space left on device/i, 'The disk is full.'],
  [/permission denied/i, 'The download folder is not writable. Choose another folder in the options.'],
  [/interrupted by app shutdown/i, 'The app was closed while this was downloading.'],
]

/** One plain sentence for one line of error text. */
export function explain(raw: string): string {
  for (const [pattern, sentence] of RULES) if (pattern.test(raw)) return sentence
  return (
    raw
      .replace(/^ERROR:\s*/, '')
      .replace(/^\[[^\]]+\]\s*(\S+:\s+)?/, '') // "[youtube] abc123: "
      .replace(/\s*\(caused by .*\)\s*$/, '')
      .trim() || 'Something went wrong.'
  )
}

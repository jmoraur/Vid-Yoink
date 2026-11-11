import type { DownloadOptions } from '../../api/types'

/** One plain line for a set of options: "Video, up to 720p · saved to ~/Videos". */
export function summarize(o: DownloadOptions): string {
  const parts = [
    o.mode === 'audio'
      ? `Audio${o.audio_format === 'best' ? '' : ` as ${o.audio_format}`}`
      : `Video, ${o.max_height ? `up to ${o.max_height}p` : 'best quality'}` +
        (o.container === 'auto' ? '' : ` as ${o.container}`),
  ]
  parts.push(o.output_dir ? `saved to ${o.output_dir}` : 'saved to the default folder')
  if (o.write_subtitles || o.write_auto_subs) parts.push('with subtitles')
  if (o.sponsorblock_remove.length) parts.push('sponsor segments removed')
  if (o.credential_label || o.cookies_label || o.cookies_from_browser) parts.push('signed in')
  if (o.force_download) parts.push('even if downloaded before')
  if (o.extra_args) parts.push(`extra: ${o.extra_args}`)
  return parts.join(' · ')
}

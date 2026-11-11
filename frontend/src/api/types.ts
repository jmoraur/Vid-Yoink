// TypeScript mirror of yoink/models.py — keep in sync by hand.

export interface DownloadOptions {
  mode: 'video' | 'audio'
  audio_format: 'best' | 'mp3' | 'm4a' | 'opus' | 'flac' | 'wav'
  max_height: number | null
  container: 'auto' | 'mp4' | 'mkv' | 'webm'
  output_dir: string | null
  no_playlist: boolean
  playlist_items: string | null
  write_subtitles: boolean
  write_auto_subs: boolean
  subtitle_langs: string | null
  embed_subtitles: boolean
  embed_metadata: boolean
  embed_thumbnail: boolean
  write_thumbnail: boolean
  sponsorblock_remove: string[]
  sponsorblock_mark: string[]
  proxy: string | null
  rate_limit: string | null
  retries: number | null
  concurrent_fragments: number | null
  credential_label: string | null
  cookies_label: string | null
  cookies_from_browser: string | null
  output_template: string | null
  extra_args: string | null
  force_download: boolean
}

export const DEFAULT_OPTIONS: DownloadOptions = {
  mode: 'video',
  audio_format: 'best',
  max_height: null,
  container: 'auto',
  output_dir: null,
  no_playlist: false,
  playlist_items: null,
  write_subtitles: false,
  write_auto_subs: false,
  subtitle_langs: null,
  embed_subtitles: false,
  embed_metadata: false,
  embed_thumbnail: false,
  write_thumbnail: false,
  sponsorblock_remove: [],
  sponsorblock_mark: [],
  proxy: null,
  rate_limit: null,
  retries: null,
  concurrent_fragments: null,
  credential_label: null,
  cookies_label: null,
  cookies_from_browser: null,
  output_template: null,
  extra_args: null,
  force_download: false,
}

export interface JobProgress {
  type: 'job_progress'
  job_id: number
  status: 'downloading' | 'postprocessing'
  progress: number | null
  downloaded_bytes?: number | null
  total_bytes?: number | null
  speed?: number | null
  eta?: number | null
  filename?: string | null
  item_title?: string | null
  thumbnail?: string | null
  playlist_index?: number | null
  playlist_count?: number | null
  postprocessor?: string | null
}

export type JobStatus = 'queued' | 'running' | 'finished' | 'error' | 'cancelled'

export interface Job {
  id: number
  url: string
  title: string | null
  status: JobStatus
  files: string[]
  error: string | null
  subscription_id: number | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  thumbnail: string | null // remote address
  site: string | null // e.g. "youtube.com"
  filesize: number | null // bytes on disk
  skipped: number // items left out because they were downloaded before
  progress: JobProgress | null
}

export interface ProbeEntry {
  id: string | null
  title: string | null
  duration: number | null
  url: string | null
  already_downloaded: boolean
}

export interface ProbeResult {
  kind: 'video' | 'playlist'
  title: string | null
  webpage_url: string | null
  thumbnail: string | null
  duration: number | null
  uploader: string | null
  heights: number[]
  count: number | null
  entries: ProbeEntry[]
}

export interface Preset {
  id: number
  name: string
  options: DownloadOptions
  updated_at: string
}

export interface Subscription {
  id: number
  name: string
  url: string
  preset_id: number | null
  enabled: boolean
  check_interval_minutes: number | null
  last_check_at: string | null
  next_check_at: string | null
  last_check_result: string | null
  created_at: string
}

export interface SubscriptionIn {
  name: string
  url: string
  preset_id: number | null
  enabled: boolean
  check_interval_minutes: number | null
}

export interface ArchiveEntry {
  id: number
  extractor: string
  video_id: string
  title: string | null
  subscription_id: number | null
  job_id: number | null
  created_at: string
}

export interface VaultStatus {
  state: 'uninitialized' | 'locked' | 'unlocked'
  credentials?: string[]
  cookies?: string[]
}

export interface AppSettings {
  default_output_dir: string
  max_concurrent: number
  notifications: boolean
  notify_available: boolean // notify-send is installed
  ffmpeg_available: boolean
  yt_dlp_version: string
  yt_dlp_outdated: boolean
}

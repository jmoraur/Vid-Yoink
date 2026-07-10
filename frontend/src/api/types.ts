// TypeScript mirror of yoink/models.py — keep in sync by hand.

export interface DownloadOptions {
  output_dir?: string | null
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
  progress: JobProgress | null
}

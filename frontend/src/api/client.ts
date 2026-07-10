import type { DownloadOptions, Job } from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let detail = await res.text()
    try {
      detail = JSON.parse(detail).detail ?? detail
    } catch {
      /* not JSON */
    }
    throw new Error(detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  listDownloads: () => request<Job[]>('/api/downloads'),
  createDownload: (url: string, options: DownloadOptions = {}) =>
    request<Job>('/api/downloads', { method: 'POST', body: JSON.stringify({ url, options }) }),
  cancelDownload: (id: number) =>
    request<{ ok: boolean }>(`/api/downloads/${id}/cancel`, { method: 'POST' }),
}

import type { ArchiveEntry, DownloadOptions, Job, Preset, ProbeResult } from './types'

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
  createDownload: (url: string, options: DownloadOptions) =>
    request<Job>('/api/downloads', { method: 'POST', body: JSON.stringify({ url, options }) }),
  cancelDownload: (id: number) =>
    request<{ ok: boolean }>(`/api/downloads/${id}/cancel`, { method: 'POST' }),
  retryDownload: (id: number) =>
    request<Job>(`/api/downloads/${id}/retry`, { method: 'POST' }),
  deleteDownload: (id: number) =>
    request<{ ok: boolean }>(`/api/downloads/${id}`, { method: 'DELETE' }),

  listArchive: (q?: string) =>
    request<ArchiveEntry[]>(`/api/archive${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  deleteArchiveEntry: (id: number) =>
    request<{ ok: boolean }>(`/api/archive/${id}`, { method: 'DELETE' }),

  probe: (url: string) =>
    request<ProbeResult>('/api/probe', { method: 'POST', body: JSON.stringify({ url }) }),

  listPresets: () => request<Preset[]>('/api/presets'),
  createPreset: (name: string, options: DownloadOptions) =>
    request<Preset>('/api/presets', { method: 'POST', body: JSON.stringify({ name, options }) }),
  updatePreset: (id: number, name: string, options: DownloadOptions) =>
    request<Preset>(`/api/presets/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ name, options }),
    }),
  deletePreset: (id: number) =>
    request<{ ok: boolean }>(`/api/presets/${id}`, { method: 'DELETE' }),
}

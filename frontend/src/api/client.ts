import type {
  AppSettings,
  ArchiveEntry,
  DownloadOptions,
  Job,
  Preset,
  ProbeResult,
  Subscription,
  SubscriptionIn,
  VaultStatus,
} from './types'

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
  openFolder: (id: number) =>
    request<{ ok: boolean }>(`/api/downloads/${id}/open-folder`, { method: 'POST' }),
  retryFailed: () =>
    request<{ retried: number }>('/api/downloads/retry-failed', { method: 'POST' }),
  clearDownloads: (status?: 'finished' | 'error' | 'cancelled') =>
    request<{ deleted: number }>(`/api/downloads${status ? `?status=${status}` : ''}`, {
      method: 'DELETE',
    }),

  listArchive: (q?: string, subscriptionId?: number) => {
    const params = new URLSearchParams()
    if (q) params.set('q', q)
    if (subscriptionId != null) params.set('subscription_id', String(subscriptionId))
    const qs = params.toString()
    return request<ArchiveEntry[]>(`/api/archive${qs ? `?${qs}` : ''}`)
  },
  deleteArchiveEntry: (id: number) =>
    request<{ ok: boolean }>(`/api/archive/${id}`, { method: 'DELETE' }),

  listSubscriptions: () => request<Subscription[]>('/api/subscriptions'),
  createSubscription: (sub: SubscriptionIn) =>
    request<Subscription>('/api/subscriptions', { method: 'POST', body: JSON.stringify(sub) }),
  updateSubscription: (id: number, sub: SubscriptionIn) =>
    request<Subscription>(`/api/subscriptions/${id}`, {
      method: 'PUT',
      body: JSON.stringify(sub),
    }),
  deleteSubscription: (id: number) =>
    request<{ ok: boolean }>(`/api/subscriptions/${id}`, { method: 'DELETE' }),
  checkSubscription: (id: number) =>
    request<{ new_jobs: number; failing: number; error: string | null }>(
      `/api/subscriptions/${id}/check`,
      { method: 'POST' },
    ),
  seedSubscription: (id: number) =>
    request<{ seeded: number }>(`/api/subscriptions/${id}/seed`, { method: 'POST' }),

  vaultStatus: () => request<VaultStatus>('/api/vault/status'),
  vaultInit: (password: string) =>
    request<VaultStatus>('/api/vault/init', { method: 'POST', body: JSON.stringify({ password }) }),
  vaultUnlock: (password: string) =>
    request<VaultStatus>('/api/vault/unlock', {
      method: 'POST',
      body: JSON.stringify({ password }),
    }),
  vaultLock: () => request<VaultStatus>('/api/vault/lock', { method: 'POST' }),
  vaultKeyring: (enabled: boolean) =>
    request<VaultStatus>('/api/vault/keyring', {
      method: 'PUT',
      body: JSON.stringify({ enabled }),
    }),
  vaultChangePassword: (oldPassword: string, newPassword: string) =>
    request<VaultStatus>('/api/vault/change-password', {
      method: 'POST',
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    }),
  vaultSetCredential: (label: string, username: string, password: string) =>
    request<VaultStatus>(`/api/vault/credentials/${encodeURIComponent(label)}`, {
      method: 'PUT',
      body: JSON.stringify({ username, password }),
    }),
  vaultDeleteCredential: (label: string) =>
    request<VaultStatus>(`/api/vault/credentials/${encodeURIComponent(label)}`, {
      method: 'DELETE',
    }),
  vaultSetCookies: (label: string, content: string) =>
    request<VaultStatus>(`/api/vault/cookies/${encodeURIComponent(label)}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),
  vaultDeleteCookies: (label: string) =>
    request<VaultStatus>(`/api/vault/cookies/${encodeURIComponent(label)}`, {
      method: 'DELETE',
    }),

  getSettings: () => request<AppSettings>('/api/settings'),
  putSettings: (settings: Partial<Pick<AppSettings, 'default_output_dir' | 'max_concurrent' | 'notifications'>>) =>
    request<AppSettings>('/api/settings', { method: 'PUT', body: JSON.stringify(settings) }),

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

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { ErrorState } from '../components/ui/ErrorState'
import { Icon } from '../components/ui/Icon'
import { Skeleton } from '../components/ui/Skeleton'

function useVaultInvalidate() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: ['vault'] })
}

function InitPanel() {
  const [pw, setPw] = useState('')
  const [pw2, setPw2] = useState('')
  const invalidate = useVaultInvalidate()
  const init = useMutation({ mutationFn: () => api.vaultInit(pw), onSuccess: invalidate })
  return (
    <div>
      <p className="hint">
        Create a vault to store site logins and cookies, encrypted with a master password.
        The password is never stored — if you forget it, the vault contents are gone.
      </p>
      <div className="row">
        <label>
          Master password
          <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} />
        </label>
        <label>
          Repeat
          <input type="password" value={pw2} onChange={(e) => setPw2(e.target.value)} />
        </label>
        <button disabled={!pw || pw !== pw2 || init.isPending} onClick={() => init.mutate()}>
          Create vault
        </button>
      </div>
      {pw && pw2 && pw !== pw2 && <p className="error">Passwords do not match.</p>}
      {init.isError && <p className="error">{init.error.message}</p>}
    </div>
  )
}

export function UnlockPanel() {
  const [pw, setPw] = useState('')
  const invalidate = useVaultInvalidate()
  const unlock = useMutation({
    mutationFn: () => api.vaultUnlock(pw),
    onSuccess: () => {
      setPw('')
      invalidate()
    },
  })
  return (
    <form
      className="row"
      onSubmit={(e) => {
        e.preventDefault()
        if (pw) unlock.mutate()
      }}
    >
      <label className="grow">
        Master password
        <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoFocus />
      </label>
      <button type="submit" disabled={!pw || unlock.isPending}>
        Unlock
      </button>
      {unlock.isError && <span className="error">{unlock.error.message}</span>}
    </form>
  )
}

function CredentialsEditor({ credentials }: { credentials: string[] }) {
  const [label, setLabel] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const invalidate = useVaultInvalidate()
  const save = useMutation({
    mutationFn: () => api.vaultSetCredential(label.trim(), username, password),
    onSuccess: () => {
      setLabel('')
      setUsername('')
      setPassword('')
      invalidate()
    },
  })
  const remove = useMutation({
    mutationFn: (l: string) => api.vaultDeleteCredential(l),
    onSuccess: invalidate,
  })
  return (
    <div className="vault-block">
      <h3>Site logins</h3>
      {credentials.map((l) => (
        <div className="row" key={l}>
          <span className="grow">{l}</span>
          <button className="small" onClick={() => remove.mutate(l)}>
            Delete
          </button>
        </div>
      ))}
      {credentials.length === 0 && <p className="muted">None stored.</p>}
      <div className="row">
        <label>
          Label
          <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="vimeo" />
        </label>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <button
          disabled={!label.trim() || !username || save.isPending}
          onClick={() => save.mutate()}
        >
          Save
        </button>
      </div>
      {save.isError && <p className="error">{save.error.message}</p>}
    </div>
  )
}

function CookiesEditor({ cookies }: { cookies: string[] }) {
  const [label, setLabel] = useState('')
  const [content, setContent] = useState('')
  const invalidate = useVaultInvalidate()
  const save = useMutation({
    mutationFn: () => api.vaultSetCookies(label.trim(), content),
    onSuccess: () => {
      setLabel('')
      setContent('')
      invalidate()
    },
  })
  const remove = useMutation({
    mutationFn: (l: string) => api.vaultDeleteCookies(l),
    onSuccess: invalidate,
  })
  return (
    <div className="vault-block">
      <h3>Cookies</h3>
      <p className="hint">
        Paste the contents of a cookies.txt (Netscape format) export — e.g. from the
        "Get cookies.txt" browser extension. Needed for sites where a password login
        doesn't work (like YouTube).
      </p>
      {cookies.map((l) => (
        <div className="row" key={l}>
          <span className="grow">{l}</span>
          <button className="small" onClick={() => remove.mutate(l)}>
            Delete
          </button>
        </div>
      ))}
      {cookies.length === 0 && <p className="muted">None stored.</p>}
      <div className="row">
        <label className="grow">
          Label
          <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="youtube" />
        </label>
      </div>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="# Netscape HTTP Cookie File&#10;…"
        rows={5}
      />
      <div className="row actions">
        <button
          disabled={!label.trim() || !content.trim() || save.isPending}
          onClick={() => save.mutate()}
        >
          Save cookies
        </button>
      </div>
      {save.isError && <p className="error">{save.error.message}</p>}
    </div>
  )
}

function ChangePassword() {
  const [oldPw, setOldPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const invalidate = useVaultInvalidate()
  const change = useMutation({
    mutationFn: () => api.vaultChangePassword(oldPw, newPw),
    onSuccess: () => {
      setOldPw('')
      setNewPw('')
      invalidate()
    },
  })
  return (
    <div className="vault-block">
      <h3>Change master password</h3>
      <div className="row">
        <label>
          Current
          <input type="password" value={oldPw} onChange={(e) => setOldPw(e.target.value)} />
        </label>
        <label>
          New
          <input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} />
        </label>
        <button disabled={!oldPw || !newPw || change.isPending} onClick={() => change.mutate()}>
          Change
        </button>
      </div>
      {change.isError && <p className="error">{change.error.message}</p>}
      {change.isSuccess && <p className="muted">Password changed.</p>}
    </div>
  )
}

function GeneralSettings() {
  const queryClient = useQueryClient()
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })
  const [dir, setDir] = useState<string | null>(null)
  const [conc, setConc] = useState<number | null>(null)
  const save = useMutation({
    mutationFn: () =>
      api.putSettings({
        ...(dir !== null ? { default_output_dir: dir } : {}),
        ...(conc !== null ? { max_concurrent: conc } : {}),
      }),
    onSuccess: () => {
      setDir(null)
      setConc(null)
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
  if (settings.isPending) {
    return (
      <div className="options-form settings-card">
        <h2>General</h2>
        <Skeleton lines={1} />
      </div>
    )
  }
  if (settings.isError) {
    return (
      <div className="options-form settings-card">
        <h2>General</h2>
        <ErrorState message={settings.error.message} onRetry={() => settings.refetch()} />
      </div>
    )
  }
  const dirty = dir !== null || conc !== null

  return (
    <div className="options-form settings-card">
      <h2>General</h2>
      {!settings.data.ffmpeg_available && (
        <p className="error">
          ffmpeg was not found on this system — merging video+audio, audio extraction and
          embedding will fail. Install it (on Fedora: RPM Fusion's ffmpeg).
        </p>
      )}
      <div className="row">
        <label className="grow">
          Default download folder
          <input
            value={dir ?? settings.data.default_output_dir}
            onChange={(e) => setDir(e.target.value)}
          />
        </label>
        <label>
          Parallel downloads
          <input
            type="number"
            min={1}
            max={10}
            value={conc ?? settings.data.max_concurrent}
            onChange={(e) => setConc(Number(e.target.value))}
          />
        </label>
        <button disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
          Save
        </button>
      </div>
      <p className="hint">
        Parallel download changes apply after a restart. yt-dlp {settings.data.yt_dlp_version}
        {' · '}ffmpeg {settings.data.ffmpeg_available ? 'found' : 'missing'}
      </p>
      {save.isError && <p className="error">{save.error.message}</p>}
    </div>
  )
}

export function Settings() {
  const vault = useQuery({ queryKey: ['vault'], queryFn: api.vaultStatus })
  const invalidate = useVaultInvalidate()
  const lock = useMutation({ mutationFn: api.vaultLock, onSuccess: invalidate })

  return (
    <div>
      <GeneralSettings />
      <div className="options-form">
        <div className="card-title-row">
          <h2>Credential vault</h2>
          {vault.data?.state === 'unlocked' && (
            <button className="small" onClick={() => lock.mutate()}>
              <Icon name="lock" size={14} /> Lock now
            </button>
          )}
          {vault.data && (
            <span
              className={`chip ${
                vault.data.state === 'unlocked'
                  ? 'chip-ok'
                  : vault.data.state === 'locked'
                    ? 'chip-warn'
                    : 'chip-muted'
              }`}
            >
              <Icon name={vault.data.state === 'unlocked' ? 'unlock' : 'lock'} size={12} />
              {vault.data.state}
            </span>
          )}
        </div>
        {vault.isPending && <Skeleton lines={1} />}
        {vault.isError && (
          <ErrorState message={vault.error.message} onRetry={() => vault.refetch()} />
        )}
        {vault.data?.state === 'uninitialized' && <InitPanel />}
        {vault.data?.state === 'locked' && <UnlockPanel />}
        {vault.data?.state === 'unlocked' && (
          <>
            <CredentialsEditor credentials={vault.data.credentials ?? []} />
            <CookiesEditor cookies={vault.data.cookies ?? []} />
            <ChangePassword />
          </>
        )}
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { DEFAULT_OPTIONS, type DownloadOptions } from '../api/types'
import { ProbeCard } from '../components/ProbeCard'
import { OptionsForm } from '../components/options/OptionsForm'
import { PresetBar } from '../components/options/PresetBar'

function useDebounced(value: string, ms: number): string {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return debounced
}

const looksLikeUrl = (s: string) => /^https?:\/\/\S+\.\S+/.test(s)

export function NewDownload() {
  const [url, setUrl] = useState('')
  const [options, setOptions] = useState<DownloadOptions>(DEFAULT_OPTIONS)
  const navigate = useNavigate()

  const probeUrl = useDebounced(url.trim(), 700)
  const probe = useQuery({
    queryKey: ['probe', probeUrl],
    queryFn: () => api.probe(probeUrl),
    enabled: looksLikeUrl(probeUrl),
    staleTime: Infinity,
    retry: false,
  })

  const create = useMutation({
    mutationFn: () => api.createDownload(url.trim(), options),
    onSuccess: () => navigate('/queue'),
  })

  return (
    <div>
      <form
        className="download-form"
        onSubmit={(e) => {
          e.preventDefault()
          if (url.trim()) create.mutate()
        }}
      >
        <input
          value={url}
          onChange={(e) => {
            setUrl(e.target.value)
            setOptions((o) => ({ ...o, playlist_items: null })) // selection belongs to old URL
          }}
          placeholder="Paste a video or playlist URL…"
          autoFocus
        />
        <button type="submit" disabled={create.isPending || !url.trim()}>
          Download
        </button>
      </form>
      {create.isError && <p className="error">{create.error.message}</p>}

      {probe.isFetching && <p className="muted">Fetching info…</p>}
      {probe.isError && <p className="error">Could not read this URL: {probe.error.message}</p>}
      {probe.data && (
        <ProbeCard
          probe={probe.data}
          playlistItems={options.playlist_items}
          onPlaylistItems={(items) => setOptions({ ...options, playlist_items: items })}
        />
      )}

      <PresetBar options={options} onLoad={setOptions} />
      <OptionsForm value={options} onChange={setOptions} heights={probe.data?.heights} />
    </div>
  )
}

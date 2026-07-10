import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api/client'
import { JobRow } from './components/JobRow'

export default function App() {
  const [url, setUrl] = useState('')
  const queryClient = useQueryClient()
  const jobs = useQuery({ queryKey: ['downloads'], queryFn: api.listDownloads })
  const create = useMutation({
    mutationFn: (u: string) => api.createDownload(u),
    onSuccess: () => {
      setUrl('')
      queryClient.invalidateQueries({ queryKey: ['downloads'] })
    },
  })

  return (
    <div className="app">
      <header>
        <h1>yoink</h1>
      </header>
      <form
        className="download-form"
        onSubmit={(e) => {
          e.preventDefault()
          if (url.trim()) create.mutate(url.trim())
        }}
      >
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste a video or playlist URL…"
          autoFocus
        />
        <button type="submit" disabled={create.isPending || !url.trim()}>
          Download
        </button>
      </form>
      {create.isError && <p className="error">{create.error.message}</p>}
      <section className="jobs">
        {jobs.data?.map((job) => <JobRow key={job.id} job={job} />)}
        {jobs.data?.length === 0 && <p className="muted">No downloads yet.</p>}
      </section>
    </div>
  )
}

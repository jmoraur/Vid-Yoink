// WebSocket connection + external progress store. Progress ticks (~4/sec/job)
// deliberately bypass React Query so only the affected job row re-renders.

import { useSyncExternalStore } from 'react'
import type { QueryClient } from '@tanstack/react-query'
import type { JobProgress, JobStatus } from './api/types'

const progressMap = new Map<number, JobProgress>()
const listeners = new Map<number, Set<() => void>>()

// Local statuses the server also reports via job_status; 'cancelling' is UI-only.
const statusOverrides = new Map<number, 'cancelling'>()

function notify(jobId: number) {
  listeners.get(jobId)?.forEach((fn) => fn())
}

export function useJobProgress(jobId: number): JobProgress | undefined {
  return useSyncExternalStore(
    (onChange) => {
      let set = listeners.get(jobId)
      if (!set) {
        set = new Set()
        listeners.set(jobId, set)
      }
      set.add(onChange)
      return () => set.delete(onChange)
    },
    () => progressMap.get(jobId),
  )
}

export function useCancelling(jobId: number): boolean {
  return useSyncExternalStore(
    (onChange) => {
      let set = listeners.get(jobId)
      if (!set) {
        set = new Set()
        listeners.set(jobId, set)
      }
      set.add(onChange)
      return () => set.delete(onChange)
    },
    () => statusOverrides.get(jobId) === 'cancelling',
  )
}

const TERMINAL: (JobStatus | string)[] = ['finished', 'error', 'cancelled']

export function connectWebSocket(queryClient: QueryClient) {
  function open() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/ws`)
    ws.onopen = () => {
      // catch up on anything missed while disconnected
      queryClient.invalidateQueries({ queryKey: ['downloads'] })
    }
    ws.onmessage = (msg) => {
      const event = JSON.parse(msg.data)
      switch (event.type) {
        case 'job_progress':
          progressMap.set(event.job_id, event)
          notify(event.job_id)
          break
        case 'job_status':
          if (event.status === 'cancelling') {
            statusOverrides.set(event.job_id, 'cancelling')
          } else if (TERMINAL.includes(event.status)) {
            progressMap.delete(event.job_id)
            statusOverrides.delete(event.job_id)
          }
          notify(event.job_id)
          queryClient.invalidateQueries({ queryKey: ['downloads'] })
          break
      }
    }
    ws.onclose = () => setTimeout(open, 2000)
  }
  open()
}

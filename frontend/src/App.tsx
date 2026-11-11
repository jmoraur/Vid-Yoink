import { useQuery } from '@tanstack/react-query'
import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { api } from './api/client'
import { NewDownload } from './pages/NewDownload'
import { Queue } from './pages/Queue'
import { Subscriptions } from './pages/Subscriptions'
import { Settings } from './pages/Settings'
import { Icon } from './components/ui/Icon'
import { ThemeToggle } from './components/ui/ThemeToggle'

function VaultBanner() {
  const location = useLocation()
  const vault = useQuery({ queryKey: ['vault'], queryFn: api.vaultStatus })
  if (vault.data?.state !== 'locked' || location.pathname === '/settings') return null
  return (
    <div className="banner" role="status">
      <Icon name="lock" />
      <span>
        Vault is locked — downloads that use stored credentials will fail.{' '}
        <NavLink to="/settings">Unlock</NavLink>
      </span>
    </div>
  )
}

function QueueBadge() {
  // Shares the ['downloads'] cache; ws.ts invalidates it on every status change.
  const jobs = useQuery({ queryKey: ['downloads'], queryFn: api.listDownloads })
  const active = jobs.data?.filter((j) => j.status === 'queued' || j.status === 'running').length
  if (!active) return null
  return <span className="nav-badge">{active}</span>
}

function ArchiveRedirect() {
  // keeps "?sub=…" so old links to one subscription's items still work
  return <Navigate to={`/subscriptions/archive${useLocation().search}`} replace />
}

export default function App() {
  return (
    <div className="app">
      <header>
        <h1 className="wordmark">
          <Icon name="download" size={18} /> yoink
        </h1>
        <nav aria-label="Primary">
          <NavLink to="/" end>
            <Icon name="download" /> <span>Downloads</span> <QueueBadge />
          </NavLink>
          <NavLink to="/subscriptions">
            <Icon name="rss" /> <span>Subscriptions</span>
          </NavLink>
          <NavLink to="/settings">
            <Icon name="settings" /> <span>Settings</span>
          </NavLink>
        </nav>
        <ThemeToggle />
      </header>
      <VaultBanner />
      <Routes>
        <Route
          path="/"
          element={
            <>
              <NewDownload />
              <Queue />
            </>
          }
        />
        <Route path="/subscriptions/*" element={<Subscriptions />} />
        <Route path="/settings" element={<Settings />} />
        {/* addresses from before the three-section layout */}
        <Route path="/queue" element={<Navigate to="/" replace />} />
        <Route path="/presets" element={<Navigate to="/settings" replace />} />
        <Route path="/archive" element={<ArchiveRedirect />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

import { useQuery } from '@tanstack/react-query'
import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { api } from './api/client'
import { NewDownload } from './pages/NewDownload'
import { Queue } from './pages/Queue'
import { Subscriptions } from './pages/Subscriptions'
import { Presets } from './pages/Presets'
import { Archive } from './pages/Archive'
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

export default function App() {
  return (
    <div className="app">
      <header>
        <h1 className="wordmark">
          <Icon name="download" size={18} /> yoink
        </h1>
        <nav aria-label="Primary">
          <NavLink to="/" end>
            <Icon name="download" /> <span>Download</span>
          </NavLink>
          <NavLink to="/queue">
            <Icon name="list" /> <span>Queue</span> <QueueBadge />
          </NavLink>
          <NavLink to="/subscriptions">
            <Icon name="rss" /> <span>Subscriptions</span>
          </NavLink>
          <NavLink to="/presets">
            <Icon name="sliders" /> <span>Presets</span>
          </NavLink>
          <NavLink to="/archive">
            <Icon name="archive" /> <span>Archive</span>
          </NavLink>
          <NavLink to="/settings">
            <Icon name="settings" /> <span>Settings</span>
          </NavLink>
        </nav>
        <ThemeToggle />
      </header>
      <VaultBanner />
      <Routes>
        <Route path="/" element={<NewDownload />} />
        <Route path="/queue" element={<Queue />} />
        <Route path="/subscriptions" element={<Subscriptions />} />
        <Route path="/presets" element={<Presets />} />
        <Route path="/archive" element={<Archive />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </div>
  )
}

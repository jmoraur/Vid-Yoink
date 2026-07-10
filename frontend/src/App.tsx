import { useQuery } from '@tanstack/react-query'
import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { api } from './api/client'
import { NewDownload } from './pages/NewDownload'
import { Queue } from './pages/Queue'
import { Subscriptions } from './pages/Subscriptions'
import { Presets } from './pages/Presets'
import { Archive } from './pages/Archive'
import { Settings } from './pages/Settings'

function VaultBanner() {
  const location = useLocation()
  const vault = useQuery({ queryKey: ['vault'], queryFn: api.vaultStatus })
  if (vault.data?.state !== 'locked' || location.pathname === '/settings') return null
  return (
    <div className="banner">
      Vault is locked — downloads that use stored credentials will fail.{' '}
      <NavLink to="/settings">Unlock</NavLink>
    </div>
  )
}

export default function App() {
  return (
    <div className="app">
      <header>
        <h1>yoink</h1>
        <nav>
          <NavLink to="/" end>
            Download
          </NavLink>
          <NavLink to="/queue">Queue</NavLink>
          <NavLink to="/subscriptions">Subscriptions</NavLink>
          <NavLink to="/presets">Presets</NavLink>
          <NavLink to="/archive">Archive</NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
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

import { NavLink, Route, Routes } from 'react-router-dom'
import { NewDownload } from './pages/NewDownload'
import { Queue } from './pages/Queue'
import { Subscriptions } from './pages/Subscriptions'
import { Presets } from './pages/Presets'
import { Archive } from './pages/Archive'

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
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<NewDownload />} />
        <Route path="/queue" element={<Queue />} />
        <Route path="/subscriptions" element={<Subscriptions />} />
        <Route path="/presets" element={<Presets />} />
        <Route path="/archive" element={<Archive />} />
      </Routes>
    </div>
  )
}

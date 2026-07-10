import { NavLink, Route, Routes } from 'react-router-dom'
import { NewDownload } from './pages/NewDownload'
import { Queue } from './pages/Queue'
import { Presets } from './pages/Presets'

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
          <NavLink to="/presets">Presets</NavLink>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<NewDownload />} />
        <Route path="/queue" element={<Queue />} />
        <Route path="/presets" element={<Presets />} />
      </Routes>
    </div>
  )
}

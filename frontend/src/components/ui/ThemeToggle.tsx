import { useState } from 'react'
import { getTheme, setTheme, type ThemePref } from '../../theme'
import { Icon, type IconName } from './Icon'

const NEXT: Record<ThemePref, ThemePref> = { system: 'light', light: 'dark', dark: 'system' }
const ICONS: Record<ThemePref, IconName> = { system: 'monitor', light: 'sun', dark: 'moon' }
const LABELS: Record<ThemePref, string> = {
  system: 'Theme: follow system',
  light: 'Theme: light',
  dark: 'Theme: dark',
}

export function ThemeToggle() {
  const [pref, setPref] = useState<ThemePref>(getTheme)
  const cycle = () => {
    const next = NEXT[pref]
    setTheme(next)
    setPref(next)
  }
  return (
    <button
      type="button"
      className="ghost-icon theme-toggle"
      onClick={cycle}
      aria-label={LABELS[pref]}
      title={LABELS[pref]}
    >
      <Icon name={ICONS[pref]} size={18} />
    </button>
  )
}

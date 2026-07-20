export type ThemePref = 'system' | 'light' | 'dark'

const KEY = 'yoink-theme'

export function getTheme(): ThemePref {
  const stored = localStorage.getItem(KEY)
  return stored === 'light' || stored === 'dark' ? stored : 'system'
}

export function setTheme(pref: ThemePref) {
  if (pref === 'system') {
    localStorage.removeItem(KEY)
    delete document.documentElement.dataset.theme
  } else {
    localStorage.setItem(KEY, pref)
    document.documentElement.dataset.theme = pref
  }
}

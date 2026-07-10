import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import type { DownloadOptions } from '../../api/types'
import { Section } from './Section'

interface Props {
  value: DownloadOptions
  onChange: (options: DownloadOptions) => void
  heights?: number[] // from probe: constrain the quality select to what exists
}

const STANDARD_HEIGHTS = [2160, 1440, 1080, 720, 480, 360]
const SPONSORBLOCK_CATEGORIES = [
  'sponsor',
  'selfpromo',
  'interaction',
  'intro',
  'outro',
  'preview',
  'music_offtopic',
  'filler',
]

// '' <-> null adapters for optional text/number inputs
const str = (v: string | null) => v ?? ''
const orNull = (v: string) => (v.trim() === '' ? null : v.trim())

export function OptionsForm({ value, onChange, heights }: Props) {
  const set = <K extends keyof DownloadOptions>(key: K, v: DownloadOptions[K]) =>
    onChange({ ...value, [key]: v })

  const heightChoices = heights?.length ? heights : STANDARD_HEIGHTS

  return (
    <div className="options-form">
      <div className="row">
        <label className="grow">
          Type
          <div className="mode-toggle">
            <button
              type="button"
              className={value.mode === 'video' ? 'active' : ''}
              onClick={() => set('mode', 'video')}
            >
              Video
            </button>
            <button
              type="button"
              className={value.mode === 'audio' ? 'active' : ''}
              onClick={() => set('mode', 'audio')}
            >
              Audio only
            </button>
          </div>
        </label>
        {value.mode === 'video' ? (
          <>
            <label>
              Max quality
              <select
                value={value.max_height ?? ''}
                onChange={(e) =>
                  set('max_height', e.target.value === '' ? null : Number(e.target.value))
                }
              >
                <option value="">Best</option>
                {heightChoices.map((h) => (
                  <option key={h} value={h}>
                    {h}p
                  </option>
                ))}
              </select>
            </label>
            <label>
              Container
              <select
                value={value.container}
                onChange={(e) => set('container', e.target.value as DownloadOptions['container'])}
              >
                <option value="auto">Auto</option>
                <option value="mp4">MP4</option>
                <option value="mkv">MKV</option>
                <option value="webm">WebM</option>
              </select>
            </label>
          </>
        ) : (
          <label>
            Audio format
            <select
              value={value.audio_format}
              onChange={(e) =>
                set('audio_format', e.target.value as DownloadOptions['audio_format'])
              }
            >
              <option value="best">Best (keep original)</option>
              <option value="mp3">MP3</option>
              <option value="m4a">M4A</option>
              <option value="opus">Opus</option>
              <option value="flac">FLAC</option>
              <option value="wav">WAV</option>
            </select>
          </label>
        )}
      </div>

      <div className="row">
        <label className="grow">
          Save to
          <input
            value={str(value.output_dir)}
            onChange={(e) => set('output_dir', orNull(e.target.value))}
            placeholder="~/Downloads (default)"
          />
        </label>
      </div>

      <div className="row checks">
        <label>
          <input
            type="checkbox"
            checked={value.embed_metadata}
            onChange={(e) => set('embed_metadata', e.target.checked)}
          />
          Embed metadata
        </label>
        <label>
          <input
            type="checkbox"
            checked={value.embed_thumbnail}
            onChange={(e) => set('embed_thumbnail', e.target.checked)}
          />
          Embed thumbnail
        </label>
        <label>
          <input
            type="checkbox"
            checked={value.write_subtitles}
            onChange={(e) => set('write_subtitles', e.target.checked)}
          />
          Subtitles
        </label>
        <label title="Skip the already-downloaded check for this download">
          <input
            type="checkbox"
            checked={value.force_download}
            onChange={(e) => set('force_download', e.target.checked)}
          />
          Re-download if in archive
        </label>
      </div>

      <Section title="Subtitles">
        <div className="row checks">
          <label>
            <input
              type="checkbox"
              checked={value.write_auto_subs}
              onChange={(e) => set('write_auto_subs', e.target.checked)}
            />
            Include auto-generated
          </label>
          <label>
            <input
              type="checkbox"
              checked={value.embed_subtitles}
              onChange={(e) => set('embed_subtitles', e.target.checked)}
            />
            Embed into file
          </label>
        </div>
        <div className="row">
          <label className="grow">
            Languages (comma-separated, e.g. en,de — empty = all)
            <input
              value={str(value.subtitle_langs)}
              onChange={(e) => set('subtitle_langs', orNull(e.target.value))}
              placeholder="all"
            />
          </label>
        </div>
      </Section>

      <Section title="SponsorBlock">
        <p className="hint">Remove these segment types from the file (YouTube only):</p>
        <div className="row checks wrap">
          {SPONSORBLOCK_CATEGORIES.map((cat) => (
            <label key={cat}>
              <input
                type="checkbox"
                checked={value.sponsorblock_remove.includes(cat)}
                onChange={(e) =>
                  set(
                    'sponsorblock_remove',
                    e.target.checked
                      ? [...value.sponsorblock_remove, cat]
                      : value.sponsorblock_remove.filter((c) => c !== cat),
                  )
                }
              />
              {cat}
            </label>
          ))}
        </div>
      </Section>

      <Section title="Network">
        <div className="row">
          <label className="grow">
            Proxy
            <input
              value={str(value.proxy)}
              onChange={(e) => set('proxy', orNull(e.target.value))}
              placeholder="socks5://127.0.0.1:9050"
            />
          </label>
          <label>
            Rate limit
            <input
              value={str(value.rate_limit)}
              onChange={(e) => set('rate_limit', orNull(e.target.value))}
              placeholder="2M"
            />
          </label>
        </div>
        <div className="row">
          <label>
            Retries
            <input
              type="number"
              min={0}
              value={value.retries ?? ''}
              onChange={(e) =>
                set('retries', e.target.value === '' ? null : Number(e.target.value))
              }
              placeholder="10"
            />
          </label>
          <label>
            Parallel fragments
            <input
              type="number"
              min={1}
              max={16}
              value={value.concurrent_fragments ?? ''}
              onChange={(e) =>
                set('concurrent_fragments', e.target.value === '' ? null : Number(e.target.value))
              }
              placeholder="1"
            />
          </label>
        </div>
      </Section>

      <Section title="Cookies & authentication">
        <AuthSection value={value} set={set} />
      </Section>

      <Section title="Output template">
        <div className="row">
          <label className="grow">
            Filename template (yt-dlp syntax)
            <input
              value={str(value.output_template)}
              onChange={(e) => set('output_template', orNull(e.target.value))}
              placeholder="%(title)s [%(id)s].%(ext)s"
            />
          </label>
        </div>
      </Section>

      <Section title="Extra yt-dlp arguments">
        <div className="row">
          <label className="grow">
            Raw CLI arguments — applied last, override everything above
            <input
              value={str(value.extra_args)}
              onChange={(e) => set('extra_args', orNull(e.target.value))}
              placeholder="--live-from-start --remux-video mp4"
            />
          </label>
        </div>
      </Section>
    </div>
  )
}

function AuthSection({
  value,
  set,
}: {
  value: DownloadOptions
  set: <K extends keyof DownloadOptions>(key: K, v: DownloadOptions[K]) => void
}) {
  const vault = useQuery({ queryKey: ['vault'], queryFn: api.vaultStatus })
  const unlocked = vault.data?.state === 'unlocked'

  return (
    <>
      <div className="row">
        <label>
          Vault login
          <select
            value={value.credential_label ?? ''}
            onChange={(e) => set('credential_label', e.target.value || null)}
            disabled={!unlocked && !value.credential_label}
          >
            <option value="">None</option>
            {vault.data?.credentials?.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label>
          Vault cookies
          <select
            value={value.cookies_label ?? ''}
            onChange={(e) => set('cookies_label', e.target.value || null)}
            disabled={!unlocked && !value.cookies_label}
          >
            <option value="">None</option>
            {vault.data?.cookies?.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label className="grow">
          Cookies from browser
          <input
            value={value.cookies_from_browser ?? ''}
            onChange={(e) =>
              set('cookies_from_browser', e.target.value.trim() === '' ? null : e.target.value)
            }
            placeholder="firefox  ·  chrome:ProfileName"
          />
        </label>
      </div>
      <p className="hint">
        {vault.data?.state === 'unlocked' && 'Manage stored logins and cookies in '}
        {vault.data?.state === 'locked' &&
          'Vault is locked — jobs using vault entries will fail until you unlock it in '}
        {vault.data?.state === 'uninitialized' &&
          'No vault yet — create one to store site logins in '}
        <Link to="/settings">Settings</Link>. "Cookies from browser" reads your browser
        profile directly and needs no vault.
      </p>
    </>
  )
}

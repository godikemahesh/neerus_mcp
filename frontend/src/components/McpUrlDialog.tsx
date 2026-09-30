import { useEffect, useState } from 'react'
import { ApiError, getMcpUrl } from '../lib/api'

export function McpUrlDialog({ onClose }: { onClose: () => void }) {
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    getMcpUrl()
      .then((data) => setUrl(data.url))
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : 'Could not load the MCP URL'),
      )
  }, [])

  async function copy() {
    if (!url) return

    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('Could not copy automatically — select and copy the URL manually')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-lg">
        <div className="flex items-center gap-2">
          <span aria-hidden className="text-lg leading-none">🔌</span>
          <h3 className="text-sm font-semibold text-[var(--text)]">
            Claude MCP connector
          </h3>
        </div>

        <p className="mt-2 text-sm text-[var(--text-muted)]">
          In Claude Desktop, go to Settings → Connectors → Add custom
          connector, and paste this URL in.
        </p>

        <div className="mt-4">
          {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

          {!error && !url && (
            <p className="text-sm text-[var(--text-muted)]">Loading…</p>
          )}

          {url && (
            <div className="flex items-center gap-2">
              <input
                readOnly
                value={url}
                onFocus={(event) => event.target.select()}
                className="min-w-0 flex-1 rounded-lg border border-[var(--border)] bg-transparent px-3 py-2 font-mono text-xs text-[var(--text)] outline-none"
              />
              <button
                onClick={copy}
                className="flex-shrink-0 rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
              >
                {copied ? 'Copied ✓' : 'Copy'}
              </button>
            </div>
          )}
        </div>

        <p className="mt-4 text-xs text-[var(--text-muted)]">
          Treat this URL like a password — anyone with it can query your
          uploaded data through Claude.
        </p>

        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--text)] hover:bg-[var(--border)]/50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

import { useState } from 'react'
import type { FormEvent } from 'react'

export function NewFolderDialog({
  parentLabel,
  onCreate,
  onCancel,
}: {
  parentLabel: string
  onCreate: (name: string) => void
  onCancel: () => void
}) {
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  function handleSubmit(event: FormEvent) {
    event.preventDefault()

    const trimmed = name.trim()

    if (!trimmed) {
      setError('Enter a folder name')
      return
    }

    if (trimmed.includes('/')) {
      setError('Folder names can\'t contain "/"')
      return
    }

    onCreate(trimmed)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-lg"
      >
        <h3 className="text-sm font-semibold text-[var(--text)]">New folder</h3>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Creating inside: <span className="font-medium text-[var(--text)]">{parentLabel}</span>
        </p>

        <label className="mt-4 block text-sm font-medium text-[var(--text)]">
          Folder name
          <input
            autoFocus
            value={name}
            onChange={(event) => {
              setName(event.target.value)
              setError(null)
            }}
            placeholder="e.g. Sales"
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-transparent px-3 py-2 text-sm text-[var(--text)] outline-none focus:border-[var(--accent)]"
          />
        </label>

        {error && <p className="mt-2 text-sm text-[var(--danger)]">{error}</p>}

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--text)] hover:bg-[var(--border)]/50"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="rounded-lg bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
          >
            Create folder
          </button>
        </div>
      </form>
    </div>
  )
}

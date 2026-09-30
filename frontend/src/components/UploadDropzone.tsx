import { useRef, useState } from 'react'
import type { DragEvent } from 'react'
import { ApiError, uploadFile } from '../lib/api'

interface UploadResult {
  fileName: string
  ok: boolean
  message: string
}

export function UploadDropzone({
  directory,
  onUploaded,
}: {
  directory: string
  onUploaded: () => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [busy, setBusy] = useState(false)
  const [results, setResults] = useState<UploadResult[]>([])

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return

    setBusy(true)
    const newResults: UploadResult[] = []

    for (const file of Array.from(files)) {
      try {
        const result = await uploadFile(directory, file)
        const created = result.created.length
        newResults.push({
          fileName: file.name,
          ok: true,
          message: `${created} sheet${created === 1 ? '' : 's'} loaded`,
        })
      } catch (err) {
        newResults.push({
          fileName: file.name,
          ok: false,
          message: err instanceof ApiError ? err.message : 'Upload failed',
        })
      }
    }

    setResults(newResults)
    setBusy(false)
    onUploaded()
  }

  return (
    <div>
      <div
        onDragOver={(event: DragEvent) => {
          event.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(event: DragEvent) => {
          event.preventDefault()
          setDragOver(false)
          handleFiles(event.dataTransfer.files)
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
          dragOver
            ? 'border-[var(--accent)] bg-[var(--accent)]/5'
            : 'border-[var(--border)] hover:border-[var(--accent)]/60'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".xlsx,.xlsm,.csv"
          className="hidden"
          onChange={(event) => handleFiles(event.target.files)}
        />
        <p className="text-sm font-medium text-[var(--text)]">
          {busy ? 'Uploading…' : 'Drop .xlsx or .csv files here, or click to browse'}
        </p>
        <p className="mt-1 text-xs text-[var(--text-muted)]">
          Uploading into: <span className="font-mono">{directory || '(root)'}</span>
        </p>
      </div>

      {results.length > 0 && (
        <ul className="mt-3 space-y-1 text-sm">
          {results.map((result) => (
            <li
              key={result.fileName}
              className={result.ok ? 'text-[var(--text-muted)]' : 'text-[var(--danger)]'}
            >
              <span className="font-medium text-[var(--text)]">{result.fileName}</span>
              {' — '}
              {result.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

import { useState } from 'react'
import type { TreeNode, FileGroup } from '../lib/tree'
import { groupByFile } from '../lib/tree'
import { UploadDropzone } from './UploadDropzone'
import { ConfirmDialog } from './ConfirmDialog'
import { deleteDirectory, deleteFile, deleteTable } from '../lib/api'

type PendingDelete =
  | { kind: 'sheet'; tableName: string; label: string }
  | { kind: 'file'; fileName: string; sheetCount: number }
  | { kind: 'folder' }

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function FileGroupCard({
  group,
  onDeleteFile,
  onDeleteSheet,
}: {
  group: FileGroup
  onDeleteFile: () => void
  onDeleteSheet: (tableName: string, label: string) => void
}) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-sm">
      <div className="flex items-start justify-between gap-2 border-b border-[var(--border)] px-4 py-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-[var(--text)]" title={group.fileName}>
            {group.fileName}
          </p>
          <p className="text-xs text-[var(--text-muted)]">
            {group.sheets.length} sheet{group.sheets.length === 1 ? '' : 's'} · updated{' '}
            {formatDate(group.updatedAt)}
          </p>
        </div>

        <div className="flex flex-shrink-0 items-center gap-2">
          <span className="rounded-full bg-[var(--accent)]/10 px-2 py-0.5 text-[10px] font-medium uppercase text-[var(--accent)]">
            {group.fileType}
          </span>
          <button
            onClick={onDeleteFile}
            className="rounded-md border border-[var(--danger)]/30 px-2 py-1 text-xs font-medium text-[var(--danger)] hover:bg-[var(--danger)]/10"
          >
            Delete file
          </button>
        </div>
      </div>

      <ul className="divide-y divide-[var(--border)]">
        {group.sheets.map((sheet) => (
          <li
            key={sheet.table_name}
            className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm"
          >
            <div className="min-w-0">
              <p className="truncate font-medium text-[var(--text)]">{sheet.sheet_name}</p>
              <p className="text-xs text-[var(--text-muted)]">
                {sheet.row_count.toLocaleString()} rows · {sheet.column_schema.length} columns
              </p>
            </div>
            <button
              onClick={() =>
                onDeleteSheet(sheet.table_name, `${group.fileName} / ${sheet.sheet_name}`)
              }
              className="flex-shrink-0 rounded-md px-2 py-1 text-xs text-[var(--text-muted)] hover:bg-[var(--danger)]/10 hover:text-[var(--danger)]"
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function DirectoryView({
  node,
  onChanged,
  onNewFolder,
}: {
  node: TreeNode
  onChanged: () => void
  onNewFolder: () => void
}) {
  const [pendingDelete, setPendingDelete] = useState<PendingDelete | null>(null)
  const fileGroups = groupByFile(node.entries)

  async function confirmDelete() {
    if (!pendingDelete) return

    if (pendingDelete.kind === 'sheet') {
      await deleteTable(pendingDelete.tableName)
    } else if (pendingDelete.kind === 'file') {
      await deleteFile(node.path, pendingDelete.fileName)
    } else {
      await deleteDirectory(node.path)
    }

    setPendingDelete(null)
    onChanged()
  }

  return (
    <div className="flex-1 overflow-y-auto px-8 py-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-[var(--text)]">
            {node.path || 'All files (root)'}
          </h1>
          <p className="text-sm text-[var(--text-muted)]">
            {fileGroups.length} file{fileGroups.length === 1 ? '' : 's'} ·{' '}
            {node.entries.length} sheet{node.entries.length === 1 ? '' : 's'} in this
            directory
          </p>
        </div>

        <div className="flex flex-shrink-0 items-center gap-2">
          <button
            onClick={onNewFolder}
            className="rounded-lg border border-[var(--accent)]/40 bg-[var(--accent)]/10 px-3 py-1.5 text-sm font-medium text-[var(--accent)] hover:bg-[var(--accent)]/20"
          >
            ＋ New subfolder
          </button>

          {node.path && (
            <button
              onClick={() => setPendingDelete({ kind: 'folder' })}
              className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--text-muted)] hover:border-[var(--danger)]/40 hover:text-[var(--danger)]"
            >
              Delete folder
            </button>
          )}
        </div>
      </div>

      <div className="mt-5">
        <UploadDropzone directory={node.path} onUploaded={onChanged} />
      </div>

      {fileGroups.length > 0 ? (
        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {fileGroups.map((group) => (
            <FileGroupCard
              key={group.fileName}
              group={group}
              onDeleteFile={() =>
                setPendingDelete({
                  kind: 'file',
                  fileName: group.fileName,
                  sheetCount: group.sheets.length,
                })
              }
              onDeleteSheet={(tableName, label) =>
                setPendingDelete({ kind: 'sheet', tableName, label })
              }
            />
          ))}
        </div>
      ) : (
        <p className="mt-8 text-sm text-[var(--text-muted)]">
          No sheets uploaded here yet.
        </p>
      )}

      {pendingDelete?.kind === 'sheet' && (
        <ConfirmDialog
          title="Delete this sheet?"
          message={`"${pendingDelete.label}" will be permanently removed from Supabase. This can't be undone.`}
          onConfirm={confirmDelete}
          onCancel={() => setPendingDelete(null)}
        />
      )}

      {pendingDelete?.kind === 'file' && (
        <ConfirmDialog
          title="Delete this file?"
          message={`All ${pendingDelete.sheetCount} sheet(s) from "${pendingDelete.fileName}" will be permanently deleted, along with the original file. This can't be undone.`}
          onConfirm={confirmDelete}
          onCancel={() => setPendingDelete(null)}
        />
      )}

      {pendingDelete?.kind === 'folder' && (
        <ConfirmDialog
          title="Delete this folder?"
          message={`All ${node.entries.length} sheet(s) directly in "${node.path}" will be permanently deleted. This can't be undone.`}
          onConfirm={confirmDelete}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </div>
  )
}

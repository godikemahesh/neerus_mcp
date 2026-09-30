import { useState } from 'react'
import type { TreeNode } from '../lib/tree'
import { countEntries } from '../lib/tree'

interface SidebarProps {
  tree: TreeNode
  selectedPath: string
  onSelect: (path: string) => void
  onNewFolder: () => void
}

function FolderRow({
  node,
  depth,
  selectedPath,
  onSelect,
}: {
  node: TreeNode
  depth: number
  selectedPath: string
  onSelect: (path: string) => void
}) {
  const [open, setOpen] = useState(true)
  const isSelected = selectedPath === node.path
  const hasChildren = node.children.length > 0

  return (
    <div>
      <button
        onClick={() => {
          onSelect(node.path)
          setOpen(true)
        }}
        style={{ paddingLeft: `${depth * 14 + 8}px` }}
        className={`flex w-full items-center gap-1.5 rounded-md py-1.5 pr-2 text-left text-sm transition ${
          isSelected
            ? 'bg-[var(--accent)]/10 text-[var(--accent)] font-medium'
            : 'text-[var(--text)] hover:bg-[var(--border)]/50'
        }`}
      >
        {hasChildren ? (
          <span
            onClick={(event) => {
              event.stopPropagation()
              setOpen((value) => !value)
            }}
            className="w-3 text-[var(--text-muted)]"
          >
            {open ? '▾' : '▸'}
          </span>
        ) : (
          <span className="w-3" />
        )}
        <span aria-hidden className="text-base leading-none">📁</span>
        <span className="truncate">{node.name}</span>
        <span className="ml-auto text-xs text-[var(--text-muted)]">
          {countEntries(node)}
        </span>
      </button>

      {open &&
        node.children.map((child) => (
          <FolderRow
            key={child.path}
            node={child}
            depth={depth + 1}
            selectedPath={selectedPath}
            onSelect={onSelect}
          />
        ))}
    </div>
  )
}

export function Sidebar({ tree, selectedPath, onSelect, onNewFolder }: SidebarProps) {
  return (
    <aside className="flex h-full w-64 flex-shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface)]">
      <div className="px-4 py-4">
        <h2 className="text-sm font-semibold text-[var(--text)]">Directories</h2>
        <button
          onClick={onNewFolder}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-[var(--accent)]/40 bg-[var(--accent)]/10 px-3 py-2 text-sm font-medium text-[var(--accent)] transition hover:bg-[var(--accent)]/20"
        >
          <span aria-hidden className="text-base leading-none">＋</span>
          New folder
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-4">
        <button
          onClick={() => onSelect('')}
          className={`mb-1 flex w-full items-center gap-1.5 rounded-md py-1.5 px-3 text-left text-sm transition ${
            selectedPath === ''
              ? 'bg-[var(--accent)]/10 text-[var(--accent)] font-medium'
              : 'text-[var(--text)] hover:bg-[var(--border)]/50'
          }`}
        >
          <span aria-hidden className="text-base leading-none">🏠</span>
          <span className="truncate">All files</span>
          <span className="ml-auto text-xs text-[var(--text-muted)]">
            {countEntries(tree)}
          </span>
        </button>

        {tree.children.map((child) => (
          <FolderRow
            key={child.path}
            node={child}
            depth={0}
            selectedPath={selectedPath}
            onSelect={onSelect}
          />
        ))}
      </div>
    </aside>
  )
}

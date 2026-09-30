import { useCallback, useEffect, useState } from 'react'
import { LoginScreen } from './components/LoginScreen'
import { Sidebar } from './components/Sidebar'
import { DirectoryView } from './components/DirectoryView'
import { NewFolderDialog } from './components/NewFolderDialog'
import { getTree, logout, me } from './lib/api'
import { buildTree, ensurePath, findNode } from './lib/tree'
import type { DirectoryTree } from './types'

type AuthState = 'checking' | 'signed-out' | 'signed-in'

function App() {
  const [auth, setAuth] = useState<AuthState>('checking')
  const [directories, setDirectories] = useState<DirectoryTree>({})
  const [selectedPath, setSelectedPath] = useState('')
  const [pendingFolders, setPendingFolders] = useState<string[]>([])
  const [showNewFolderDialog, setShowNewFolderDialog] = useState(false)

  const refresh = useCallback(() => {
    getTree()
      .then((data) => setDirectories(data.directories))
      .catch(() => setAuth('signed-out'))
  }, [])

  useEffect(() => {
    me()
      .then(() => {
        setAuth('signed-in')
        refresh()
      })
      .catch(() => setAuth('signed-out'))
  }, [refresh])

  if (auth === 'checking') {
    return <div className="min-h-screen bg-[var(--bg)]" />
  }

  if (auth === 'signed-out') {
    return (
      <LoginScreen
        onSuccess={() => {
          setAuth('signed-in')
          refresh()
        }}
      />
    )
  }

  const tree = buildTree(directories)
  pendingFolders.forEach((path) => ensurePath(tree, path))
  const selectedNode = findNode(tree, selectedPath) ?? tree

  return (
    <div className="flex h-screen bg-[var(--bg)]">
      <Sidebar
        tree={tree}
        selectedPath={selectedPath}
        onSelect={setSelectedPath}
        onNewFolder={() => setShowNewFolderDialog(true)}
      />

      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-[var(--border)] bg-[var(--surface)] px-8 py-3">
          <span className="text-sm font-semibold text-[var(--text)]">
            Neerus Data Admin
          </span>
          <button
            onClick={() => logout().then(() => setAuth('signed-out'))}
            className="text-sm text-[var(--text-muted)] hover:text-[var(--text)]"
          >
            Sign out
          </button>
        </header>

        <DirectoryView
          node={selectedNode}
          onChanged={refresh}
          onNewFolder={() => setShowNewFolderDialog(true)}
        />
      </div>

      {showNewFolderDialog && (
        <NewFolderDialog
          parentLabel={selectedNode.path || 'All files'}
          onCancel={() => setShowNewFolderDialog(false)}
          onCreate={(name) => {
            const path = selectedNode.path ? `${selectedNode.path}/${name}` : name
            setPendingFolders((paths) => [...paths, path])
            setSelectedPath(path)
            setShowNewFolderDialog(false)
          }}
        />
      )}
    </div>
  )
}

export default App

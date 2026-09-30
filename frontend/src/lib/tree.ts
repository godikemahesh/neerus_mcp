import type { CatalogEntry, DirectoryTree } from '../types'

export interface TreeNode {
  name: string
  path: string
  children: TreeNode[]
  entries: CatalogEntry[]
}

export function buildTree(directories: DirectoryTree): TreeNode {
  const root: TreeNode = { name: '', path: '', children: [], entries: [] }

  const findOrCreate = (parent: TreeNode, name: string, path: string): TreeNode => {
    let node = parent.children.find((child) => child.name === name)

    if (!node) {
      node = { name, path, children: [], entries: [] }
      parent.children.push(node)
    }

    return node
  }

  for (const [directoryPath, entries] of Object.entries(directories)) {
    if (directoryPath === '') {
      root.entries.push(...entries)
      continue
    }

    const parts = directoryPath.split('/').filter(Boolean)
    let current = root
    let accumulatedPath = ''

    for (const part of parts) {
      accumulatedPath = accumulatedPath ? `${accumulatedPath}/${part}` : part
      current = findOrCreate(current, part, accumulatedPath)
    }

    current.entries.push(...entries)
  }

  const sortRecursively = (node: TreeNode) => {
    node.children.sort((a, b) => a.name.localeCompare(b.name))
    node.entries.sort((a, b) => a.file_name.localeCompare(b.file_name))
    node.children.forEach(sortRecursively)
  }

  sortRecursively(root)

  return root
}

export function ensurePath(root: TreeNode, directoryPath: string): void {
  if (!directoryPath) return

  const parts = directoryPath.split('/').filter(Boolean)
  let current = root
  let accumulatedPath = ''

  for (const part of parts) {
    accumulatedPath = accumulatedPath ? `${accumulatedPath}/${part}` : part
    let node = current.children.find((child) => child.name === part)

    if (!node) {
      node = { name: part, path: accumulatedPath, children: [], entries: [] }
      current.children.push(node)
      current.children.sort((a, b) => a.name.localeCompare(b.name))
    }

    current = node
  }
}

export function findNode(root: TreeNode, path: string): TreeNode | null {
  if (path === root.path) return root

  const parts = path.split('/').filter(Boolean)
  let current = root

  for (const part of parts) {
    const next = current.children.find((child) => child.name === part)
    if (!next) return null
    current = next
  }

  return current
}

export interface FileGroup {
  fileName: string
  fileType: CatalogEntry['file_type']
  uploadedAt: string
  updatedAt: string
  sheets: CatalogEntry[]
}

export function groupByFile(entries: CatalogEntry[]): FileGroup[] {
  const groups = new Map<string, FileGroup>()

  for (const entry of entries) {
    let group = groups.get(entry.file_name)

    if (!group) {
      group = {
        fileName: entry.file_name,
        fileType: entry.file_type,
        uploadedAt: entry.uploaded_at,
        updatedAt: entry.updated_at,
        sheets: [],
      }
      groups.set(entry.file_name, group)
    }

    group.sheets.push(entry)

    if (entry.updated_at > group.updatedAt) {
      group.updatedAt = entry.updated_at
    }
  }

  for (const group of groups.values()) {
    group.sheets.sort((a, b) => a.sheet_name.localeCompare(b.sheet_name))
  }

  return [...groups.values()].sort((a, b) => a.fileName.localeCompare(b.fileName))
}

export function countEntries(node: TreeNode): number {
  return (
    node.entries.length +
    node.children.reduce((sum, child) => sum + countEntries(child), 0)
  )
}

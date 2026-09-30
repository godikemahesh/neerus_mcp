import type { DirectoryTree } from '../types'

const API_URL = import.meta.env.VITE_API_URL as string

class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    credentials: 'include',
    ...init,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, body.detail ?? response.statusText)
  }

  return response.json() as Promise<T>
}

export { ApiError }

export function login(password: string) {
  const form = new FormData()
  form.set('password', password)

  return request<{ ok: true }>('/api/auth/login', {
    method: 'POST',
    body: form,
  })
}

export function logout() {
  return request<{ ok: true }>('/api/auth/logout', { method: 'POST' })
}

export function me() {
  return request<{ authenticated: true }>('/api/me')
}

export function getTree() {
  return request<{ directories: DirectoryTree }>('/api/tree')
}

export function uploadFile(directory: string, file: File) {
  const form = new FormData()
  form.set('directory', directory)
  form.set('file', file)

  return request<{ created: unknown[]; skipped_empty_sheets: string[] }>(
    '/api/upload',
    { method: 'POST', body: form },
  )
}

export function deleteTable(tableName: string) {
  return request<{ ok: true }>(`/api/tables/${encodeURIComponent(tableName)}`, {
    method: 'DELETE',
  })
}

export function deleteFile(directory: string, fileName: string) {
  const params = new URLSearchParams({ directory, file_name: fileName })

  return request<{ ok: true; deleted: number }>(`/api/files?${params}`, {
    method: 'DELETE',
  })
}

export function deleteDirectory(directoryPath: string) {
  return request<{ ok: true; deleted: number }>(
    `/api/directories/${encodeURIComponent(directoryPath)}`,
    { method: 'DELETE' },
  )
}

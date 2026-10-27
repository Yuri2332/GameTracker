const API = import.meta.env.VITE_API_URL || '/api'

function csrfCookie() {
  return document.cookie.split('; ').find((part) => part.startsWith('gametracker_csrf='))?.split('=').slice(1).join('=')
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method || 'GET').toUpperCase()
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrf = csrfCookie()
    if (csrf) headers.set('X-CSRF-Token', decodeURIComponent(csrf))
  }
  const response = await fetch(`${API}${path}`, { ...init, headers, credentials: 'include' })
  if (response.status === 204) return undefined as T
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.detail || 'Não foi possível concluir a solicitação.')
  return payload as T
}

export async function ensureCsrf() {
  await api('/auth/csrf')
}

export function downloadExport(format: 'json' | 'csv') {
  window.location.href = `${API}/export?format=${format}`
}

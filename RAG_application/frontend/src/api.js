const API_BASE = '/api'

function authHeaders(extra = {}) {
  const headers = { ...extra }
  const apiKey = import.meta.env.VITE_API_KEY
  if (apiKey) {
    headers['X-API-Key'] = apiKey
  }
  const token = localStorage.getItem('rag_access_token')
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

async function request(path, options = {}) {
  const headers = authHeaders(options.headers || {})
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    throw new Error('Unauthorized — check API key or login token')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export async function createSession(title = 'New Chat') {
  return request('/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
}

export async function getMessages(sessionId) {
  return request(`/sessions/${sessionId}/messages`)
}

export async function sendMessage(sessionId, message) {
  return request('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
  })
}

export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  return request('/upload/document', { method: 'POST', body: form })
}

export async function uploadImage(file) {
  const form = new FormData()
  form.append('file', file)
  return request('/upload/image', { method: 'POST', body: form })
}

export async function listDocuments() {
  return request('/documents')
}

export async function listImages() {
  return request('/images')
}

export async function healthCheck() {
  return request('/health')
}

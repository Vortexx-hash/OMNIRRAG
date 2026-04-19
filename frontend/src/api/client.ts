import type {
  HealthResponse,
  DocumentRecord,
  UploadRequest,
  UploadResponse,
  QueryRequest,
  QueryResponse,
} from '../types/api'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<HealthResponse>('/health'),

  documents: () => request<DocumentRecord[]>('/documents'),

  upload: (body: UploadRequest) =>
    request<UploadResponse>('/upload', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  query: (body: QueryRequest) =>
    request<QueryResponse>('/query', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}

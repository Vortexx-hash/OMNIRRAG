import type {
  HealthResponse,
  DocumentRecord,
  UploadRequest,
  UploadResponse,
  QueryRequest,
  QueryResponse,
  StreamEvent,
} from '../types/api'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData
  const res = await fetch(`${BASE}${path}`, {
    // For FormData let the browser set Content-Type (includes multipart boundary)
    headers: isFormData ? {} : { 'Content-Type': 'application/json', ...init?.headers },
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

  uploadPdf: (formData: FormData) =>
    request<UploadResponse>('/upload/pdf', {
      method: 'POST',
      body: formData,
    }),

  uploadUrl: (body: {
    url: string
    doc_id: string
    source_type: string
    chunking_strategy: string
    title?: string
    author?: string
  }) =>
    request<UploadResponse>('/upload/url', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  suggestSourceType: (url: string) =>
    request<{ suggested_source_type: string }>(
      `/upload/url/suggest-source-type?url=${encodeURIComponent(url)}`
    ),

  query: (body: QueryRequest) =>
    request<QueryResponse>('/query', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  queryStream: async (
    query: string,
    onEvent: (e: StreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> => {
    const res = await fetch(`${BASE}/query/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
      signal,
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(body.detail ?? `HTTP ${res.status}`)
    }
    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() ?? ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try { onEvent(JSON.parse(line.slice(6)) as StreamEvent) } catch { /* ignore */ }
        }
      }
    }
  },
}

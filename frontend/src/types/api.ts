export interface SourceMetadata {
  source_type: string
  title?: string
  author?: string
  url?: string
  [key: string]: unknown
}

export interface UploadRequest {
  text: string
  doc_id: string
  source_metadata: SourceMetadata
  chunking_strategy?: 'semantic' | 'character' | 'overlap' | 'hybrid'
}

export interface UploadResponse {
  doc_id: string
  chunks_stored: number
  chunk_ids: string[]
}

export interface QueryRequest {
  query: string
}

export interface EvidenceSummary {
  chunk_id: string
  text_excerpt: string
  source_doc_id: string
  credibility_tier: number
  credibility_score: number
}

export interface RejectedEvidenceSummary {
  chunk_id: string
  text_excerpt: string
  source_doc_id: string
  credibility_tier: number
  conflict_type: string
}

export interface ConflictReportSummary {
  conflict_type: 'ambiguity' | 'outlier' | 'oversimplification' | 'noise'
  chunk_ids: string[]
  evidence_strength: number
  decision_case: number
  has_scope_qualifier: boolean
}

export interface AgentPositionSummary {
  agent_id: string
  chunk_id: string
  position_text: string
  confidence: number
  status: 'stable' | 'revised' | 'isolated'
  reasoning: string
}

export interface DebateSummary {
  agent_positions: AgentPositionSummary[]
  support_map: Record<string, string[]>
  isolated_agent_ids: string[]
  rounds_completed: number
}

export interface QueryResponse {
  answer: string
  decision_case: 1 | 2 | 3
  decision_label: 'ambiguity' | 'strong_winner' | 'unresolved'
  conflict_reports: ConflictReportSummary[]
  selected_evidence: EvidenceSummary[]
  rejected_evidence: RejectedEvidenceSummary[]
  sources_cited: string[]
  conflict_handling_tags: string[]
  debate_summary?: DebateSummary
}

export interface HealthResponse {
  status: string
  chunks_indexed: number
}

export interface DocumentRecord {
  doc_id: string
  title?: string
  source_type: string
  chunks_stored: number
  chunk_ids: string[]
  uploaded_at: string
}

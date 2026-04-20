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

// ── SSE streaming events ──────────────────────────────────────────────────

export interface StreamEventNormalize {
  type: 'normalize'
  data: { normalized: string; entities: Array<{text:string;label:string}>; intent: string; property: string }
}
export interface StreamEventRetrieve {
  type: 'retrieve'
  data: { count: number; chunks: Array<{id:string;excerpt:string;doc_id:string}> }
}
export interface StreamEventRelations {
  type: 'relations'
  data: { pair_count: number; contradiction_count: number; scope_diff_count: number }
}
export interface StreamEventDPP {
  type: 'dpp'
  data: { selected_count: number; dropped_count: number; drop_reasons: Record<string,string> }
}
export interface StreamEventDebateInit {
  type: 'debate_init'
  data: { agent_count: number; agents: Array<{agent_id:string;chunk_id:string;excerpt:string;doc_id:string}> }
}
export interface StreamEventDebatePositions {
  type: 'debate_positions'
  data: { round: number; label: string; positions: StreamAgentPos[]; support_map: Record<string,string[]>; isolated_ids: string[] }
}
export interface StreamEventDebateRound {
  type: 'debate_round'
  data: { round: number; label: string; positions: StreamAgentPos[]; support_map: Record<string,string[]>; isolated_ids: string[] }
}
export interface StreamEventDebateEnd {
  type: 'debate_end'
  data: { rounds_completed: number; isolated_agent_ids: string[] }
}
export interface StreamEventConflict {
  type: 'conflict'
  data: { report_count: number; reports: Array<{conflict_type:string;chunk_count:number;evidence_strength:number;has_scope_qualifier:boolean}> }
}
export interface StreamEventSynthesis {
  type: 'synthesis'
  data: { decision_case: number; decision_label: string; answer_preview: string }
}
export interface StreamEventComplete {
  type: 'complete'
  data: QueryResponse
}
export interface StreamEventError {
  type: 'error'
  data: { message: string }
}

export interface StreamAgentPos {
  agent_id: string
  chunk_id: string
  position_text: string
  confidence: number
  status: 'stable' | 'revised' | 'isolated'
  reasoning: string
}

export type StreamEvent =
  | StreamEventNormalize
  | StreamEventRetrieve
  | StreamEventRelations
  | StreamEventDPP
  | StreamEventDebateInit
  | StreamEventDebatePositions
  | StreamEventDebateRound
  | StreamEventDebateEnd
  | StreamEventConflict
  | StreamEventSynthesis
  | StreamEventComplete
  | StreamEventError

export interface DocumentRecord {
  doc_id: string
  title?: string
  source_type: string
  chunks_stored: number
  chunk_ids: string[]
  uploaded_at?: string
}

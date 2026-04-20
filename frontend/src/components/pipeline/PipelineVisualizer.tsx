import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search, Network, Layers, Target, Users, AlertCircle,
  Sparkles, ChevronDown, CheckCircle, Loader2, Brain
} from 'lucide-react'
import type { QueryResponse } from '../../types/api'
import { Badge } from '../ui/Badge'
import { DebateArena } from '../debate/DebateArena'

interface PipelineVisualizerProps {
  status: 'idle' | 'loading' | 'success' | 'error'
  result?: QueryResponse
  query?: string
}

interface StageConfig {
  id: string
  icon: React.ElementType
  label: string
  color: string
  description: string
}

const STAGES: StageConfig[] = [
  { id: 'normalize', icon: Brain,       label: 'Query Normalization',  color: '#8B5CF6', description: 'Parsing entities, intent, and normalized form' },
  { id: 'retrieve',  icon: Search,      label: 'Retrieval',            color: '#06B6D4', description: 'Cosine similarity search over vector store' },
  { id: 'relations', icon: Network,     label: 'Relation Building',    color: '#6366F1', description: 'NLI · NER · Chunk Similarity · Query Relevance' },
  { id: 'dpp',       icon: Layers,      label: 'DPP Selection',        color: '#F59E0B', description: 'Diversity-preserving conflict-cluster selection' },
  { id: 'debate',    icon: Users,       label: 'Agent Debate',         color: '#EC4899', description: 'Multi-agent debate rounds with early stop' },
  { id: 'conflict',  icon: AlertCircle, label: 'Conflict Analysis',    color: '#EF4444', description: 'Classifying conflict type and decision case' },
  { id: 'synthesis', icon: Sparkles,    label: 'Synthesis',            color: '#10B981', description: 'Generating the final conflict-aware answer' },
]

function LoadingStage({ stage, active, done }: { stage: StageConfig; active: boolean; done: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <motion.div
        className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
        style={{
          background: done ? `${stage.color}25` : active ? `${stage.color}15` : 'rgba(255,255,255,0.03)',
          border: `1px solid ${done ? stage.color + '60' : active ? stage.color + '40' : 'rgba(255,255,255,0.07)'}`,
          boxShadow: active ? `0 0 12px ${stage.color}40` : 'none',
        }}
        animate={active ? { boxShadow: [`0 0 6px ${stage.color}30`, `0 0 18px ${stage.color}60`, `0 0 6px ${stage.color}30`] } : {}}
        transition={{ duration: 1.2, repeat: Infinity }}
      >
        {done
          ? <CheckCircle size={12} style={{ color: stage.color }} />
          : active
          ? <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
              <Loader2 size={12} style={{ color: stage.color }} />
            </motion.div>
          : <stage.icon size={12} className="text-slate-600" />
        }
      </motion.div>
      <div className="flex-1 min-w-0">
        <p className={`text-xs font-medium ${done ? 'text-slate-300' : active ? 'text-white' : 'text-slate-600'}`}>
          {stage.label}
        </p>
        {active && (
          <motion.p
            className="text-[10px] text-slate-500 truncate"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {stage.description}
          </motion.p>
        )}
      </div>
      {active && (
        <div className="w-16 h-1 bg-white/5 rounded-full overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ background: `linear-gradient(90deg, ${stage.color}, ${stage.color}80)` }}
            animate={{ width: ['0%', '100%'] }}
            transition={{ duration: 2.5, ease: 'easeInOut', repeat: Infinity }}
          />
        </div>
      )}
    </div>
  )
}

function NormalizeDetail({ result }: { result: QueryResponse }) {
  return (
    <div className="space-y-2 text-xs">
      <p className="text-slate-500">Normalized query extracted entities and intent</p>
      {result.conflict_handling_tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {result.conflict_handling_tags.map(tag => (
            <Badge key={tag} variant="violet" size="sm">{tag}</Badge>
          ))}
        </div>
      )}
    </div>
  )
}

function RetrieveDetail({ result }: { result: QueryResponse }) {
  const total = result.selected_evidence.length + result.rejected_evidence.length
  return (
    <div className="flex items-center gap-4 text-xs">
      <div className="text-center">
        <p className="text-xl font-bold font-mono text-cyan-400">{total}</p>
        <p className="text-slate-500">chunks retrieved</p>
      </div>
      <div className="h-10 w-px bg-white/10" />
      <div className="space-y-1">
        <p className="text-slate-400">
          <span className="font-mono text-emerald-400 font-semibold">{result.selected_evidence.length}</span> selected
        </p>
        <p className="text-slate-400">
          <span className="font-mono text-red-400 font-semibold">{result.rejected_evidence.length}</span> rejected
        </p>
      </div>
    </div>
  )
}

function RelationsDetail({ result }: { result: QueryResponse }) {
  const tasks = [
    { label: 'Query Relevance',   color: '#8B5CF6', value: `${result.selected_evidence.length} scored` },
    { label: 'Chunk Similarity',  color: '#06B6D4', value: 'N×N matrix' },
    { label: 'NLI Classification', color: '#6366F1', value: `${result.conflict_reports.length} pairs` },
    { label: 'NER Extraction',    color: '#F59E0B', value: 'entities + qualifiers' },
  ]
  return (
    <div className="grid grid-cols-2 gap-2">
      {tasks.map(t => (
        <div key={t.label} className="flex items-center gap-2 rounded-lg bg-white/3 px-2.5 py-2">
          <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: t.color }} />
          <div>
            <p className="text-[10px] text-slate-400">{t.label}</p>
            <p className="text-[11px] font-mono" style={{ color: t.color }}>{t.value}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

function DPPDetail({ result }: { result: QueryResponse }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 text-xs">
        <div className="flex-1 space-y-1">
          <div className="flex justify-between">
            <span className="text-slate-500">Selected</span>
            <span className="font-mono text-emerald-400 font-semibold">{result.selected_evidence.length}</span>
          </div>
          <div className="h-2 bg-white/5 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-emerald-600 to-emerald-500 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${(result.selected_evidence.length / (result.selected_evidence.length + result.rejected_evidence.length)) * 100}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
          </div>
        </div>
        <div className="flex-1 space-y-1">
          <div className="flex justify-between">
            <span className="text-slate-500">Rejected</span>
            <span className="font-mono text-red-400 font-semibold">{result.rejected_evidence.length}</span>
          </div>
          <div className="h-2 bg-white/5 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-red-700 to-red-600 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${(result.rejected_evidence.length / (result.selected_evidence.length + result.rejected_evidence.length)) * 100}%` }}
              transition={{ duration: 0.8, ease: 'easeOut', delay: 0.2 }}
            />
          </div>
        </div>
      </div>
      <p className="text-[10px] text-slate-500">Diversity + conflict-cluster preservation enforced</p>
    </div>
  )
}

function ConflictDetail({ result }: { result: QueryResponse }) {
  const types = result.conflict_reports.reduce<Record<string, number>>((acc, r) => {
    acc[r.conflict_type] = (acc[r.conflict_type] ?? 0) + 1
    return acc
  }, {})
  return (
    <div className="space-y-2">
      {Object.entries(types).map(([type, count]) => (
        <div key={type} className="flex items-center justify-between text-xs">
          <span className="text-slate-400 capitalize">{type}</span>
          <span className="font-mono font-semibold text-red-400">{count}×</span>
        </div>
      ))}
      {Object.keys(types).length === 0 && (
        <p className="text-xs text-slate-500">No conflicts detected</p>
      )}
    </div>
  )
}

function SynthesisDetail({ result }: { result: QueryResponse }) {
  const caseColor: Record<string, string> = {
    ambiguity:     'text-amber-400',
    strong_winner: 'text-emerald-400',
    unresolved:    'text-red-400',
  }
  return (
    <div className="space-y-2 text-xs">
      <div className="flex items-center gap-2">
        <span className="text-slate-500">Decision:</span>
        <span className={`font-semibold capitalize ${caseColor[result.decision_label] ?? 'text-slate-300'}`}>
          Case {result.decision_case} — {result.decision_label.replace('_', ' ')}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-slate-500">Sources cited:</span>
        <span className="font-mono font-semibold text-emerald-400">{result.sources_cited.length}</span>
      </div>
    </div>
  )
}

function StageRow({
  stage,
  result,
  visible,
  expanded,
  onToggle,
}: {
  stage: StageConfig
  result: QueryResponse
  visible: boolean
  expanded: boolean
  onToggle: () => void
}) {
  const renderDetail = () => {
    switch (stage.id) {
      case 'normalize': return <NormalizeDetail result={result} />
      case 'retrieve':  return <RetrieveDetail result={result} />
      case 'relations': return <RelationsDetail result={result} />
      case 'dpp':       return <DPPDetail result={result} />
      case 'debate':    return result.debate_summary
        ? <DebateArena debate={result.debate_summary} visible={visible && expanded} />
        : <p className="text-xs text-slate-500">Debate data not available</p>
      case 'conflict':  return <ConflictDetail result={result} />
      case 'synthesis': return <SynthesisDetail result={result} />
      default:          return null
    }
  }

  return (
    <motion.div
      className="rounded-xl overflow-hidden"
      style={{ border: `1px solid ${stage.color}20` }}
      initial={{ opacity: 0, x: -16 }}
      animate={visible ? { opacity: 1, x: 0 } : { opacity: 0, x: -16 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
    >
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/2 transition-colors"
        style={{ background: `${stage.color}06` }}
      >
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: `${stage.color}20`, border: `1px solid ${stage.color}50` }}
        >
          <stage.icon size={13} style={{ color: stage.color }} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-200">{stage.label}</p>
          <p className="text-[10px] text-slate-500">{stage.description}</p>
        </div>
        <div className="flex items-center gap-2">
          <CheckCircle size={13} style={{ color: stage.color }} />
          <motion.div animate={{ rotate: expanded ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <ChevronDown size={14} className="text-slate-500" />
          </motion.div>
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            className="px-4 py-3 border-t"
            style={{ borderColor: `${stage.color}15` }}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            {renderDetail()}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function PipelineVisualizer({ status, result, query }: PipelineVisualizerProps) {
  const [visibleCount, setVisibleCount] = useState(0)
  const [expanded, setExpanded] = useState<string | null>('debate')
  const [activeLoading, setActiveLoading] = useState(0)

  // Loading animation: cycle through stages while waiting
  useEffect(() => {
    if (status !== 'loading') return
    setVisibleCount(0)
    setActiveLoading(0)
    const id = setInterval(() => {
      setActiveLoading(n => (n + 1) % STAGES.length)
    }, 800)
    return () => clearInterval(id)
  }, [status])

  // Result replay: reveal stages one by one
  useEffect(() => {
    if (status !== 'success' || !result) return
    const delays = [0, 300, 700, 1200, 1800, 2500, 3100]
    const timers = delays.map((d, i) => setTimeout(() => setVisibleCount(i + 1), d))
    return () => timers.forEach(clearTimeout)
  }, [status, result])

  if (status === 'idle') return null

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 mb-4">
        <div className="h-px flex-1 bg-gradient-to-r from-transparent via-violet-500/30 to-transparent" />
        <span className="text-xs font-medium text-violet-400 flex items-center gap-1.5">
          <Target size={12} />
          Pipeline Execution
        </span>
        <div className="h-px flex-1 bg-gradient-to-r from-transparent via-violet-500/30 to-transparent" />
      </div>

      {/* Loading state */}
      {status === 'loading' && (
        <div className="glass rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-3 mb-2">
            <motion.div
              className="w-5 h-5 rounded-full border-2 border-t-violet-500 border-violet-500/20"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            />
            <p className="text-sm text-slate-300 font-medium">Running conflict-aware pipeline…</p>
            {query && <span className="text-xs text-slate-500 italic truncate max-w-xs">"{query}"</span>}
          </div>
          {STAGES.map((stage, i) => (
            <LoadingStage
              key={stage.id}
              stage={stage}
              active={i === activeLoading}
              done={i < activeLoading}
            />
          ))}
        </div>
      )}

      {/* Success: staged reveal */}
      {status === 'success' && result && (
        <div className="space-y-2">
          {STAGES.map((stage, i) => (
            <StageRow
              key={stage.id}
              stage={stage}
              result={result}
              visible={visibleCount > i}
              expanded={expanded === stage.id}
              onToggle={() => setExpanded(expanded === stage.id ? null : stage.id)}
            />
          ))}
        </div>
      )}

      {status === 'error' && (
        <div className="glass rounded-xl p-5 flex items-center gap-3 border border-red-500/20">
          <AlertCircle size={18} className="text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-300">Pipeline execution failed. Check the backend logs.</p>
        </div>
      )}
    </div>
  )
}

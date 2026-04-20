import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Brain, Search, Network, Layers, Users, AlertCircle,
  Sparkles, CheckCircle, Loader2, Quote, Shield
} from 'lucide-react'
import type {
  StreamEvent, StreamAgentPos, QueryResponse
} from '../../types/api'
import { api } from '../../api/client'
import { DecisionBadge } from '../ui/Badge'

interface QueryModalProps {
  query: string
  onClose: () => void
  onComplete: (result: QueryResponse) => void
}

// ── Stage config ─────────────────────────────────────────────────────────────

const STAGE_ORDER = ['normalize','retrieve','relations','dpp','debate','conflict','synthesis'] as const
type StageName = typeof STAGE_ORDER[number]

const STAGE_CFG: Record<StageName, { icon: React.ElementType; label: string; color: string }> = {
  normalize:  { icon: Brain,        label: 'Query Normalization',  color: '#8B5CF6' },
  retrieve:   { icon: Search,       label: 'Retrieval',            color: '#06B6D4' },
  relations:  { icon: Network,      label: 'Relation Building',    color: '#6366F1' },
  dpp:        { icon: Layers,       label: 'DPP Selection',        color: '#F59E0B' },
  debate:     { icon: Users,        label: 'Agent Debate',         color: '#EC4899' },
  conflict:   { icon: AlertCircle,  label: 'Conflict Analysis',    color: '#EF4444' },
  synthesis:  { icon: Sparkles,     label: 'Synthesis',            color: '#10B981' },
}

// ── Agent status ─────────────────────────────────────────────────────────────

const STATUS_CFG = {
  stable:   { color: '#10B981', label: 'Stable'   },
  revised:  { color: '#F59E0B', label: 'Revised'  },
  isolated: { color: '#EF4444', label: 'Isolated' },
}

// ── Live debate arena ─────────────────────────────────────────────────────────

function LiveDebateArena({
  positions,
  supportMap,
  isolatedIds,
  roundLabel,
  agentCount,
}: {
  positions: StreamAgentPos[]
  supportMap: Record<string, string[]>
  isolatedIds: string[]
  roundLabel: string
  agentCount: number
}) {
  // Show ALL agents in the arena — active ones prominent, isolated ones dimmed
  const allAgents = positions.length > 0 ? positions : []
  const activeAgents = allAgents.filter(p => !isolatedIds.includes(p.agent_id))

  // Scale radius to fit more agents without overlap
  const size = 300
  const cx = size / 2, cy = size / 2
  const r = allAgents.length <= 5 ? 100 : allAgents.length <= 8 ? 110 : 118

  const getPos = (i: number, total: number) => {
    const angle = total === 1 ? -Math.PI / 2 : (2 * Math.PI * i) / total - Math.PI / 2
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) }
  }

  // Build connection pairs from support map (active agents only)
  const connections: Array<[number,number,string]> = []
  Object.entries(supportMap).forEach(([, ids]) => {
    if (ids.length < 2) return
    for (let i = 0; i < ids.length - 1; i++)
      for (let j = i + 1; j < ids.length; j++) {
        const ai = allAgents.findIndex(p => p.agent_id === ids[i])
        const bi = allAgents.findIndex(p => p.agent_id === ids[j])
        if (ai >= 0 && bi >= 0) connections.push([ai, bi, ids[i]+ids[j]])
      }
  })

  return (
    <div className="relative flex flex-col items-center gap-3 py-2">
      <div className="flex items-center gap-2 text-xs">
        <motion.div className="w-1.5 h-1.5 rounded-full bg-pink-400" animate={{ opacity:[1,0.3,1] }} transition={{ duration:1, repeat:Infinity }} />
        <span className="text-pink-400 font-medium">{roundLabel}</span>
        <span className="text-slate-600">·</span>
        <span className="text-slate-500">{agentCount} agents</span>
        {activeAgents.length === 0 && allAgents.length > 0 && (
          <span className="text-red-400/70 text-[10px]">· all isolated</span>
        )}
      </div>

      <div className="relative" style={{ width: size, height: size }}>
        {/* Background grid */}
        <svg className="absolute inset-0 opacity-[0.04]" width={size} height={size}>
          {[1,2,3,4].map(i=><circle key={i} cx={cx} cy={cy} r={i*26} fill="none" stroke="#EC4899" strokeWidth="0.5"/>)}
        </svg>

        {/* Connection lines */}
        <svg className="absolute inset-0" width={size} height={size}>
          <defs>
            <linearGradient id="connGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.7"/>
              <stop offset="100%" stopColor="#06B6D4" stopOpacity="0.7"/>
            </linearGradient>
          </defs>
          {connections.map(([ai, bi, key]) => {
            const pa = getPos(ai, allAgents.length)
            const pb = getPos(bi, allAgents.length)
            const len = Math.hypot(pb.x - pa.x, pb.y - pa.y)
            return (
              <motion.line
                key={key} x1={pa.x} y1={pa.y} x2={pb.x} y2={pb.y}
                stroke="url(#connGrad)" strokeWidth="1.5" strokeLinecap="round"
                strokeDasharray={len}
                initial={{ strokeDashoffset: len, opacity: 0 }}
                animate={{ strokeDashoffset: 0, opacity: 0.8 }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
              />
            )
          })}
        </svg>

        {/* Center pulse */}
        <motion.div
          className="absolute rounded-full"
          style={{ left: cx-20, top: cy-20, width:40, height:40, background:'radial-gradient(circle, rgba(236,72,153,0.15) 0%, transparent 70%)' }}
          animate={{ scale:[1,1.4,1], opacity:[0.4,0.9,0.4] }}
          transition={{ duration:2.5, repeat:Infinity }}
        />
        <div className="absolute flex items-center justify-center" style={{ left:cx-8, top:cy-8, width:16, height:16 }}>
          <Shield size={12} className="text-pink-500/40" />
        </div>

        {/* All agents in circle */}
        {allAgents.map((agent, i) => {
          const isIsolated = isolatedIds.includes(agent.agent_id)
          const pos = getPos(i, allAgents.length)
          const cfg = isIsolated ? STATUS_CFG.isolated : (STATUS_CFG[agent.status] ?? STATUS_CFG.stable)
          const shortId = agent.agent_id.slice(-4).toUpperCase()
          const opacity = isIsolated ? 0.45 : 1
          return (
            <motion.div
              key={agent.agent_id}
              className="absolute flex flex-col items-center gap-0.5 group"
              style={{ left: pos.x - 22, top: pos.y - 22, width: 44, opacity }}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity }}
              transition={{ type: 'spring', stiffness: 350, damping: 22, delay: i * 0.05 }}
            >
              <motion.div
                className="w-11 h-11 rounded-xl flex flex-col items-center justify-center cursor-help relative"
                style={{
                  background: `${cfg.color}18`,
                  border: `1.5px solid ${cfg.color}${isIsolated ? '35' : '50'}`,
                  boxShadow: `0 0 ${isIsolated ? '6' : '12'}px ${cfg.color}${isIsolated ? '25' : '40'}`,
                }}
                animate={isIsolated ? {} : {
                  boxShadow: [`0 0 8px ${cfg.color}30`, `0 0 22px ${cfg.color}70`, `0 0 8px ${cfg.color}30`]
                }}
                transition={{ duration: 2, repeat: Infinity, delay: i * 0.2 }}
              >
                {/* Confidence arc */}
                <svg className="absolute inset-0 -rotate-90" viewBox="0 0 44 44" width="44" height="44">
                  <circle cx="22" cy="22" r="19" fill="none" stroke={`${cfg.color}15`} strokeWidth="2"/>
                  <motion.circle
                    cx="22" cy="22" r="19" fill="none" stroke={cfg.color} strokeWidth="2" strokeLinecap="round"
                    strokeDasharray={`${2*Math.PI*19}`}
                    initial={{ strokeDashoffset: 2*Math.PI*19 }}
                    animate={{ strokeDashoffset: 2*Math.PI*19*(1-agent.confidence) }}
                    transition={{ duration: 0.8, ease:'easeOut' }}
                  />
                </svg>
                <span className="text-[9px] font-mono font-bold" style={{ color: cfg.color }}>{shortId}</span>
                <span className="text-[7px] font-mono" style={{ color: cfg.color }}>{Math.round(agent.confidence*100)}%</span>

                {/* Tooltip */}
                <div className="absolute z-50 bottom-full mb-2 left-1/2 -translate-x-1/2 hidden group-hover:block w-52">
                  <div className="glass border border-white/10 rounded-xl p-2.5 text-left shadow-2xl">
                    <p className="text-[9px] font-mono text-slate-500 mb-1">{agent.chunk_id.slice(-14)}</p>
                    <p className="text-[10px] text-slate-300 leading-relaxed line-clamp-3">{agent.position_text}</p>
                    {agent.reasoning && <p className="text-[9px] text-slate-500 italic mt-1 line-clamp-2">{agent.reasoning}</p>}
                  </div>
                </div>
              </motion.div>
              <span className="text-[8px]" style={{ color: cfg.color }}>{cfg.label}</span>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

// ── Stage row ─────────────────────────────────────────────────────────────────

function StageRow({
  stage, status, data
}: {
  stage: StageName
  status: 'waiting' | 'running' | 'done'
  data?: Record<string, unknown>
}) {
  const cfg = STAGE_CFG[stage]
  const Icon = cfg.icon

  const renderDetail = () => {
    if (!data || status !== 'done') return null
    switch (stage) {
      case 'normalize': return (
        <div className="space-y-1.5 text-xs">
          <p className="text-slate-400 font-mono">{String(data.normalized ?? '')}</p>
          {Array.isArray(data.entities) && data.entities.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {(data.entities as Array<{text:string;label:string}>).slice(0,6).map((e,i)=>(
                <span key={i} className="px-1.5 py-0.5 rounded font-mono text-[10px]"
                  style={{ background:`${cfg.color}15`, color:cfg.color, border:`1px solid ${cfg.color}30`}}>
                  {e.text} <span className="opacity-50">{e.label}</span>
                </span>
              ))}
            </div>
          )}
          {data.intent != null && <p className="text-slate-500 text-[10px]">Intent: <span className="text-slate-300">{String(data.intent)}</span></p>}
        </div>
      )
      case 'retrieve': return (
        <div className="flex items-center gap-4 text-xs">
          <p className="text-2xl font-bold font-mono" style={{ color: cfg.color }}>{String(data.count)}</p>
          <p className="text-slate-500">chunks retrieved from vector store</p>
        </div>
      )
      case 'relations': return (
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'Total pairs',     value: data.pair_count,          color: cfg.color },
            { label: 'Contradictions',  value: data.contradiction_count, color: '#EF4444' },
            { label: 'Scope diffs',     value: data.scope_diff_count,    color: '#06B6D4' },
          ].map(s => (
            <div key={s.label} className="text-center py-2 rounded-lg bg-white/3 border border-white/5">
              <p className="text-lg font-mono font-bold" style={{ color: s.color }}>{String(s.value)}</p>
              <p className="text-[9px] text-slate-500">{s.label}</p>
            </div>
          ))}
        </div>
      )
      case 'dpp': return (
        <div className="flex items-center gap-4 text-xs">
          <span className="text-emerald-400 font-mono font-bold text-lg">{String(data.selected_count)}</span>
          <span className="text-slate-500">selected</span>
          <span className="text-slate-700">·</span>
          <span className="text-red-400 font-mono font-bold text-lg">{String(data.dropped_count)}</span>
          <span className="text-slate-500">dropped</span>
        </div>
      )
      case 'conflict': {
        const reports = data.reports as Array<{conflict_type:string;chunk_count:number;evidence_strength:number}> ?? []
        const CCOLORS: Record<string,string> = { ambiguity:'#F59E0B', outlier:'#EF4444', oversimplification:'#8B5CF6', noise:'#64748B' }
        return (
          <div className="space-y-1.5">
            {reports.length === 0
              ? <p className="text-xs text-emerald-400">No conflicts detected</p>
              : reports.map((r,i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span className="w-2 h-2 rounded-full" style={{ background: CCOLORS[r.conflict_type]??'#64748B'}} />
                  <span className="text-slate-300 capitalize">{r.conflict_type}</span>
                  <span className="text-slate-500">·</span>
                  <span className="font-mono" style={{ color: CCOLORS[r.conflict_type]??'#64748B' }}>
                    {Math.round(r.evidence_strength*100)}% strength
                  </span>
                </div>
              ))
            }
          </div>
        )
      }
      case 'synthesis': return (
        <div className="space-y-1 text-xs">
          <p className="text-slate-400 italic line-clamp-2">{String(data.answer_preview ?? '')}…</p>
        </div>
      )
      default: return null
    }
  }

  return (
    <motion.div
      className="flex gap-3"
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Icon column */}
      <div className="flex flex-col items-center gap-1 pt-0.5">
        <motion.div
          className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{
            background: status === 'waiting' ? 'rgba(255,255,255,0.03)' : `${cfg.color}18`,
            border: `1px solid ${status === 'waiting' ? 'rgba(255,255,255,0.06)' : `${cfg.color}40`}`,
            boxShadow: status === 'running' ? `0 0 14px ${cfg.color}50` : 'none',
          }}
          animate={status === 'running' ? { boxShadow: [`0 0 6px ${cfg.color}30`, `0 0 20px ${cfg.color}70`, `0 0 6px ${cfg.color}30`] } : {}}
          transition={{ duration: 1, repeat: Infinity }}
        >
          {status === 'done'
            ? <CheckCircle size={12} style={{ color: cfg.color }} />
            : status === 'running'
            ? <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
                <Loader2 size={12} style={{ color: cfg.color }} />
              </motion.div>
            : <Icon size={12} className="text-slate-700" />
          }
        </motion.div>
        {/* connector */}
        <div className="w-px flex-1 min-h-3" style={{ background: status !== 'waiting' ? `${cfg.color}25` : 'rgba(255,255,255,0.05)' }} />
      </div>

      {/* Content */}
      <div className="flex-1 pb-4 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-xs font-semibold ${status === 'waiting' ? 'text-slate-600' : 'text-slate-200'}`}>
            {cfg.label}
          </span>
          {status === 'running' && (
            <motion.span className="text-[10px] text-slate-500" animate={{ opacity:[0.4,1,0.4] }} transition={{ duration:1, repeat:Infinity }}>
              processing…
            </motion.span>
          )}
        </div>

        {/* Debate arena */}
        {stage === 'debate' && status !== 'waiting' && data && (
          <LiveDebateArena
            positions={(data.positions as StreamAgentPos[]) ?? []}
            supportMap={(data.support_map as Record<string,string[]>) ?? {}}
            isolatedIds={(data.isolated_ids as string[]) ?? []}
            roundLabel={String(data.label ?? 'Debate')}
            agentCount={Number(data.agent_count ?? 0)}
          />
        )}

        {/* Other stages detail */}
        {stage !== 'debate' && status === 'done' && data && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg px-3 py-2.5 text-xs"
            style={{ background: `${cfg.color}08`, border: `1px solid ${cfg.color}18` }}
          >
            {renderDetail()}
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}

// ── Main modal ────────────────────────────────────────────────────────────────

export function QueryModal({ query, onClose, onComplete }: QueryModalProps) {
  const [stageStatus, setStageStatus] = useState<Record<string, 'waiting'|'running'|'done'>>({
    normalize:'waiting', retrieve:'waiting', relations:'waiting',
    dpp:'waiting', debate:'waiting', conflict:'waiting', synthesis:'waiting',
  })
  const [stageData, setStageData] = useState<Record<string, Record<string, unknown>>>({})
  const [debateData, setDebateData] = useState<{
    positions: StreamAgentPos[]; support_map: Record<string,string[]>
    isolated_ids: string[]; label: string; agent_count: number
  } | null>(null)
  const [result, setResult] = useState<QueryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeStage, setActiveStage] = useState<StageName | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Map SSE event types to stage names
  const EVENT_TO_STAGE: Record<string, StageName> = {
    normalize: 'normalize', retrieve: 'retrieve', relations: 'relations',
    dpp: 'dpp', debate_init: 'debate', debate_positions: 'debate',
    debate_round: 'debate', debate_end: 'debate', conflict: 'conflict', synthesis: 'synthesis',
  }

  function markDone(stage: StageName) {
    setStageStatus(s => ({ ...s, [stage]: 'done' }))
  }
  function markRunning(stage: StageName) {
    setActiveStage(stage)
    setStageStatus(s => {
      const next = { ...s }
      // Mark previous stages done
      let found = false
      for (const name of STAGE_ORDER) {
        if (name === stage) { found = true; next[name] = 'running'; break }
        if (!found && next[name] === 'waiting') next[name] = 'done'
      }
      return next
    })
  }

  useEffect(() => {
    const ctrl = new AbortController()
    abortRef.current = ctrl

    // Set first stage running
    markRunning('normalize')

    api.queryStream(query, (event) => {
      const stage = EVENT_TO_STAGE[event.type]

      if (stage && stageStatus[stage] !== 'done') markRunning(stage)

      switch (event.type) {
        case 'normalize':
          setStageData(d => ({ ...d, normalize: event.data as Record<string,unknown> }))
          markDone('normalize')
          markRunning('retrieve')
          break
        case 'retrieve':
          setStageData(d => ({ ...d, retrieve: event.data as Record<string,unknown> }))
          markDone('retrieve')
          markRunning('relations')
          break
        case 'relations':
          setStageData(d => ({ ...d, relations: event.data as Record<string,unknown> }))
          markDone('relations')
          markRunning('dpp')
          break
        case 'dpp':
          setStageData(d => ({ ...d, dpp: event.data as Record<string,unknown> }))
          markDone('dpp')
          markRunning('debate')
          break
        case 'debate_init':
          setDebateData({ positions:[], support_map:{}, isolated_ids:[], label:'Initialising agents', agent_count: event.data.agent_count })
          break
        case 'debate_positions':
          setDebateData({ positions: event.data.positions, support_map: event.data.support_map, isolated_ids: event.data.isolated_ids, label: event.data.label, agent_count: event.data.positions.length })
          break
        case 'debate_round':
          setDebateData({ positions: event.data.positions, support_map: event.data.support_map, isolated_ids: event.data.isolated_ids, label: event.data.label, agent_count: event.data.positions.length })
          break
        case 'debate_end':
          markDone('debate')
          markRunning('conflict')
          break
        case 'conflict':
          setStageData(d => ({ ...d, conflict: event.data as Record<string,unknown> }))
          markDone('conflict')
          markRunning('synthesis')
          break
        case 'synthesis':
          setStageData(d => ({ ...d, synthesis: event.data as Record<string,unknown> }))
          markDone('synthesis')
          break
        case 'complete':
          setResult(event.data)
          setStageStatus({ normalize:'done',retrieve:'done',relations:'done',dpp:'done',debate:'done',conflict:'done',synthesis:'done' })
          break
        case 'error':
          setError(event.data.message)
          break
      }

      // Auto-scroll
      setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior:'smooth' }), 50)
    }, ctrl.signal).catch(e => {
      if (e?.name !== 'AbortError') setError(e?.message ?? 'Stream failed')
    })

    return () => ctrl.abort()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-start justify-center pt-8 px-4 pb-4"
      style={{ background: 'rgba(4,4,13,0.92)', backdropFilter: 'blur(12px)' }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
      onClick={e => { if (e.target === e.currentTarget) { if (result) onComplete(result); onClose() } }}
    >
      <motion.div
        className="w-full max-w-2xl glass rounded-2xl overflow-hidden flex flex-col"
        style={{ maxHeight: 'calc(100vh - 4rem)', border: '1px solid rgba(139,92,246,0.2)', boxShadow: '0 0 60px rgba(139,92,246,0.15)' }}
        initial={{ scale: 0.95, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: 20 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
      >
        {/* Header */}
        <div className="flex items-start gap-3 px-5 py-4 border-b border-violet-900/25 flex-shrink-0">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              {!result && !error ? (
                <motion.div className="w-1.5 h-1.5 rounded-full bg-violet-400" animate={{ opacity:[1,0.3,1] }} transition={{ duration:1, repeat:Infinity }} />
              ) : result ? (
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              ) : (
                <div className="w-1.5 h-1.5 rounded-full bg-red-400" />
              )}
              <span className="text-xs font-semibold text-violet-400 tracking-wide uppercase">
                {result ? 'Pipeline Complete' : error ? 'Pipeline Error' : 'Live Pipeline Execution'}
              </span>
            </div>
            <div className="flex items-start gap-2">
              <Quote size={11} className="text-slate-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-slate-300 leading-snug line-clamp-2">{query}</p>
            </div>
          </div>
          <button
            onClick={() => { if (result) onComplete(result); onClose() }}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-500 hover:text-slate-300 hover:bg-white/8 transition-all flex-shrink-0"
          >
            <X size={14} />
          </button>
        </div>

        {/* Scrollable pipeline content */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-5">
          {STAGE_ORDER.map(stage => (
            <StageRow
              key={stage}
              stage={stage}
              status={stageStatus[stage] ?? 'waiting'}
              data={stage === 'debate' && debateData
                ? { ...debateData } as Record<string,unknown>
                : stageData[stage]}
            />
          ))}

          {/* Error */}
          {error && (
            <motion.div
              className="flex items-center gap-3 p-4 rounded-xl border border-red-500/25 bg-red-500/5 mt-2"
              initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }}
            >
              <AlertCircle size={16} className="text-red-400 flex-shrink-0" />
              <p className="text-sm text-red-300">{error}</p>
            </motion.div>
          )}
        </div>

        {/* Footer — final answer preview + CTA */}
        <AnimatePresence>
          {result && (
            <motion.div
              className="border-t border-violet-900/25 px-5 py-4 space-y-3 flex-shrink-0"
              style={{ background: 'rgba(139,92,246,0.04)' }}
              initial={{ opacity:0, y:12 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0 }}
              transition={{ duration:0.4 }}
            >
              <div className="flex items-center gap-2 flex-wrap">
                <Sparkles size={13} className="text-violet-400" />
                <span className="text-xs font-semibold text-slate-300">Final Answer</span>
                <DecisionBadge label={result.decision_label} />
              </div>
              <p className="text-sm text-slate-200 leading-relaxed line-clamp-3">{result.answer}</p>
              <div className="flex items-center gap-3">
                <motion.button
                  onClick={() => { onComplete(result); onClose() }}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gradient-to-r from-violet-700 to-violet-600 hover:from-violet-600 hover:to-violet-500 text-white text-sm font-medium shadow-glow-violet transition-all"
                  whileTap={{ scale: 0.98 }}
                >
                  <Sparkles size={14} />
                  View Full Results
                </motion.button>
                <button
                  onClick={() => { onComplete(result); onClose() }}
                  className="px-4 py-2.5 rounded-xl border border-white/10 text-slate-400 text-sm hover:text-slate-200 hover:bg-white/5 transition-all"
                >
                  Dismiss
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  )
}

import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MessageSquare, Shield, AlertTriangle, Users } from 'lucide-react'
import type { DebateSummary, AgentPositionSummary } from '../../types/api'

interface DebateArenaProps {
  debate: DebateSummary
  visible: boolean
}

const STATUS_CONFIG = {
  stable:   { color: '#10B981', border: '#10B981', label: 'Stable',   glow: 'rgba(16,185,129,0.4)'  },
  revised:  { color: '#F59E0B', border: '#F59E0B', label: 'Revised',  glow: 'rgba(245,158,11,0.4)'  },
  isolated: { color: '#EF4444', border: '#EF4444', label: 'Isolated', glow: 'rgba(239,68,68,0.4)'   },
}

function agentPosition(index: number, total: number, radius: number) {
  const angle = total === 1
    ? -Math.PI / 2
    : (2 * Math.PI * index) / total - Math.PI / 2
  return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius }
}

function AgentNode({
  agent,
  index,
  total,
  cx,
  cy,
  radius,
  isIsolated,
  visible,
}: {
  agent: AgentPositionSummary
  index: number
  total: number
  cx: number
  cy: number
  radius: number
  isIsolated: boolean
  visible: boolean
}) {
  const [hovered, setHovered] = useState(false)
  const pos = agentPosition(index, total, radius)
  const cfg = STATUS_CONFIG[agent.status] ?? STATUS_CONFIG.stable
  const shortId = agent.agent_id.slice(-4).toUpperCase()

  return (
    <motion.div
      className="absolute flex flex-col items-center gap-1"
      style={{
        left: cx + pos.x - 40,
        top:  cy + pos.y - 40,
        width: 80,
        zIndex: hovered ? 20 : 10,
      }}
      initial={{ scale: 0, opacity: 0 }}
      animate={visible ? { scale: 1, opacity: isIsolated ? 0.6 : 1 } : { scale: 0, opacity: 0 }}
      transition={{ type: 'spring', stiffness: 350, damping: 25, delay: index * 0.12 }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Node circle */}
      <motion.div
        className="w-14 h-14 rounded-xl flex flex-col items-center justify-center cursor-pointer relative"
        style={{
          background: `${cfg.color}15`,
          border: `1.5px solid ${cfg.border}50`,
          boxShadow: hovered ? `0 0 20px ${cfg.glow}` : `0 0 8px ${cfg.glow}50`,
        }}
        animate={agent.status === 'stable' ? {
          boxShadow: [`0 0 8px ${cfg.glow}30`, `0 0 20px ${cfg.glow}`, `0 0 8px ${cfg.glow}30`],
        } : {}}
        transition={{ duration: 2.5, repeat: Infinity, delay: index * 0.3 }}
      >
        {/* Confidence ring */}
        <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 56 56">
          <circle cx="28" cy="28" r="24" fill="none" stroke={`${cfg.color}15`} strokeWidth="2" />
          <motion.circle
            cx="28" cy="28" r="24"
            fill="none"
            stroke={cfg.color}
            strokeWidth="2"
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 24}`}
            initial={{ strokeDashoffset: 2 * Math.PI * 24 }}
            animate={visible ? { strokeDashoffset: 2 * Math.PI * 24 * (1 - agent.confidence) } : {}}
            transition={{ duration: 1, ease: 'easeOut', delay: index * 0.12 + 0.4 }}
          />
        </svg>

        <span className="font-mono text-[10px] font-bold" style={{ color: cfg.color }}>
          {shortId}
        </span>
        <span className="text-[8px]" style={{ color: cfg.color }}>
          {Math.round(agent.confidence * 100)}%
        </span>
      </motion.div>

      {/* Status label */}
      <span className="text-[9px] font-medium" style={{ color: cfg.color }}>
        {cfg.label}
      </span>

      {/* Hover tooltip */}
      <AnimatePresence>
        {hovered && (
          <motion.div
            className="absolute z-30 glass border border-white/10 rounded-xl p-3 w-56 text-left pointer-events-none"
            style={{
              top: index < total / 2 ? 'calc(100% + 8px)' : 'auto',
              bottom: index >= total / 2 ? 'calc(100% + 8px)' : 'auto',
              left: '50%',
              transform: 'translateX(-50%)',
            }}
            initial={{ opacity: 0, y: 4, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.95 }}
            transition={{ duration: 0.15 }}
          >
            <div className="flex items-center gap-2 mb-2">
              <MessageSquare size={10} style={{ color: cfg.color }} />
              <span className="text-[10px] font-semibold" style={{ color: cfg.color }}>
                Agent {shortId}
              </span>
              <span className="ml-auto text-[9px] font-mono text-slate-500">
                chunk: {agent.chunk_id.slice(-8)}
              </span>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed line-clamp-3 mb-2">
              {agent.position_text || '(no position text)'}
            </p>
            {agent.reasoning && (
              <p className="text-[10px] text-slate-500 italic line-clamp-2">
                {agent.reasoning}
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function ConnectionLines({
  positions,
  supportMap,
  cx,
  cy,
  radius,
  visible,
}: {
  positions: AgentPositionSummary[]
  supportMap: Record<string, string[]>
  cx: number
  cy: number
  radius: number
  visible: boolean
}) {
  const total = positions.filter(p => p.status !== 'isolated').length
  const activePositions = positions.filter(p => p.status !== 'isolated')

  const connections: Array<{ x1: number; y1: number; x2: number; y2: number; color: string }> = []

  Object.entries(supportMap).forEach(([, agentIds]) => {
    if (agentIds.length < 2) return
    for (let i = 0; i < agentIds.length - 1; i++) {
      for (let j = i + 1; j < agentIds.length; j++) {
        const idxA = activePositions.findIndex(p => p.agent_id === agentIds[i])
        const idxB = activePositions.findIndex(p => p.agent_id === agentIds[j])
        if (idxA === -1 || idxB === -1) continue
        const posA = agentPosition(idxA, total, radius)
        const posB = agentPosition(idxB, total, radius)
        connections.push({
          x1: cx + posA.x, y1: cy + posA.y,
          x2: cx + posB.x, y2: cy + posB.y,
          color: '#8B5CF6',
        })
      }
    }
  })

  return (
    <svg className="absolute inset-0 w-full h-full pointer-events-none">
      <defs>
        <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.6" />
          <stop offset="100%" stopColor="#06B6D4" stopOpacity="0.6" />
        </linearGradient>
      </defs>
      {connections.map((c, i) => {
        const len = Math.hypot(c.x2 - c.x1, c.y2 - c.y1)
        return (
          <motion.line
            key={i}
            x1={c.x1} y1={c.y1}
            x2={c.x2} y2={c.y2}
            stroke="url(#lineGrad)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeDasharray={len}
            initial={{ strokeDashoffset: len, opacity: 0 }}
            animate={visible ? { strokeDashoffset: 0, opacity: 0.7 } : {}}
            transition={{ duration: 0.8, ease: 'easeOut', delay: 0.8 + i * 0.1 }}
          />
        )
      })}
    </svg>
  )
}

export function DebateArena({ debate, visible }: DebateArenaProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dims, setDims] = useState({ w: 500, h: 360 })
  const [round, setRound] = useState(0)
  const [replaying, setReplaying] = useState(false)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => {
      setDims({ w: entry.contentRect.width, h: entry.contentRect.height })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // Auto-replay rounds
  useEffect(() => {
    if (!visible || debate.rounds_completed === 0) return
    setRound(0)
    setReplaying(true)
    const interval = setInterval(() => {
      setRound(r => {
        if (r >= debate.rounds_completed) {
          clearInterval(interval)
          setReplaying(false)
          return r
        }
        return r + 1
      })
    }, 900)
    return () => clearInterval(interval)
  }, [visible, debate.rounds_completed])

  const cx = dims.w / 2
  const cy = dims.h / 2
  const radius = Math.min(dims.w, dims.h) / 2 - 80

  const activeAgents = debate.agent_positions.filter(p => p.status !== 'isolated')
  const isolatedAgents = debate.agent_positions.filter(p => p.status === 'isolated')
  const isolatedIds = new Set(debate.isolated_agent_ids)

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Users size={14} className="text-violet-400" />
            <span className="text-sm font-semibold text-slate-200">Debate Arena</span>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              {activeAgents.length} active
            </span>
            {isolatedAgents.length > 0 && (
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-red-400" />
                {isolatedAgents.length} isolated
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {replaying && (
            <motion.div
              className="flex items-center gap-1.5 text-xs text-violet-400"
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 1, repeat: Infinity }}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
              Round {round}/{debate.rounds_completed}
            </motion.div>
          )}
          {!replaying && (
            <span className="text-xs text-slate-500 font-mono">
              {debate.rounds_completed} rounds completed
            </span>
          )}
        </div>
      </div>

      {/* Arena */}
      <div
        ref={containerRef}
        className="relative rounded-xl bg-surface border border-violet-900/20 overflow-hidden"
        style={{ height: 360 }}
      >
        {/* Background grid */}
        <svg className="absolute inset-0 w-full h-full opacity-[0.04]" style={{ pointerEvents: 'none' }}>
          {Array.from({ length: 20 }, (_, i) => (
            <line key={`h${i}`} x1="0" y1={`${i * 5}%`} x2="100%" y2={`${i * 5}%`} stroke="#8B5CF6" strokeWidth="0.5" />
          ))}
          {Array.from({ length: 20 }, (_, i) => (
            <line key={`v${i}`} x1={`${i * 5}%`} y1="0" x2={`${i * 5}%`} y2="100%" stroke="#8B5CF6" strokeWidth="0.5" />
          ))}
        </svg>

        {/* Ambient center glow */}
        <motion.div
          className="absolute rounded-full pointer-events-none"
          style={{
            left: cx - 80,
            top: cy - 80,
            width: 160,
            height: 160,
            background: 'radial-gradient(circle, rgba(139,92,246,0.08) 0%, transparent 70%)',
          }}
          animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        />

        {/* Connection lines */}
        {dims.w > 0 && (
          <ConnectionLines
            positions={activeAgents}
            supportMap={debate.support_map}
            cx={cx}
            cy={cy}
            radius={radius}
            visible={visible}
          />
        )}

        {/* Active agents in circle */}
        {activeAgents.map((agent, i) => (
          <AgentNode
            key={agent.agent_id}
            agent={agent}
            index={i}
            total={activeAgents.length}
            cx={cx}
            cy={cy}
            radius={radius}
            isIsolated={false}
            visible={visible}
          />
        ))}

        {/* Isolated agents — row at bottom */}
        {isolatedAgents.length > 0 && (
          <div className="absolute bottom-3 left-0 right-0 flex items-center justify-center gap-3">
            <div className="flex items-center gap-1.5 mr-1">
              <AlertTriangle size={10} className="text-red-400" />
              <span className="text-[10px] text-red-400">Isolated:</span>
            </div>
            {isolatedAgents.map((agent) => {
              const cfg = STATUS_CONFIG.isolated
              const shortId = agent.agent_id.slice(-4).toUpperCase()
              return (
                <motion.div
                  key={agent.agent_id}
                  className="flex flex-col items-center gap-0.5"
                  initial={{ opacity: 0, y: 10 }}
                  animate={visible ? { opacity: 0.6, y: 0 } : {}}
                  transition={{ delay: 1.2 }}
                >
                  <div
                    className="w-10 h-10 rounded-xl flex flex-col items-center justify-center text-[9px] font-mono font-bold"
                    style={{
                      background: `${cfg.color}10`,
                      border: `1px dashed ${cfg.border}50`,
                      color: cfg.color,
                    }}
                  >
                    {shortId}
                  </div>
                </motion.div>
              )
            })}
          </div>
        )}

        {/* Center label */}
        <div
          className="absolute text-center pointer-events-none"
          style={{ left: cx - 50, top: cy - 20, width: 100 }}
        >
          <motion.div
            animate={{ opacity: [0.3, 0.6, 0.3] }}
            transition={{ duration: 3, repeat: Infinity }}
          >
            <Shield size={16} className="text-violet-500/40 mx-auto mb-1" />
            <p className="text-[9px] text-slate-600">consensus</p>
          </motion.div>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-[11px] text-slate-500">
        {Object.entries(STATUS_CONFIG).map(([key, cfg]) => (
          <span key={key} className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: cfg.color }} />
            {cfg.label}
          </span>
        ))}
        <span className="flex items-center gap-1.5 ml-2">
          <svg width="20" height="8"><line x1="0" y1="4" x2="20" y2="4" stroke="url(#lineGrad)" strokeWidth="1.5" /></svg>
          Support link
        </span>
        <span className="ml-auto flex items-center gap-1.5 text-violet-400">
          <span className="text-[9px]">Hover agents for details</span>
        </span>
      </div>
    </div>
  )
}

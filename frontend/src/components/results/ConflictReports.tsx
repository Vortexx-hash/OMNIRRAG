import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertCircle, ChevronDown, AlertTriangle, Volume2, Layers, Info } from 'lucide-react'
import type { ConflictReportSummary } from '../../types/api'
import { Badge } from '../ui/Badge'

interface ConflictReportsProps {
  reports: ConflictReportSummary[]
}

const CONFLICT_CONFIG = {
  ambiguity: {
    icon: AlertTriangle,
    color: '#F59E0B',
    bg: 'rgba(245,158,11,0.06)',
    border: 'rgba(245,158,11,0.2)',
    label: 'Ambiguity',
    description: 'Multiple valid but conflicting interpretations detected',
  },
  outlier: {
    icon: AlertCircle,
    color: '#EF4444',
    bg: 'rgba(239,68,68,0.06)',
    border: 'rgba(239,68,68,0.2)',
    label: 'Outlier',
    description: 'A chunk strongly contradicts the consensus position',
  },
  oversimplification: {
    icon: Layers,
    color: '#8B5CF6',
    bg: 'rgba(139,92,246,0.06)',
    border: 'rgba(139,92,246,0.2)',
    label: 'Oversimplification',
    description: 'Evidence suggests the question has an over-simplified framing',
  },
  noise: {
    icon: Volume2,
    color: '#64748B',
    bg: 'rgba(100,116,139,0.06)',
    border: 'rgba(100,116,139,0.2)',
    label: 'Noise',
    description: 'Weak or low-credibility evidence with no clear signal',
  },
}

function ConflictCard({ report, index }: { report: ConflictReportSummary; index: number }) {
  const [open, setOpen] = useState(index === 0)
  const cfg = CONFLICT_CONFIG[report.conflict_type as keyof typeof CONFLICT_CONFIG] ?? CONFLICT_CONFIG.noise

  return (
    <motion.div
      className="rounded-xl overflow-hidden"
      style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.35 }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/2 transition-colors"
      >
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: `${cfg.color}20`, border: `1px solid ${cfg.color}40` }}
        >
          <cfg.icon size={13} style={{ color: cfg.color }} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-slate-200">{cfg.label}</span>
            {report.has_scope_qualifier && (
              <Badge variant="cyan" size="sm">
                <Info size={9} className="mr-0.5" />
                Scope qualifier
              </Badge>
            )}
          </div>
          <p className="text-[10px] text-slate-500 mt-0.5">{cfg.description}</p>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="text-right">
            <p className="text-xs font-mono font-semibold" style={{ color: cfg.color }}>
              {Math.round(report.evidence_strength * 100)}%
            </p>
            <p className="text-[9px] text-slate-600">strength</p>
          </div>
          <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <ChevronDown size={14} className="text-slate-500" />
          </motion.div>
        </div>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="border-t px-4 py-3 space-y-3"
            style={{ borderColor: cfg.border }}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            {/* Evidence strength bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-slate-500">Evidence strength</span>
                <span className="font-mono font-semibold" style={{ color: cfg.color }}>
                  {Math.round(report.evidence_strength * 100)}%
                </span>
              </div>
              <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: cfg.color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${report.evidence_strength * 100}%` }}
                  transition={{ duration: 0.7, ease: 'easeOut' }}
                />
              </div>
            </div>

            {/* Involved chunks */}
            <div>
              <p className="text-[10px] text-slate-500 mb-1.5">
                Involved chunks ({report.chunk_ids.length})
              </p>
              <div className="flex flex-wrap gap-1.5">
                {report.chunk_ids.map(id => (
                  <span
                    key={id}
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                    style={{
                      background: `${cfg.color}15`,
                      color: `${cfg.color}`,
                      border: `1px solid ${cfg.color}30`,
                    }}
                  >
                    {id.slice(-12)}
                  </span>
                ))}
              </div>
            </div>

            {/* Scope qualifier explanation */}
            {report.has_scope_qualifier && (
              <div
                className="flex items-start gap-2 rounded-lg p-2.5 text-xs"
                style={{ background: 'rgba(6,182,212,0.08)', border: '1px solid rgba(6,182,212,0.2)' }}
              >
                <Info size={12} className="text-cyan-400 mt-0.5 flex-shrink-0" />
                <p className="text-cyan-300/80">
                  Scope qualifier detected — chunks may refer to different contexts of the same entity.
                  This is not a hard contradiction.
                </p>
              </div>
            )}

            {/* Decision case */}
            <div className="flex items-center gap-2 text-[10px]">
              <span className="text-slate-500">Decision case for this cluster:</span>
              <span className="font-mono font-semibold text-slate-300">Case {report.decision_case}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function ConflictReports({ reports }: ConflictReportsProps) {
  if (reports.length === 0) {
    return (
      <div className="flex items-center gap-3 p-5 glass rounded-xl border border-emerald-500/20">
        <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center">
          <AlertCircle size={14} className="text-emerald-400" />
        </div>
        <div>
          <p className="text-sm font-medium text-emerald-300">No conflicts detected</p>
          <p className="text-xs text-slate-500">All evidence was consistent</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <AlertCircle size={14} className="text-red-400" />
        <h3 className="text-sm font-semibold text-slate-200">Conflict Reports</h3>
        <Badge variant="red" size="sm">{reports.length}</Badge>
      </div>
      <div className="space-y-2">
        {reports.map((r, i) => (
          <ConflictCard key={i} report={r} index={i} />
        ))}
      </div>
    </div>
  )
}

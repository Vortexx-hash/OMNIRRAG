import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, XCircle, ChevronDown, FileText } from 'lucide-react'
import type { EvidenceSummary, RejectedEvidenceSummary } from '../../types/api'
import { CredibilityBar } from '../ui/CredibilityBar'
import { Badge, ConflictTypeBadge, CredibilityTierBadge } from '../ui/Badge'

interface EvidenceGridProps {
  selected: EvidenceSummary[]
  rejected: RejectedEvidenceSummary[]
}

function EvidenceCard({ evidence, index }: { evidence: EvidenceSummary; index: number }) {
  const [open, setOpen] = useState(false)

  return (
    <motion.div
      className="glass rounded-xl overflow-hidden hover:border-emerald-500/30 transition-all duration-300"
      style={{ border: '1px solid rgba(16,185,129,0.15)' }}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.07, duration: 0.4 }}
      whileHover={{ boxShadow: '0 0 20px rgba(16,185,129,0.1)' }}
    >
      {/* Header */}
      <div className="flex items-center gap-2.5 px-4 py-3 border-b border-white/5">
        <CheckCircle size={13} className="text-emerald-400 flex-shrink-0" />
        <span className="text-xs font-mono text-slate-400 truncate flex-1">
          {evidence.source_doc_id}
        </span>
        <CredibilityTierBadge tier={evidence.credibility_tier} />
      </div>

      {/* Text excerpt */}
      <div className="px-4 py-3">
        <p className="text-xs text-slate-300 leading-relaxed line-clamp-3">
          {evidence.text_excerpt}
        </p>
      </div>

      {/* Credibility bar */}
      <div className="px-4 pb-3">
        <CredibilityBar
          score={evidence.credibility_score}
          tier={evidence.credibility_tier}
          showLabel
        />
      </div>

      {/* Expand for chunk ID */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-1.5 px-4 py-2 text-[10px] text-slate-600 hover:text-slate-400 transition-colors border-t border-white/5"
      >
        <motion.span animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown size={11} />
        </motion.span>
        Chunk ID
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            className="px-4 py-2 bg-black/20"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <p className="text-[10px] font-mono text-violet-400 break-all">{evidence.chunk_id}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function RejectedCard({ evidence, index }: { evidence: RejectedEvidenceSummary; index: number }) {
  const [open, setOpen] = useState(false)

  return (
    <motion.div
      className="rounded-xl overflow-hidden opacity-60 hover:opacity-80 transition-all duration-300"
      style={{
        background: 'rgba(239,68,68,0.04)',
        border: '1px solid rgba(239,68,68,0.12)',
      }}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 0.6, y: 0 }}
      transition={{ delay: index * 0.07, duration: 0.4 }}
      whileHover={{ opacity: 0.85 }}
    >
      {/* Header */}
      <div className="flex items-center gap-2.5 px-4 py-3 border-b border-white/5">
        <XCircle size={13} className="text-red-400 flex-shrink-0" />
        <span className="text-xs font-mono text-slate-500 truncate flex-1">
          {evidence.source_doc_id}
        </span>
        <ConflictTypeBadge type={evidence.conflict_type} />
      </div>

      {/* Text excerpt */}
      <div className="px-4 py-3">
        <p className="text-xs text-slate-500 leading-relaxed line-clamp-3">
          {evidence.text_excerpt}
        </p>
      </div>

      {/* Tier */}
      <div className="px-4 pb-3">
        <CredibilityTierBadge tier={evidence.credibility_tier} />
      </div>

      {/* Chunk ID expand */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-1.5 px-4 py-2 text-[10px] text-slate-600 hover:text-slate-500 transition-colors border-t border-white/5"
      >
        <motion.span animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown size={11} />
        </motion.span>
        Chunk ID
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            className="px-4 py-2 bg-black/20"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <p className="text-[10px] font-mono text-red-400 break-all">{evidence.chunk_id}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function EvidenceGrid({ selected, rejected }: EvidenceGridProps) {
  return (
    <div className="space-y-6">
      {/* Selected evidence */}
      {selected.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <CheckCircle size={14} className="text-emerald-400" />
            <h3 className="text-sm font-semibold text-slate-200">Selected Evidence</h3>
            <Badge variant="green" size="sm">{selected.length}</Badge>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {selected.map((e, i) => (
              <EvidenceCard key={e.chunk_id} evidence={e} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* Rejected evidence */}
      {rejected.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <XCircle size={14} className="text-red-400" />
            <h3 className="text-sm font-semibold text-slate-400">Rejected / Downweighted</h3>
            <Badge variant="red" size="sm">{rejected.length}</Badge>
            <span className="text-[11px] text-slate-600 ml-1">classified as outlier or noise</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {rejected.map((e, i) => (
              <RejectedCard key={e.chunk_id} evidence={e} index={i} />
            ))}
          </div>
        </div>
      )}

      {selected.length === 0 && rejected.length === 0 && (
        <div className="flex items-center gap-3 p-6 glass rounded-xl">
          <FileText size={16} className="text-slate-600" />
          <p className="text-sm text-slate-500">No evidence to display</p>
        </div>
      )}
    </div>
  )
}

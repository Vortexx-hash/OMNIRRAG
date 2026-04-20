import { motion } from 'framer-motion'
import { Sparkles, Quote } from 'lucide-react'
import { DecisionBadge } from '../ui/Badge'
import type { QueryResponse } from '../../types/api'

interface FinalAnswerProps {
  result: QueryResponse
  query: string
}

const DECISION_COLORS: Record<string, { bg: string; border: string; glow: string }> = {
  ambiguity:     { bg: 'rgba(245,158,11,0.06)',  border: 'rgba(245,158,11,0.25)',  glow: 'rgba(245,158,11,0.15)'  },
  strong_winner: { bg: 'rgba(16,185,129,0.06)',   border: 'rgba(16,185,129,0.25)',  glow: 'rgba(16,185,129,0.15)'  },
  unresolved:    { bg: 'rgba(239,68,68,0.06)',    border: 'rgba(239,68,68,0.25)',   glow: 'rgba(239,68,68,0.15)'   },
}

export function FinalAnswer({ result, query }: FinalAnswerProps) {
  const colors = DECISION_COLORS[result.decision_label] ?? DECISION_COLORS.unresolved

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      {/* Query echo */}
      <div className="flex items-start gap-2.5 mb-5">
        <Quote size={14} className="text-slate-600 mt-0.5 flex-shrink-0" />
        <p className="text-sm text-slate-400 italic">{query}</p>
      </div>

      {/* Answer card */}
      <motion.div
        className="relative rounded-2xl overflow-hidden"
        style={{
          background: colors.bg,
          border: `1px solid ${colors.border}`,
          boxShadow: `0 0 40px ${colors.glow}, 0 0 1px ${colors.border}`,
        }}
        animate={{
          boxShadow: [
            `0 0 30px ${colors.glow}, 0 0 1px ${colors.border}`,
            `0 0 60px ${colors.glow}, 0 0 1px ${colors.border}`,
            `0 0 30px ${colors.glow}, 0 0 1px ${colors.border}`,
          ],
        }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
      >
        {/* Header bar */}
        <div
          className="flex items-center justify-between px-5 py-3 border-b"
          style={{ borderColor: colors.border, background: 'rgba(255,255,255,0.02)' }}
        >
          <div className="flex items-center gap-2.5">
            <motion.div
              animate={{ rotate: [0, 360] }}
              transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
            >
              <Sparkles size={14} className="text-violet-400" />
            </motion.div>
            <span className="text-xs font-semibold text-slate-300 tracking-wide uppercase">
              Final Answer
            </span>
          </div>
          <div className="flex items-center gap-2.5">
            <DecisionBadge label={result.decision_label} />
            <span className="text-xs text-slate-600 font-mono">
              Case {result.decision_case}
            </span>
          </div>
        </div>

        {/* Answer text */}
        <div className="px-6 py-5">
          <motion.p
            className="text-base text-slate-100 leading-7 font-light"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            {result.answer}
          </motion.p>
        </div>

        {/* Footer: tags + sources */}
        {(result.conflict_handling_tags.length > 0 || result.sources_cited.length > 0) && (
          <div
            className="flex items-center gap-3 px-5 py-3 border-t flex-wrap"
            style={{ borderColor: colors.border, background: 'rgba(0,0,0,0.1)' }}
          >
            {result.conflict_handling_tags.map(tag => (
              <span
                key={tag}
                className="text-[10px] px-2 py-0.5 rounded-md font-mono"
                style={{ background: `${colors.border}`, color: 'rgba(255,255,255,0.5)' }}
              >
                {tag}
              </span>
            ))}
            {result.sources_cited.length > 0 && (
              <span className="ml-auto text-[10px] text-slate-600 font-mono">
                {result.sources_cited.length} source{result.sources_cited.length > 1 ? 's' : ''} cited
              </span>
            )}
          </div>
        )}
      </motion.div>
    </motion.div>
  )
}

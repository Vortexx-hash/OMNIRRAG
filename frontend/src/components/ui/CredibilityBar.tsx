import { motion } from 'framer-motion'

interface CredibilityBarProps {
  score: number
  tier: number
  showLabel?: boolean
}

const TIER_COLORS = ['#10B981', '#06B6D4', '#F59E0B', '#EF4444']
const TIER_LABELS = ['High', 'Medium', 'Low', 'Unverified']

export function CredibilityBar({ score, tier, showLabel = false }: CredibilityBarProps) {
  const color = TIER_COLORS[tier - 1] ?? '#64748B'
  const label = TIER_LABELS[tier - 1] ?? 'Unknown'
  const pct = Math.round(score * 100)

  return (
    <div className="space-y-1">
      {showLabel && (
        <div className="flex justify-between text-[11px]">
          <span className="text-slate-500">Credibility</span>
          <span style={{ color }} className="font-mono font-medium">{pct}% · {label}</span>
        </div>
      )}
      <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}

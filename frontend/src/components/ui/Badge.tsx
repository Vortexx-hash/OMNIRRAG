import type { ReactNode } from 'react'

type Variant = 'violet' | 'cyan' | 'green' | 'amber' | 'red' | 'slate' | 'pink'

interface BadgeProps {
  children: ReactNode
  variant?: Variant
  size?: 'sm' | 'md'
  dot?: boolean
  className?: string
}

const STYLES: Record<Variant, string> = {
  violet: 'bg-violet-500/15 text-violet-300 border-violet-500/30',
  cyan:   'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
  green:  'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  amber:  'bg-amber-500/15 text-amber-300 border-amber-500/30',
  red:    'bg-red-500/15 text-red-300 border-red-500/30',
  slate:  'bg-slate-500/15 text-slate-400 border-slate-500/30',
  pink:   'bg-pink-500/15 text-pink-300 border-pink-500/30',
}

const DOT_STYLES: Record<Variant, string> = {
  violet: 'bg-violet-400',
  cyan:   'bg-cyan-400',
  green:  'bg-emerald-400',
  amber:  'bg-amber-400',
  red:    'bg-red-400',
  slate:  'bg-slate-400',
  pink:   'bg-pink-400',
}

export function Badge({ children, variant = 'violet', size = 'sm', dot, className = '' }: BadgeProps) {
  const sizeClass = size === 'sm' ? 'text-[11px] px-2 py-0.5' : 'text-xs px-2.5 py-1'
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${STYLES[variant]} ${sizeClass} ${className}`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${DOT_STYLES[variant]}`} />}
      {children}
    </span>
  )
}

export function DecisionBadge({ label }: { label: string }) {
  const map: Record<string, { variant: Variant; text: string }> = {
    ambiguity:     { variant: 'amber', text: 'Ambiguity' },
    strong_winner: { variant: 'green', text: 'Strong Winner' },
    unresolved:    { variant: 'red',   text: 'Unresolved' },
  }
  const { variant, text } = map[label] ?? { variant: 'slate', text: label }
  return <Badge variant={variant} size="md" dot>{text}</Badge>
}

export function ConflictTypeBadge({ type }: { type: string }) {
  const map: Record<string, Variant> = {
    ambiguity:        'amber',
    outlier:          'red',
    oversimplification: 'violet',
    noise:            'slate',
  }
  return <Badge variant={map[type] ?? 'slate'}>{type}</Badge>
}

export function CredibilityTierBadge({ tier }: { tier: number }) {
  const variants: Variant[] = ['green', 'cyan', 'amber', 'red']
  const labels = ['Tier 1 · High', 'Tier 2 · Medium', 'Tier 3 · Low', 'Tier 4 · Unverified']
  return <Badge variant={variants[tier - 1] ?? 'slate'}>{labels[tier - 1] ?? `Tier ${tier}`}</Badge>
}

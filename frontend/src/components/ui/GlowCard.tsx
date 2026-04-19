import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

interface GlowCardProps {
  children: ReactNode
  className?: string
  glow?: 'violet' | 'cyan' | 'green' | 'amber' | 'red' | 'none'
  onClick?: () => void
  animate?: boolean
}

const GLOW_CLASSES = {
  violet: 'hover:shadow-glow-violet hover:border-violet-500/40',
  cyan: 'hover:shadow-glow-cyan hover:border-cyan-500/40',
  green: 'hover:shadow-glow-green hover:border-emerald-500/40',
  amber: 'hover:shadow-glow-amber hover:border-amber-500/40',
  red: 'hover:shadow-glow-red hover:border-red-500/40',
  none: '',
}

export function GlowCard({ children, className = '', glow = 'violet', onClick, animate = false }: GlowCardProps) {
  const Tag = onClick ? motion.button : motion.div

  return (
    <Tag
      onClick={onClick}
      className={`glass rounded-xl transition-all duration-300 ${GLOW_CLASSES[glow]} ${onClick ? 'cursor-pointer text-left w-full' : ''} ${className}`}
      whileHover={onClick ? { scale: 1.005 } : undefined}
      whileTap={onClick ? { scale: 0.998 } : undefined}
      {...(animate ? {
        initial: { opacity: 0, y: 16 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.4, ease: 'easeOut' }
      } : {})}
    >
      {children}
    </Tag>
  )
}

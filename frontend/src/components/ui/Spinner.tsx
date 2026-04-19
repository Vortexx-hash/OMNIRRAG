import { motion } from 'framer-motion'

interface SpinnerProps {
  size?: number
  color?: string
}

export function Spinner({ size = 24, color = '#8B5CF6' }: SpinnerProps) {
  return (
    <motion.svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
    >
      <circle cx="12" cy="12" r="10" stroke={color} strokeOpacity="0.2" strokeWidth="2.5" />
      <path
        d="M12 2 A10 10 0 0 1 22 12"
        stroke={color}
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </motion.svg>
  )
}

export function PulsingDot({ color = 'bg-violet-500' }: { color?: string }) {
  return (
    <span className="relative inline-flex">
      <span className={`w-2 h-2 rounded-full ${color}`} />
      <span className={`absolute inset-0 w-2 h-2 rounded-full ${color} animate-ping opacity-75`} />
    </span>
  )
}

export function SkeletonLine({ width = 'w-full', height = 'h-4' }: { width?: string; height?: string }) {
  return (
    <div className={`${width} ${height} rounded shimmer-bg`} />
  )
}

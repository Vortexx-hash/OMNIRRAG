import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import { LayoutDashboard, Upload, Search, Cpu, Activity } from 'lucide-react'

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/upload', icon: Upload, label: 'Upload' },
  { to: '/query', icon: Search, label: 'Query' },
]

export function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-screen w-16 lg:w-56 flex flex-col glass border-r border-violet-900/20 z-40">
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-violet-900/20">
        <motion.div
          className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-600 to-cyan-500 flex items-center justify-center flex-shrink-0 shadow-glow-violet"
          animate={{ boxShadow: ['0 0 10px rgba(139,92,246,0.3)', '0 0 25px rgba(139,92,246,0.6)', '0 0 10px rgba(139,92,246,0.3)'] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
        >
          <Cpu size={16} className="text-white" />
        </motion.div>
        <div className="hidden lg:block overflow-hidden">
          <p className="font-semibold text-sm text-gradient leading-tight">VIPP</p>
          <p className="text-[10px] text-slate-500 leading-tight">Conflict-Aware RAG</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-2 space-y-1">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group
              ${isActive
                ? 'bg-violet-600/20 border border-violet-500/30 text-violet-300 shadow-glow-sm'
                : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={18} className={`flex-shrink-0 transition-colors ${isActive ? 'text-violet-400' : 'group-hover:text-slate-300'}`} />
                <span className="hidden lg:block text-sm font-medium">{label}</span>
                {isActive && (
                  <motion.div
                    layoutId="nav-indicator"
                    className="hidden lg:block ml-auto w-1.5 h-1.5 rounded-full bg-violet-400"
                  />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer status */}
      <div className="p-3 border-t border-violet-900/20">
        <div className="hidden lg:flex items-center gap-2 px-2 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
          <motion.div
            className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
          <div className="flex items-center gap-1.5">
            <Activity size={11} className="text-emerald-400" />
            <span className="text-[11px] text-emerald-400 font-medium">Pipeline active</span>
          </div>
        </div>
        <div className="lg:hidden flex justify-center">
          <motion.div
            className="w-2 h-2 rounded-full bg-emerald-400"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
        </div>
      </div>
    </aside>
  )
}

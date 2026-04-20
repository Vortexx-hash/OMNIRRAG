import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Database, Upload, Search, Activity, FileText,
  ArrowRight, Clock, Shield, ChevronRight
} from 'lucide-react'
import { PipelineExplorer } from '../components/pipeline/PipelineExplorer'
import { api } from '../api/client'
import type { HealthResponse, DocumentRecord } from '../types/api'
import { GlowCard } from '../components/ui/GlowCard'
import { Badge } from '../components/ui/Badge'
import { EmptyState } from '../components/ui/EmptyState'
import { Spinner } from '../components/ui/Spinner'

const SOURCE_TIER: Record<string, number> = {
  government: 1,
  academic: 2,
  blog: 3,
  unverified: 4,
}

function StatCard({ label, value, icon: Icon, color, sub }: {
  label: string; value: string | number; icon: React.ElementType; color: string; sub?: string
}) {
  return (
    <GlowCard className="p-5 flex items-start gap-4" animate>
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ background: `${color}18`, border: `1px solid ${color}40` }}
      >
        <Icon size={18} style={{ color }} />
      </div>
      <div>
        <p className="text-2xl font-bold font-mono" style={{ color }}>{value}</p>
        <p className="text-xs text-slate-400 font-medium mt-0.5">{label}</p>
        {sub && <p className="text-[10px] text-slate-600 mt-0.5">{sub}</p>}
      </div>
    </GlowCard>
  )
}

function DocumentRow({ doc, index }: { doc: DocumentRecord; index: number }) {
  const tier = SOURCE_TIER[doc.source_type] ?? 4
  const TIER_COLORS = ['#10B981', '#06B6D4', '#F59E0B', '#EF4444']
  const color = TIER_COLORS[tier - 1]

  const ago = (() => {
    if (!doc.uploaded_at) return 'unknown'
    const ms = Date.now() - new Date(doc.uploaded_at).getTime()
    const mins = Math.floor(ms / 60000)
    if (mins < 1) return 'just now'
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return `${Math.floor(hrs / 24)}d ago`
  })()

  return (
    <motion.div
      className="flex items-center gap-4 px-4 py-3 rounded-xl glass-hover border border-white/5 cursor-default"
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.06, duration: 0.35 }}
    >
      <div
        className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
        style={{ background: `${color}15`, border: `1px solid ${color}30` }}
      >
        <FileText size={13} style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-200 truncate">
          {doc.title ?? doc.doc_id}
        </p>
        <p className="text-[10px] text-slate-600 font-mono">{doc.doc_id}</p>
      </div>
      <div className="flex items-center gap-3 flex-shrink-0">
        <Badge variant={tier === 1 ? 'green' : tier === 2 ? 'cyan' : tier === 3 ? 'amber' : 'red'} size="sm">
          {doc.source_type}
        </Badge>
        <span className="text-[11px] font-mono text-slate-500">{doc.chunks_stored} chunks</span>
        <span className="text-[11px] text-slate-600 flex items-center gap-1">
          <Clock size={9} />
          {ago}
        </span>
      </div>
    </motion.div>
  )
}

export function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [docs, setDocs] = useState<DocumentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const location = useLocation()

  useEffect(() => {
    if (location.pathname !== '/') return
    setLoading(true)
    Promise.all([api.health(), api.documents()])
      .then(([h, d]) => { setHealth(h); setDocs(d) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [location.pathname])

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <motion.div
        className="space-y-2"
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gradient">VIPP Dashboard</h1>
          {health && (
            <span className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border
              ${health.status === 'ok'
                ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-400'
                : 'bg-amber-500/10 border-amber-500/25 text-amber-400'}`}
            >
              <motion.span
                className={`w-1.5 h-1.5 rounded-full ${health.status === 'ok' ? 'bg-emerald-400' : 'bg-amber-400'}`}
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              {health.status}
            </span>
          )}
        </div>
        <p className="text-sm text-slate-500">
          Conflict-aware RAG pipeline with multi-agent debate and evidence synthesis
        </p>
      </motion.div>

      {/* Stats */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Spinner size={32} />
        </div>
      ) : (
        <motion.div
          className="grid grid-cols-2 lg:grid-cols-4 gap-4"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <StatCard
            label="Chunks Indexed"
            value={health?.chunks_indexed ?? 0}
            icon={Database}
            color="#8B5CF6"
            sub="in vector store"
          />
          <StatCard
            label="Documents"
            value={docs.length}
            icon={FileText}
            color="#06B6D4"
            sub="uploaded this session"
          />
          <StatCard
            label="Pipeline Status"
            value={health?.status === 'ok' ? 'Ready' : 'Init'}
            icon={Activity}
            color="#10B981"
            sub="all modules loaded"
          />
          <StatCard
            label="Conflict Types"
            value="4"
            icon={Shield}
            color="#F59E0B"
            sub="ambiguity · outlier · noise · over"
          />
        </motion.div>
      )}

      {/* Quick actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link to="/upload">
          <GlowCard
            className="p-5 flex items-center gap-4 group"
            onClick={() => {}}
            glow="violet"
          >
            <div className="w-10 h-10 rounded-xl bg-violet-500/15 border border-violet-500/30 flex items-center justify-center flex-shrink-0 group-hover:shadow-glow-violet transition-all">
              <Upload size={18} className="text-violet-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-200">Upload Documents</p>
              <p className="text-xs text-slate-500 mt-0.5">Ingest and index new knowledge sources</p>
            </div>
            <ChevronRight size={16} className="text-slate-600 group-hover:text-violet-400 group-hover:translate-x-1 transition-all" />
          </GlowCard>
        </Link>
        <Link to="/query">
          <GlowCard
            className="p-5 flex items-center gap-4 group"
            onClick={() => {}}
            glow="cyan"
          >
            <div className="w-10 h-10 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center flex-shrink-0 group-hover:shadow-glow-cyan transition-all">
              <Search size={18} className="text-cyan-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-200">Query the Knowledge Base</p>
              <p className="text-xs text-slate-500 mt-0.5">Run conflict-aware retrieval and synthesis</p>
            </div>
            <ChevronRight size={16} className="text-slate-600 group-hover:text-cyan-400 group-hover:translate-x-1 transition-all" />
          </GlowCard>
        </Link>
      </div>

      {/* Documents list */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <FileText size={14} className="text-violet-400" />
            Uploaded Documents
          </h2>
          <Link to="/upload" className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1 transition-colors">
            Upload new
            <ArrowRight size={12} />
          </Link>
        </div>

        {docs.length === 0 ? (
          <EmptyState
            icon={<Database size={24} />}
            title="No documents indexed yet"
            description="Upload your first document to start building the knowledge base"
            action={
              <Link to="/upload">
                <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600/20 border border-violet-500/30 text-violet-300 text-sm hover:bg-violet-600/30 transition-all">
                  <Upload size={14} />
                  Upload a document
                </button>
              </Link>
            }
          />
        ) : (
          <div className="space-y-2">
            {docs.slice().reverse().map((doc, i) => (
              <DocumentRow key={doc.doc_id} doc={doc} index={i} />
            ))}
          </div>
        )}
      </div>

      {/* Pipeline explorer */}
      <PipelineExplorer />
    </div>
  )
}

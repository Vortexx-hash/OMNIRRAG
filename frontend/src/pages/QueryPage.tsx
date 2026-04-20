import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Send, Sparkles, AlertCircle, RotateCcw } from 'lucide-react'
import type { QueryResponse } from '../types/api'
import { PipelineVisualizer } from '../components/pipeline/PipelineVisualizer'
import { FinalAnswer } from '../components/results/FinalAnswer'
import { EvidenceGrid } from '../components/results/EvidenceGrid'
import { ConflictReports } from '../components/results/ConflictReports'
import { QueryModal } from '../components/pipeline/QueryModal'

type Status = 'idle' | 'loading' | 'success' | 'error'

const EXAMPLE_QUERIES = [
  'What is the capital of Bolivia?',
  'What are the effects of caffeine on sleep?',
  'How does climate change affect biodiversity?',
]

function QueryInput({
  onSubmit,
  loading,
}: {
  onSubmit: (q: string) => void
  loading: boolean
}) {
  const [value, setValue] = useState('')

  function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault()
    const q = value.trim()
    if (!q || loading) return
    onSubmit(q)
  }

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit}>
        <div className="relative">
          <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          <input
            value={value}
            onChange={e => setValue(e.target.value)}
            placeholder="Ask a question about your knowledge base…"
            disabled={loading}
            className="w-full bg-surface border border-violet-900/40 rounded-2xl pl-11 pr-14 py-4 text-sm text-slate-200 placeholder-slate-600
              focus:outline-none focus:border-violet-500/60 focus:ring-2 focus:ring-violet-500/15
              disabled:opacity-50 transition-all duration-200"
          />
          <motion.button
            type="submit"
            disabled={!value.trim() || loading}
            className={`absolute right-3 top-1/2 -translate-y-1/2 w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200
              ${value.trim() && !loading
                ? 'bg-violet-600 hover:bg-violet-500 text-white shadow-glow-violet cursor-pointer'
                : 'bg-white/5 text-slate-600 cursor-not-allowed'
              }`}
            whileTap={value.trim() && !loading ? { scale: 0.92 } : {}}
          >
            {loading ? (
              <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
                <Send size={14} />
              </motion.div>
            ) : (
              <Send size={14} />
            )}
          </motion.button>
        </div>
      </form>

      {/* Example queries */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[11px] text-slate-600">Try:</span>
        {EXAMPLE_QUERIES.map(q => (
          <button
            key={q}
            onClick={() => { setValue(q); onSubmit(q) }}
            disabled={loading}
            className="text-[11px] px-2.5 py-1 rounded-lg border border-violet-900/30 text-slate-500 hover:text-violet-300 hover:border-violet-500/40 transition-all disabled:opacity-40"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}

export function QueryPage() {
  const [status, setStatus] = useState<Status>('idle')
  const [result, setResult] = useState<QueryResponse | undefined>()
  const [query, setQuery] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [activeQuery, setActiveQuery] = useState('')
  const completedRef = useRef(false)

  function handleSubmit(q: string) {
    completedRef.current = false
    setActiveQuery(q)
    setModalOpen(true)
    setResult(undefined)
    setErrorMsg('')
    setStatus('loading')
  }

  function handleModalComplete(r: QueryResponse) {
    completedRef.current = true
    setQuery(activeQuery)
    setResult(r)
    setStatus('success')
  }

  function handleModalClose() {
    setModalOpen(false)
    if (!completedRef.current) {
      setStatus('error')
      setErrorMsg('Query cancelled')
    }
  }

  function handleReset() {
    setStatus('idle')
    setResult(undefined)
    setQuery('')
    setActiveQuery('')
    setErrorMsg('')
  }

  return (
    <>
      <AnimatePresence>
        {modalOpen && (
          <QueryModal
            query={activeQuery}
            onClose={handleModalClose}
            onComplete={handleModalComplete}
          />
        )}
      </AnimatePresence>

    <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <motion.div
        className="space-y-1"
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center shadow-glow-cyan">
              <Search size={16} className="text-cyan-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100">Query Interface</h1>
              <p className="text-xs text-slate-500">Conflict-aware retrieval with multi-agent debate</p>
            </div>
          </div>
          {status !== 'idle' && (
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
              <RotateCcw size={12} />
              New query
            </button>
          )}
        </div>
      </motion.div>

      {/* Query input */}
      <motion.div
        className="glass rounded-2xl p-5"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        <QueryInput onSubmit={handleSubmit} loading={status === 'loading'} />
      </motion.div>

      {/* Error banner */}
      <AnimatePresence>
        {status === 'error' && (
          <motion.div
            className="glass rounded-xl p-4 flex items-center gap-3 border border-red-500/25"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <AlertCircle size={16} className="text-red-400 flex-shrink-0" />
            <p className="text-sm text-red-300">{errorMsg || 'Pipeline failed — is the backend running?'}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Pipeline visualizer (loading + replay) */}
      <AnimatePresence>
        {status !== 'idle' && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            <PipelineVisualizer
              status={status}
              result={result}
              query={query}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results section */}
      <AnimatePresence>
        {status === 'success' && result && (
          <motion.div
            className="space-y-8"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5, delay: 3.5 }}
          >
            {/* Divider */}
            <div className="flex items-center gap-4">
              <div className="h-px flex-1 bg-gradient-to-r from-transparent via-violet-500/30 to-transparent" />
              <div className="flex items-center gap-2 text-xs text-violet-400 font-medium">
                <Sparkles size={12} />
                Synthesis Results
              </div>
              <div className="h-px flex-1 bg-gradient-to-r from-transparent via-violet-500/30 to-transparent" />
            </div>

            {/* Final answer */}
            <FinalAnswer result={result} query={query} />

            {/* Conflict reports */}
            <ConflictReports reports={result.conflict_reports} />

            {/* Evidence grid */}
            <EvidenceGrid
              selected={result.selected_evidence}
              rejected={result.rejected_evidence}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Idle state */}
      {status === 'idle' && (
        <motion.div
          className="flex flex-col items-center justify-center py-16 text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <motion.div
            className="w-16 h-16 rounded-2xl glass border border-violet-500/20 flex items-center justify-center mb-4 shadow-glow-sm"
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          >
            <Sparkles size={24} className="text-violet-400/60" />
          </motion.div>
          <h3 className="text-base font-semibold text-slate-400 mb-2">Ready to reason</h3>
          <p className="text-sm text-slate-600 max-w-sm">
            Submit a query to run the full conflict-aware pipeline — retrieval, debate, and synthesis
          </p>
        </motion.div>
      )}
    </div>
    </>
  )
}

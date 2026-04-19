import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, FileText, Scissors, Cpu, Database } from 'lucide-react'
import type { UploadResponse } from '../../types/api'

type Phase = 'idle' | 'uploading' | 'chunking' | 'embedding' | 'storing' | 'done'

interface IngestionFlowProps {
  status: 'idle' | 'loading' | 'success' | 'error'
  result?: UploadResponse
  inputText?: string
  error?: string
}

const CHUNK_COLORS = [
  '#8B5CF6', '#06B6D4', '#10B981', '#F59E0B',
  '#EC4899', '#6366F1', '#14B8A6', '#F97316',
]

function estimateChunkPreviews(text: string, count: number): string[] {
  if (!text || count === 0) return []
  const len = Math.ceil(text.length / count)
  return Array.from({ length: Math.min(count, 12) }, (_, i) =>
    text.slice(i * len, (i + 1) * len).replace(/\s+/g, ' ').trim().slice(0, 60)
  )
}

export function IngestionFlow({ status, result, inputText = '', error }: IngestionFlowProps) {
  const [phase, setPhase] = useState<Phase>('idle')
  const [visibleChunks, setVisibleChunks] = useState<number>(0)
  const [visibleOrbs, setVisibleOrbs] = useState<number>(0)

  const chunkPreviews = result ? estimateChunkPreviews(inputText, result.chunks_stored) : []
  const orbCount = Math.min(result?.chunks_stored ?? 0, 12)

  useEffect(() => {
    if (status === 'loading') {
      setPhase('uploading')
      setVisibleChunks(0)
      setVisibleOrbs(0)
    } else if (status === 'success' && result) {
      // Animate through phases after success
      const t1 = setTimeout(() => setPhase('chunking'), 200)
      const t2 = setTimeout(() => {
        // Stagger chunks appearing
        Array.from({ length: orbCount }, (_, i) =>
          setTimeout(() => setVisibleChunks(i + 1), i * 120)
        )
      }, 600)
      const t3 = setTimeout(() => setPhase('embedding'), 600 + orbCount * 120 + 400)
      const t4 = setTimeout(() => {
        setVisibleOrbs(0)
        Array.from({ length: orbCount }, (_, i) =>
          setTimeout(() => setVisibleOrbs(i + 1), i * 100)
        )
      }, 600 + orbCount * 120 + 700)
      const t5 = setTimeout(() => setPhase('storing'), 600 + orbCount * 120 + 1600)
      const t6 = setTimeout(() => setPhase('done'), 600 + orbCount * 120 + 2600)
      return () => [t1, t2, t3, t4, t5, t6].forEach(clearTimeout)
    } else if (status === 'error') {
      setPhase('idle')
    } else if (status === 'idle') {
      setPhase('idle')
    }
  }, [status, result, orbCount])

  const stages = [
    { id: 'upload',   icon: FileText,   label: 'Parse document',   done: phase !== 'idle' && phase !== 'uploading' },
    { id: 'chunk',    icon: Scissors,   label: 'Chunk text',       done: phase === 'embedding' || phase === 'storing' || phase === 'done' },
    { id: 'embed',    icon: Cpu,        label: 'Generate embeddings', done: phase === 'storing' || phase === 'done' },
    { id: 'store',    icon: Database,   label: 'Index vectors',    done: phase === 'done' },
  ]

  return (
    <div className="h-full flex flex-col">
      {/* Stage progress bar */}
      <div className="flex items-center gap-0 mb-8">
        {stages.map((s, i) => (
          <div key={s.id} className="flex items-center flex-1">
            <div className="flex flex-col items-center gap-1.5">
              <motion.div
                className={`w-8 h-8 rounded-full flex items-center justify-center border transition-all duration-500
                  ${s.done ? 'bg-violet-600/30 border-violet-400/60' :
                    (phase === 'uploading' && i === 0) ||
                    (phase === 'chunking' && i === 1) ||
                    (phase === 'embedding' && i === 2) ||
                    (phase === 'storing' && i === 3)
                    ? 'bg-violet-500/20 border-violet-500/40 animate-pulse-glow'
                    : 'bg-white/3 border-white/10'
                  }`}
                animate={s.done ? { scale: [1, 1.1, 1] } : {}}
                transition={{ duration: 0.3 }}
              >
                {s.done
                  ? <CheckCircle size={14} className="text-violet-400" />
                  : <s.icon size={14} className={`
                    ${(phase === 'uploading' && i === 0) || (phase === 'chunking' && i === 1) ||
                      (phase === 'embedding' && i === 2) || (phase === 'storing' && i === 3)
                      ? 'text-violet-400' : 'text-slate-600'}`} />
                }
              </motion.div>
              <span className="text-[10px] text-slate-500 text-center leading-tight max-w-[60px]">{s.label}</span>
            </div>
            {i < stages.length - 1 && (
              <div className="flex-1 h-px mx-1 mb-5">
                <motion.div
                  className="h-full bg-gradient-to-r from-violet-500/40 to-cyan-500/40"
                  initial={{ scaleX: 0, originX: 0 }}
                  animate={{ scaleX: s.done ? 1 : 0 }}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                />
                {!s.done && <div className="h-full bg-white/5" />}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Main visualization area */}
      <div className="flex-1 relative rounded-xl overflow-hidden bg-surface border border-violet-900/20 min-h-[320px]">
        <AnimatePresence mode="wait">

          {/* IDLE state */}
          {phase === 'idle' && (
            <motion.div
              key="idle"
              className="absolute inset-0 flex flex-col items-center justify-center gap-4"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            >
              <motion.div
                className="w-16 h-16 rounded-2xl glass border border-violet-500/20 flex items-center justify-center"
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              >
                <FileText size={28} className="text-violet-400/50" />
              </motion.div>
              <p className="text-slate-500 text-sm">Upload a document to see the ingestion pipeline</p>
            </motion.div>
          )}

          {/* UPLOADING state */}
          {phase === 'uploading' && (
            <motion.div
              key="uploading"
              className="absolute inset-0 flex flex-col items-center justify-center gap-4"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            >
              <div className="relative">
                <motion.div
                  className="w-20 h-20 rounded-full border-2 border-violet-500/30"
                  animate={{ scale: [1, 1.15, 1], opacity: [0.4, 0.8, 0.4] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <motion.div
                    className="w-12 h-12 rounded-full border-2 border-t-violet-500 border-violet-500/20"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  />
                </div>
                <div className="absolute inset-0 flex items-center justify-center">
                  <Cpu size={20} className="text-violet-400" />
                </div>
              </div>
              <p className="text-violet-300 text-sm font-medium">Processing document…</p>
              <p className="text-slate-500 text-xs">Parsing, chunking, embedding</p>
            </motion.div>
          )}

          {/* CHUNKING state */}
          {phase === 'chunking' && (
            <motion.div
              key="chunking"
              className="absolute inset-0 p-5 overflow-auto"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            >
              <p className="text-xs text-violet-400 font-medium mb-3 flex items-center gap-2">
                <Scissors size={12} />
                Chunking document into {result?.chunks_stored} segments
              </p>
              <div className="grid grid-cols-2 gap-2">
                {chunkPreviews.map((preview, i) => (
                  <motion.div
                    key={i}
                    className="rounded-lg border p-2.5 text-[11px] font-mono text-slate-300 leading-relaxed overflow-hidden"
                    style={{
                      borderColor: `${CHUNK_COLORS[i % CHUNK_COLORS.length]}40`,
                      backgroundColor: `${CHUNK_COLORS[i % CHUNK_COLORS.length]}08`,
                      boxShadow: i < visibleChunks ? `0 0 10px ${CHUNK_COLORS[i % CHUNK_COLORS.length]}20` : 'none',
                    }}
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={i < visibleChunks ? { scale: 1, opacity: 1 } : { scale: 0.8, opacity: 0 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                  >
                    <div className="flex items-center gap-1.5 mb-1">
                      <span
                        className="text-[9px] font-semibold px-1.5 py-0.5 rounded-sm font-mono"
                        style={{ color: CHUNK_COLORS[i % CHUNK_COLORS.length], backgroundColor: `${CHUNK_COLORS[i % CHUNK_COLORS.length]}20` }}
                      >
                        #{i + 1}
                      </span>
                    </div>
                    <span className="text-slate-400 line-clamp-2">{preview || '…'}</span>
                  </motion.div>
                ))}
                {result && result.chunks_stored > 12 && (
                  <div className="rounded-lg border border-white/10 p-2.5 flex items-center justify-center text-slate-500 text-xs">
                    +{result.chunks_stored - 12} more chunks
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* EMBEDDING state */}
          {phase === 'embedding' && (
            <motion.div
              key="embedding"
              className="absolute inset-0 flex flex-col items-center justify-center p-6"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            >
              <p className="text-xs text-cyan-400 font-medium mb-6 flex items-center gap-2">
                <Cpu size={12} />
                Encoding {orbCount} chunks into vector embeddings
              </p>
              {/* Vector space grid */}
              <div className="relative w-full max-w-xs h-48">
                {/* Grid lines */}
                <svg className="absolute inset-0 w-full h-full opacity-10">
                  {[1,2,3,4].map(i => (
                    <line key={`h${i}`} x1="0" y1={`${i*20}%`} x2="100%" y2={`${i*20}%`} stroke="#8B5CF6" strokeWidth="0.5" />
                  ))}
                  {[1,2,3,4,5,6].map(i => (
                    <line key={`v${i}`} x1={`${i*16.6}%`} y1="0" x2={`${i*16.6}%`} y2="100%" stroke="#8B5CF6" strokeWidth="0.5" />
                  ))}
                </svg>
                {/* Orbs */}
                {Array.from({ length: orbCount }, (_, i) => {
                  const angle = (2 * Math.PI * i) / orbCount
                  const rx = 38, ry = 32
                  const cx = 50 + rx * Math.cos(angle)
                  const cy = 50 + ry * Math.sin(angle)
                  const color = CHUNK_COLORS[i % CHUNK_COLORS.length]
                  return (
                    <motion.div
                      key={i}
                      className="absolute w-8 h-8 rounded-full flex items-center justify-center text-[9px] font-mono font-semibold"
                      style={{
                        left: `calc(${cx}% - 16px)`,
                        top: `calc(${cy}% - 16px)`,
                        backgroundColor: `${color}20`,
                        border: `1px solid ${color}60`,
                        color,
                        boxShadow: `0 0 12px ${color}40`,
                      }}
                      initial={{ scale: 0, opacity: 0 }}
                      animate={i < visibleOrbs ? { scale: 1, opacity: 1 } : { scale: 0, opacity: 0 }}
                      transition={{ type: 'spring', stiffness: 500, damping: 30, delay: i * 0.05 }}
                    >
                      {i + 1}
                    </motion.div>
                  )
                })}
                {/* Center label */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <motion.div
                    className="text-center"
                    animate={{ opacity: [0.4, 1, 0.4] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <p className="text-[10px] text-slate-500">vector space</p>
                  </motion.div>
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-4">
                {visibleOrbs}/{orbCount} vectors computed
              </p>
            </motion.div>
          )}

          {/* STORING state */}
          {phase === 'storing' && (
            <motion.div
              key="storing"
              className="absolute inset-0 flex flex-col items-center justify-center gap-5"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            >
              <motion.div
                className="w-20 h-20 rounded-2xl border-2 border-cyan-500/50 bg-cyan-500/10 flex items-center justify-center"
                animate={{ boxShadow: ['0 0 20px rgba(6,182,212,0.2)', '0 0 50px rgba(6,182,212,0.5)', '0 0 20px rgba(6,182,212,0.2)'] }}
                transition={{ duration: 1.2, repeat: Infinity }}
              >
                <Database size={32} className="text-cyan-400" />
              </motion.div>
              <div className="space-y-1 text-center">
                <p className="text-cyan-300 font-medium text-sm">Writing to vector store…</p>
                <p className="text-slate-500 text-xs">Persisting {result?.chunks_stored} indexed chunks</p>
              </div>
              <div className="w-40 h-1.5 bg-white/5 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-cyan-500 to-violet-500 rounded-full"
                  initial={{ width: '0%' }}
                  animate={{ width: '100%' }}
                  transition={{ duration: 0.8, ease: 'easeInOut' }}
                />
              </div>
            </motion.div>
          )}

          {/* DONE state */}
          {phase === 'done' && result && (
            <motion.div
              key="done"
              className="absolute inset-0 flex flex-col items-center justify-center gap-5 p-6"
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
            >
              <motion.div
                className="w-16 h-16 rounded-2xl bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center shadow-glow-green"
                animate={{ boxShadow: ['0 0 20px rgba(16,185,129,0.2)', '0 0 40px rgba(16,185,129,0.4)', '0 0 20px rgba(16,185,129,0.2)'] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <CheckCircle size={28} className="text-emerald-400" />
              </motion.div>

              <div className="text-center space-y-1">
                <p className="text-emerald-400 font-semibold text-base">Indexed successfully</p>
                <p className="text-slate-400 text-sm">
                  <span className="text-white font-semibold font-mono">{result.chunks_stored}</span> chunks stored for doc{' '}
                  <span className="text-violet-400 font-mono text-xs">"{result.doc_id}"</span>
                </p>
              </div>

              {/* Chunk ID list */}
              <div className="w-full max-w-sm max-h-28 overflow-y-auto rounded-lg bg-white/3 border border-white/8 p-3 space-y-1">
                {result.chunk_ids.slice(0, 8).map((id, i) => (
                  <motion.div
                    key={id}
                    className="flex items-center gap-2"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                  >
                    <div
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: CHUNK_COLORS[i % CHUNK_COLORS.length] }}
                    />
                    <span className="text-[11px] font-mono text-slate-400">{id}</span>
                  </motion.div>
                ))}
                {result.chunk_ids.length > 8 && (
                  <p className="text-[10px] text-slate-600 pl-4">+{result.chunk_ids.length - 8} more…</p>
                )}
              </div>
            </motion.div>
          )}

          {/* ERROR state */}
          {status === 'error' && (
            <motion.div
              key="error"
              className="absolute inset-0 flex flex-col items-center justify-center gap-4"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            >
              <div className="w-14 h-14 rounded-2xl bg-red-500/15 border border-red-500/40 flex items-center justify-center">
                <span className="text-2xl">⚠</span>
              </div>
              <div className="text-center space-y-1">
                <p className="text-red-400 font-medium text-sm">Upload failed</p>
                {error && <p className="text-slate-500 text-xs max-w-xs">{error}</p>}
              </div>
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </div>
  )
}

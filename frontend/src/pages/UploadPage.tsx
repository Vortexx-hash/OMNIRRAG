import { useState } from 'react'
import { motion } from 'framer-motion'
import { Upload, Zap } from 'lucide-react'
import { UploadForm } from '../components/upload/UploadForm'
import { IngestionFlow } from '../components/upload/IngestionFlow'
import type { UploadResponse } from '../types/api'

type Status = 'idle' | 'loading' | 'success' | 'error'

export function UploadPage() {
  const [status, setStatus] = useState<Status>('idle')
  const [result, setResult] = useState<UploadResponse | undefined>()
  const [inputText, setInputText] = useState('')
  const [fileName, setFileName] = useState<string | undefined>()
  const [error, setError] = useState('')

  function handleResult(r: UploadResponse, text: string, file?: string) {
    setResult(r)
    setInputText(text)
    setFileName(file)
  }

  function handleStatusChange(s: Status) {
    setStatus(s)
    if (s === 'loading') {
      setResult(undefined)
      setError('')
    }
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <motion.div
        className="mb-8 space-y-2"
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-violet-500/15 border border-violet-500/30 flex items-center justify-center shadow-glow-sm">
            <Upload size={16} className="text-violet-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100">Document Upload</h1>
            <p className="text-xs text-slate-500">Ingest documents into the conflict-aware knowledge base</p>
          </div>
        </div>

        {/* Pipeline hint */}
        <div className="flex items-center gap-2 mt-3 text-xs text-slate-500">
          <Zap size={11} className="text-violet-400" />
          <span>Upload triggers:</span>
          {['Chunking', 'Embedding', 'Credibility scoring', 'Vector indexing'].map((s, i) => (
            <span key={s} className="flex items-center gap-1">
              {i > 0 && <span className="text-slate-700">·</span>}
              <span className="text-slate-400">{s}</span>
            </span>
          ))}
        </div>
      </motion.div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Form */}
        <motion.div
          className="glass rounded-2xl p-6"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.45, delay: 0.1 }}
        >
          <h2 className="text-sm font-semibold text-slate-300 mb-5 flex items-center gap-2">
            <span className="w-5 h-5 rounded-md bg-violet-500/20 border border-violet-500/30 flex items-center justify-center text-[10px] font-bold text-violet-400">1</span>
            Document Details
          </h2>
          <UploadForm
            onStatusChange={handleStatusChange}
            onResult={handleResult}
            onError={setError}
          />
        </motion.div>

        {/* Right: Ingestion visualizer */}
        <motion.div
          className="glass rounded-2xl p-6"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.45, delay: 0.15 }}
        >
          <h2 className="text-sm font-semibold text-slate-300 mb-5 flex items-center gap-2">
            <span className="w-5 h-5 rounded-md bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center text-[10px] font-bold text-cyan-400">2</span>
            Ingestion Pipeline
          </h2>
          <IngestionFlow
            status={status}
            result={result}
            inputText={inputText}
            fileName={fileName}
            error={error}
          />
        </motion.div>
      </div>
    </div>
  )
}

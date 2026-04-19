import { useState } from 'react'
import { motion } from 'framer-motion'
import { Upload, FileText, Tag, User, Link, ChevronDown } from 'lucide-react'
import { api } from '../../api/client'
import type { UploadRequest, UploadResponse } from '../../types/api'

interface UploadFormProps {
  onStatusChange: (status: 'idle' | 'loading' | 'success' | 'error') => void
  onResult: (result: UploadResponse, text: string) => void
  onError: (msg: string) => void
}

const SOURCE_TYPES = ['academic', 'government', 'blog', 'unverified']
const STRATEGIES = ['semantic', 'character', 'overlap', 'hybrid']

export function UploadForm({ onStatusChange, onResult, onError }: UploadFormProps) {
  const [text, setText] = useState('')
  const [docId, setDocId] = useState('')
  const [sourceType, setSourceType] = useState('academic')
  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [url, setUrl] = useState('')
  const [strategy, setStrategy] = useState('semantic')
  const [showAdvanced, setShowAdvanced] = useState(false)

  const canSubmit = text.trim().length > 0 && docId.trim().length > 0

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return

    onStatusChange('loading')

    const body: UploadRequest = {
      text: text.trim(),
      doc_id: docId.trim(),
      source_metadata: {
        source_type: sourceType,
        ...(title && { title }),
        ...(author && { author }),
        ...(url && { url }),
      },
      chunking_strategy: strategy as UploadRequest['chunking_strategy'],
    }

    try {
      const result = await api.upload(body)
      onResult(result, text)
      onStatusChange('success')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      onError(msg)
      onStatusChange('error')
    }
  }

  const fieldCls = 'w-full bg-surface border border-violet-900/30 rounded-lg px-3 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/20 transition-all duration-200'

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Document text */}
      <div className="space-y-1.5">
        <label className="flex items-center gap-2 text-xs font-medium text-slate-400">
          <FileText size={12} className="text-violet-400" />
          Document Text
          <span className="text-red-400">*</span>
        </label>
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Paste your document content here…"
          rows={8}
          className={`${fieldCls} resize-none font-mono text-[12px] leading-relaxed`}
        />
        {text && (
          <p className="text-[11px] text-slate-600 text-right font-mono">
            {text.length.toLocaleString()} chars · ~{Math.ceil(text.split(/\s+/).length / 150)} min read
          </p>
        )}
      </div>

      {/* Doc ID */}
      <div className="space-y-1.5">
        <label className="flex items-center gap-2 text-xs font-medium text-slate-400">
          <Tag size={12} className="text-violet-400" />
          Document ID
          <span className="text-red-400">*</span>
        </label>
        <input
          value={docId}
          onChange={e => setDocId(e.target.value)}
          placeholder="e.g. climate-report-2024"
          className={fieldCls}
        />
      </div>

      {/* Source type */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-slate-400">Source Type</label>
        <div className="flex gap-2 flex-wrap">
          {SOURCE_TYPES.map(t => (
            <button
              key={t}
              type="button"
              onClick={() => setSourceType(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200
                ${sourceType === t
                  ? 'bg-violet-600/25 border-violet-500/50 text-violet-300 shadow-glow-sm'
                  : 'border-violet-900/30 text-slate-500 hover:border-violet-700/40 hover:text-slate-300'
                }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Advanced toggle */}
      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-300 transition-colors"
      >
        <motion.span animate={{ rotate: showAdvanced ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown size={14} />
        </motion.span>
        Advanced options
      </button>

      {showAdvanced && (
        <motion.div
          className="space-y-3 pl-4 border-l border-violet-900/30"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
        >
          <div className="space-y-1.5">
            <label className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <User size={11} className="text-violet-400" />
              Title
            </label>
            <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Document title" className={fieldCls} />
          </div>
          <div className="space-y-1.5">
            <label className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <User size={11} className="text-violet-400" />
              Author
            </label>
            <input value={author} onChange={e => setAuthor(e.target.value)} placeholder="Author name" className={fieldCls} />
          </div>
          <div className="space-y-1.5">
            <label className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <Link size={11} className="text-violet-400" />
              URL
            </label>
            <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://…" className={fieldCls} />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-400">Chunking Strategy</label>
            <div className="flex gap-2 flex-wrap">
              {STRATEGIES.map(s => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setStrategy(s)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all
                    ${strategy === s
                      ? 'bg-cyan-600/20 border-cyan-500/40 text-cyan-300'
                      : 'border-violet-900/30 text-slate-500 hover:border-violet-700/40 hover:text-slate-300'
                    }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* Submit */}
      <motion.button
        type="submit"
        disabled={!canSubmit}
        className={`w-full flex items-center justify-center gap-2.5 py-3 rounded-xl font-medium text-sm transition-all duration-300
          ${canSubmit
            ? 'bg-gradient-to-r from-violet-700 to-violet-600 hover:from-violet-600 hover:to-violet-500 text-white shadow-glow-violet cursor-pointer'
            : 'bg-white/5 text-slate-600 cursor-not-allowed border border-white/8'
          }`}
        whileTap={canSubmit ? { scale: 0.98 } : {}}
      >
        <Upload size={16} />
        Ingest document
      </motion.button>
    </form>
  )
}

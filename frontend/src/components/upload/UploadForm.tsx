import { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, FileText, Tag, User, Link, ChevronDown, FileUp, X, File, Globe, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react'
import { api } from '../../api/client'
import type { UploadRequest, UploadResponse } from '../../types/api'

interface UploadFormProps {
  onStatusChange: (status: 'idle' | 'loading' | 'success' | 'error') => void
  onResult: (result: UploadResponse, text: string, fileName?: string) => void
  onError: (msg: string) => void
}

type Mode = 'text' | 'pdf' | 'url'
const SOURCE_TYPES = ['peer_reviewed', 'journal', 'academic', 'government', 'blog', 'unverified']

const SOURCE_TYPE_LABELS: Record<string, string> = {
  peer_reviewed: 'Peer Reviewed',
  journal: 'Journal',
  academic: 'Academic',
  government: 'Government',
  blog: 'Blog',
  unverified: 'Unverified',
}

const SOURCE_TYPE_TIERS: Record<string, string> = {
  peer_reviewed: 'T1',
  journal: 'T1',
  academic: 'T2',
  government: 'T1',
  blog: 'T3',
  unverified: 'T4',
}

const SOURCE_TYPE_TIER_COLORS: Record<string, string> = {
  T1: 'text-emerald-400',
  T2: 'text-cyan-400',
  T3: 'text-amber-400',
  T4: 'text-red-400',
}
const STRATEGIES  = ['semantic', 'character', 'overlap', 'hybrid']

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function UploadForm({ onStatusChange, onResult, onError }: UploadFormProps) {
  const [mode, setMode] = useState<Mode>('text')

  // Text-mode state
  const [text, setText] = useState('')

  // PDF-mode state
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // URL-mode state
  const [urlValue, setUrlValue] = useState('')
  const [urlValidating, setUrlValidating] = useState(false)
  const [urlValid, setUrlValid] = useState<boolean | null>(null)
  const [urlSuggestedType, setUrlSuggestedType] = useState<string | null>(null)
  const urlDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Shared state
  const [docId, setDocId]         = useState('')
  const [sourceType, setSourceType] = useState('peer_reviewed')
  const [title, setTitle]         = useState('')
  const [author, setAuthor]       = useState('')
  const [url, setUrl]             = useState('')
  const [strategy, setStrategy]   = useState('semantic')
  const [showAdvanced, setShowAdvanced] = useState(false)

  const isValidUrl = (s: string) => { try { new URL(s); return true } catch { return false } }
  const canSubmit = docId.trim().length > 0 && (
    mode === 'text' ? text.trim().length > 0 :
    mode === 'pdf' ? pdfFile !== null :
    isValidUrl(urlValue.trim())
  )

  // Auto-fill doc_id + suggest source type when URL changes
  useEffect(() => {
    if (mode !== 'url') return
    if (urlDebounceRef.current) clearTimeout(urlDebounceRef.current)
    const raw = urlValue.trim()
    if (!raw || !isValidUrl(raw)) {
      setUrlValid(raw ? false : null)
      setUrlSuggestedType(null)
      return
    }
    setUrlValid(true)
    // Auto-fill doc_id from URL
    if (!docId) {
      try {
        const u = new URL(raw)
        const slug = (u.hostname + u.pathname)
          .replace(/[^a-z0-9]+/gi, '-')
          .replace(/^-|-$/g, '')
          .toLowerCase()
          .slice(0, 60)
        setDocId(slug)
      } catch { /* ignore */ }
    }
    // Debounce the suggest API call
    setUrlValidating(true)
    urlDebounceRef.current = setTimeout(async () => {
      try {
        const res = await api.suggestSourceType(raw)
        setUrlSuggestedType(res.suggested_source_type)
        setSourceType(res.suggested_source_type)
      } catch { /* ignore */ } finally {
        setUrlValidating(false)
      }
    }, 600)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlValue, mode])

  // ── PDF drag-and-drop handlers ──────────────────────────────────────────
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file && file.name.toLowerCase().endsWith('.pdf')) {
      setPdfFile(file)
      if (!docId) setDocId(file.name.replace(/\.pdf$/i, '').replace(/[\s_]+/g, '-').toLowerCase())
      if (!title) setTitle(file.name.replace(/\.pdf$/i, ''))
    }
  }, [docId, title])

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setPdfFile(file)
    if (!docId) setDocId(file.name.replace(/\.pdf$/i, '').replace(/[\s_]+/g, '-').toLowerCase())
    if (!title) setTitle(file.name.replace(/\.pdf$/i, ''))
  }, [docId, title])

  // ── Submit ──────────────────────────────────────────────────────────────
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    onStatusChange('loading')

    try {
      if (mode === 'text') {
        const body: UploadRequest = {
          text: text.trim(),
          doc_id: docId.trim(),
          source_metadata: {
            source_type: sourceType,
            ...(title  && { title }),
            ...(author && { author }),
            ...(url    && { url }),
          },
          chunking_strategy: strategy as UploadRequest['chunking_strategy'],
        }
        const result = await api.upload(body)
        onResult(result, text)
      } else if (mode === 'pdf') {
        const fd = new FormData()
        fd.append('file', pdfFile!)
        fd.append('doc_id', docId.trim())
        fd.append('source_type', sourceType)
        fd.append('chunking_strategy', strategy)
        if (title)  fd.append('title', title)
        if (author) fd.append('author', author)
        if (url)    fd.append('url', url)
        const result = await api.uploadPdf(fd)
        onResult(result, '', pdfFile!.name)
      } else {
        const result = await api.uploadUrl({
          url: urlValue.trim(),
          doc_id: docId.trim(),
          source_type: sourceType,
          chunking_strategy: strategy,
          ...(title  && { title }),
          ...(author && { author }),
        })
        onResult(result, '', urlValue.trim())
      }
      onStatusChange('success')
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Upload failed')
      onStatusChange('error')
    }
  }

  const fieldCls = 'w-full bg-surface border border-violet-900/30 rounded-lg px-3 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/20 transition-all duration-200'

  return (
    <form onSubmit={handleSubmit} className="space-y-5">

      {/* Mode toggle */}
      <div className="flex rounded-xl overflow-hidden border border-violet-900/30 p-1 gap-1 bg-surface">
        {([
          { id: 'text', icon: <FileText size={13} />, label: 'Paste Text' },
          { id: 'pdf',  icon: <File size={13} />,     label: 'Upload PDF' },
          { id: 'url',  icon: <Globe size={13} />,    label: 'Web URL' },
        ] as { id: Mode; icon: React.ReactNode; label: string }[]).map(m => (
          <button
            key={m.id}
            type="button"
            onClick={() => setMode(m.id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-all duration-200
              ${mode === m.id
                ? 'bg-violet-600/25 border border-violet-500/40 text-violet-300 shadow-glow-sm'
                : 'text-slate-500 hover:text-slate-300'
              }`}
          >
            {m.icon}
            {m.label}
          </button>
        ))}
      </div>

      {/* ── TEXT MODE ─────────────────────────────────────────────────── */}
      <AnimatePresence mode="wait">
        {mode === 'text' && (
          <motion.div
            key="text"
            className="space-y-1.5"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
          >
            <label className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <FileText size={12} className="text-violet-400" />
              Document Text <span className="text-red-400">*</span>
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
                {text.length.toLocaleString()} chars
              </p>
            )}
          </motion.div>
        )}

        {/* ── PDF MODE ──────────────────────────────────────────────────── */}
        {mode === 'pdf' && (
          <motion.div
            key="pdf"
            className="space-y-1.5"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
          >
            <label className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <File size={12} className="text-violet-400" />
              PDF File <span className="text-red-400">*</span>
            </label>

            {pdfFile ? (
              /* File selected state */
              <motion.div
                className="flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/5 px-4 py-3"
                initial={{ scale: 0.97, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
              >
                <div className="w-10 h-10 rounded-lg bg-red-500/15 border border-red-500/30 flex items-center justify-center flex-shrink-0">
                  <FileUp size={18} className="text-red-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">{pdfFile.name}</p>
                  <p className="text-[11px] text-slate-500 font-mono">{formatBytes(pdfFile.size)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => { setPdfFile(null); if (fileInputRef.current) fileInputRef.current.value = '' }}
                  className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
                >
                  <X size={14} />
                </button>
              </motion.div>
            ) : (
              /* Drop zone */
              <div
                onDragOver={e => { e.preventDefault(); setDragging(true) }}
                onDragEnter={e => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`relative rounded-xl border-2 border-dashed px-6 py-10 text-center cursor-pointer transition-all duration-200
                  ${dragging
                    ? 'border-violet-500 bg-violet-500/10 scale-[1.01]'
                    : 'border-violet-900/40 hover:border-violet-500/50 hover:bg-violet-500/5'
                  }`}
              >
                <motion.div
                  className="flex flex-col items-center gap-3"
                  animate={dragging ? { scale: 1.05 } : { scale: 1 }}
                >
                  <div className={`w-12 h-12 rounded-xl border flex items-center justify-center transition-all
                    ${dragging ? 'bg-violet-500/20 border-violet-500/50' : 'bg-white/5 border-white/10'}`}
                  >
                    <FileUp size={22} className={dragging ? 'text-violet-400' : 'text-slate-500'} />
                  </div>
                  <div>
                    <p className={`text-sm font-medium ${dragging ? 'text-violet-300' : 'text-slate-400'}`}>
                      {dragging ? 'Drop your PDF here' : 'Drag & drop a PDF'}
                    </p>
                    <p className="text-xs text-slate-600 mt-0.5">or click to browse — text-based PDFs only</p>
                  </div>
                </motion.div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>
            )}
          </motion.div>
        )}
        {/* ── URL MODE ──────────────────────────────────────────────────── */}
        {mode === 'url' && (
          <motion.div
            key="url"
            className="space-y-3"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
          >
            <label className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <Globe size={12} className="text-violet-400" />
              Web Page URL <span className="text-red-400">*</span>
            </label>

            {/* URL input */}
            <div className="relative">
              <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
                {urlValidating
                  ? <Loader2 size={14} className="text-violet-400 animate-spin" />
                  : urlValid === true
                    ? <CheckCircle2 size={14} className="text-emerald-400" />
                    : urlValid === false
                      ? <AlertCircle size={14} className="text-red-400" />
                      : <Globe size={14} className="text-slate-500" />
                }
              </div>
              <input
                value={urlValue}
                onChange={e => { setUrlValue(e.target.value); setUrlValid(null) }}
                placeholder="https://example.com/article"
                className={`${fieldCls} pl-9 font-mono text-[12px] ${
                  urlValid === false ? 'border-red-500/50 focus:border-red-500/60' : ''
                }`}
              />
            </div>

            {/* Validation feedback */}
            <AnimatePresence>
              {urlValid === false && urlValue && (
                <motion.p
                  className="text-[11px] text-red-400 flex items-center gap-1.5"
                  initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                >
                  <AlertCircle size={10} /> Enter a valid URL starting with http:// or https://
                </motion.p>
              )}
              {urlSuggestedType && urlValid && (
                <motion.p
                  className="text-[11px] text-emerald-400/80 flex items-center gap-1.5"
                  initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                >
                  <CheckCircle2 size={10} />
                  Domain recognized — source type auto-set to <span className="font-semibold">{urlSuggestedType}</span>
                </motion.p>
              )}
            </AnimatePresence>

            {/* Limitations notice */}
            <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2.5 space-y-1">
              <p className="text-[11px] text-amber-400/80 font-medium">Supported pages</p>
              <ul className="text-[11px] text-slate-500 space-y-0.5 list-disc list-inside">
                <li>Static HTML pages (Wikipedia, news articles, academic pages)</li>
                <li>Pages with machine-readable text content</li>
                <li className="text-slate-600">Not supported: JavaScript-only SPAs, paywalled content, login-required pages</li>
              </ul>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Doc ID */}
      <div className="space-y-1.5">
        <label className="flex items-center gap-2 text-xs font-medium text-slate-400">
          <Tag size={12} className="text-violet-400" />
          Document ID <span className="text-red-400">*</span>
        </label>
        <input
          value={docId}
          onChange={e => setDocId(e.target.value)}
          placeholder="e.g. aspirin-study-2024"
          className={fieldCls}
        />
      </div>

      {/* Source type */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-slate-400">
          Source Type <span className="text-slate-600 font-normal">(determines credibility tier)</span>
        </label>
        <div className="flex gap-2 flex-wrap">
          {SOURCE_TYPES.map(t => {
            const tier = SOURCE_TYPE_TIERS[t]
            const tierColor = SOURCE_TYPE_TIER_COLORS[tier]
            return (
              <button
                key={t}
                type="button"
                onClick={() => setSourceType(t)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200
                  ${sourceType === t
                    ? 'bg-violet-600/25 border-violet-500/50 text-violet-300 shadow-glow-sm'
                    : 'border-violet-900/30 text-slate-500 hover:border-violet-700/40 hover:text-slate-300'
                  }`}
              >
                {SOURCE_TYPE_LABELS[t]}
                <span className={`text-[10px] font-mono font-bold ${tierColor} opacity-80`}>{tier}</span>
              </button>
            )
          })}
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

      <AnimatePresence>
        {showAdvanced && (
          <motion.div
            className="space-y-3 pl-4 border-l border-violet-900/30"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <div className="space-y-1.5">
              <label className="flex items-center gap-2 text-xs font-medium text-slate-400">
                <FileText size={11} className="text-violet-400" /> Title
              </label>
              <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Document title" className={fieldCls} />
            </div>
            <div className="space-y-1.5">
              <label className="flex items-center gap-2 text-xs font-medium text-slate-400">
                <User size={11} className="text-violet-400" /> Author
              </label>
              <input value={author} onChange={e => setAuthor(e.target.value)} placeholder="Author name" className={fieldCls} />
            </div>
            <div className="space-y-1.5">
              <label className="flex items-center gap-2 text-xs font-medium text-slate-400">
                <Link size={11} className="text-violet-400" /> URL
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
      </AnimatePresence>

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
        {mode === 'pdf' ? 'Parse & Ingest PDF' : mode === 'url' ? 'Fetch & Ingest URL' : 'Ingest document'}
      </motion.button>
    </form>
  )
}

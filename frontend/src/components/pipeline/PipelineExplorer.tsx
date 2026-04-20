import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronLeft, ChevronRight } from 'lucide-react'

// ─── Shared primitives ────────────────────────────────────────────────────────

function GlowBox({ color, title, children, className = '' }: {
  color: string; title?: string; children: React.ReactNode; className?: string
}) {
  return (
    <div
      className={`rounded-xl p-4 ${className}`}
      style={{ background: `${color}0a`, border: `1px solid ${color}35`, boxShadow: `0 0 20px ${color}12` }}
    >
      {title && (
        <p className="text-[10px] font-bold tracking-widest uppercase mb-3" style={{ color }}>
          {title}
        </p>
      )}
      {children}
    </div>
  )
}

function Bar({ pct, color, label, sub }: { pct: number; color: string; label: string; sub?: string }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[11px]">
        <span className="text-slate-300">{label}</span>
        {sub && <span className="text-slate-500">{sub}</span>}
      </div>
      <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, delay: 0.1 }}
        />
      </div>
    </div>
  )
}

function Bubble({ color, from, children }: { color: string; from: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl p-3" style={{ background: `${color}08`, border: `1px solid ${color}25` }}>
      <p className="text-[9px] font-bold tracking-wider uppercase mb-1.5" style={{ color }}>{from}</p>
      <p className="text-[12px] text-slate-300 leading-relaxed">{children}</p>
    </div>
  )
}

function Chunk({ id, text, color }: { id: string; text: string; color: string }) {
  return (
    <motion.div
      className="rounded-lg px-3 py-2 text-[11px]"
      style={{ background: `${color}12`, border: `1px solid ${color}30` }}
      initial={{ opacity: 0, scale: 0.92 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <span className="font-bold font-mono" style={{ color }}>{id}</span>
      <span className="text-slate-400 ml-2">{text}</span>
    </motion.div>
  )
}

// ─── Stage 0: Query ───────────────────────────────────────────────────────────

function Stage0() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div className="space-y-4">
        <GlowBox color="#4488ff" title="What it does">
          <p className="text-[12px] text-slate-400 leading-relaxed">
            Removes filler words, normalises phrasing, and extracts key <span className="text-slate-200 font-medium">entities</span> and{' '}
            <span className="text-slate-200 font-medium">intent</span>. The output is a clean query vector used in retrieval.
          </p>
          <div className="mt-3 pt-3 border-t border-white/5">
            <p className="text-[11px] font-semibold text-slate-400 mb-2">WHY THIS MATTERS</p>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              A messy query produces noisy embeddings. Normalisation ensures "What's the capital city of Bolivia?" and "Bolivia capital?"
              map to the same retrieval space.
            </p>
          </div>
        </GlowBox>
      </div>
      <div className="space-y-3">
        <GlowBox color="#4488ff" title="Example — raw user query">
          <p className="text-base text-slate-200 italic">"What is the capital of Bolivia?"</p>
        </GlowBox>
        <div className="text-center text-slate-600">↓ normalise → embed</div>
        <GlowBox color="#22ddaa" title="Normalised output">
          <div className="font-mono text-[12px] text-emerald-300 bg-black/30 px-3 py-2 rounded-lg mb-3">
            query = "capital Bolivia"
          </div>
          <div className="flex flex-wrap gap-2">
            {[
              { label: 'entity: Bolivia', color: '#4488ff' },
              { label: 'property: capital', color: '#aa66ff' },
              { label: 'intent: factual lookup', color: '#22ddaa' },
            ].map(t => (
              <span
                key={t.label}
                className="text-[10px] px-2.5 py-1 rounded-full border font-medium"
                style={{ borderColor: t.color, color: t.color, background: `${t.color}15` }}
              >
                {t.label}
              </span>
            ))}
          </div>
        </GlowBox>
      </div>
    </div>
  )
}

// ─── Stage 1: Retriever ───────────────────────────────────────────────────────

function Stage1() {
  const results = [
    { id: 'C1', text: 'Sucre is the constitutional capital…', sim: 92, color: '#22ddaa' },
    { id: 'C2', text: 'La Paz is the seat of government…', sim: 88, color: '#22ddaa' },
    { id: 'C7', text: 'The capital is Santa Cruz…', sim: 74, color: '#ffaa33' },
    { id: 'C8', text: 'Largest city is Santa Cruz…', sim: 21, color: '#6868a0', dropped: true },
  ]
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div
          className="rounded-xl p-3"
          style={{ background: 'rgba(34,221,170,0.06)', border: '1px solid rgba(34,221,170,0.25)' }}
        >
          <p className="text-[9px] font-bold tracking-wider text-emerald-400 uppercase mb-2">📥 Phase 1 — Document Upload Time</p>
          <div className="space-y-1.5 text-[11px] text-slate-400">
            <p><span className="text-emerald-400 font-bold">1.</span> Chunk the document</p>
            <p><span className="text-emerald-400 font-bold">2.</span> Encode each chunk → embedding</p>
            <p><span className="text-emerald-400 font-bold">3.</span> Store embeddings in vector DB</p>
          </div>
          <p className="text-[9px] text-emerald-400/60 mt-2">Done once, offline — before any query arrives</p>
        </div>
        <div
          className="rounded-xl p-3"
          style={{ background: 'rgba(170,102,255,0.06)', border: '1px solid rgba(170,102,255,0.25)' }}
        >
          <p className="text-[9px] font-bold tracking-wider text-violet-400 uppercase mb-2">🔍 Phase 2 — Query Time (this stage)</p>
          <div className="space-y-1.5 text-[11px] text-slate-400">
            <p><span className="text-violet-400 font-bold">4.</span> Encode user query → embedding</p>
            <p><span className="text-violet-400 font-bold">5.</span> Cosine similarity vs all chunk vectors</p>
            <p><span className="text-violet-400 font-bold">6.</span> Return top-K most similar chunks</p>
          </div>
          <p className="text-[9px] text-violet-400/60 mt-2">Happens live — for every user query</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <GlowBox color="#4488ff" title="Cosine similarity formula">
          <p className="text-[12px] text-slate-400 mb-3 leading-relaxed">
            The query embedding is compared against every stored chunk. Top-K chunks are returned regardless of credibility — every chunk gets a fair shot.
          </p>
          <div className="font-mono text-[11px] text-blue-300 bg-black/30 px-3 py-2 rounded-lg">
            sim(q, d) = q·d / (|q| |d|)  ∈ [−1, 1]
          </div>
          <GlowBox color="#aa66ff" title="Why not BM25?" className="mt-3">
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Dense embedding models capture <span className="text-slate-200">semantic meaning</span>, not keyword overlap —
              retrieving relevant chunks even when they use different words than the query.
            </p>
          </GlowBox>
        </GlowBox>
        <div>
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Retrieval results for "capital of Bolivia"</p>
          <div className="space-y-2">
            {results.map((r, i) => (
              <motion.div
                key={r.id}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 ${r.dropped ? 'opacity-35' : ''}`}
                style={{ background: `${r.color}0a`, border: `1px solid ${r.color}25` }}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: r.dropped ? 0.35 : 1, x: 0 }}
                transition={{ delay: i * 0.08 }}
              >
                <span className="font-mono text-[11px] w-6" style={{ color: r.color }}>{r.id}</span>
                <span className="flex-1 text-[11px] text-slate-400 truncate italic">"{r.text}"</span>
                <div className="w-16 h-1.5 rounded-full bg-white/5 overflow-hidden flex-shrink-0">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: r.color }}
                    initial={{ width: 0 }}
                    animate={{ width: `${r.sim}%` }}
                    transition={{ delay: i * 0.08 + 0.2, duration: 0.5 }}
                  />
                </div>
                <span className="text-[10px] font-mono w-7 text-right flex-shrink-0" style={{ color: r.color }}>
                  {r.sim}%
                </span>
                {r.dropped && <span className="text-[9px] text-slate-600">↓ dropped</span>}
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Stage 2: Chunker ─────────────────────────────────────────────────────────

function Stage2() {
  const chunks = [
    { id: 'C1', src: 'D1 · Britannica', text: 'Sucre is the constitutional capital of Bolivia.', color: '#22ddaa' },
    { id: 'C2', src: 'D2 · Embassy', text: 'La Paz is the administrative capital and seat of government.', color: '#4488ff' },
    { id: 'C3', src: 'D3 · Textbook', text: 'Bolivia has two capitals in different senses.', color: '#aa66ff' },
    { id: 'C4', src: 'D3 · Textbook', text: 'Sucre is the constitutional capital.', color: '#aa66ff' },
    { id: 'C5', src: 'D3 · Textbook', text: 'La Paz is the seat of government.', color: '#aa66ff' },
    { id: 'C6', src: 'D4 · Blog', text: 'The capital of Bolivia is La Paz.', color: '#ffaa33' },
    { id: 'C7', src: 'D5 · Forum', text: "Bolivia's capital is Santa Cruz. ⚠", color: '#ff6677' },
    { id: 'C8', src: 'D6 · Scraped', text: "Santa Cruz is Bolivia's largest city. (noise)", color: '#6868a0' },
  ]
  const strategies = [
    { name: 'Semantic', color: '#22ddaa', desc: 'Splits on topic/meaning shift. Best quality, higher cost.' },
    { name: 'Character', color: '#4488ff', desc: 'Fixed-size chunks. Simple and fast, may cut mid-sentence.' },
    { name: 'Overlap', color: '#aa66ff', desc: 'Adjacent chunks share a window — preserves boundary context.' },
    { name: 'Hybrid', color: '#ffaa33', desc: 'Semantic splits + character overlap within each block. Most robust.' },
  ]
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div className="space-y-4">
        <GlowBox color="#22ddaa" title="⏰ Chunking happens at upload time, not query time">
          <p className="text-[12px] text-slate-400 leading-relaxed">
            Chunks are created when documents are uploaded — each chunk is encoded into an embedding and stored in the
            vector DB. By query time, all embeddings are already ready. This enables fine-grained claim-level comparison.
          </p>
        </GlowBox>
        <div className="space-y-2">
          {strategies.map(s => (
            <div key={s.name} className="rounded-lg px-3 py-2.5" style={{ background: `${s.color}0a`, border: `1px solid ${s.color}25` }}>
              <p className="text-[11px] font-semibold mb-0.5" style={{ color: s.color }}>{s.name} Chunking</p>
              <p className="text-[10px] text-slate-500">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
      <div>
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">All 8 chunks stored in vector DB</p>
        <div className="space-y-1.5">
          {chunks.map((c, i) => (
            <motion.div
              key={c.id}
              className="rounded-lg px-3 py-2 text-[11px]"
              style={{ background: `${c.color}10`, border: `1px solid ${c.color}28` }}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.06 }}
            >
              <span className="font-bold font-mono" style={{ color: c.color }}>{c.id}</span>
              <span className="text-slate-500 mx-1.5 text-[9px]">({c.src})</span>
              <span className="text-slate-300">{c.text}</span>
            </motion.div>
          ))}
        </div>
        <p className="text-[10px] text-slate-600 mt-3 font-mono">chunk_id = f"{"{doc_id}"}_chunk_{"{i}"}"</p>
      </div>
    </div>
  )
}

// ─── Stage 3: Relations ───────────────────────────────────────────────────────

function RelevanceTab() {
  const data = [
    { id: 'C1', pct: 90, color: '#22ddaa', label: 'High' },
    { id: 'C2', pct: 88, color: '#22ddaa', label: 'High' },
    { id: 'C3', pct: 72, color: '#aa66ff', label: 'Med' },
    { id: 'C4', pct: 85, color: '#22ddaa', label: 'High' },
    { id: 'C5', pct: 83, color: '#aa66ff', label: 'Med' },
    { id: 'C6', pct: 80, color: '#4488ff', label: 'High' },
    { id: 'C7', pct: 60, color: '#ffaa33', label: 'Med' },
    { id: 'C8', pct: 20, color: '#6868a0', label: 'Low' },
  ]
  const R = 16, C = 2 * Math.PI * R
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <GlowBox color="#ffaa33" title="How it works">
        <p className="text-[12px] text-slate-400 leading-relaxed mb-3">
          Each chunk is encoded into a vector. Cosine similarity is computed against the query vector.
          Higher score = more directly answers the question.
        </p>
        <div className="font-mono text-[11px] text-amber-300 bg-black/30 px-3 py-2 rounded-lg">
          sim(query, chunk) = cos(v_q, v_c)
        </div>
      </GlowBox>
      <div>
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Relevance scores per chunk</p>
        <div className="grid grid-cols-4 gap-2">
          {data.map((d, i) => (
            <motion.div
              key={d.id}
              className="rounded-xl flex flex-col items-center py-3"
              style={{ background: `${d.color}0e`, border: `1px solid ${d.color}25` }}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.07 }}
            >
              <p className="text-[10px] font-mono text-slate-400 mb-2">{d.id}</p>
              <div className="relative w-10 h-10">
                <svg viewBox="0 0 40 40" className="w-full h-full -rotate-90">
                  <circle cx="20" cy="20" r={R} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="4" />
                  <motion.circle
                    cx="20" cy="20" r={R} fill="none" stroke={d.color} strokeWidth="4" strokeLinecap="round"
                    strokeDasharray={`${C}`}
                    initial={{ strokeDashoffset: C }}
                    animate={{ strokeDashoffset: C * (1 - d.pct / 100) }}
                    transition={{ delay: i * 0.07 + 0.2, duration: 0.7 }}
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-[10px] font-bold" style={{ color: d.color }}>{d.pct}%</span>
                </div>
              </div>
              <p className="text-[9px] mt-1.5" style={{ color: d.color }}>{d.label}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}

function SimilarityTab() {
  const labels = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7']
  const matrix = [
    [1.00, 0.30, 0.60, 0.92, 0.20, 0.30, 0.10],
    [0.30, 1.00, 0.60, 0.25, 0.85, 0.88, 0.15],
    [0.60, 0.60, 1.00, 0.70, 0.70, 0.50, 0.20],
    [0.92, 0.25, 0.70, 1.00, 0.22, 0.28, 0.12],
    [0.20, 0.85, 0.70, 0.22, 1.00, 0.80, 0.18],
    [0.30, 0.88, 0.50, 0.28, 0.80, 1.00, 0.16],
    [0.10, 0.15, 0.20, 0.12, 0.18, 0.16, 1.00],
  ]
  const pairs = [
    { a: 'C1', b: 'C4', sim: 0.92, note: 'Redundant — same claim, different source' },
    { a: 'C2', b: 'C6', sim: 0.88, note: 'Redundant — both say La Paz is capital' },
    { a: 'C2', b: 'C5', sim: 0.85, note: 'Redundant — seat of government = same' },
  ]
  function cellColor(v: number) {
    if (v >= 0.85) return '#ff6677'
    if (v >= 0.60) return '#22ddaa'
    if (v >= 0.30) return '#4488ff'
    return '#3a3a60'
  }
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div className="space-y-3">
        <GlowBox color="#4488ff" title="Pairwise cosine similarity">
          <p className="text-[12px] text-slate-400 leading-relaxed mb-3">
            Detects which chunks express the same information. Pairs ≥0.85 are flagged redundant for DPP to drop.
          </p>
          <div className="space-y-2">
            {pairs.map((p, i) => (
              <motion.div
                key={i}
                className="flex items-center gap-2 text-[11px]"
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <span className="font-mono text-red-400">{p.a}↔{p.b}</span>
                <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-red-400"
                    initial={{ width: 0 }}
                    animate={{ width: `${p.sim * 100}%` }}
                    transition={{ delay: i * 0.1 + 0.2, duration: 0.5 }}
                  />
                </div>
                <span className="text-red-400 font-mono w-8 text-right">{p.sim}</span>
                <span className="text-slate-500 text-[9px] w-36 truncate">{p.note}</span>
              </motion.div>
            ))}
          </div>
        </GlowBox>
        <div className="flex flex-wrap gap-2 text-[10px]">
          {[['#ff6677', '≥0.85 redundant'], ['#22ddaa', '0.60–0.84'], ['#4488ff', '0.30–0.59'], ['#3a3a60', '<0.30']].map(([c, l]) => (
            <span key={l} className="flex items-center gap-1.5 text-slate-500">
              <span className="w-2.5 h-2.5 rounded-sm" style={{ background: `${c}40`, border: `1px solid ${c}` }} />
              {l}
            </span>
          ))}
        </div>
      </div>
      <div>
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">N×N similarity heatmap</p>
        <div className="overflow-x-auto">
          <table className="text-[9px] font-mono border-collapse">
            <thead>
              <tr>
                <th className="w-6 h-5" />
                {labels.map(l => <th key={l} className="w-8 h-5 text-slate-500 font-normal text-center">{l}</th>)}
              </tr>
            </thead>
            <tbody>
              {matrix.map((row, ri) => (
                <tr key={ri}>
                  <td className="text-slate-500 pr-1 text-right py-0.5">{labels[ri]}</td>
                  {row.map((v, ci) => (
                    <motion.td
                      key={ci}
                      className="w-8 h-7 text-center text-[8px] rounded-sm"
                      style={{ background: `${cellColor(v)}28`, color: cellColor(v) }}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: (ri * 7 + ci) * 0.008 }}
                    >
                      {v === 1 ? '—' : v.toFixed(2)}
                    </motion.td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function NLITab() {
  const pairs = [
    {
      premise: 'Sucre is the constitutional capital of Bolivia.',
      hypothesis: 'La Paz is the administrative capital.',
      result: 'NO CONTRADICTION', color: '#55ee88',
      note: 'Scope difference — Sucre (constitutional) vs La Paz (administrative) coexist',
    },
    {
      premise: 'Capital is Sucre.',
      hypothesis: 'Capital is La Paz.',
      result: 'CONTRADICTION', color: '#ff6677',
      note: 'Surface contradiction — same property, conflicting values — flagged for resolution',
    },
    {
      premise: 'La Paz is seat of government.',
      hypothesis: "Bolivia's capital is Santa Cruz.",
      result: 'CONTRADICTION', color: '#ff6677',
      note: 'Strong contradiction — all La Paz claims reject Santa Cruz',
    },
    {
      premise: 'Sucre is the constitutional capital.',
      hypothesis: 'Sucre is a capital of Bolivia.',
      result: 'NO CONTRADICTION', color: '#55ee88',
      note: 'Generalisation — constitutional capital implies being a capital',
    },
  ]
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <GlowBox color="#ff6677" title="NLI — Natural Language Inference">
        <p className="text-[12px] text-slate-400 leading-relaxed mb-3">
          A cross-encoder classifier takes two chunks (premise + hypothesis) and outputs{' '}
          <span className="text-red-400 font-medium">contradiction</span> or{' '}
          <span className="text-emerald-400 font-medium">no-contradiction</span>.
        </p>
        <GlowBox color="#55ee88" title="🔑 Scope qualifier rule">
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Two chunks that produce a surface NLI contradiction but carry different scope qualifiers
            (e.g. "constitutional capital" vs "administrative capital") must be classified as{' '}
            <span className="text-yellow-300 font-medium">is_scope_difference=True</span>.
            They are NOT misinformation.
          </p>
        </GlowBox>
      </GlowBox>
      <div className="space-y-2.5">
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Example NLI pairs</p>
        {pairs.map((p, i) => (
          <motion.div
            key={i}
            className="rounded-xl p-3 space-y-2"
            style={{ background: `${p.color}06`, border: `1px solid ${p.color}20` }}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.09 }}
          >
            <div className="grid grid-cols-2 gap-2">
              <div>
                <p className="text-[9px] text-slate-500 mb-1">Premise</p>
                <div className="text-[10px] text-slate-300 bg-black/20 rounded px-2 py-1.5 border-l-2 border-emerald-400/50">{p.premise}</div>
              </div>
              <div>
                <p className="text-[9px] text-slate-500 mb-1">Hypothesis</p>
                <div className="text-[10px] text-slate-300 bg-black/20 rounded px-2 py-1.5 border-l-2 border-violet-400/50">{p.hypothesis}</div>
              </div>
            </div>
            <div
              className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-[10px] font-bold"
              style={{ background: `${p.color}15`, color: p.color }}
            >
              {p.result}
              <div className="flex-1 h-0.5 rounded-full bg-white/5 overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: p.color }}
                  animate={{ x: ['-100%', '100%'] }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'linear', delay: i * 0.3 }}
                />
              </div>
            </div>
            <p className="text-[9px] text-slate-500">{p.note}</p>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

function EntityTab() {
  const data = [
    { chunks: 'C1 ↔ C2', entities: 'Same country + same property', qualifier: 'different role (const. vs admin.)', color: '#ffaa33', type: 'scope-diff' },
    { chunks: 'C1 ↔ C7', entities: 'Same property, different city', qualifier: 'No qualifier — likely error', color: '#ff6677', type: 'outlier' },
    { chunks: 'C1 ↔ C4', entities: 'Same city, same qualifier', qualifier: 'Redundant pair', color: '#22ddaa', type: 'redundant' },
    { chunks: 'C7 ↔ C8', entities: 'Different property (largest city ≠ capital)', qualifier: 'C8 is noise', color: '#6868a0', type: 'noise' },
  ]
  const ents = [
    { text: 'Bolivia', type: 'COUNTRY', color: '#4488ff' },
    { text: 'Sucre', type: 'CITY', color: '#22ddaa' },
    { text: 'La Paz', type: 'CITY', color: '#4488ff' },
    { text: 'Santa Cruz', type: 'CITY', color: '#ff6677' },
    { text: 'capital', type: 'PROPERTY', color: '#ffaa33' },
    { text: 'constitutional', type: 'QUALIFIER', color: '#aa66ff' },
    { text: 'seat of government', type: 'QUALIFIER', color: '#aa66ff' },
  ]
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div className="space-y-3">
        <GlowBox color="#aa66ff" title="NER — Named Entity Recognition">
          <p className="text-[12px] text-slate-400 leading-relaxed mb-3">
            Identifies entity mentions and scope qualifiers that distinguish legitimate ambiguity from misinformation.
          </p>
          <p className="text-[10px] font-semibold text-slate-400 mb-2">Entities extracted:</p>
          <div className="flex flex-wrap gap-1.5">
            {ents.map(e => (
              <span key={e.text} className="text-[10px] px-2 py-0.5 rounded-full border font-medium"
                style={{ borderColor: e.color, color: e.color, background: `${e.color}15` }}>
                {e.text} <span className="opacity-50">[{e.type}]</span>
              </span>
            ))}
          </div>
        </GlowBox>
        <GlowBox color="#55ee88" title="Key insight — scope qualifiers">
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Sucre vs La Paz is NOT a true contradiction — they refer to{' '}
            <span className="text-slate-200">different roles</span> of the same concept.
            NER + qualifier detection reveals this distinction before NLI fires.
          </p>
        </GlowBox>
      </div>
      <div>
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Entity overlap analysis</p>
        <div className="space-y-2">
          {data.map((d, i) => (
            <motion.div
              key={i}
              className="rounded-lg px-3 py-2.5"
              style={{ background: `${d.color}08`, border: `1px solid ${d.color}22` }}
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.09 }}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-[10px] font-bold" style={{ color: d.color }}>{d.chunks}</span>
                <span
                  className="text-[8px] px-1.5 py-0.5 rounded font-semibold uppercase"
                  style={{ background: `${d.color}20`, color: d.color }}
                >
                  {d.type}
                </span>
              </div>
              <p className="text-[10px] text-slate-400">{d.entities}</p>
              <p className="text-[10px] text-slate-500 mt-0.5">{d.qualifier}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}

function Stage3() {
  const [sub, setSub] = useState(0)
  const tabs = ['3.1 Query Relevance', '3.2 Similarity', '3.3 Contradiction (NLI)', '3.4 Entity Overlap']
  const panels = [<RelevanceTab key={0} />, <SimilarityTab key={1} />, <NLITab key={2} />, <EntityTab key={3} />]
  return (
    <div className="space-y-4">
      <div className="flex gap-1.5 flex-wrap">
        {tabs.map((t, i) => (
          <button
            key={t}
            onClick={() => setSub(i)}
            className={`px-3 py-1.5 rounded-lg text-[11px] font-medium border transition-all
              ${sub === i ? 'bg-amber-500/20 border-amber-500/40 text-amber-300' : 'border-white/8 text-slate-500 hover:text-slate-300'}`}
          >
            {t}
          </button>
        ))}
      </div>
      <AnimatePresence mode="wait">
        <motion.div key={sub} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
          {panels[sub]}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

// ─── Stage 4: Credibility ─────────────────────────────────────────────────────

function Stage4() {
  const tiers = [
    { icon: '🏛️', tier: 1, name: 'Institutional Authority', examples: 'AUB administration, government sources, peer-reviewed publications', range: '0.9–1.0', color: '#55ee88' },
    { icon: '📚', tier: 2, name: 'Verified Academic', examples: 'Faculty materials, textbooks, encyclopedias', range: '0.7–0.89', color: '#4488ff' },
    { icon: '👤', tier: 3, name: 'Student / Community', examples: 'Student submissions, club pages, informal write-ups', range: '0.4–0.69', color: '#ffaa33' },
    { icon: '❓', tier: 4, name: 'Unverified / External', examples: 'Anonymous posts, scraped web, unattributed uploads', range: '0.1–0.39', color: '#ff6677' },
  ]
  const cards = [
    { id: 'C1', src: 'Britannica', type: 'Encyclopedia', tier: 'Tier 2', pct: 88, color: '#4488ff' },
    { id: 'C2', src: 'Embassy/Gov', type: 'Official', tier: 'Tier 1', pct: 95, color: '#55ee88' },
    { id: 'C3', src: 'Textbook', type: 'Academic', tier: 'Tier 2', pct: 82, color: '#4488ff' },
    { id: 'C6', src: 'Travel Blog', type: 'Informal', tier: 'Tier 3', pct: 48, color: '#ffaa33' },
    { id: 'C7', src: 'Forum Post', type: 'Unverified', tier: 'Tier 4', pct: 15, color: '#ff6677' },
  ]
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div className="space-y-3">
        <GlowBox color="#ffaa33" title="What is a credibility score?">
          <p className="text-[12px] text-slate-400 leading-relaxed mb-3">
            Different sources carry different levels of authority. The credibility score encodes this prior —
            it does <span className="text-slate-200 italic">not</span> filter chunks, but gives the synthesiser a weighted signal.
          </p>
        </GlowBox>
        <div className="space-y-2">
          {tiers.map((t, i) => (
            <motion.div
              key={t.tier}
              className="flex items-center gap-3 rounded-xl px-3 py-2.5"
              style={{ background: `${t.color}0a`, border: `1px solid ${t.color}28` }}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
            >
              <span className="text-lg">{t.icon}</span>
              <div className="flex-1 min-w-0">
                <p className="text-[11px] font-semibold" style={{ color: t.color }}>Tier {t.tier} — {t.name}</p>
                <p className="text-[10px] text-slate-500 truncate">{t.examples}</p>
              </div>
              <span className="text-[12px] font-bold font-mono flex-shrink-0" style={{ color: t.color }}>{t.range}</span>
            </motion.div>
          ))}
        </div>
        <GlowBox color="#55ee88" title="Soft signal — not a hard filter">
          <p className="text-[11px] text-slate-400 leading-relaxed">
            A low-credibility chunk may still carry a correct claim. Filtering happens through debate, not authority alone.
          </p>
        </GlowBox>
      </div>
      <div>
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Bolivia example — chunk credibility</p>
        <div className="space-y-3">
          {cards.map((c, i) => (
            <motion.div
              key={c.id}
              className="rounded-xl p-3.5"
              style={{ background: `${c.color}0a`, border: `1px solid ${c.color}28` }}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
            >
              <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-[12px]" style={{ color: c.color }}>{c.id}</span>
                  <span className="text-[10px] text-slate-500">— {c.src}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[9px] px-1.5 py-0.5 rounded border text-slate-400" style={{ borderColor: `${c.color}40` }}>{c.type}</span>
                  <span className="text-[13px] font-bold font-mono" style={{ color: c.color }}>{c.pct}%</span>
                </div>
              </div>
              <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: c.color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${c.pct}%` }}
                  transition={{ delay: i * 0.08 + 0.2, duration: 0.6 }}
                />
              </div>
              <p className="text-[9px] text-slate-600 mt-1.5">{c.tier} — Verified Academic</p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Stage 5: DPP ─────────────────────────────────────────────────────────────

function Stage5() {
  const [animated, setAnimated] = useState(true)
  const items = [
    { id: 'C1', label: 'Sucre (Britannica)', status: 'kept', color: '#22ddaa', note: '✓ kept' },
    { id: 'C2', label: 'La Paz (Embassy)', status: 'kept', color: '#22ddaa', note: '✓ kept' },
    { id: 'C3', label: 'Two-capital explanation', status: 'kept', color: '#aa66ff', note: '✓ kept' },
    { id: 'C4', label: 'Redundant with C1', status: 'dropped', color: '#6868a0', note: '✗ dropped' },
    { id: 'C5', label: 'Redundant with C2', status: 'dropped', color: '#6868a0', note: '✗ dropped' },
    { id: 'C6', label: 'La Paz (blog)', status: 'kept', color: '#ffaa33', note: '✓ kept' },
    { id: 'C7', label: 'Santa Cruz (kept for debate!)', status: 'conflict', color: '#ff6677', note: '⚡ kept — conflict' },
    { id: 'C8', label: 'Irrelevant (largest city)', status: 'dropped', color: '#6868a0', note: '✗ dropped' },
  ]
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div className="space-y-4">
        <GlowBox color="#ff77cc" title="What is DPP and why use it?">
          <p className="text-[12px] text-slate-400 leading-relaxed mb-3">
            A Determinantal Point Process selects a <span className="text-slate-200">diverse subset</span> from retrieved chunks,
            balancing relevance, diversity, and conflict preservation. It prevents agents from being flooded with 5 copies of the same claim.
          </p>
        </GlowBox>
        <GlowBox color="#aa66ff" title="Scoring function">
          <div className="font-mono text-[11px] bg-black/30 rounded-lg p-3 space-y-1">
            <p className="text-violet-300">Score(S) = Relevance(S)</p>
            <p className="text-blue-300">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ β · Diversity(S)</p>
            <p className="text-amber-300">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;− Redundancy(S)</p>
            <p className="text-red-300">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;− γ · ConflictPenalty(S)</p>
          </div>
        </GlowBox>
        <GlowBox color="#ff77cc" title="Key design principle">
          <p className="text-[11px] text-slate-400 leading-relaxed">
            DPP <span className="text-slate-200 italic">keeps both sides</span> of real conflicts.
            C4 and C5 are dropped (redundant), but <span className="text-red-400 font-medium">C7 (Santa Cruz) is preserved</span> so
            debate agents can surface and reject misinformation.
          </p>
        </GlowBox>
      </div>
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Selection result</p>
          <button
            onClick={() => { setAnimated(false); setTimeout(() => setAnimated(true), 50) }}
            className="text-[10px] px-2.5 py-1 rounded-lg border border-white/10 text-slate-500 hover:text-slate-300 transition-all"
          >
            Replay
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {items.map((item, i) => (
            <motion.div
              key={item.id}
              className={`rounded-xl p-3 text-center transition-all ${
                item.status === 'dropped' ? 'opacity-40' : ''
              }`}
              style={{
                background: `${item.color}10`,
                border: `1px solid ${item.color}${item.status === 'dropped' ? '20' : '40'}`,
                boxShadow: item.status !== 'dropped' ? `0 0 12px ${item.color}15` : 'none',
              }}
              initial={animated ? { opacity: 0, scale: 0.85 } : false}
              animate={animated ? { opacity: item.status === 'dropped' ? 0.4 : 1, scale: 1 } : {}}
              transition={{ delay: i * 0.1 }}
            >
              <p className="font-mono font-bold text-[12px] mb-1" style={{ color: item.color }}>{item.id}</p>
              <p className="text-[9px] text-slate-500 mb-1.5">{item.label}</p>
              <p className={`text-[9px] font-semibold ${item.status === 'dropped' ? 'line-through text-slate-600' : ''}`}
                style={{ color: item.color }}>
                {item.note}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Stage 6: Agents ──────────────────────────────────────────────────────────

function Stage6() {
  const agents = [
    { id: 'A1', src: 'E1 · Britannica', color: '#22ddaa',
      position: 'Based on my evidence, Sucre is the constitutional capital of Bolivia. My source is a high-credibility encyclopedia.' },
    { id: 'A2', src: 'E2 · Embassy', color: '#4488ff',
      position: 'My evidence states La Paz is the administrative capital and seat of government. Official government source.' },
    { id: 'A3', src: 'E3 · Textbook', color: '#aa66ff',
      position: 'My card explicitly states Bolivia has two capitals depending on definition used. This may resolve an apparent conflict.' },
    { id: 'A4', src: 'E4 · Blog', color: '#ffaa33',
      position: 'According to my source, La Paz is the capital. No qualification provided.' },
    { id: 'A5', src: 'E5 · Forum', color: '#ff6677',
      position: "My evidence claims Bolivia's capital is Santa Cruz." },
  ]
  const cx = 100, cy = 100, r = 72
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div className="space-y-4">
        <GlowBox color="#4488ff" title="Strict isolation rule">
          <p className="text-[12px] text-slate-400 leading-relaxed mb-3">
            One agent is instantiated per DPP-selected chunk. Each agent sees <span className="text-slate-200 font-medium">only its own chunk</span> at initialisation.
            During debate rounds they see other agents' <span className="text-slate-200">positions</span> — never their source chunks.
          </p>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            If agents saw all evidence, they would converge before debate starts. Isolation forces each agent to make the
            strongest possible case for its card's claim — ensuring genuine conflict surfaces in debate.
          </p>
        </GlowBox>
        <div className="flex justify-center">
          <svg width="200" height="200" viewBox="0 0 200 200">
            {agents.map((a, i) => {
              const angle = (i / agents.length) * 2 * Math.PI - Math.PI / 2
              const x = cx + r * Math.cos(angle)
              const y = cy + r * Math.sin(angle)
              return (
                <g key={a.id}>
                  <motion.circle
                    cx={x} cy={y} r={20}
                    fill={`${a.color}18`} stroke={a.color} strokeWidth={1.5}
                    initial={{ opacity: 0, scale: 0 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.1 }}
                  />
                  <motion.text x={x} y={y - 4} textAnchor="middle" fontSize="9" fill={a.color} fontWeight="bold" fontFamily="monospace"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.1 + 0.15 }}>
                    {a.id}
                  </motion.text>
                  <motion.text x={x} y={y + 7} textAnchor="middle" fontSize="7" fill="rgba(148,163,184,0.7)" fontFamily="monospace"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.1 + 0.2 }}>
                    🔒
                  </motion.text>
                </g>
              )
            })}
            <text x={cx} y={cy} textAnchor="middle" fontSize="8" fill="#4444aa" fontFamily="monospace">isolated</text>
            <text x={cx} y={cy + 12} textAnchor="middle" fontSize="8" fill="#4444aa" fontFamily="monospace">init</text>
          </svg>
        </div>
      </div>
      <div>
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Agent initial positions</p>
        <div className="space-y-2">
          {agents.map((a, i) => (
            <motion.div
              key={a.id}
              className="rounded-xl p-3"
              style={{ background: `${a.color}08`, border: `1px solid ${a.color}25` }}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.09 }}
            >
              <p className="text-[9px] font-bold uppercase tracking-wider mb-1.5" style={{ color: a.color }}>
                {a.id} ({a.src})
              </p>
              <p className="text-[11px] text-slate-300 leading-relaxed italic">"{a.position}"</p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Stage 7: Debate ──────────────────────────────────────────────────────────

function Stage7() {
  const [round, setRound] = useState(1)
  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {[1, 2].map(r => (
          <button
            key={r}
            onClick={() => setRound(r)}
            className={`px-4 py-1.5 rounded-lg text-[11px] font-medium border transition-all
              ${round === r ? 'bg-pink-500/20 border-pink-500/40 text-pink-300' : 'border-white/8 text-slate-500 hover:text-slate-300'}`}
          >
            Round {r}
          </button>
        ))}
      </div>
      <AnimatePresence mode="wait">
        {round === 1 && (
          <motion.div key="r1" className="grid grid-cols-1 lg:grid-cols-2 gap-5"
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <div className="space-y-2.5">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Round 1 — agents see each other's claims</p>
              <Bubble color="#22ddaa" from="A1 → A2">
                My card specifies <em>constitutional</em> capital. Your claim for La Paz may refer to a different sense. We may not be in conflict.
              </Bubble>
              <Bubble color="#4488ff" from="A2 → A1">
                Agreed. I support La Paz as <em>seat of government</em>, not constitutional capital. These are distinct claims about different roles.
              </Bubble>
              <Bubble color="#aa66ff" from="A3 → ALL">
                <strong>A1 and A2 are not contradictory</strong> — they refer to different senses of "capital". Sucre = constitutional, La Paz = administrative.
                This is a scope difference, not misinformation.
              </Bubble>
              <Bubble color="#ff6677" from="A1, A2, A3, A4 → A5">
                The Santa Cruz claim directly contradicts all other evidence. Neither the constitutional nor the administrative capital of Bolivia is Santa Cruz.{' '}
                <strong>No supporting evidence found.</strong>
              </Bubble>
            </div>
            <div>
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Support map after round 1</p>
              <div className="space-y-2">
                {[
                  { agent: 'A1', claim: 'Sucre = constitutional capital', support: 'A1+A3', pct: 85, color: '#22ddaa', status: 'stable' },
                  { agent: 'A2', claim: 'La Paz = seat of government', support: 'A2+A4', pct: 88, color: '#4488ff', status: 'stable' },
                  { agent: 'A3', claim: 'Both valid — scope difference', support: 'A1+A2+A3', pct: 90, color: '#aa66ff', status: 'bridge' },
                  { agent: 'A4', claim: 'La Paz (unqualified)', support: 'A2', pct: 55, color: '#ffaa33', status: 'contested' },
                  { agent: 'A5', claim: 'Santa Cruz is capital', support: 'none', pct: 5, color: '#ff6677', status: 'isolated' },
                ].map((a, i) => (
                  <motion.div key={a.agent} className="rounded-lg p-2.5" style={{ background: `${a.color}08`, border: `1px solid ${a.color}20` }}
                    initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="font-mono font-bold text-[11px] w-6" style={{ color: a.color }}>{a.agent}</span>
                      <span className="text-[10px] text-slate-400 flex-1">{a.claim}</span>
                      <span className="text-[8px] px-1.5 py-0.5 rounded font-semibold uppercase"
                        style={{ background: `${a.color}20`, color: a.color }}>{a.status}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1 rounded-full bg-white/5 overflow-hidden">
                        <motion.div className="h-full rounded-full" style={{ background: a.color }}
                          initial={{ width: 0 }} animate={{ width: `${a.pct}%` }} transition={{ delay: i * 0.08 + 0.3, duration: 0.5 }} />
                      </div>
                      <span className="text-[9px] font-mono text-slate-500">{a.support}</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
        {round === 2 && (
          <motion.div key="r2" className="grid grid-cols-1 lg:grid-cols-2 gap-5"
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <div className="space-y-2.5">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Round 2 — revisions & early stop</p>
              <Bubble color="#ffaa33" from="A4 revises">
                My initial claim was oversimplified. Acknowledging A2 and A3's positions — La Paz is the seat of government,
                Sucre is the constitutional capital. I lower my confidence in "La Paz = capital (unqualified)".
              </Bubble>
              <Bubble color="#ff6677" from="A5 — unchanged">
                Still supporting Santa Cruz, but unable to counter any of the challenges. No new evidence available to defend the claim.
              </Bubble>
              <Bubble color="#22ddaa" from="A1, A2, A3 — stable">
                Positions unchanged. The two-capital interpretation is now the dominant view. Debate reaches stability.
              </Bubble>
              <GlowBox color="#55ee88" title="Early stop triggered">
                <p className="text-[11px] text-slate-400">
                  A1, A2, A3 are stable. A4 has revised. A5 is isolated but cannot change its evidence.
                  Debate ends — sufficient consensus reached on non-A5 claims.
                </p>
              </GlowBox>
            </div>
            <div>
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Final agent positions</p>
              <div className="space-y-2">
                {[
                  { a: 'A1', text: 'Sucre = constitutional capital ✓', sub: 'stable, high confidence', color: '#22ddaa' },
                  { a: 'A2', text: 'La Paz = seat of government ✓', sub: 'stable, high confidence', color: '#4488ff' },
                  { a: 'A3', text: 'Both valid — scope difference ✓', sub: 'stable, bridge', color: '#aa66ff' },
                  { a: 'A4', text: 'La Paz, softened claim', sub: 'revised, medium confidence', color: '#ffaa33' },
                  { a: 'A5', text: 'Santa Cruz ←', sub: 'isolated, zero support', color: '#ff6677' },
                ].map((a, i) => (
                  <motion.div key={a.a} className="flex items-center gap-3 rounded-lg px-3 py-2.5"
                    style={{ background: `${a.color}08`, border: `1px solid ${a.color}25` }}
                    initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.09 }}>
                    <span className="font-mono font-bold text-[11px] w-6" style={{ color: a.color }}>{a.a}</span>
                    <div>
                      <p className="text-[11px] text-slate-200">{a.text}</p>
                      <p className="text-[9px] text-slate-500">{a.sub}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ─── Stage 8: Report ──────────────────────────────────────────────────────────

function Stage8() {
  const conflicts = [
    {
      icon: '⚖️', type: 'TRUE AMBIGUITY / SCOPE DIFFERENCE', color: '#ffaa33',
      desc: 'Sucre (constitutional) vs La Paz (administrative) — both correct in different senses. Preserved in final answer.',
    },
    {
      icon: '✗', type: 'REJECTED OUTLIER / MISINFORMATION', color: '#ff6677',
      desc: 'Santa Cruz capital claim — contradicted by all other agents, no qualifier, low-credibility source. Rejected.',
    },
    {
      icon: '~', type: 'WEAK OVERSIMPLIFICATION', color: '#4488ff',
      desc: 'La Paz as unqualified "capital" (travel blog) — factually incomplete, downweighted in final answer.',
    },
    {
      icon: '○', type: 'NOISE REMOVED', color: '#6868a0',
      desc: 'Largest city chunk — different property, not relevant to capital question. Filtered at DPP stage.',
    },
  ]
  const strengths = [
    { label: 'Sucre (constitutional capital)', sub: 'Britannica + textbook', pct: 90, color: '#22ddaa' },
    { label: 'La Paz (seat of government)', sub: 'Embassy + textbook', pct: 88, color: '#4488ff' },
    { label: 'La Paz (unqualified)', sub: 'travel blog, no qualifier', pct: 45, color: '#ffaa33' },
    { label: 'Santa Cruz (capital)', sub: 'zero agent support', pct: 5, color: '#ff6677' },
  ]
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div>
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Conflict classification</p>
        <div className="space-y-2.5">
          {conflicts.map((c, i) => (
            <motion.div key={c.type} className="flex gap-3 rounded-xl px-3 py-2.5"
              style={{ background: `${c.color}08`, border: `1px solid ${c.color}25` }}
              initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
              <span className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] flex-shrink-0 mt-0.5"
                style={{ background: `${c.color}25`, color: c.color }}>
                {c.icon}
              </span>
              <div>
                <p className="text-[10px] font-bold mb-1" style={{ color: c.color }}>{c.type}</p>
                <p className="text-[11px] text-slate-400 leading-relaxed">{c.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
      <div className="space-y-4">
        <div>
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Evidence strength summary</p>
          <div className="space-y-3">
            {strengths.map((s, i) => (
              <motion.div key={s.label} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}>
                <Bar pct={s.pct} color={s.color} label={s.label} sub={s.sub} />
              </motion.div>
            ))}
          </div>
        </div>
        <GlowBox color="#55ee88" title="Decision: Case 1 — True Ambiguity">
          <p className="text-[12px] text-slate-400 leading-relaxed">
            Multiple valid answers exist with scope qualifiers. Final answer must present{' '}
            <span className="text-emerald-400 font-medium">both Sucre and La Paz</span> with their respective qualifiers.
          </p>
        </GlowBox>
      </div>
    </div>
  )
}

// ─── Stage 9: Answer ──────────────────────────────────────────────────────────

function Stage9() {
  const cases = [
    { n: 1, label: 'Ambiguity', cond: '≥2 surviving claims with scope qualifiers', out: 'Present all valid answers labelled with their scope', color: '#22ddaa', active: true },
    { n: 2, label: 'Strong Winner', cond: 'Exactly 1 dominant non-outlier cluster', out: 'Return single best-supported answer', color: '#4488ff', active: false },
    { n: 3, label: 'Unresolved', cond: 'No clear winner, no scope qualifiers', out: 'State that evidence is inconclusive', color: '#ff6677', active: false },
  ]
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div className="space-y-4">
        <div>
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Decision logic</p>
          <div className="space-y-2">
            {cases.map((c, i) => (
              <motion.div key={c.n}
                className="rounded-xl px-3 py-2.5"
                style={{
                  background: c.active ? `${c.color}12` : 'rgba(255,255,255,0.02)',
                  border: `1px solid ${c.active ? c.color + '50' : 'rgba(255,255,255,0.06)'}`,
                  boxShadow: c.active ? `0 0 16px ${c.color}20` : 'none',
                }}
                initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ background: `${c.color}25`, color: c.color }}>
                    Case {c.n}
                  </span>
                  <span className="text-[11px] font-semibold" style={{ color: c.active ? c.color : '#6868a0' }}>{c.label}</span>
                  {c.active && <span className="text-[8px] text-emerald-400 ml-auto">← selected</span>}
                </div>
                <p className="text-[10px] text-slate-500"><span className="text-slate-400">condition: </span>{c.cond}</p>
                <p className="text-[10px] text-slate-500 mt-0.5"><span className="text-slate-400">output: </span>{c.out}</p>
              </motion.div>
            ))}
          </div>
        </div>
        <GlowBox color="#aa66ff" title="Core idea — not normal RAG">
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Normal RAG: retrieve → dump → generate. This pipeline: retrieval →{' '}
            <span className="text-slate-200">relationship reasoning</span> → structured selection →{' '}
            <span className="text-slate-200">multi-agent validation</span> → conflict interpretation → answer.
            Correctly handles ambiguity, detects misinformation, removes noise — all in one pass.
          </p>
        </GlowBox>
      </div>
      <div>
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Final answer</p>
        <div
          className="rounded-xl p-5 relative"
          style={{
            background: 'rgba(34,221,170,0.06)',
            border: '1px solid rgba(34,221,170,0.3)',
            boxShadow: '0 0 30px rgba(34,221,170,0.08)',
          }}
        >
          <div className="absolute -top-2.5 left-4 px-2.5 py-0.5 rounded-full text-[9px] font-bold bg-emerald-400 text-black">
            Final Answer
          </div>
          <p className="text-[13px] text-slate-200 leading-relaxed">
            Bolivia has two capitals depending on the definition used.
          </p>
          <p className="text-[13px] text-slate-200 leading-relaxed mt-3">
            <span className="text-emerald-400 font-semibold">Sucre</span> is the{' '}
            <em className="text-slate-300">constitutional capital</em> — formally designated in Bolivia's constitution and home to the Supreme Court.
          </p>
          <p className="text-[13px] text-slate-200 leading-relaxed mt-3">
            <span className="text-blue-400 font-semibold">La Paz</span> is the{' '}
            <em className="text-slate-300">seat of government</em> — where the executive and legislative branches operate.
          </p>
          <p className="text-[12px] text-slate-400 mt-3 leading-relaxed">
            If the question refers to the constitutional capital, the answer is <span className="text-emerald-400">Sucre</span>.
            If it refers to where the government is based, the answer is <span className="text-blue-400">La Paz</span>.
          </p>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {[
            { label: 'Scope conflict: preserved', color: '#ffaa33' },
            { label: 'Santa Cruz: rejected', color: '#ff6677' },
            { label: 'Noise: filtered', color: '#6868a0' },
            { label: 'Normal RAG would fail this', color: '#55ee88' },
          ].map(t => (
            <span key={t.label} className="text-[9px] px-2 py-0.5 rounded-full border font-medium"
              style={{ borderColor: t.color, color: t.color, background: `${t.color}12` }}>
              {t.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Stage definitions ────────────────────────────────────────────────────────

const STAGES = [
  { id: 0, label: 'Query',        color: '#4488ff', sub: 'Normalizer',         component: <Stage0 /> },
  { id: 1, label: 'Retriever',    color: '#aa66ff', sub: 'Vector Search',      component: <Stage1 /> },
  { id: 2, label: 'Chunker',      color: '#22ddaa', sub: 'Upload-time',        component: <Stage2 /> },
  { id: 3, label: 'Relations',    color: '#ffaa33', sub: '×4 parallel',        component: <Stage3 /> },
  { id: 4, label: 'Credibility',  color: '#ffaa33', sub: 'Score',              component: <Stage4 /> },
  { id: 5, label: 'DPP',          color: '#ff77cc', sub: 'Selector',           component: <Stage5 /> },
  { id: 6, label: 'Agents',       color: '#4488ff', sub: 'Bank',               component: <Stage6 /> },
  { id: 7, label: 'Debate',       color: '#ff77cc', sub: 'Orchestrator',       component: <Stage7 /> },
  { id: 8, label: 'Report',       color: '#ffaa33', sub: 'Conflict Classifier', component: <Stage8 /> },
  { id: 9, label: 'Answer',       color: '#22ddaa', sub: 'Synthesizer',        component: <Stage9 /> },
]

// ─── Main ─────────────────────────────────────────────────────────────────────

export function PipelineExplorer() {
  const [active, setActive] = useState(0)
  const stage = STAGES[active]

  return (
    <div className="rounded-2xl overflow-hidden" style={{
      background: 'rgba(10,10,24,0.85)',
      border: '1px solid rgba(68,136,255,0.18)',
      boxShadow: '0 0 60px rgba(68,136,255,0.07)',
    }}>
      {/* Header */}
      <div className="px-6 pt-6 pb-4 text-center" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
        <div className="inline-block px-3 py-1 rounded-full text-[10px] font-medium border border-blue-500/30 text-blue-400 bg-blue-500/10 mb-3 tracking-wide">
          Conflict-Aware RAG Pipeline
        </div>
        <h2
          className="text-xl font-bold mb-1"
          style={{ background: 'linear-gradient(135deg,#4488ff,#aa66ff,#22ddaa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}
        >
          Resolving Conflicts in Retrieval-Augmented Generation
        </h2>
        <p className="text-xs text-slate-500">
          An interactive walkthrough of a multi-agent pipeline that detects, debates, and resolves conflicts in retrieved evidence.
        </p>
      </div>

      {/* Stage tabs */}
      <div className="flex gap-1.5 px-4 py-3 overflow-x-auto" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
        {STAGES.map(s => (
          <motion.button
            key={s.id}
            onClick={() => setActive(s.id)}
            className="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-medium border transition-all duration-200"
            style={active === s.id
              ? { background: `${s.color}22`, border: `1px solid ${s.color}45`, color: s.color, boxShadow: `0 0 16px ${s.color}30` }
              : { border: '1px solid rgba(255,255,255,0.07)', color: '#6868a0' }}
            whileTap={{ scale: 0.95 }}
          >
            <span className="text-[8px] opacity-50 font-mono">{s.id}.</span>
            {s.label}
          </motion.button>
        ))}
      </div>

      {/* Stage header */}
      <div className="px-6 pt-5 pb-3 flex items-center gap-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
        <div className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 text-lg font-bold"
          style={{ background: `${stage.color}18`, border: `1px solid ${stage.color}35`, color: stage.color, boxShadow: `0 0 20px ${stage.color}20` }}>
          {stage.id}
        </div>
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-base font-bold text-slate-100">{stage.label}</span>
            {stage.sub && <span className="text-[10px] text-slate-500">{stage.sub}</span>}
          </div>
          <p className="text-[10px] text-slate-500 font-mono">stage {stage.id} of {STAGES.length - 1}</p>
        </div>
      </div>

      {/* Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={active}
          className="px-6 py-5"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.22 }}
        >
          {stage.component}
        </motion.div>
      </AnimatePresence>

      {/* Footer nav */}
      <div className="flex items-center justify-between px-6 py-4" style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
        <button
          onClick={() => setActive(Math.max(0, active - 1))}
          disabled={active === 0}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-white/8 text-xs text-slate-400 hover:text-slate-200 hover:border-white/15 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        >
          <ChevronLeft size={13} /> Back
        </button>

        <div className="flex items-center gap-1.5">
          {STAGES.map(s => (
            <button key={s.id} onClick={() => setActive(s.id)}>
              <motion.div
                className="rounded-full transition-all"
                style={{
                  width: active === s.id ? 18 : 5,
                  height: 5,
                  background: active === s.id ? s.color : 'rgba(255,255,255,0.1)',
                  boxShadow: active === s.id ? `0 0 8px ${s.color}` : 'none',
                }}
                layout
                transition={{ duration: 0.2 }}
              />
            </button>
          ))}
        </div>

        <button
          onClick={() => setActive(Math.min(STAGES.length - 1, active + 1))}
          disabled={active === STAGES.length - 1}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          style={{ background: `${stage.color}20`, border: `1px solid ${stage.color}35`, color: stage.color }}
        >
          {active === STAGES.length - 1 ? 'Complete' : `Next: ${STAGES[active + 1]?.label} →`}
        </button>
      </div>
    </div>
  )
}

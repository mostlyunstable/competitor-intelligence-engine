import React, { useState } from 'react'
import { Brain, ChevronDown, ChevronUp, Database } from 'lucide-react'
import { StatusBadge } from './StatusBadge'

interface EvidenceItem {
  key: string
  val: string
}

interface InsightCardProps {
  category: string
  title: string
  insightText: string
  evidence?: EvidenceItem[]
  confidenceScore?: number
  dbRecordsCount?: number
  provenanceSource?: string
}

export function InsightCard({
  category,
  title,
  insightText,
  evidence = [],
  confidenceScore,
  dbRecordsCount,
  provenanceSource,
}: InsightCardProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="card p-6 space-y-4 hover:border-brand-300 dark:hover:border-brand-700 transition">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400">
            <Brain className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-400">
              {category}
            </span>
            <h3 className="text-base font-bold text-surface-900 dark:text-white">
              {title}
            </h3>
          </div>
        </div>

        {confidenceScore !== undefined && (
          <StatusBadge
            status={`${Math.round(confidenceScore * (confidenceScore <= 1 ? 100 : 1))}% Confidence`}
          />
        )}
      </div>

      <p className="text-sm leading-relaxed text-surface-700 dark:text-surface-300 bg-surface-50 dark:bg-surface-800/50 p-4 rounded-lg border border-surface-100 dark:border-surface-800">
        {insightText}
      </p>

      {(evidence.length > 0 || dbRecordsCount !== undefined || provenanceSource) && (
        <div className="pt-2 border-t border-surface-100 dark:border-surface-800">
          <button
            onClick={() => setOpen(!open)}
            className="flex items-center justify-between w-full text-xs font-semibold text-surface-500 dark:text-surface-400 hover:text-surface-900 dark:hover:text-white transition"
          >
            <span className="flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-brand-500" />
              Database Evidence & Provenance Audit
              {dbRecordsCount !== undefined && (
                <span className="badge badge-neutral ml-1">
                  {dbRecordsCount} DB Records
                </span>
              )}
            </span>
            {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {open && (
            <div className="mt-3 space-y-2 text-xs bg-surface-50 dark:bg-surface-800/80 p-3 rounded-lg border border-surface-200 dark:border-surface-700">
              {provenanceSource && (
                <div className="text-surface-500 font-mono mb-2">
                  Source: <strong className="text-surface-700 dark:text-surface-200">{provenanceSource}</strong>
                </div>
              )}
              {evidence.map((e, idx) => (
                <div key={idx} className="flex justify-between py-1 border-b border-surface-200/50 dark:border-surface-700/50 last:border-0">
                  <span className="text-surface-600 dark:text-surface-400 font-medium">{e.key}</span>
                  <span className="text-surface-900 dark:text-white font-mono font-semibold">{e.val}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

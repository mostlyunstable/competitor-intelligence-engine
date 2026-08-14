import React from 'react'
import { TrendingUp, TrendingDown, Target, Brain } from 'lucide-react'
import { StatusBadge } from './StatusBadge'

interface PredictionCardProps {
  serviceName: string
  competitorName: string
  currentPrice: number
  predictedPrice: number
  utservioPrice: number
  priceRange?: { min: number; max: number }
  confidenceScore: number
  onExplain?: () => void
}

export function PredictionCard({
  serviceName,
  competitorName,
  currentPrice,
  predictedPrice,
  utservioPrice,
  priceRange,
  confidenceScore,
  onExplain,
}: PredictionCardProps) {
  const gap = predictedPrice - utservioPrice
  const gapPct = utservioPrice > 0 ? Number(((gap / utservioPrice) * 100).toFixed(1)) : 0

  return (
    <div className="card p-5 space-y-4 hover:border-brand-300 dark:hover:border-brand-700 transition">
      <div className="flex items-start justify-between">
        <div>
          <span className="text-xs font-semibold text-surface-500 uppercase tracking-wider block">
            {competitorName}
          </span>
          <h4 className="text-base font-bold text-surface-900 dark:text-white">
            {serviceName}
          </h4>
        </div>
        <StatusBadge status={`${Math.round(confidenceScore * (confidenceScore <= 1 ? 100 : 1))}% ML Confidence`} />
      </div>

      <div className="grid grid-cols-3 gap-2 py-3 bg-surface-50 dark:bg-surface-800/50 rounded-lg px-3 text-center border border-surface-100 dark:border-surface-800">
        <div>
          <span className="text-[10px] text-surface-500 uppercase block font-semibold">Current Price</span>
          <span className="text-sm font-bold font-mono text-surface-700 dark:text-surface-300">
            {currentPrice > 0 ? `₹${currentPrice.toLocaleString()}` : 'N/A'}
          </span>
        </div>
        <div className="border-x border-surface-200 dark:border-surface-700">
          <span className="text-[10px] text-brand-600 dark:text-brand-400 uppercase block font-bold">Predicted Price</span>
          <span className="text-base font-extrabold font-mono text-brand-700 dark:text-brand-300">
            ₹{predictedPrice.toLocaleString()}
          </span>
        </div>
        <div>
          <span className="text-[10px] text-surface-500 uppercase block font-semibold">Utservio Baseline</span>
          <span className="text-sm font-bold font-mono text-surface-900 dark:text-white">
            ₹{utservioPrice.toLocaleString()}
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs pt-1">
        <div className="flex items-center gap-1.5 font-medium">
          <Target className="w-3.5 h-3.5 text-surface-400" />
          <span>Expected Gap vs Utservio:</span>
          <span className={`font-mono font-bold ${gapPct > 0 ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
            {gapPct > 0 ? `+${gapPct}%` : `${gapPct}%`}
          </span>
        </div>

        {priceRange && (
          <span className="text-[11px] text-surface-500 font-mono">
            Range: ₹{priceRange.min} – ₹{priceRange.max}
          </span>
        )}
      </div>

      {onExplain && (
        <button
          onClick={onExplain}
          className="w-full btn-secondary py-1.5 text-xs font-semibold justify-center mt-2"
        >
          <Brain className="w-3.5 h-3.5 text-brand-500" />
          Explain ML Factors
        </button>
      )}
    </div>
  )
}

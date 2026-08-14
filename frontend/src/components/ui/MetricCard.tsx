import React from 'react'
import type { LucideIcon } from 'lucide-react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: LucideIcon
  change?: string | number
  changeType?: 'positive' | 'negative' | 'neutral'
  color?: string
  loading?: boolean
  onClick?: () => void
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  change,
  changeType = 'neutral',
  color = 'text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/30',
  loading = false,
  onClick,
}: MetricCardProps) {
  if (loading) {
    return (
      <div className="stat-card">
        <div className="skeleton h-4 w-24 mb-2" />
        <div className="skeleton h-8 w-32 mb-1" />
        <div className="skeleton h-3 w-20" />
      </div>
    )
  }

  return (
    <div
      onClick={onClick}
      className={`stat-card ${onClick ? 'cursor-pointer hover:border-brand-400' : ''}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
          {title}
        </span>
        {Icon && (
          <div className={`p-2 rounded-lg ${color} flex items-center justify-center`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-2 mt-1">
        <span className="text-2xl font-bold font-mono text-surface-900 dark:text-white">
          {value}
        </span>
        {change !== undefined && (
          <span
            className={`inline-flex items-center text-xs font-bold px-1.5 py-0.5 rounded ${
              changeType === 'positive'
                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                : changeType === 'negative'
                ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                : 'bg-surface-100 text-surface-700 dark:bg-surface-800 dark:text-surface-300'
            }`}
          >
            {changeType === 'positive' && <TrendingUp className="w-3 h-3 mr-0.5" />}
            {changeType === 'negative' && <TrendingDown className="w-3 h-3 mr-0.5" />}
            {changeType === 'neutral' && <Minus className="w-3 h-3 mr-0.5" />}
            {change}
          </span>
        )}
      </div>

      {subtitle && (
        <span className="text-xs text-surface-500 dark:text-surface-400 mt-1 block">
          {subtitle}
        </span>
      )}
    </div>
  )
}

import React from 'react'
import { Loader2 } from 'lucide-react'

interface LoadingStateProps {
  message?: string
  rows?: number
  type?: 'card' | 'table' | 'spinner'
}

export function LoadingState({
  message = 'Loading data from database...',
  rows = 4,
  type = 'card',
}: LoadingStateProps) {
  if (type === 'spinner') {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-brand-600 dark:text-brand-400 gap-3">
        <Loader2 className="w-8 h-8 animate-spin" />
        <span className="text-sm font-medium">{message}</span>
      </div>
    )
  }

  if (type === 'table') {
    return (
      <div className="card overflow-hidden">
        <div className="p-4 bg-surface-50 dark:bg-surface-800 border-b border-surface-200 dark:border-surface-700">
          <div className="skeleton h-5 w-48" />
        </div>
        <div className="p-4 space-y-3">
          {[...Array(rows)].map((_, i) => (
            <div key={i} className="flex gap-4">
              <div className="skeleton h-4 flex-1" />
              <div className="skeleton h-4 w-24" />
              <div className="skeleton h-4 w-16" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {[...Array(rows)].map((_, i) => (
        <div key={i} className="card p-5 space-y-3">
          <div className="skeleton h-4 w-24" />
          <div className="skeleton h-8 w-32" />
          <div className="skeleton h-3 w-16" />
        </div>
      ))}
    </div>
  )
}

import React from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
}

export function ErrorState({
  title = 'Unable to Load Data',
  message,
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="card p-8 border-red-200 dark:border-red-900/50 bg-red-50/50 dark:bg-red-950/20 text-center flex flex-col items-center justify-center">
      <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 flex items-center justify-center mb-3">
        <AlertCircle className="w-5 h-5" />
      </div>
      <h3 className="text-base font-semibold text-red-900 dark:text-red-200 mb-1">
        {title}
      </h3>
      <p className="text-sm text-red-700 dark:text-red-300 max-w-md mb-4">
        {message}
      </p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary text-xs">
          <RefreshCw className="w-3.5 h-3.5" />
          Try Again
        </button>
      )}
    </div>
  )
}

import React from 'react'
import type { LucideIcon } from 'lucide-react'

interface PageHeaderProps {
  title: string
  description?: string
  icon?: LucideIcon
  badge?: React.ReactNode
  actions?: React.ReactNode
}

export function PageHeader({
  title,
  description,
  icon: Icon,
  badge,
  actions,
}: PageHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
      <div>
        <div className="flex items-center gap-3">
          {Icon && <Icon className="w-7 h-7 text-brand-600 dark:text-brand-400 flex-shrink-0" />}
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white flex items-center gap-2">
            {title}
          </h1>
          {badge && <div>{badge}</div>}
        </div>
        {description && (
          <p className="text-sm text-surface-500 dark:text-surface-400 mt-1">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-3 flex-wrap">{actions}</div>}
    </div>
  )
}

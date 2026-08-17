import React from 'react'
import { CheckCircle, AlertTriangle, AlertCircle, Info, Minus } from 'lucide-react'

export type StatusVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral'

interface StatusBadgeProps {
  status: string
  variant?: StatusVariant
  icon?: boolean
  className?: string
}

export function StatusBadge({
  status,
  variant,
  icon = true,
  className = '',
}: StatusBadgeProps) {
  // Infer variant from status string if not explicitly passed
  const resolvedVariant: StatusVariant = variant || (() => {
    const s = (status || '').toLowerCase()
    if (s.includes('high') || s.includes('success') || s.includes('healthy') || s.includes('active') || s.includes('valid')) return 'success'
    if (s.includes('medium') || s.includes('warn') || s.includes('degraded') || s.includes('moderate') || s.includes('pending')) return 'warning'
    if (s.includes('low') || s.includes('fail') || s.includes('risk') || s.includes('danger') || s.includes('stop') || s.includes('error')) return 'danger'
    if (s.includes('info') || s.includes('ml') || s.includes('predict')) return 'info'
    return 'neutral'
  })()

  const badgeStyles: Record<StatusVariant, string> = {
    success: 'badge-success',
    warning: 'badge-warning',
    danger: 'badge-danger',
    info: 'badge-info',
    neutral: 'badge-neutral',
  }

  const IconMap: Record<StatusVariant, React.ComponentType<{ className?: string }>> = {
    success: CheckCircle,
    warning: AlertTriangle,
    danger: AlertCircle,
    info: Info,
    neutral: Minus,
  }

  const IconComponent = IconMap[resolvedVariant]

  return (
    <span className={`${badgeStyles[resolvedVariant]} ${className}`}>
      {icon && <IconComponent className="w-3 h-3 mr-1 flex-shrink-0" />}
      {status}
    </span>
  )
}

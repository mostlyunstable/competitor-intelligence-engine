import React from 'react'

interface FilterOption {
  value: string | number
  label: string
}

interface SelectFieldProps {
  label?: string
  value: string | number
  onChange: (value: string) => void
  options: FilterOption[]
  className?: string
}

export function SelectField({
  label,
  value,
  onChange,
  options,
  className = '',
}: SelectFieldProps) {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      {label && (
        <label className="text-xs font-semibold uppercase tracking-wider text-surface-500 dark:text-surface-400">
          {label}
        </label>
      )}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="input py-2 text-xs font-medium cursor-pointer"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

interface FilterBarProps {
  children: React.ReactNode
  className?: string
}

export function FilterBar({ children, className = '' }: FilterBarProps) {
  return (
    <div className={`card p-4 flex flex-wrap items-center gap-4 bg-white dark:bg-surface-900 border-surface-200 dark:border-surface-800 ${className}`}>
      {children}
    </div>
  )
}

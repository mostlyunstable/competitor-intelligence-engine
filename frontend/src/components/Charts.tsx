interface BarChartProps {
  data: { label: string; value: number; color?: string }[]
  height?: number
  showLabels?: boolean
}

export function BarChart({ data, height = 150, showLabels = true }: BarChartProps) {
  if (!data || data.length === 0) {
    return <div className="text-center text-surface-400 text-sm py-8">No data available</div>
  }

  const max = Math.max(...data.map(d => d.value), 1)

  return (
    <div className="w-full">
      <div className="flex items-end gap-1" style={{ height }}>
        {data.map((item, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1">
            <div
              className={`w-full rounded-t ${item.color || 'bg-brand-500'} transition-all duration-500`}
              style={{ height: `${(item.value / max) * 100}%`, minHeight: item.value > 0 ? 4 : 0 }}
              title={`${item.label}: ${item.value}`}
            />
          </div>
        ))}
      </div>
      {showLabels && (
        <div className="flex gap-1 mt-2">
          {data.map((item, i) => (
            <div key={i} className="flex-1 text-center">
              <span className="text-xs text-surface-500 truncate block">{item.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

interface LineChartProps {
  data: { label: string; values: number[] }[]
  labels: string[]
  height?: number
  colors?: string[]
}

export function LineChart({ data, labels, height = 150, colors = ['bg-brand-500', 'bg-emerald-500', 'bg-purple-500'] }: LineChartProps) {
  if (!data || data.length === 0) {
    return <div className="text-center text-surface-400 text-sm py-8">No data available</div>
  }

  const allValues = data.flatMap(d => d.values)
  const max = Math.max(...allValues, 1)

  return (
    <div className="w-full">
      <div className="relative" style={{ height }}>
        {/* Grid lines */}
        {[0, 25, 50, 75, 100].map(pct => (
          <div
            key={pct}
            className="absolute w-full border-t border-surface-100"
            style={{ bottom: `${pct}%` }}
          />
        ))}
        {/* Bars for each dataset */}
        <div className="flex items-end gap-0.5 h-full relative z-10">
          {labels.map((_, i) => (
            <div key={i} className="flex-1 flex items-end gap-px h-full">
              {data.map((dataset, di) => (
                <div
                  key={di}
                  className={`flex-1 rounded-t ${colors[di % colors.length]} transition-all duration-500`}
                  style={{
                    height: `${(dataset.values[i] / max) * 100}%`,
                    minHeight: dataset.values[i] > 0 ? 2 : 0,
                  }}
                  title={`${dataset.label}: ${dataset.values[i]}`}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
      {/* X-axis labels */}
      <div className="flex gap-0.5 mt-2">
        {labels.map((label, i) => (
          <div key={i} className="flex-1 text-center">
            <span className="text-xs text-surface-500 truncate block">{label}</span>
          </div>
        ))}
      </div>
      {/* Legend */}
      <div className="flex gap-4 mt-3 justify-center">
        {data.map((dataset, i) => (
          <div key={i} className="flex items-center gap-1.5">
            <div className={`w-3 h-3 rounded ${colors[i % colors.length]}`} />
            <span className="text-xs text-surface-600">{dataset.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

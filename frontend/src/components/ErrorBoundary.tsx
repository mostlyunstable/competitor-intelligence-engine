import { Component, type ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
          <AlertTriangle size={48} className="text-amber-500 mb-4" />
          <h2 className="text-lg font-semibold text-surface-900 mb-2">Something went wrong</h2>
          <p className="text-sm text-surface-500 mb-6 text-center max-w-md">
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <button
            onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload() }}
            className="btn-primary"
          >
            <RefreshCw size={16} /> Reload page
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

import { useParams, useNavigate } from 'react-router-dom'
import { usePolling } from '../hooks'
import { api } from '../lib/api'
import { formatDate, timeAgo } from '../lib/utils'
import {
  ArrowLeft, Globe, Play, Edit, ExternalLink, Clock,
  CheckCircle, XCircle, Code, DollarSign, FileText,
  Users, Share2, Database, History
} from 'lucide-react'

export default function CompetitorProfilePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const competitorId = parseInt(id || '0')

  const { data, loading } = usePolling(() => api.getCompetitor(competitorId), 30000)
  const { data: extracted } = usePolling(() => api.getExtracted(competitorId), 60000)

  if (loading && !data) {
    return <div className="space-y-4">{[...Array(3)].map((_, i) => <div key={i} className="skeleton h-32 w-full" />)}</div>
  }

  if (!data) return <div className="text-center py-12 text-gray-500">Competitor not found</div>

  const { competitor: c, services, pricing, content, social, tech_stack, sources, pages, collection_logs } = data

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/competitors')} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{c.name}</h1>
            {c.enabled ? <span className="badge-success">Active</span> : <span className="badge-danger">Disabled</span>}
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
            <Globe size={14} />
            <a href={c.website_url} target="_blank" rel="noopener noreferrer" className="hover:text-brand-600 flex items-center gap-1">
              {c.website_url} <ExternalLink size={12} />
            </a>
          </div>
        </div>
        <button onClick={async () => { await api.triggerCollection(competitorId) }} className="btn-primary">
          <Play size={16} /> Collect Now
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {[
          { label: 'Services', value: services?.length || 0, icon: Code, color: 'text-purple-600' },
          { label: 'Pricing', value: pricing?.length || 0, icon: DollarSign, color: 'text-green-600' },
          { label: 'Content', value: content?.length || 0, icon: FileText, color: 'text-blue-600' },
          { label: 'Social', value: social?.length || 0, icon: Share2, color: 'text-pink-600' },
          { label: 'Tech Stack', value: tech_stack?.length || 0, icon: Database, color: 'text-orange-600' },
          { label: 'Sources', value: sources?.length || 0, icon: Globe, color: 'text-gray-600' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="stat-card">
            <Icon size={18} className={color} />
            <div className="text-xl font-bold text-gray-900">{value}</div>
            <div className="text-xs text-gray-500">{label}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="space-y-6">
        {/* Services */}
        {services?.length > 0 && (
          <div className="card">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
              <Code size={16} className="text-purple-600" />
              <h2 className="font-semibold text-gray-900">Services ({services.length})</h2>
            </div>
            <div className="divide-y divide-gray-50">
              {services.map((s: any) => (
                <div key={s.id} className="px-5 py-3">
                  <div className="font-medium text-sm text-gray-900">{s.name}</div>
                  {s.description && <div className="text-xs text-gray-500 mt-1">{s.description}</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pricing */}
        {pricing?.length > 0 && (
          <div className="card">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
              <DollarSign size={16} className="text-green-600" />
              <h2 className="font-semibold text-gray-900">Pricing ({pricing.length})</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="table-header">Service</th>
                    <th className="table-header">Price</th>
                    <th className="table-header">Currency</th>
                    <th className="table-header">Category</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {pricing.map((p: any) => (
                    <tr key={p.id}>
                      <td className="table-cell font-medium">{p.service_name}</td>
                      <td className="table-cell">{p.base_price || '-'}</td>
                      <td className="table-cell">{p.currency || '-'}</td>
                      <td className="table-cell">{p.category || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tech Stack */}
        {tech_stack?.length > 0 && (
          <div className="card">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
              <Database size={16} className="text-orange-600" />
              <h2 className="font-semibold text-gray-900">Technology Stack ({tech_stack.length})</h2>
            </div>
            <div className="p-5 flex flex-wrap gap-2">
              {tech_stack.map((t: any) => (
                <div key={t.id} className="px-3 py-2 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="text-sm font-medium text-gray-900">{t.technology_name}</div>
                  {t.category && <div className="text-xs text-gray-500">{t.category}</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Content */}
        {content?.length > 0 && (
          <div className="card">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
              <FileText size={16} className="text-blue-600" />
              <h2 className="font-semibold text-gray-900">Content ({content.length})</h2>
            </div>
            <div className="divide-y divide-gray-50 max-h-80 overflow-auto">
              {content.map((c: any) => (
                <div key={c.id} className="px-5 py-3 flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{c.title}</div>
                    <div className="text-xs text-gray-400">{c.content_type}</div>
                  </div>
                  <a href={c.url} target="_blank" rel="noopener noreferrer" className="text-brand-600 hover:underline text-xs flex items-center gap-1">
                    View <ExternalLink size={10} />
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Social */}
        {social?.length > 0 && (
          <div className="card">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
              <Share2 size={16} className="text-pink-600" />
              <h2 className="font-semibold text-gray-900">Social Profiles ({social.length})</h2>
            </div>
            <div className="divide-y divide-gray-50">
              {social.map((s: any) => (
                <div key={s.id} className="px-5 py-3 flex items-center justify-between">
                  <div>
                    <span className="badge-info">{s.platform}</span>
                    <span className="text-sm text-gray-900 ml-2">{s.username || s.url}</span>
                  </div>
                  <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-brand-600 hover:underline text-xs flex items-center gap-1">
                    Visit <ExternalLink size={10} />
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Collection History */}
        {collection_logs?.length > 0 && (
          <div className="card">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
              <History size={16} className="text-gray-600" />
              <h2 className="font-semibold text-gray-900">Collection History ({collection_logs.length})</h2>
            </div>
            <div className="divide-y divide-gray-50 max-h-80 overflow-auto">
              {collection_logs.map((l: any) => (
                <div key={l.id} className="px-5 py-3 flex items-center gap-3">
                  {l.success ? (
                    <CheckCircle size={16} className="text-green-500" />
                  ) : (
                    <XCircle size={16} className="text-red-500" />
                  )}
                  <div className="flex-1">
                    <div className="text-sm text-gray-900">
                      {l.success ? 'Successful' : 'Failed'} collection
                    </div>
                    <div className="text-xs text-gray-400">
                      {formatDate(l.start_time)} {l.duration_seconds ? `(${l.duration_seconds.toFixed(1)}s)` : ''}
                    </div>
                  </div>
                  <div className="text-sm text-gray-500">{l.records_collected} records</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

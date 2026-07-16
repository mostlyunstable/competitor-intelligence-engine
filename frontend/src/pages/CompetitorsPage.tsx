import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePolling, useDebounce } from '../hooks'
import { api } from '../lib/api'
import { formatDate, timeAgo } from '../lib/utils'
import {
  Plus, Search, Filter, Trash2, Edit, Copy, Play, Pause,
  ChevronLeft, ChevronRight, MoreVertical, ExternalLink, Globe,
  AlertTriangle, XCircle
} from 'lucide-react'

export default function CompetitorsPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [filterEnabled, setFilterEnabled] = useState<boolean | undefined>(undefined)
  const [filterFrequency, setFilterFrequency] = useState<string>('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [showAdd, setShowAdd] = useState(false)
  const [editing, setEditing] = useState<any>(null)

  const debouncedSearch = useDebounce(search, 300)

  const fetchData = useCallback(() => api.getCompetitors({
    search: debouncedSearch || undefined,
    enabled: filterEnabled,
    frequency: filterFrequency || undefined,
    page,
    page_size: 20,
  }), [debouncedSearch, filterEnabled, filterFrequency, page])

  const { data, loading, refresh } = usePolling(fetchData, 15000)

  const competitors = data?.competitors || []
  const totalPages = data?.total_pages || 1

  const toggleSelect = (id: number) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelected(next)
  }

  const selectAll = () => {
    if (selected.size === competitors.length) setSelected(new Set())
    else setSelected(new Set(competitors.map((c: any) => c.id)))
  }

  const handleBulkDelete = async () => {
    if (!confirm(`Delete ${selected.size} competitors?`)) return
    await api.bulkDelete(Array.from(selected))
    setSelected(new Set())
    refresh()
  }

  const handleBulkEnable = async () => {
    await api.bulkEnable(Array.from(selected))
    setSelected(new Set())
    refresh()
  }

  const handleBulkDisable = async () => {
    await api.bulkDisable(Array.from(selected))
    setSelected(new Set())
    refresh()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-surface-900">Competitors</h1>
        <button onClick={() => setShowAdd(true)} className="btn-primary">
          <Plus size={16} /> Add Competitor
        </button>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400" />
            <input
              type="text"
              placeholder="Search competitors..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              className="input pl-9"
            />
          </div>
          <select
            value={filterEnabled === undefined ? '' : String(filterEnabled)}
            onChange={(e) => {
              const v = e.target.value
              setFilterEnabled(v === '' ? undefined : v === 'true')
              setPage(1)
            }}
            className="input w-auto"
          >
            <option value="">All Status</option>
            <option value="true">Enabled</option>
            <option value="false">Disabled</option>
          </select>
          <select
            value={filterFrequency}
            onChange={(e) => { setFilterFrequency(e.target.value); setPage(1) }}
            className="input w-auto"
          >
            <option value="">All Frequencies</option>
            <option value="hourly">Hourly</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
          </select>
        </div>

        {selected.size > 0 && (
          <div className="mt-3 flex items-center gap-2 pt-3 border-t border-surface-100">
            <span className="text-sm text-surface-500">{selected.size} selected</span>
            <button onClick={handleBulkEnable} className="btn-secondary btn-sm">Enable</button>
            <button onClick={handleBulkDisable} className="btn-secondary btn-sm">Disable</button>
            <button onClick={handleBulkDelete} className="btn-danger btn-sm">Delete</button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="bg-surface-50 border-b border-surface-200">
            <tr>
              <th className="table-header w-10">
                <input type="checkbox" onChange={selectAll} checked={selected.size === competitors.length && competitors.length > 0} className="rounded" />
              </th>
              <th className="table-header">Competitor</th>
              <th className="table-header">Frequency</th>
              <th className="table-header">Modules</th>
              <th className="table-header">Status</th>
              <th className="table-header">Last Collected</th>
              <th className="table-header">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-50">
            {loading && competitors.length === 0 ? (
              [...Array(5)].map((_, i) => (
                <tr key={i}><td colSpan={7} className="p-4"><div className="skeleton h-12 w-full" /></td></tr>
              ))
            ) : competitors.length === 0 ? (
              <tr><td colSpan={7} className="p-8 text-center text-surface-400">No competitors found</td></tr>
            ) : (
              competitors.map((c: any) => (
                <tr key={c.id} className="hover:bg-surface-50">
                  <td className="table-cell">
                    <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggleSelect(c.id)} className="rounded" />
                  </td>
                  <td className="table-cell">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-brand-100 rounded-lg flex items-center justify-center text-brand-700 font-medium text-sm">
                        {c.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <button
                          onClick={() => navigate(`/competitors/${c.id}`)}
                          className="font-medium text-surface-900 hover:text-brand-600 text-left"
                        >
                          {c.name}
                        </button>
                        <div className="flex items-center gap-1 text-xs text-surface-400">
                          <Globe size={10} />
                          {new URL(c.website_url).hostname}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="table-cell">
                    <span className="badge-neutral">{c.collection_frequency}</span>
                  </td>
                  <td className="table-cell">
                    <div className="flex flex-wrap gap-1">
                      {(c.modules || []).slice(0, 3).map((m: string) => (
                        <span key={m} className="badge-info text-[10px]">{m}</span>
                      ))}
                      {(c.modules || []).length > 3 && (
                        <span className="badge-neutral text-[10px]">+{c.modules.length - 3}</span>
                      )}
                    </div>
                  </td>
                  <td className="table-cell">
                    {c.enabled ? (
                      <span className="badge-success">Active</span>
                    ) : (
                      <span className="badge-danger">Disabled</span>
                    )}
                  </td>
                  <td className="table-cell text-surface-500 text-xs">
                    {timeAgo(c.last_collected)}
                  </td>
                  <td className="table-cell">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={async () => { await api.triggerCollection(c.id); refresh() }}
                        className="p-1.5 text-green-600 hover:bg-green-50 rounded"
                        title="Trigger Collection"
                      >
                        <Play size={14} />
                      </button>
                      <button
                        onClick={() => { setEditing(c); setShowAdd(true) }}
                        className="p-1.5 text-surface-500 hover:bg-surface-100 rounded"
                        title="Edit"
                      >
                        <Edit size={14} />
                      </button>
                      <button
                        onClick={async () => { await api.duplicateCompetitor(c.id); refresh() }}
                        className="p-1.5 text-surface-500 hover:bg-surface-100 rounded"
                        title="Duplicate"
                      >
                        <Copy size={14} />
                      </button>
                      <button
                        onClick={async () => { if (confirm('Delete this competitor?')) { await api.deleteCompetitor(c.id); refresh() } }}
                        className="p-1.5 text-red-500 hover:bg-red-50 rounded"
                        title="Delete"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        <div className="px-4 py-3 border-t border-surface-100 flex items-center justify-between">
          <span className="text-sm text-surface-500">
            Page {page} of {totalPages} ({data?.total || 0} total)
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="btn-secondary btn-sm"
            >
              <ChevronLeft size={14} /> Prev
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="btn-secondary btn-sm"
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Add/Edit Modal */}
      {showAdd && (
        <CompetitorModal
          competitor={editing}
          onClose={() => { setShowAdd(false); setEditing(null) }}
          onSaved={() => { setShowAdd(false); setEditing(null); refresh() }}
        />
      )}
    </div>
  )
}

function CompetitorModal({ competitor, onClose, onSaved }: {
  competitor?: any; onClose: () => void; onSaved: () => void
}) {
  const [form, setForm] = useState({
    name: competitor?.name || '',
    website_url: competitor?.website_url || '',
    enabled: competitor?.enabled ?? true,
    collection_frequency: competitor?.collection_frequency || 'daily',
    modules: competitor?.modules || ['discovery', 'company', 'services', 'pricing', 'content', 'social'],
    notes: competitor?.notes || '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<{name?: string; url?: string}>({})

  const [urlError, setUrlError] = useState('')
  const [urlChecking, setUrlChecking] = useState(false)

  const validateName = (name: string): string => {
    if (!name.trim()) return 'Competitor name is required'
    if (name.trim().length < 2) return 'Name must be at least 2 characters'
    if (name.trim().length > 255) return 'Name must be less than 255 characters'
    return ''
  }

  const validateUrl = (url: string): string => {
    if (!url.trim()) return 'Website URL is required'
    try {
      const parsed = new URL(url)
      if (!['http:', 'https:'].includes(parsed.protocol)) return 'URL must start with http:// or https://'
      if (!parsed.hostname || !parsed.hostname.includes('.')) return 'URL must contain a valid domain (e.g. example.com)'
      return ''
    } catch {
      return 'Invalid URL format — use https://example.com'
    }
  }

  const handleUrlBlur = async () => {
    const err = validateUrl(form.website_url)
    if (err) { setUrlError(err); return }
    setUrlChecking(true)
    try {
      await fetch(form.website_url, { method: 'HEAD', mode: 'no-cors', signal: AbortSignal.timeout(8000) })
      setUrlError('')
    } catch (e: any) {
      if (e.name === 'TimeoutError') setUrlError('URL timed out — server may be unreachable')
      else setUrlError('')
    } finally {
      setUrlChecking(false)
    }
  }

  const handleNameBlur = () => {
    const err = validateName(form.name)
    setFieldErrors(prev => ({ ...prev, name: err }))
  }

  const validateAll = (): boolean => {
    const nameErr = validateName(form.name)
    const urlErr = validateUrl(form.website_url)
    setFieldErrors({ name: nameErr, url: urlErr })
    return !nameErr && !urlErr
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')

    if (!validateAll()) {
      setSaving(false)
      return
    }

    try {
      if (competitor) {
        await api.updateCompetitor(competitor.id, form)
      } else {
        await api.createCompetitor(form)
      }
      onSaved()
    } catch (e: any) {
      let msg = e.message
      if (msg.includes('409')) msg = 'A competitor with this name already exists'
      else if (msg.includes('422')) msg = 'Invalid data — check name and URL fields'
      else if (msg.includes('Failed to fetch')) msg = 'Cannot reach server — is the backend running?'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  const allModules = ['discovery', 'company', 'services', 'pricing', 'content', 'social', 'technographic']

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-auto">
        <div className="px-6 py-4 border-b border-surface-200">
          <h2 className="text-lg font-semibold text-surface-900">{competitor ? 'Edit Competitor' : 'Add Competitor'}</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-start gap-2">
              <XCircle size={16} className="mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium">Failed to save competitor</p>
                <p className="mt-0.5">{error}</p>
              </div>
            </div>
          )}
          {!error && (fieldErrors.name || fieldErrors.url) && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700 flex items-start gap-2">
              <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" />
              <span>Please fix the errors below before saving.</span>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">Competitor Name *</label>
            <input
              value={form.name}
              onChange={e => { setForm({...form, name: e.target.value}); setFieldErrors(prev => ({...prev, name: ''})) }}
              onBlur={handleNameBlur}
              className={`input ${fieldErrors.name ? 'border-red-400 focus:ring-red-500 focus:border-red-500' : ''}`}
              placeholder="e.g. Ox Home Services"
              required
            />
            {fieldErrors.name && <p className="text-xs text-red-600 mt-1 flex items-center gap-1"><AlertTriangle size={12} />{fieldErrors.name}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">Website URL *</label>
            <input
              value={form.website_url}
              onChange={e => { setForm({...form, website_url: e.target.value}); setUrlError(''); setFieldErrors(prev => ({...prev, url: ''})) }}
              onBlur={handleUrlBlur}
              className={`input ${(urlError || fieldErrors.url) ? 'border-red-400 focus:ring-red-500 focus:border-red-500' : ''}`}
              placeholder="https://example.com"
              required
            />
            {urlChecking && <p className="text-xs text-surface-400 mt-1">Checking URL...</p>}
            {(urlError || fieldErrors.url) && (
              <p className="text-xs text-red-600 mt-1 flex items-center gap-1">
                <AlertTriangle size={12} />{urlError || fieldErrors.url}
              </p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-surface-700 mb-1">Frequency</label>
              <select value={form.collection_frequency} onChange={e => setForm({...form, collection_frequency: e.target.value})} className="input">
                <option value="hourly">Hourly</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-surface-700 mb-1">Status</label>
              <select value={String(form.enabled)} onChange={e => setForm({...form, enabled: e.target.value === 'true'})} className="input">
                <option value="true">Enabled</option>
                <option value="false">Disabled</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-2">Modules</label>
            <div className="flex flex-wrap gap-2">
              {allModules.map(m => (
                <button
                  key={m}
                  type="button"
                  onClick={() => {
                    const mods = form.modules.includes(m)
                      ? form.modules.filter((x: string) => x !== m)
                      : [...form.modules, m]
                    setForm({...form, modules: mods})
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    form.modules.includes(m)
                      ? 'bg-brand-50 border-brand-300 text-brand-700'
                      : 'bg-white border-surface-200 text-surface-500 hover:border-surface-300'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">Notes</label>
            <textarea value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} className="input" rows={2} />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={saving || urlChecking} className="btn-primary">
              {saving ? 'Saving...' : urlChecking ? 'Checking URL...' : competitor ? 'Update' : 'Create Competitor'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

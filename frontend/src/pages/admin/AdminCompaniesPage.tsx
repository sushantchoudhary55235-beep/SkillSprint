import { useCallback, useEffect, useState } from 'react'
import { adminApi } from '../../services/api'
import type { Company } from '../../types'

export default function AdminCompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    adminApi
      .companies()
      .then((res) => setCompanies(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load companies'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  const saveEdit = async (id: number) => {
    setError('')
    try {
      await adminApi.updateCompany(id, { name: editName })
      setEditingId(null)
      load()
    } catch (err: unknown) {
      setError((err as { response?: { data?: { message?: string } } })?.response?.data?.message || 'Update failed')
    }
  }

  const toggle = async (c: Company) => {
    setError('')
    try {
      await adminApi.updateCompany(c.id, { is_active: !c.is_active })
      load()
    } catch (err: unknown) {
      setError((err as { response?: { data?: { message?: string } } })?.response?.data?.message || 'Update failed')
    }
  }

  const create = async () => {
    if (!newName.trim()) return
    setCreating(true)
    setError('')
    try {
      await adminApi.createCompany(newName.trim())
      setNewName('')
      load()
    } catch (err: unknown) {
      setError((err as { response?: { data?: { message?: string } } })?.response?.data?.message || 'Create failed')
    } finally {
      setCreating(false)
    }
  }

  if (loading) return <div className="text-center py-12 text-slate-500">Loading companies…</div>

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Company Management</h1>
        <p className="text-sm text-slate-500">Placement partners whose question sets students can practice</p>
      </div>

      {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>}

      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-wrap gap-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Company name (e.g. TCS)"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm flex-1 min-w-40"
        />
        <button
          onClick={create}
          disabled={creating || !newName.trim()}
          className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          + Add company
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-3">Name</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-left px-4 py-3">Website</th>
              <th className="text-right px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {companies.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50">
                <td className="px-4 py-3">
                  {editingId === c.id ? (
                    <input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="rounded border border-slate-300 px-2 py-1 text-sm w-full"
                    />
                  ) : (
                    <span className="font-medium text-slate-700">{c.name}</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      c.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}
                  >
                    {c.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-400 text-xs">
                  {c.website || '—'}
                </td>
                <td className="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                  {editingId === c.id ? (
                    <>
                      <button
                        onClick={() => saveEdit(c.id)}
                        className="text-xs font-medium text-indigo-600 hover:underline"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="text-xs text-slate-400 hover:underline"
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => {
                          setEditingId(c.id)
                          setEditName(c.name)
                        }}
                        className="text-xs font-medium text-indigo-600 hover:underline"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => toggle(c)}
                        className={`text-xs font-medium ${
                          c.is_active ? 'text-red-600' : 'text-green-600'
                        } hover:underline`}
                      >
                        {c.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

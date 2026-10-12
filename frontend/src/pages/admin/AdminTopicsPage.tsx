import { useCallback, useEffect, useState } from 'react'
import { adminApi } from '../../services/api'
import type { Topic } from '../../types'

export default function AdminTopicsPage() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [editCategory, setEditCategory] = useState('')
  const [newName, setNewName] = useState('')
  const [newCategory, setNewCategory] = useState('')
  const [creating, setCreating] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    adminApi
      .topics()
      .then((res) => setTopics(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load topics'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  const saveEdit = async (id: number) => {
    setError('')
    try {
      await adminApi.updateTopic(id, { name: editName, category: editCategory })
      setEditingId(null)
      load()
    } catch (err: unknown) {
      setError((err as { response?: { data?: { message?: string } } })?.response?.data?.message || 'Update failed')
    }
  }

  const toggle = async (t: Topic) => {
    setError('')
    try {
      await adminApi.updateTopic(t.id, { is_active: !t.is_active })
      load()
    } catch (err: unknown) {
      setError((err as { response?: { data?: { message?: string } } })?.response?.data?.message || 'Update failed')
    }
  }

  const create = async () => {
    if (!newName.trim() || !newCategory.trim()) return
    setCreating(true)
    setError('')
    try {
      await adminApi.createTopic(newName.trim(), newCategory.trim())
      setNewName('')
      setNewCategory('')
      load()
    } catch (err: unknown) {
      setError((err as { response?: { data?: { message?: string } } })?.response?.data?.message || 'Create failed')
    } finally {
      setCreating(false)
    }
  }

  if (loading) return <div className="text-center py-12 text-slate-500">Loading topics…</div>

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Topic Management</h1>
        <p className="text-sm text-slate-500">Inactive topics are hidden from students</p>
      </div>

      {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>}

      {/* Create */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-wrap gap-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Topic name (e.g. Percentages)"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm flex-1 min-w-40"
        />
        <input
          value={newCategory}
          onChange={(e) => setNewCategory(e.target.value)}
          placeholder="Category (e.g. quantitative)"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm flex-1 min-w-40"
        />
        <button
          onClick={create}
          disabled={creating || !newName.trim() || !newCategory.trim()}
          className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          + Add topic
        </button>
      </div>

      {/* Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-3">Name</th>
              <th className="text-left px-4 py-3">Category</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-right px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {topics.map((t) => (
              <tr key={t.id} className="hover:bg-slate-50">
                <td className="px-4 py-3">
                  {editingId === t.id ? (
                    <input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="rounded border border-slate-300 px-2 py-1 text-sm w-full"
                    />
                  ) : (
                    <span className="font-medium text-slate-700">{t.name}</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {editingId === t.id ? (
                    <input
                      value={editCategory}
                      onChange={(e) => setEditCategory(e.target.value)}
                      className="rounded border border-slate-300 px-2 py-1 text-sm w-full"
                    />
                  ) : (
                    <span className="capitalize text-slate-500">{t.category}</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      t.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}
                  >
                    {t.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                  {editingId === t.id ? (
                    <>
                      <button
                        onClick={() => saveEdit(t.id)}
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
                          setEditingId(t.id)
                          setEditName(t.name)
                          setEditCategory(t.category)
                        }}
                        className="text-xs font-medium text-indigo-600 hover:underline"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => toggle(t)}
                        className={`text-xs font-medium ${
                          t.is_active ? 'text-red-600' : 'text-green-600'
                        } hover:underline`}
                      >
                        {t.is_active ? 'Deactivate' : 'Activate'}
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

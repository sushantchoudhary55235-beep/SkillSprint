import { useEffect, useState } from 'react'
import { practiceApi } from '../services/api'
import type { PracticeHistoryData } from '../types'

export default function HistoryPage() {
  const [data, setData] = useState<PracticeHistoryData | null>(null)
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')

  useEffect(() => {
    practiceApi.history(page, 10)
      .then((res) => setData(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load history'))
  }, [page])

  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
  if (!data) return <div className="text-center py-12 text-slate-500">Loading…</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Practice History</h1>
        <p className="text-sm text-slate-500">{data.total} sessions</p>
      </div>

      {data.sessions.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
          No practice sessions yet.
        </div>
      ) : (
        <div className="space-y-3">
          {data.sessions.map((s) => (
            <div key={s.id} className="bg-white border border-slate-200 rounded-xl p-4 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-slate-800">{s.mode}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    s.status === 'COMPLETED' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {s.status}
                  </span>
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  {s.question_count} questions · {s.correct_count} correct
                  {s.difficulty && ` · ${s.difficulty}`}
                </div>
              </div>
              <div className="text-right">
                <div className="text-lg font-bold text-slate-800">
                  {s.score !== null ? `${s.score}%` : '—'}
                </div>
                <div className="text-xs text-indigo-600">+{s.xp_earned} XP</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {data.total > 10 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40 hover:bg-slate-50"
          >
            Previous
          </button>
          <span className="px-3 py-1.5 text-sm text-slate-500">Page {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={data.sessions.length < 10}
            className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40 hover:bg-slate-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}

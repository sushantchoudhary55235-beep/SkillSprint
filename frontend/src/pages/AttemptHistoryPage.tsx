import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { assessmentApi } from '../services/api'
import type { AttemptHistoryItem } from '../types'

export default function AttemptHistoryPage() {
  const [attempts, setAttempts] = useState<AttemptHistoryItem[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    assessmentApi.myAttempts()
      .then((res) => setAttempts(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load attempts'))
  }, [])

  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">My Attempts</h1>
        <p className="text-sm text-slate-500">Your assessment history</p>
      </div>

      {attempts.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
          No assessment attempts yet.
          <Link to="/assessments" className="block mt-2 text-indigo-600 hover:underline text-sm">
            Take an assessment →
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {attempts.map((a) => (
            <Link
              key={a.id}
              to={a.status === 'SUBMITTED' ? `/attempts/${a.id}/result` : `/attempts/${a.id}`}
              className="block bg-white border border-slate-200 rounded-xl p-4 hover:border-indigo-300 hover:shadow-md transition-all"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-slate-800">{a.assessment_title}</h3>
                  <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                    <span className={`px-2 py-0.5 rounded-full ${
                      a.status === 'SUBMITTED' ? 'bg-green-100 text-green-700' :
                      a.status === 'EXPIRED' ? 'bg-red-100 text-red-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                      {a.status}
                    </span>
                    <span>{a.correct_count} correct / {a.correct_count + a.incorrect_count + a.unattempted_count} total</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xl font-bold text-slate-800">
                    {a.score !== null ? `${a.score}%` : '—'}
                  </div>
                  <div className="text-xs text-slate-400">
                    {new Date(a.started_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

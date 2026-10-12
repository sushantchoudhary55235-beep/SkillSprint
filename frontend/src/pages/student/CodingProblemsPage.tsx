import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { codingApi } from '../../services/api'
import type { CodingProblemListItem } from '../../types'

const DIFFICULTY_STYLES: Record<string, string> = {
  EASY: 'bg-green-100 text-green-700',
  MEDIUM: 'bg-yellow-100 text-yellow-700',
  HARD: 'bg-red-100 text-red-700',
}

export default function CodingProblemsPage() {
  const [problems, setProblems] = useState<CodingProblemListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [difficulty, setDifficulty] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const limit = 20

  useEffect(() => {
    setLoading(true)
    codingApi
      .problems(page, limit, difficulty ? { difficulty } : undefined)
      .then((res) => {
        setProblems(res.data.data.problems)
        setTotal(res.data.data.total)
        setError('')
      })
      .catch((err) => setError(err.response?.data?.message || 'Failed to load problems'))
      .finally(() => setLoading(false))
  }, [page, difficulty])

  const totalPages = Math.max(1, Math.ceil(total / limit))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Coding Problems</h1>
          <p className="text-sm text-slate-500">{total} problems · solve them to earn XP</p>
        </div>
        <select
          value={difficulty}
          onChange={(e) => {
            setDifficulty(e.target.value)
            setPage(1)
          }}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">All difficulties</option>
          <option value="EASY">Easy</option>
          <option value="MEDIUM">Medium</option>
          <option value="HARD">Hard</option>
        </select>
      </div>

      {error && <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>}
      {loading && <div className="text-center py-12 text-slate-500">Loading problems…</div>}

      {!loading && !error && problems.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
          No problems available yet. Check back soon!
        </div>
      )}

      {!loading && problems.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100">
          {problems.map((p) => (
            <Link
              key={p.id}
              to={`/student/coding/problems/${p.id}`}
              className="flex items-center justify-between p-4 hover:bg-slate-50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span
                  className={`w-6 text-center font-semibold ${p.solved ? 'text-green-600' : 'text-slate-300'}`}
                  title={p.solved ? 'Solved' : 'Unsolved'}
                >
                  {p.solved ? '✓' : '○'}
                </span>
                <span className="font-medium text-slate-700">{p.title}</span>
              </div>
              <span
                className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                  DIFFICULTY_STYLES[p.difficulty] || 'bg-slate-100 text-slate-600'
                }`}
              >
                {p.difficulty}
              </span>
            </Link>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => setPage((v) => Math.max(1, v - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 rounded-lg border border-slate-300 text-sm disabled:opacity-40"
          >
            ← Prev
          </button>
          <span className="text-sm text-slate-500">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((v) => Math.min(totalPages, v + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 rounded-lg border border-slate-300 text-sm disabled:opacity-40"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}

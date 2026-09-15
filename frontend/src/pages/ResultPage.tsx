import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { assessmentApi } from '../services/api'
import type { AttemptResultResponse } from '../types'

export default function ResultPage() {
  const { id } = useParams<{ id: string }>()
  const [result, setResult] = useState<AttemptResultResponse | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    assessmentApi.result(Number(id))
      .then((res) => setResult(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load result'))
  }, [id])

  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
  if (!result) return <div className="text-center py-12 text-slate-500">Loading result…</div>

  const formatTime = (s: number | null) => {
    if (s === null) return '—'
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m}m ${sec}s`
  }

  const isPass = result.accuracy >= 60

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Link to="/attempts" className="text-sm text-slate-500 hover:text-indigo-600">
        ← Back to attempts
      </Link>

      {/* Score Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 text-center">
        <div className="text-sm text-slate-500 mb-1">{result.assessment_title}</div>
        <h1 className="text-2xl font-bold text-slate-800 mb-4">Assessment Result</h1>

        <div className={`text-6xl font-bold mb-2 ${isPass ? 'text-green-600' : 'text-red-600'}`}>
          {result.score}%
        </div>
        <div className={`text-sm font-medium mb-4 ${isPass ? 'text-green-600' : 'text-red-600'}`}>
          {isPass ? '✓ Passed' : '✗ Needs Improvement'}
        </div>

        <div className="grid grid-cols-3 gap-4 text-sm max-w-sm mx-auto">
          <div className="bg-green-50 rounded-lg p-3">
            <div className="text-xl font-bold text-green-600">{result.correct_count}</div>
            <div className="text-xs text-green-700">Correct</div>
          </div>
          <div className="bg-red-50 rounded-lg p-3">
            <div className="text-xl font-bold text-red-600">{result.incorrect_count}</div>
            <div className="text-xs text-red-700">Incorrect</div>
          </div>
          <div className="bg-slate-50 rounded-lg p-3">
            <div className="text-xl font-bold text-slate-600">{result.unattempted_count}</div>
            <div className="text-xs text-slate-700">Unattempted</div>
          </div>
        </div>

        <div className="mt-4 flex items-center justify-center gap-6 text-sm text-slate-500">
          <span>Time: {formatTime(result.time_taken_seconds)}</span>
          <span>Questions: {result.total_questions}</span>
          <span>Accuracy: {result.accuracy}%</span>
        </div>

        <div className="mt-2 text-xs text-slate-400">
          Started: {new Date(result.started_at).toLocaleString()}
          {result.submitted_at && ` · Submitted: ${new Date(result.submitted_at).toLocaleString()}`}
        </div>
      </div>

      {/* Topic Performance */}
      {result.topic_performance.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-4">Topic Performance</h2>
          <div className="space-y-3">
            {result.topic_performance.map((tp) => (
              <div key={tp.topic_id}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-slate-700">{tp.topic_name}</span>
                  <span className="text-sm text-slate-500">{tp.correct}/{tp.total} ({tp.accuracy}%)</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${tp.accuracy >= 70 ? 'bg-green-500' : tp.accuracy >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${Math.min(tp.accuracy, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <Link
          to="/assessments"
          className="flex-1 bg-slate-100 text-slate-700 py-2.5 rounded-lg font-medium text-center hover:bg-slate-200 transition-colors"
        >
          Take Another
        </Link>
        <Link
          to="/dashboard"
          className="flex-1 bg-indigo-600 text-white py-2.5 rounded-lg font-medium text-center hover:bg-indigo-700 transition-colors"
        >
          Dashboard
        </Link>
      </div>
    </div>
  )
}

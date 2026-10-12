import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { codingApi } from '../../services/api'
import type { CodingSubmissionResult } from '../../types'

const VERDICT_STYLES: Record<string, string> = {
  ACCEPTED: 'text-green-600',
  WRONG_ANSWER: 'text-red-600',
  RUNTIME_ERROR: 'text-red-600',
  COMPILE_ERROR: 'text-orange-600',
  TIME_LIMIT_EXCEEDED: 'text-orange-600',
}

interface LocationState {
  result?: CodingSubmissionResult
}

export default function CodingResultPage() {
  const { id } = useParams()
  const location = useLocation()
  const state = (location.state || {}) as LocationState
  const [result, setResult] = useState<CodingSubmissionResult | null>(state.result ?? null)
  const [loading, setLoading] = useState(!state.result)
  const [error, setError] = useState('')

  useEffect(() => {
    if (result || !id) return
    // Fallback: fetch the most recent submission for this problem.
    codingApi
      .submissions(1, 1, Number(id))
      .then((res) => {
        const latest = res.data.data.submissions[0]
        if (!latest) {
          setError('No submission found for this problem yet.')
          return
        }
        // The history endpoint returns summary rows; fetch the full problem to
        // at least show status. Per-case data comes from the submit response,
        // which the solve page passes via router state.
        setResult({
          id: latest.id,
          problem_id: latest.problem_id,
          language: latest.language,
          status: latest.status,
          passed_test_cases: latest.passed_test_cases,
          total_test_cases: latest.total_test_cases,
          execution_time_ms: null,
          error_message: null,
          results: [],
        })
      })
      .catch((err) => setError(err.response?.data?.message || 'Failed to load result'))
      .finally(() => setLoading(false))
  }, [id, result])

  if (loading) return <div className="text-center py-12 text-slate-500">Loading result…</div>
  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
  if (!result) return null

  const accepted = result.status === 'ACCEPTED'

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div
        className={`rounded-xl p-8 text-center ${
          accepted ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
        }`}
      >
        <div className="text-4xl mb-2">{accepted ? '🎉' : '🧪'}</div>
        <h1 className={`text-2xl font-bold ${accepted ? 'text-green-700' : 'text-red-700'}`}>
          {result.status.replace(/_/g, ' ')}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          {result.passed_test_cases}/{result.total_test_cases} test cases passed ·{' '}
          {result.execution_time_ms ?? 0} ms · {result.language}
        </p>
        {accepted && (
          <p className="mt-3 text-sm font-medium text-green-700">
            +XP earned! Placement readiness improved.
          </p>
        )}
        {!accepted && result.results.some((r) => r.stderr) && (
          <div className="mt-4 bg-white border border-red-200 rounded-lg p-4 text-left">
            <p className="text-xs font-semibold text-red-500 mb-2">HINT — check this:</p>
            <pre className="text-xs text-slate-700 whitespace-pre-wrap overflow-x-auto">
              {result.results.find((r) => r.stderr)?.stderr}
            </pre>
          </div>
        )}
      </div>

      {result.results.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Per-test-case results</h2>
          <div className="space-y-2">
            {result.results.map((r) => (
              <div key={r.index} className="rounded-lg border border-slate-100 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-2 bg-slate-50 text-sm">
                  <span className="font-medium text-slate-600">
                    Case {r.index + 1} {r.hidden ? '(hidden)' : ''}
                  </span>
                  <span className={VERDICT_STYLES[r.verdict] || 'text-slate-600'}>
                    {r.verdict.replace(/_/g, ' ')} · {r.time_ms} ms
                  </span>
                </div>
                {!r.hidden && (r.expected !== null || r.actual !== null) && (
                  <div className="grid grid-cols-2 gap-3 p-3 text-xs font-mono">
                    <div>
                      <div className="text-slate-400 mb-1">Expected</div>
                      <div className="text-slate-700 whitespace-pre-wrap">{r.expected}</div>
                    </div>
                    <div>
                      <div className="text-slate-400 mb-1">Your output</div>
                      <div className="text-slate-700 whitespace-pre-wrap">{r.actual}</div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-3 justify-center">
        <Link
          to={`/student/coding/problems/${result.problem_id}`}
          className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
        >
          ← Back to problem
        </Link>
        <Link
          to="/student/coding/problems"
          className="px-4 py-2 rounded-lg border border-slate-300 text-sm hover:bg-slate-50"
        >
          All problems
        </Link>
      </div>
    </div>
  )
}

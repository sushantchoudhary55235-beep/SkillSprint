import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { codingApi, recommendationsApi } from '../../services/api'
import type { CodingProblemListItem, Recommendation } from '../../types'

const PRIORITY_STYLES: Record<string, string> = {
  HIGH: 'bg-red-100 text-red-700',
  MEDIUM: 'bg-yellow-100 text-yellow-700',
  LOW: 'bg-green-100 text-green-700',
}

export default function RecommendationsPage() {
  const [recs, setRecs] = useState<Recommendation[]>([])
  const [nextProblem, setNextProblem] = useState<CodingProblemListItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      recommendationsApi.list(10),
      codingApi.problems(1, 50).catch(() => null),
    ])
      .then(([recRes, probRes]) => {
        setRecs(recRes.data.data.recommendations)
        const unsolved = probRes?.data.data.problems.find((p) => !p.solved)
        setNextProblem(unsolved ?? probRes?.data.data.problems[0] ?? null)
      })
      .catch((err) => setError(err.response?.data?.message || 'Failed to load recommendations'))
      .finally(() => setLoading(false))
  }, [])

  const weakTopics = recs.filter((r) => r.priority === 'HIGH' && r.recommended_difficulty)
  const others = recs.filter((r) => !(r.priority === 'HIGH' && r.recommended_difficulty))

  if (loading) return <div className="text-center py-12 text-slate-500">Analyzing your performance…</div>
  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Your Recommendations</h1>
        <p className="text-sm text-slate-500">
          Personalized from your quiz accuracy — practice weak topics first
        </p>
      </div>

      {recs.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
          No recommendations yet. Take a practice quiz and they will appear here.
          <div className="mt-4">
            <Link to="/student/aptitude/topics" className="text-indigo-600 hover:underline text-sm font-medium">
              Start your first quiz →
            </Link>
          </div>
        </div>
      )}

      {/* Weak topics */}
      {weakTopics.length > 0 && (
        <div>
          <h2 className="font-semibold text-slate-700 mb-3">⚠ Weak topics (below 60% accuracy)</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {weakTopics.map((r) => (
              <div key={r.id} className="bg-white border border-red-200 rounded-xl p-5">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-slate-800">{r.topic_name}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${PRIORITY_STYLES[r.priority]}`}>
                    {r.priority.toLowerCase()} priority
                  </span>
                </div>
                <p className="text-sm text-slate-600 mb-3">{r.reason}</p>
                <Link
                  to={`/student/practice?topic_id=${r.topic_id}&difficulty=${r.recommended_difficulty || ''}`}
                  className="inline-block px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
                >
                  Practice now →
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Other recommendations */}
      {others.length > 0 && (
        <div>
          <h2 className="font-semibold text-slate-700 mb-3">Next steps</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {others.map((r) => (
              <div key={r.id} className="bg-white border border-slate-200 rounded-xl p-5">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-slate-800">{r.topic_name}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${PRIORITY_STYLES[r.priority] || ''}`}>
                    {r.recommendation_type.replace(/_/g, ' ').toLowerCase()}
                  </span>
                </div>
                <p className="text-sm text-slate-600 mb-3">{r.reason}</p>
                {r.recommendation_type === 'TAKE_TOPIC_TEST' ? (
                  <Link to="/student/assessments" className="text-indigo-600 hover:underline text-sm font-medium">
                    Take a topic test →
                  </Link>
                ) : (
                  <Link
                    to={`/student/practice?topic_id=${r.topic_id}&difficulty=${r.recommended_difficulty || 'medium'}`}
                    className="text-indigo-600 hover:underline text-sm font-medium"
                  >
                    Keep practicing →
                  </Link>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Companies + coding suggestion */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-2">🏢 Company preparation</h2>
          <p className="text-sm text-slate-600 mb-3">
            Practice company-specific question sets to simulate real placement drives.
          </p>
          <Link to="/student/companies" className="text-indigo-600 hover:underline text-sm font-medium">
            Browse companies →
          </Link>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-2">💻 Suggested next problem</h2>
          {nextProblem ? (
            <>
              <p className="text-sm text-slate-600 mb-3">
                {nextProblem.title} ({nextProblem.difficulty.toLowerCase()})
                {nextProblem.solved ? ' — already solved, try again for speed!' : ''}
              </p>
              <Link
                to={`/student/coding/problems/${nextProblem.id}`}
                className="text-indigo-600 hover:underline text-sm font-medium"
              >
                Solve it →
              </Link>
            </>
          ) : (
            <p className="text-sm text-slate-500">
              No coding problems available yet.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

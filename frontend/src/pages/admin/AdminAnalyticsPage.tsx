import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { adminApi } from '../../services/api'
import type {
  PopularTopicRow,
  QuestionAnalytics,
  StudentAnalyticsRow,
  SubmissionAnalytics,
} from '../../types'

const TABS = [
  { to: '/admin/analytics/students', label: 'Students' },
  { to: '/admin/analytics/questions', label: 'Questions' },
  { to: '/admin/analytics/submissions', label: 'Code Submissions' },
  { to: '/admin/analytics/popular-topics', label: 'Popular Topics' },
]

function Bar({ value, max, color }: { value: number; max: number; color: string }) {
  return (
    <div className="w-full bg-slate-100 rounded-full h-2">
      <div className={`${color} h-2 rounded-full`} style={{ width: `${max > 0 ? (value / max) * 100 : 0}%` }} />
    </div>
  )
}

export default function AdminAnalyticsPage() {
  const location = useLocation()
  const [students, setStudents] = useState<StudentAnalyticsRow[]>([])
  const [questions, setQuestions] = useState<QuestionAnalytics | null>(null)
  const [submissions, setSubmissions] = useState<SubmissionAnalytics | null>(null)
  const [popular, setPopular] = useState<PopularTopicRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')
    const jobs = [
      location.pathname.endsWith('/questions')
        ? adminApi.analyticsQuestions().then((r) => setQuestions(r.data.data))
        : location.pathname.endsWith('/submissions')
          ? adminApi.analyticsSubmissions().then((r) => setSubmissions(r.data.data))
          : location.pathname.endsWith('/popular-topics')
            ? adminApi.analyticsPopularTopics().then((r) => setPopular(r.data.data))
            : adminApi.analyticsStudents().then((r) => setStudents(r.data.data)),
    ]
    Promise.all(jobs)
      .catch((err) => setError(err.response?.data?.message || 'Failed to load analytics'))
      .finally(() => setLoading(false))
  }, [location.pathname])

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Platform Analytics</h1>
        <p className="text-sm text-slate-500">Server-computed metrics — never client-reported</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white border border-slate-200 rounded-xl p-1 w-fit">
        {TABS.map((t) => (
          <Link
            key={t.to}
            to={t.to}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              location.pathname === t.to
                ? 'bg-indigo-600 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {t.label}
          </Link>
        ))}
      </div>

      {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>}
      {loading && <div className="text-center py-12 text-slate-500">Loading…</div>}

      {/* Students tab */}
      {!loading && location.pathname.endsWith('/students') && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
              <tr>
                <th className="text-left px-4 py-3">Student</th>
                <th className="text-left px-4 py-3">Accuracy</th>
                <th className="text-left px-4 py-3">Readiness</th>
                <th className="text-left px-4 py-3">Streak</th>
                <th className="text-left px-4 py-3">XP</th>
                <th className="text-left px-4 py-3">Solved</th>
                <th className="text-left px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {students.map((s) => (
                <tr key={s.student_profile_id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-700">{s.name}</div>
                    <div className="text-xs text-slate-400">{s.email}</div>
                  </td>
                  <td className="px-4 py-3">{s.accuracy !== null ? `${s.accuracy}%` : '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="w-10">{Math.round(s.readiness_score)}</span>
                      <div className="w-16">
                        <Bar value={s.readiness_score} max={100} color="bg-green-500" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">{s.streak_days}🔥</td>
                  <td className="px-4 py-3">{s.xp}</td>
                  <td className="px-4 py-3">{s.problems_solved}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        s.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {s.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                </tr>
              ))}
              {students.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                    No students yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Questions tab */}
      {!loading && questions && (
        <div className="space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h2 className="font-semibold text-slate-800 mb-3">Most attempted topics</h2>
            {questions.topics.length === 0 ? (
              <p className="text-sm text-slate-500">No topic data yet.</p>
            ) : (
              <div className="space-y-3">
                {questions.topics.map((t) => (
                  <div key={t.topic_id}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-700">{t.topic_name}</span>
                      <span className="text-slate-500">
                        {t.total_attempts} attempts · {t.accuracy ?? 0}%
                      </span>
                    </div>
                    <Bar value={t.total_attempts} max={questions.topics[0].total_attempts} color="bg-indigo-500" />
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h2 className="font-semibold text-slate-800 mb-3">Question difficulty distribution</h2>
            <div className="grid grid-cols-3 gap-4">
              {Object.entries(questions.difficulty_distribution).map(([diff, count]) => (
                <div key={diff} className="text-center bg-slate-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-slate-800 capitalize">{diff}</div>
                  <div className="text-sm text-slate-500">{count} questions</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Submissions tab */}
      {!loading && submissions && (
        <div className="space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
                <tr>
                  <th className="text-left px-4 py-3">Problem</th>
                  <th className="text-left px-4 py-3">Difficulty</th>
                  <th className="text-left px-4 py-3">Submissions</th>
                  <th className="text-left px-4 py-3">Pass rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {submissions.problems.map((p) => (
                  <tr key={p.problem_id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-700">{p.title}</td>
                    <td className="px-4 py-3 capitalize">{p.difficulty.toLowerCase()}</td>
                    <td className="px-4 py-3">{p.submissions}</td>
                    <td className="px-4 py-3">{p.pass_rate !== null ? `${p.pass_rate}%` : '—'}</td>
                  </tr>
                ))}
                {submissions.problems.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-slate-400">
                      No code submissions yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h2 className="font-semibold text-slate-800 mb-3">Language distribution</h2>
            <div className="flex gap-4">
              {Object.entries(submissions.language_distribution).map(([lang, count]) => (
                <div key={lang} className="bg-slate-50 rounded-lg px-4 py-3 text-center">
                  <div className="text-lg font-bold capitalize">{lang}</div>
                  <div className="text-xs text-slate-500">{count} submissions</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Popular topics tab */}
      {!loading && location.pathname.endsWith('/popular-topics') && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-4">Top 10 attempted topics this week</h2>
          {popular.length === 0 ? (
            <p className="text-sm text-slate-500">No attempts recorded this week.</p>
          ) : (
            <div className="space-y-3">
              {popular.map((p) => (
                <div key={p.topic_id}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-700">{p.topic_name}</span>
                    <span className="text-slate-500">{p.attempts} answers</span>
                  </div>
                  <Bar value={p.attempts} max={popular[0].attempts} color="bg-orange-500" />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

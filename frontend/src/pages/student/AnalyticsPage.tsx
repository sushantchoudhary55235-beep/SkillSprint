import { useEffect, useState } from 'react'
import api from '../../services/api'
import type { ApiResponse } from '../../types'

interface PerformanceSummaryData {
  overall: {
    total_questions_attempted: number
    correct: number
    incorrect: number
    unanswered: number
    overall_accuracy: number | null
    practice_sessions: number
    practice_accuracy: number | null
    assessment_attempts: number
    assessment_avg_score: number | null
    coding_attempted: number
    coding_solved: number
    classification: string
  }
  topics: {
    topic_id: number
    topic_name: string
    total_attempts: number
    correct: number
    accuracy: number | null
    trend: string
    classification: string
  }[]
  by_difficulty: { difficulty: string; total_attempts: number; accuracy: number | null }[]
  by_company: { company_id: number; company_name: string; total_attempts: number; accuracy: number | null }[]
  strengths: { topic_id: number; topic_name: string; accuracy: number }[]
  weaknesses: { topic_id: number; topic_name: string; accuracy: number }[]
  trends: { label: string; score: number | null; accuracy: number | null; date: string | null }[]
}

export default function AnalyticsPage() {
  const [data, setData] = useState<PerformanceSummaryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .get<ApiResponse<PerformanceSummaryData>>('/performance/me')
      .then((res: { data: ApiResponse<PerformanceSummaryData> }) => setData(res.data.data))
      .catch((err: { response?: { data?: { message?: string } } }) =>
        setError(err.response?.data?.message || 'Failed to load analytics'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center py-12 text-slate-500">Crunching your numbers…</div>
  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
  if (!data) return null

  const maxAttempts = Math.max(1, ...data.trends.map((t) => t.score ?? 0))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Performance Analytics</h1>
        <p className="text-sm text-slate-500">
          Overall classification:{' '}
          <span className="font-medium capitalize">{data.overall.classification}</span>
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Questions attempted', value: data.overall.total_questions_attempted },
          { label: 'Overall accuracy', value: `${data.overall.overall_accuracy ?? 0}%` },
          { label: 'Practice sessions', value: data.overall.practice_sessions },
          {
            label: 'Coding solved',
            value: `${data.overall.coding_solved}/${data.overall.coding_attempted}`,
          },
          {
            label: 'Assessment avg',
            value:
              data.overall.assessment_avg_score !== null
                ? `${data.overall.assessment_avg_score}%`
                : '—',
          },
          { label: 'Correct', value: data.overall.correct },
          { label: 'Incorrect', value: data.overall.incorrect },
          { label: 'Unanswered', value: data.overall.unanswered },
        ].map((s) => (
          <div key={s.label} className="bg-white border border-slate-200 rounded-xl p-4">
            <div className="text-xl font-bold text-slate-800">{s.value}</div>
            <div className="text-xs text-slate-500 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">💪 Strengths</h2>
          {data.strengths.length === 0 ? (
            <p className="text-sm text-slate-500">Keep practicing — strengths appear at 80%+ accuracy.</p>
          ) : (
            <div className="space-y-2">
              {data.strengths.map((s) => (
                <div key={s.topic_id} className="flex justify-between text-sm">
                  <span className="text-slate-700">{s.topic_name}</span>
                  <span className="font-medium text-green-600">{s.accuracy}%</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">⚠ Weaknesses</h2>
          {data.weaknesses.length === 0 ? (
            <p className="text-sm text-slate-500">No weak topics detected. Great work!</p>
          ) : (
            <div className="space-y-2">
              {data.weaknesses.map((s) => (
                <div key={s.topic_id} className="flex justify-between text-sm">
                  <span className="text-slate-700">{s.topic_name}</span>
                  <span className="font-medium text-red-600">{s.accuracy}%</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Topics */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="font-semibold text-slate-800 mb-3">Topic breakdown</h2>
        {data.topics.length === 0 ? (
          <p className="text-sm text-slate-500">No topic data yet.</p>
        ) : (
          <div className="space-y-3">
            {data.topics.map((t) => (
              <div key={t.topic_id}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-700">
                    {t.topic_name}
                    <span className="ml-2 text-xs text-slate-400">
                      {t.correct}/{t.total_attempts} · {t.trend.toLowerCase()}
                    </span>
                  </span>
                  <span className="text-slate-500">{t.accuracy ?? 0}%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      (t.accuracy ?? 0) >= 80
                        ? 'bg-green-500'
                        : (t.accuracy ?? 0) >= 60
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                    }`}
                    style={{ width: `${Math.min(t.accuracy ?? 0, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Difficulty + Company */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">By difficulty</h2>
          {data.by_difficulty.length === 0 ? (
            <p className="text-sm text-slate-500">No data yet.</p>
          ) : (
            <div className="space-y-2 text-sm">
              {data.by_difficulty.map((d) => (
                <div key={d.difficulty} className="flex justify-between">
                  <span className="capitalize text-slate-700">{d.difficulty}</span>
                  <span className="text-slate-500">
                    {d.accuracy ?? 0}% of {d.total_attempts}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">By company</h2>
          {data.by_company.length === 0 ? (
            <p className="text-sm text-slate-500">No company-specific practice yet.</p>
          ) : (
            <div className="space-y-2 text-sm">
              {data.by_company.map((c) => (
                <div key={c.company_id} className="flex justify-between">
                  <span className="text-slate-700">{c.company_name}</span>
                  <span className="text-slate-500">
                    {c.accuracy ?? 0}% of {c.total_attempts}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Trend */}
      {data.trends.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Assessment score trend</h2>
          <div className="flex items-end gap-2 h-40">
            {data.trends.map((t, i) => (
              <div key={i} className="flex-1 flex flex-col items-center justify-end h-full">
                <div
                  className="w-full bg-indigo-500 rounded-t"
                  style={{ height: `${((t.score ?? 0) / maxAttempts) * 100}%` }}
                  title={`${t.label}: ${t.score ?? '—'}%`}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

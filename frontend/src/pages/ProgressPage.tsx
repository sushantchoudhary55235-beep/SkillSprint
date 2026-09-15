import { useEffect, useState } from 'react'
import { studentApi } from '../services/api'
import type { OverallProgressData } from '../types'

export default function ProgressPage() {
  const [data, setData] = useState<OverallProgressData | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    studentApi.progress()
      .then((res) => setData(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load progress'))
  }, [])

  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
  if (!data) return <div className="text-center py-12 text-slate-500">Loading…</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Your Progress</h1>
        <p className="text-sm text-slate-500">Track your learning journey</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-indigo-600">{data.total_questions_attempted}</div>
          <div className="text-xs text-slate-500 mt-1">Questions Attempted</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-green-600">{data.total_correct}</div>
          <div className="text-xs text-slate-500 mt-1">Correct Answers</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-purple-600">{data.overall_accuracy}%</div>
          <div className="text-xs text-slate-500 mt-1">Accuracy</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-orange-600">{data.total_sessions}</div>
          <div className="text-xs text-slate-500 mt-1">Total Sessions</div>
        </div>
      </div>

      {/* XP & Level */}
      <div className="bg-gradient-to-r from-indigo-500 to-purple-500 rounded-xl p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm opacity-75">Level</div>
            <div className="text-4xl font-bold">{data.level}</div>
          </div>
          <div className="text-right">
            <div className="text-sm opacity-75">Total XP</div>
            <div className="text-4xl font-bold">{data.xp}</div>
          </div>
        </div>
        <div className="mt-3 text-sm opacity-75">Current Streak: {data.current_streak} days</div>
      </div>

      {/* Topic Breakdown */}
      {data.topic_progress.length > 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-4">Topic-wise Performance</h2>
          <div className="space-y-4">
            {data.topic_progress.map((t) => (
              <div key={t.topic_id}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-slate-700">{t.topic_name}</span>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span>{t.correct_answers}/{t.total_attempts}</span>
                    <span className="font-medium text-slate-700">{t.accuracy}%</span>
                    <span className={`px-1.5 py-0.5 rounded ${
                      t.trend === 'improving' ? 'bg-green-100 text-green-700' :
                      t.trend === 'declining' ? 'bg-red-100 text-red-700' :
                      'bg-slate-100 text-slate-600'
                    }`}>
                      {t.trend}
                    </span>
                  </div>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2.5">
                  <div
                    className={`h-2.5 rounded-full transition-all ${
                      t.accuracy >= 70 ? 'bg-green-500' : t.accuracy >= 40 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${Math.min(t.accuracy, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
          No topic data yet. Complete some practice sessions to see your breakdown.
        </div>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { studentApi } from '../services/api'
import type { DashboardData } from '../types'

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    studentApi.dashboard()
      .then((res) => setData(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load dashboard'))
  }, [])

  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
  if (!data) return <div className="text-center py-12 text-slate-500">Loading dashboard…</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Welcome, {data.name}</h1>
          <p className="text-sm text-slate-500">Student ID: {data.student_id}</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-indigo-600">Level {data.level}</div>
          <div className="text-sm text-slate-500">{data.xp} XP</div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Questions Attempted', value: data.total_questions_attempted, color: 'bg-blue-50 text-blue-700' },
          { label: 'Correct', value: data.total_correct, color: 'bg-green-50 text-green-700' },
          { label: 'Accuracy', value: `${data.overall_accuracy}%`, color: 'bg-purple-50 text-purple-700' },
          { label: 'Current Streak', value: `${data.current_streak} days`, color: 'bg-orange-50 text-orange-700' },
        ].map((s) => (
          <div key={s.label} className={`rounded-xl p-4 ${s.color}`}>
            <div className="text-2xl font-bold">{s.value}</div>
            <div className="text-xs mt-1 opacity-75">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Link to="/quiz/daily" className="bg-indigo-600 text-white rounded-xl p-4 text-center hover:bg-indigo-700 transition-colors">
          <div className="text-lg font-semibold">📝</div>
          <div className="text-sm mt-1">Daily Quiz</div>
        </Link>
        <Link to="/topics" className="bg-white border border-slate-200 rounded-xl p-4 text-center hover:bg-slate-50 transition-colors">
          <div className="text-lg font-semibold">📚</div>
          <div className="text-sm mt-1">Practice Topic</div>
        </Link>
        <Link to="/companies" className="bg-white border border-slate-200 rounded-xl p-4 text-center hover:bg-slate-50 transition-colors">
          <div className="text-lg font-semibold">🏢</div>
          <div className="text-sm mt-1">Company Prep</div>
        </Link>
        <Link to="/assessments" className="bg-white border border-slate-200 rounded-xl p-4 text-center hover:bg-slate-50 transition-colors">
          <div className="text-lg font-semibold">📋</div>
          <div className="text-sm mt-1">Assessments</div>
        </Link>
      </div>

      {/* Topic Progress */}
      {data.topic_progress.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Topic Progress</h2>
          <div className="space-y-3">
            {data.topic_progress.map((t) => (
              <div key={t.topic_id} className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-slate-700">{t.topic_name}</span>
                    <span className="text-slate-500">{t.correct_answers}/{t.total_attempts} ({t.accuracy}%)</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2">
                    <div
                      className="bg-indigo-500 h-2 rounded-full transition-all"
                      style={{ width: `${Math.min(t.accuracy, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Sessions */}
      {data.recent_sessions.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Recent Activity</h2>
          <div className="space-y-2">
            {data.recent_sessions.map((s) => (
              <div key={s.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                <div>
                  <span className="text-sm font-medium text-slate-700">{s.mode}</span>
                  {s.topic_id && <span className="text-xs text-slate-500 ml-2">Topic #{s.topic_id}</span>}
                  {s.company_id && <span className="text-xs text-slate-500 ml-2">Company #{s.company_id}</span>}
                </div>
                <div className="text-sm">
                  <span className={`font-medium ${s.score !== null && s.score >= 70 ? 'text-green-600' : 'text-red-600'}`}>
                    {s.score !== null ? `${s.score}%` : '—'}
                  </span>
                  <span className="text-slate-400 ml-2">+{s.xp_earned} XP</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.topic_progress.length === 0 && data.recent_sessions.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center">
          <p className="text-slate-500">No activity yet. Start practicing to see your progress here!</p>
          <Link to="/topics" className="mt-3 inline-block text-indigo-600 hover:underline text-sm font-medium">
            Start Practice →
          </Link>
        </div>
      )}
    </div>
  )
}

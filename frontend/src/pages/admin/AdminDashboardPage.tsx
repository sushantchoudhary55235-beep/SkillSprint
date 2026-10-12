import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminApi } from '../../services/api'
import type { PlatformAnalytics } from '../../types'

export default function AdminDashboardPage() {
  const [data, setData] = useState<PlatformAnalytics | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    adminApi
      .analytics()
      .then((res) => setData(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load analytics'))
  }, [])

  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
  if (!data) return <div className="text-center py-12 text-slate-500">Loading dashboard…</div>

  const cards = [
    { label: 'Total students', value: data.total_students, icon: '🎓', color: 'bg-blue-50 text-blue-700' },
    { label: 'Total teachers', value: data.total_teachers, icon: '👨‍🏫', color: 'bg-purple-50 text-purple-700' },
    { label: 'Attempts', value: data.total_attempts, icon: '📝', color: 'bg-green-50 text-green-700' },
    { label: 'Active streaks', value: data.active_students_7d, icon: '🔥', color: 'bg-orange-50 text-orange-700' },
    { label: 'Code submissions', value: data.total_code_submissions, icon: '💻', color: 'bg-indigo-50 text-indigo-700' },
    { label: 'Questions in bank', value: data.total_questions, icon: '❓', color: 'bg-slate-100 text-slate-700' },
  ]

  const links = [
    { to: '/admin/users', label: 'Manage users', desc: 'Search, activate, deactivate' },
    { to: '/admin/topics', label: 'Manage topics', desc: 'Edit names, toggle status' },
    { to: '/admin/companies', label: 'Manage companies', desc: 'Placement partners' },
    { to: '/admin/analytics/students', label: 'View analytics', desc: 'Students, questions, code' },
    { to: '/admin/gamification-config', label: 'Gamification config', desc: 'XP rules, levels, badges' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Admin Dashboard</h1>
        <p className="text-sm text-slate-500">Platform overview at a glance</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {cards.map((c) => (
          <div key={c.label} className={`rounded-xl p-5 ${c.color}`}>
            <div className="text-2xl mb-1">{c.icon}</div>
            <div className="text-2xl font-bold">{c.value}</div>
            <div className="text-xs mt-1 opacity-75">{c.label}</div>
          </div>
        ))}
      </div>

      {data.average_accuracy !== null && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="text-sm text-slate-500">Average accuracy across submitted attempts</div>
          <div className="text-3xl font-bold text-indigo-600 mt-1">{data.average_accuracy}%</div>
        </div>
      )}

      <div>
        <h2 className="font-semibold text-slate-700 mb-3">Quick actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className="bg-white border border-slate-200 rounded-xl p-4 hover:border-indigo-300 transition-colors"
            >
              <div className="font-medium text-slate-800 text-sm">{l.label}</div>
              <div className="text-xs text-slate-500 mt-0.5">{l.desc}</div>
            </Link>
          ))}
        </div>
      </div>

      {/* Popular topics */}
      {data.popular_topics.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Most practiced topics</h2>
          <div className="space-y-2">
            {data.popular_topics.map((t) => (
              <div key={t.topic_id} className="flex justify-between text-sm">
                <span className="text-slate-700">{t.topic_name}</span>
                <span className="text-slate-500">{t.students_tracked} students tracked</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

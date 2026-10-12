import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { teacherApi } from '../../services/api'
import type { TeacherDashboardData } from '../../types'

const REASON_LABELS: Record<string, { label: string; style: string }> = {
  LOW_ACCURACY: { label: 'Low accuracy (<50%)', style: 'bg-red-100 text-red-700' },
  DECLINING: { label: 'Declining performance', style: 'bg-orange-100 text-orange-700' },
  INACTIVE: { label: 'Inactive 7+ days', style: 'bg-slate-100 text-slate-600' },
}

export default function TeacherDashboardPage() {
  const { user } = useAuth()
  const [data, setData] = useState<TeacherDashboardData | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    teacherApi
      .dashboard()
      .then((res) => setData(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load dashboard'))
  }, [])

  if (error) {
    return (
      <div className="space-y-4">
        <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!data) {
    return <div className="text-center py-12 text-slate-500">Loading your class…</div>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Teacher Dashboard</h1>
        <p className="text-sm text-slate-500">{user?.name} · class overview</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-indigo-600">{data.total_students}</div>
          <div className="text-xs text-slate-500 mt-1">Associated students</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-green-600">
            {data.average_accuracy !== null ? `${data.average_accuracy}%` : '—'}
          </div>
          <div className="text-xs text-slate-500 mt-1">Class average accuracy</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-purple-600">
            {data.average_assessment_score !== null ? `${data.average_assessment_score}%` : '—'}
          </div>
          <div className="text-xs text-slate-500 mt-1">Average assessment score</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-amber-600">
            {data.students_needing_attention?.length ?? 0}
          </div>
          <div className="text-xs text-slate-500 mt-1">Students needing attention</div>
        </div>
      </div>

      {data.students_needing_attention && data.students_needing_attention.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
          <h2 className="font-semibold text-amber-800 mb-1">Students needing attention</h2>
          <p className="text-xs text-amber-600 mb-3">
            Based on documented rules only: low recent accuracy, declining topic performance, or 7+ days of inactivity.
          </p>
          <div className="space-y-2">
            {data.students_needing_attention.map((s) => (
              <div
                key={s.student_profile_id}
                className="flex flex-wrap items-center justify-between gap-2 bg-white rounded-lg px-3 py-2"
              >
                <div>
                  <span className="text-sm font-medium text-slate-800">{s.name}</span>
                  <span className="text-xs text-slate-400 ml-2">{s.student_id}</span>
                </div>
                <div className="flex flex-wrap items-center gap-1">
                  {s.reasons.map((r) => (
                    <span
                      key={r}
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${REASON_LABELS[r]?.style ?? 'bg-slate-100 text-slate-600'}`}
                    >
                      {REASON_LABELS[r]?.label ?? r}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <Link to="/teacher/students" className="inline-block mt-3 text-sm text-indigo-600 hover:underline font-medium">
            Review full class list →
          </Link>
        </div>
      )}

      {data.weak_topics_class_wide.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Class-wide weak topics</h2>
          <p className="text-xs text-slate-500 mb-3">
            Topics flagged as weak by the most associated students.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
                <tr>
                  <th className="text-left px-4 py-3">Topic</th>
                  <th className="text-left px-4 py-3">Students affected</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.weak_topics_class_wide.map((t) => (
                  <tr key={t.topic_id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-700">{t.topic_name}</td>
                    <td className="px-4 py-3 text-slate-500">{t.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!error && data.students.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 text-center">
          <p className="text-slate-500">No students associated yet.</p>
          <Link
            to="/teacher/students"
            className="mt-3 inline-block px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
          >
            Add students →
          </Link>
        </div>
      )}
    </div>
  )
}

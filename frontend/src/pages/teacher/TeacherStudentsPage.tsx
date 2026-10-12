import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { teacherApi } from '../../services/api'
import type { AttentionStudent, TeacherStudentRow } from '../../types'

const REASON_LABELS: Record<string, { label: string; style: string }> = {
  LOW_ACCURACY: { label: 'Low accuracy (<50%)', style: 'bg-red-100 text-red-700' },
  DECLINING: { label: 'Declining performance', style: 'bg-orange-100 text-orange-700' },
  INACTIVE: { label: 'Inactive 7+ days', style: 'bg-slate-100 text-slate-600' },
}

export default function TeacherStudentsPage() {
  const { user } = useAuth()
  const [students, setStudents] = useState<TeacherStudentRow[]>([])
  const [attention, setAttention] = useState<AttentionStudent[]>([])
  const [stats, setStats] = useState<{ total: number; avgAcc: number | null; avgScore: number | null }>({
    total: 0,
    avgAcc: null,
    avgScore: null,
  })
  const [studentId, setStudentId] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    teacherApi
      .dashboard()
      .then((res) => {
        const d = res.data.data
        setStudents(d.students)
        setAttention(d.students_needing_attention ?? [])
        setStats({
          total: d.total_students,
          avgAcc: d.average_accuracy,
          avgScore: d.average_assessment_score,
        })
        setError('')
      })
      .catch((err) => setError(err.response?.data?.message || 'Failed to load students'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  const addStudent = async () => {
    if (!studentId.trim()) return
    setMessage('')
    setError('')
    try {
      await teacherApi.addStudent(studentId.trim())
      setMessage(`Student ${studentId.trim()} associated successfully.`)
      setStudentId('')
      load()
    } catch (err: unknown) {
      setError((err as { response?: { data?: { message?: string } } })?.response?.data?.message || 'Failed to add student')
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">My Students</h1>
        <p className="text-sm text-slate-500">
          {user?.name} · students you monitor via their Student ID
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-indigo-600">{stats.total}</div>
          <div className="text-xs text-slate-500 mt-1">Associated students</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-green-600">
            {stats.avgAcc !== null ? `${stats.avgAcc}%` : '—'}
          </div>
          <div className="text-xs text-slate-500 mt-1">Class average accuracy</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-purple-600">
            {stats.avgScore !== null ? `${stats.avgScore}%` : '—'}
          </div>
          <div className="text-xs text-slate-500 mt-1">Average assessment score</div>
        </div>
      </div>

      {/* Students needing attention (Feature Group 16 — documented rules) */}
      {attention.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
          <h2 className="font-semibold text-amber-800 mb-1">Students needing attention</h2>
          <p className="text-xs text-amber-600 mb-3">
            Based on documented rules only: low recent accuracy, declining topic performance, or 7+ days of inactivity.
          </p>
          <div className="space-y-2">
            {attention.map((s) => (
              <div key={s.student_profile_id} className="flex flex-wrap items-center justify-between gap-2 bg-white rounded-lg px-3 py-2">
                <div>
                  <span className="text-sm font-medium text-slate-800">{s.name}</span>
                  <span className="text-xs text-slate-400 ml-2">{s.student_id}</span>
                </div>
                <div className="flex flex-wrap items-center gap-1">
                  {s.reasons.map((r) => (
                    <span key={r} className={`px-2 py-0.5 rounded-full text-xs font-medium ${REASON_LABELS[r]?.style ?? 'bg-slate-100 text-slate-600'}`}>
                      {REASON_LABELS[r]?.label ?? r}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Add student */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-wrap gap-2 items-center">
        <input
          value={studentId}
          onChange={(e) => setStudentId(e.target.value)}
          placeholder="Student ID (e.g. SS202600123)"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm flex-1 min-w-48"
        />
        <button
          onClick={addStudent}
          disabled={!studentId.trim()}
          className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          + Associate student
        </button>
        {message && <span className="text-sm text-green-600">{message}</span>}
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>

      {/* Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-3">Student</th>
              <th className="text-left px-4 py-3">Student ID</th>
              <th className="text-left px-4 py-3">Accuracy</th>
              <th className="text-left px-4 py-3">Assessment avg</th>
              <th className="text-left px-4 py-3">XP</th>
              <th className="text-left px-4 py-3">Level</th>
              <th className="text-left px-4 py-3">Streak</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {students.map((s) => (
              <tr key={s.student_profile_id} className="hover:bg-slate-50">
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-700">{s.name}</div>
                  <div className="text-xs text-slate-400">{s.email}</div>
                </td>
                <td className="px-4 py-3 text-slate-500">{s.student_id}</td>
                <td className="px-4 py-3">{s.overall_accuracy !== null ? `${s.overall_accuracy}%` : '—'}</td>
                <td className="px-4 py-3">
                  {s.assessment_avg_score !== null ? `${s.assessment_avg_score}%` : '—'}
                </td>
                <td className="px-4 py-3">{s.xp}</td>
                <td className="px-4 py-3">{s.level}</td>
                <td className="px-4 py-3">{s.current_streak}🔥</td>
              </tr>
            ))}
            {students.length === 0 && !loading && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                  No students associated yet. Add one by their Student ID above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

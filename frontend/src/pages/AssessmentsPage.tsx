import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { assessmentApi } from '../services/api'
import type { AssessmentRead } from '../types'

export default function AssessmentsPage() {
  const [assessments, setAssessments] = useState<AssessmentRead[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    assessmentApi.list()
      .then((res) => setAssessments(res.data.data.assessments))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load assessments'))
  }, [])

  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Assessments</h1>
        <p className="text-sm text-slate-500">Take timed tests and track your progress</p>
      </div>

      {assessments.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
          No assessments available yet.
        </div>
      ) : (
        <div className="space-y-4">
          {assessments.map((a) => (
            <Link
              key={a.id}
              to={`/assessments/${a.id}/start`}
              className="block bg-white border border-slate-200 rounded-xl p-5 hover:border-indigo-300 hover:shadow-md transition-all"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-slate-800">{a.title}</h3>
                  <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                    <span className="px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">
                      {a.assessment_type.replace('_', ' ')}
                    </span>
                    <span>{a.question_count} questions</span>
                    <span>{a.duration_minutes} min</span>
                  </div>
                </div>
                <div className="text-indigo-600 font-medium text-sm">Start →</div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

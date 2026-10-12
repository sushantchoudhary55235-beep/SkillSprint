import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { assessmentApi } from '../services/api'

export default function AssessmentStartPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [detail, setDetail] = useState<{ id: number; title: string; assessment_type: string; duration_minutes: number; question_count: number; is_active: boolean } | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!id) return
    assessmentApi.detail(Number(id))
      .then((res) => setDetail(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load assessment'))
  }, [id])

  const handleStart = async () => {
    if (!id) return
    setLoading(true)
    setError('')
    try {
      const res = await assessmentApi.start(Number(id))
      navigate(`/student/attempts/${res.data.data.attempt_id}`)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg || 'Failed to start assessment')
    } finally {
      setLoading(false)
    }
  }

  if (error) {
    return (
      <div className="max-w-lg mx-auto space-y-4">
        <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
        <button onClick={() => navigate('/student/assessments')} className="text-indigo-600 hover:underline text-sm">
          ← Back to assessments
        </button>
      </div>
    )
  }

  if (!detail) return <div className="text-center py-12 text-slate-500">Loading…</div>

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <button onClick={() => navigate('/student/assessments')} className="text-sm text-slate-500 hover:text-indigo-600">
        ← Back to assessments
      </button>

      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <h1 className="text-2xl font-bold text-slate-800 mb-4">{detail.title}</h1>

        <div className="space-y-3 mb-6">
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">Type</span>
            <span className="font-medium text-slate-700 capitalize">{detail.assessment_type.replace('_', ' ')}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">Duration</span>
            <span className="font-medium text-slate-700">{detail.duration_minutes} minutes</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">Questions</span>
            <span className="font-medium text-slate-700">{detail.question_count}</span>
          </div>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700 mb-4">
          ⚠️ Once you start, the timer begins. You cannot pause or restart.
        </div>

        <button
          onClick={handleStart}
          disabled={loading || !detail.is_active}
          className="w-full bg-indigo-600 text-white py-3 rounded-xl font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Starting…' : 'Start Assessment'}
        </button>
      </div>
    </div>
  )
}

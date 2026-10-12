import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { practiceApi } from '../services/api'

export default function DailyQuizPage() {
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    practiceApi.dailyQuiz()
      .then((res) => {
        // `session_id` is the param PracticePage consumes to resume an
        // in-progress session (`daily_session` never existed — audit fix H1).
        navigate(`/student/practice?session_id=${res.data.data.session_id}`)
      })
      .catch((err) => {
        setError(err.response?.data?.message || 'Failed to start daily quiz')
      })
  }, [navigate])

  if (error) {
    return (
      <div className="max-w-lg mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Daily Quiz</h1>
          <p className="text-sm text-slate-500">Challenge yourself with a daily set of questions</p>
        </div>
        <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto text-center py-12">
      <div className="text-4xl mb-4">📝</div>
      <h1 className="text-2xl font-bold text-slate-800 mb-2">Starting Daily Quiz…</h1>
      <p className="text-slate-500">Loading your questions</p>
    </div>
  )
}

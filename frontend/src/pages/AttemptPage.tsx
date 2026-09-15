import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { assessmentApi } from '../services/api'
import type { AttemptStartResponse, AttemptAnswerResponse } from '../types'

export default function AttemptPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const attemptId = Number(id)

  const [attempt, setAttempt] = useState<AttemptStartResponse | null>(null)
  const [currentIdx, setCurrentIdx] = useState(0)
  const [, setAnswers] = useState<Record<number, AttemptAnswerResponse>>({})
  const [selectedOptions, setSelectedOptions] = useState<Record<number, number>>({})
  const [marked, setMarked] = useState<Set<number>>(new Set())
  const [timeLeft, setTimeLeft] = useState(0)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  // Load attempt
  useEffect(() => {
    assessmentApi.result(attemptId)
      .then((res) => {
        const data = res.data.data
        if (data.status !== 'IN_PROGRESS') {
          navigate(`/attempts/${attemptId}/result`)
          return
        }
        // Reconstruct from result — but we need questions, so start is needed
        // Actually, let's use a different approach: load from the result endpoint for now
        // The backend returns questions only on start. We need to handle this differently.
        // For now, we'll redirect if already submitted.
      })
      .catch(() => {
        // Attempt might need to be started — this shouldn't happen normally
        setError('Could not load attempt')
        setLoading(false)
      })
  }, [attemptId, navigate])

  // We need to store attempt data in a way that survives page refresh
  // For now, we'll load from localStorage or re-start
  useEffect(() => {
    const saved = localStorage.getItem(`attempt_${attemptId}`)
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as AttemptStartResponse
        setAttempt(parsed)
        const deadline = new Date(parsed.started_at).getTime() + parsed.duration_minutes * 60 * 1000
        const remaining = Math.max(0, Math.floor((deadline - Date.now()) / 1000))
        setTimeLeft(remaining)
        setLoading(false)
      } catch {
        setLoading(false)
      }
    } else {
      setLoading(false)
    }
  }, [attemptId])

  // Timer
  useEffect(() => {
    if (timeLeft <= 0 && attempt) {
      // Auto-submit
      handleSubmit()
      return
    }
    const interval = setInterval(() => setTimeLeft((t) => Math.max(0, t - 1)), 1000)
    return () => clearInterval(interval)
  }, [timeLeft, attempt])

  const submitAnswer = useCallback(async (questionId: number, optionId: number | null) => {
    if (!attempt) return
    try {
      const res = await assessmentApi.submitAnswer(attempt.attempt_id, {
        question_id: questionId,
        selected_option_id: optionId,
      })
      setAnswers((prev) => ({ ...prev, [questionId]: res.data.data }))
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
      if (msg?.includes('expired')) {
        navigate(`/attempts/${attemptId}/result`)
      }
      setError(msg || 'Failed to submit answer')
    }
  }, [attempt, attemptId, navigate])

  const selectOption = async (questionId: number, optionId: number) => {
    setSelectedOptions((prev) => ({ ...prev, [questionId]: optionId }))
    await submitAnswer(questionId, optionId)
  }

  const handleSubmit = async () => {
    if (submitting) return
    setSubmitting(true)
    try {
      await assessmentApi.submitAttempt(attemptId)
      localStorage.removeItem(`attempt_${attemptId}`)
      navigate(`/attempts/${attemptId}/result`)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg || 'Failed to submit')
      setSubmitting(false)
    }
  }

  const toggleMark = (idx: number) => {
    setMarked((prev) => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`
  }

  if (loading) return <div className="text-center py-12 text-slate-500">Loading attempt…</div>
  if (!attempt) return <div className="text-center py-12 text-red-500">Attempt not found or already completed</div>
  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>

  const questions = attempt.questions
  const currentQ = questions[currentIdx]
  const answeredCount = Object.keys(selectedOptions).length
  const isTimeLow = timeLeft < 60

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* Header Bar */}
      <div className="bg-white border border-slate-200 rounded-xl px-4 py-3 flex items-center justify-between">
        <div className="text-sm font-medium text-slate-700">{attempt.question_count} Questions</div>
        <div className={`text-lg font-mono font-bold ${isTimeLow ? 'text-red-600 animate-pulse' : 'text-slate-700'}`}>
          {formatTime(timeLeft)}
        </div>
        <div className="text-sm text-slate-500">
          {answeredCount}/{attempt.question_count} answered
        </div>
      </div>

      {isTimeLow && (
        <div className="bg-red-50 border border-red-200 text-red-600 p-2 rounded-lg text-sm text-center">
          ⚠️ Less than 1 minute remaining!
        </div>
      )}

      <div className="flex gap-4">
        {/* Question Panel */}
        <div className="flex-1">
          <div className="bg-white border border-slate-200 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">Q{currentIdx + 1}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">{currentQ.difficulty}</span>
              {selectedOptions[currentQ.id] !== undefined && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">Answered</span>
              )}
            </div>

            <p className="text-slate-800 font-medium leading-relaxed mb-4">{currentQ.question_text}</p>

            <div className="space-y-2">
              {currentQ.options.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => selectOption(currentQ.id, opt.id)}
                  className={`w-full text-left border rounded-lg px-4 py-3 text-sm transition-all ${
                    selectedOptions[currentQ.id] === opt.id
                      ? 'border-indigo-500 bg-indigo-50'
                      : 'border-slate-200 bg-white hover:border-indigo-300'
                  }`}
                >
                  <span className="font-medium mr-2">{String.fromCharCode(65 + opt.option_order - 1)}.</span>
                  {opt.option_text}
                </button>
              ))}
            </div>

            <button
              onClick={() => toggleMark(currentIdx)}
              className={`mt-4 text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                marked.has(currentIdx)
                  ? 'bg-yellow-100 border-yellow-300 text-yellow-700'
                  : 'border-slate-200 text-slate-500 hover:bg-slate-50'
              }`}
            >
              {marked.has(currentIdx) ? '★ Marked for Review' : '☆ Mark for Review'}
            </button>
          </div>

          {/* Navigation */}
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => setCurrentIdx((i) => Math.max(0, i - 1))}
              disabled={currentIdx === 0}
              className="px-4 py-2 rounded-lg border text-sm disabled:opacity-40 hover:bg-slate-50"
            >
              ← Prev
            </button>
            <button
              onClick={() => setCurrentIdx((i) => Math.min(questions.length - 1, i + 1))}
              disabled={currentIdx >= questions.length - 1}
              className="px-4 py-2 rounded-lg border text-sm disabled:opacity-40 hover:bg-slate-50"
            >
              Next →
            </button>
          </div>
        </div>

        {/* Question Navigator Sidebar */}
        <div className="hidden md:block w-48">
          <div className="bg-white border border-slate-200 rounded-xl p-4 sticky top-20">
            <h3 className="text-xs font-medium text-slate-500 mb-2">Question Navigator</h3>
            <div className="grid grid-cols-5 gap-1.5">
              {questions.map((q, i) => {
                const isAnswered = selectedOptions[q.id] !== undefined
                const isCurrent = i === currentIdx
                const isMarked = marked.has(i)
                let bg = 'bg-slate-100 text-slate-600'
                if (isAnswered) bg = 'bg-green-500 text-white'
                if (isMarked && !isAnswered) bg = 'bg-yellow-400 text-white'
                if (isCurrent) bg += ' ring-2 ring-indigo-400'
                return (
                  <button
                    key={q.id}
                    onClick={() => setCurrentIdx(i)}
                    className={`w-8 h-8 rounded text-xs font-medium ${bg}`}
                  >
                    {i + 1}
                  </button>
                )
              })}
            </div>
            <div className="mt-3 space-y-1 text-xs">
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded bg-green-500" /> Answered</div>
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded bg-yellow-400" /> Marked</div>
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded bg-slate-100" /> Not answered</div>
            </div>

            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="w-full mt-4 bg-indigo-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {submitting ? 'Submitting…' : 'Submit Assessment'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

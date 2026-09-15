import { useEffect, useState, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { practiceApi } from '../services/api'
import type { PracticeStartData, PracticeAnswerData, PracticeCompleteData, QuestionForPractice } from '../types'

type Phase = 'config' | 'playing' | 'result'

export default function PracticePage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const topicId = searchParams.get('topic_id') ? Number(searchParams.get('topic_id')) : undefined
  const companyId = searchParams.get('company_id') ? Number(searchParams.get('company_id')) : undefined

  const [phase, setPhase] = useState<Phase>('config')
  const [session, setSession] = useState<PracticeStartData | null>(null)
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<number, PracticeAnswerData>>({})
  const [selectedOption, setSelectedOption] = useState<number | null>(null)
  const [timer, setTimer] = useState(0)

  const [questionStartTime, setQuestionStartTime] = useState<number>(Date.now())
  const [result, setResult] = useState<PracticeCompleteData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Difficulty selection
  const [difficulty, setDifficulty] = useState<string>('')

  // Timer
  useEffect(() => {
    if (phase !== 'playing') return
    const interval = setInterval(() => setTimer((t) => t + 1), 1000)
    return () => clearInterval(interval)
  }, [phase])

  const startSession = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await practiceApi.start({
        topic_id: topicId,
        company_id: companyId,
        difficulty: difficulty || undefined,
        question_count: 10,
      })
      setSession(res.data.data)
      setCurrentIdx(0)
      setAnswers({})
      setTimer(0)
      setQuestionStartTime(Date.now())
      setPhase('playing')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg || 'Failed to start practice')
    } finally {
      setLoading(false)
    }
  }, [topicId, companyId, difficulty])

  const currentQuestion: QuestionForPractice | null = session?.questions[currentIdx] ?? null

  const submitAnswer = async () => {
    if (!session || !currentQuestion) return
    const timeTaken = Math.round((Date.now() - questionStartTime) / 1000)


    try {
      const res = await practiceApi.answer(session.session_id, {
        question_id: currentQuestion.id,
        selected_option_id: selectedOption,
        time_taken_seconds: timeTaken,
      })
      setAnswers((prev) => ({ ...prev, [currentQuestion.id]: res.data.data }))
      setSelectedOption(null)
      setQuestionStartTime(Date.now())

      // Auto-advance after short delay
      setTimeout(() => {
        if (currentIdx < (session?.questions.length ?? 0) - 1) {
          setCurrentIdx((i) => i + 1)
        }
      }, 1500)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg || 'Failed to submit answer')
    }
  }

  const completeSession = async () => {
    if (!session) return
    setLoading(true)
    try {
      const res = await practiceApi.complete(session.session_id)
      setResult(res.data.data)
      setPhase('result')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg || 'Failed to complete session')
    } finally {
      setLoading(false)
    }
  }

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`

  // Config Phase
  if (phase === 'config') {
    return (
      <div className="max-w-lg mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Practice Session</h1>
          <p className="text-sm text-slate-500">
            {topicId ? `Topic #${topicId}` : companyId ? `Company #${companyId}` : 'Questions'}
          </p>
        </div>

        {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>}

        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Difficulty (optional)</label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            >
              <option value="">Any</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>

          <button
            onClick={startSession}
            disabled={loading}
            className="w-full bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Starting…' : 'Start Practice'}
          </button>
        </div>
      </div>
    )
  }

  // Result Phase
  if (phase === 'result' && result) {
    return (
      <div className="max-w-lg mx-auto space-y-6">
        <div className="bg-white border border-slate-200 rounded-xl p-6 text-center">
          <h1 className="text-2xl font-bold text-slate-800 mb-2">Session Complete!</h1>
          <div className="text-5xl font-bold text-indigo-600 my-4">{result.score}%</div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="bg-green-50 rounded-lg p-3">
              <div className="text-xl font-bold text-green-600">{result.correct}</div>
              <div className="text-xs text-green-700">Correct</div>
            </div>
            <div className="bg-red-50 rounded-lg p-3">
              <div className="text-xl font-bold text-red-600">{result.incorrect}</div>
              <div className="text-xs text-red-700">Incorrect</div>
            </div>
            <div className="bg-slate-50 rounded-lg p-3">
              <div className="text-xl font-bold text-slate-600">{result.unattempted}</div>
              <div className="text-xs text-slate-700">Skipped</div>
            </div>
          </div>
          <div className="mt-4 text-sm text-slate-500">
            Time: {formatTime(result.total_time_seconds)} · +{result.xp_earned} XP
          </div>
        </div>

        {/* Answer Review */}
        {session && (
          <div className="space-y-3">
            <h2 className="font-semibold text-slate-800">Review Answers</h2>
            {session.questions.map((q, i) => {
              const ans = answers[q.id]
              const correct = ans?.is_correct
              return (
                <div key={q.id} className={`border rounded-xl p-4 ${correct ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
                  <div className="text-xs text-slate-500 mb-1">Q{i + 1}</div>
                  <p className="text-sm font-medium text-slate-800">{q.question_text}</p>
                  {ans && (
                    <div className="mt-2 text-xs">
                      <span className={correct ? 'text-green-600' : 'text-red-600'}>
                        {correct ? '✓ Correct' : '✗ Incorrect'}
                      </span>
                      {ans.explanation && <span className="text-slate-500 ml-2">— {ans.explanation}</span>}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        <div className="flex gap-3">
          <button onClick={() => { setPhase('config'); setResult(null) }} className="flex-1 bg-slate-100 text-slate-700 py-2.5 rounded-lg font-medium hover:bg-slate-200 transition-colors">
            Practice Again
          </button>
          <button onClick={() => navigate('/dashboard')} className="flex-1 bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 transition-colors">
            Dashboard
          </button>
        </div>
      </div>
    )
  }

  // Playing Phase
  if (!currentQuestion || !session) return null
  const answered = !!answers[currentQuestion.id]
  const ans = answers[currentQuestion.id]
  const progress = ((currentIdx + 1) / session.questions.length) * 100

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between bg-white border border-slate-200 rounded-xl px-4 py-3">
        <div className="text-sm text-slate-500">
          Q{currentIdx + 1} / {session.questions.length}
        </div>
        <div className="text-sm font-mono font-medium text-slate-700">{formatTime(timer)}</div>
        <div className="text-sm text-slate-500">
          {Object.keys(answers).length} answered
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-100 rounded-full h-2">
        <div className="bg-indigo-500 h-2 rounded-full transition-all" style={{ width: `${progress}%` }} />
      </div>

      {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>}

      {/* Question */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">{currentQuestion.difficulty}</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">{currentQuestion.question_type}</span>
        </div>
        <p className="text-slate-800 font-medium leading-relaxed">{currentQuestion.question_text}</p>

        {/* Options */}
        <div className="mt-4 space-y-2">
          {currentQuestion.options.map((opt) => {
            const isSelected = selectedOption === opt.id
            const isCorrectOption = ans && opt.id === ans.correct_option_id
            const isWrongSelection = ans && isSelected && !ans.is_correct

            let optClass = 'border-slate-200 bg-white hover:border-indigo-300'
            if (isSelected && !answered) optClass = 'border-indigo-500 bg-indigo-50'
            if (isCorrectOption) optClass = 'border-green-500 bg-green-50'
            if (isWrongSelection) optClass = 'border-red-500 bg-red-50'

            return (
              <button
                key={opt.id}
                onClick={() => !answered && setSelectedOption(opt.id)}
                disabled={answered}
                className={`w-full text-left border rounded-lg px-4 py-3 text-sm transition-all ${optClass}`}
              >
                <span className="font-medium mr-2">{String.fromCharCode(65 + opt.option_order - 1)}.</span>
                {opt.option_text}
                {isCorrectOption && <span className="ml-2 text-green-600 font-medium">✓</span>}
                {isWrongSelection && <span className="ml-2 text-red-600 font-medium">✗</span>}
              </button>
            )
          })}
        </div>

        {/* Explanation */}
        {ans?.explanation && (
          <div className="mt-4 p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
            💡 {ans.explanation}
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex gap-3">
        <button
          onClick={() => setCurrentIdx((i) => Math.max(0, i - 1))}
          disabled={currentIdx === 0}
          className="px-4 py-2.5 rounded-lg border border-slate-200 text-sm font-medium disabled:opacity-40 hover:bg-slate-50"
        >
          ← Prev
        </button>

        {!answered ? (
          <button
            onClick={submitAnswer}
            disabled={loading}
            className="flex-1 bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Submitting…' : 'Submit Answer'}
          </button>
        ) : (
          <button
            onClick={() => {
              if (currentIdx < session.questions.length - 1) setCurrentIdx((i) => i + 1)
            }}
            disabled={currentIdx >= session.questions.length - 1}
            className="flex-1 bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {currentIdx >= session.questions.length - 1 ? 'All Done' : 'Next →'}
          </button>
        )}
      </div>

      {/* Complete button */}
      {Object.keys(answers).length === session.questions.length && (
        <button
          onClick={completeSession}
          disabled={loading}
          className="w-full bg-green-600 text-white py-3 rounded-xl font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Finishing…' : 'Complete Session'}
        </button>
      )}
    </div>
  )
}

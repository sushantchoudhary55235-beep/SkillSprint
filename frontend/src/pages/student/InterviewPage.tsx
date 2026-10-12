import { useEffect, useState } from 'react'
import { interviewApi } from '../../services/api'
import type {
  InterviewConfig,
  InterviewFeedback,
  InterviewQuestions,
} from '../../types'

type Phase = 'config' | 'answering' | 'feedback'

export default function InterviewPage() {
  const [config, setConfig] = useState<InterviewConfig | null>(null)
  const [phase, setPhase] = useState<Phase>('config')
  const [category, setCategory] = useState('TECHNICAL')
  const [difficulty, setDifficulty] = useState('easy')
  const [experience, setExperience] = useState('fresher')
  const [questions, setQuestions] = useState<InterviewQuestions | null>(null)
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState<InterviewFeedback | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    interviewApi.config()
      .then((res) => setConfig(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load interview prep'))
      .finally(() => setLoading(false))
  }, [])

  const loadQuestions = async () => {
    setSubmitting(true)
    setError('')
    try {
      const res = await interviewApi.questions(category, difficulty, experience, 5)
      setQuestions(res.data.data)
      setCurrentIdx(0)
      setAnswer('')
      setFeedback(null)
      setPhase('answering')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg || 'Failed to load questions')
    } finally {
      setSubmitting(false)
    }
  }

  const submitAnswer = async () => {
    if (!questions) return
    const q = questions.questions[currentIdx]
    setSubmitting(true)
    setError('')
    try {
      const res = await interviewApi.evaluate(category, q.id, answer)
      setFeedback(res.data.data)
      setPhase('feedback')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg || 'Failed to evaluate answer')
    } finally {
      setSubmitting(false)
    }
  }

  const next = () => {
    if (questions && currentIdx < questions.questions.length - 1) {
      setCurrentIdx((i) => i + 1)
      setAnswer('')
      setFeedback(null)
      setPhase('answering')
    } else {
      setPhase('config')
    }
  }

  if (loading) return <div className="text-center py-12 text-slate-500">Loading interview prep…</div>
  if (error && !config) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
  if (!config) return null

  const inputCls = 'w-full border border-slate-300 rounded-lg px-3 py-2 text-sm'

  if (phase === 'config') {
    const categoryLabel = config.categories.find((c) => c.id === category)?.label
    return (
      <div className="max-w-lg mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Interview Preparation</h1>
          <p className="text-sm text-slate-500">Practice with structured feedback on your answers.</p>
        </div>
        {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>}
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div>
            <label htmlFor="iv-category" className="block text-sm font-medium text-slate-700 mb-1">Category</label>
            <select id="iv-category" value={category} onChange={(e) => setCategory(e.target.value)} className={inputCls}>
              {config.categories.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="iv-difficulty" className="block text-sm font-medium text-slate-700 mb-1">Difficulty</label>
            <select id="iv-difficulty" value={difficulty} onChange={(e) => setDifficulty(e.target.value)} className={inputCls}>
              {config.difficulties.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="iv-exp" className="block text-sm font-medium text-slate-700 mb-1">Experience level</label>
            <select id="iv-exp" value={experience} onChange={(e) => setExperience(e.target.value)} className={inputCls}>
              {config.experience_levels.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
          <button
            onClick={loadQuestions}
            disabled={submitting}
            className="w-full bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {submitting ? 'Loading…' : `Start ${categoryLabel} practice`}
          </button>
        </div>
      </div>
    )
  }

  if (!questions) return null
  const q = questions.questions[currentIdx]

  if (phase === 'answering') {
    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-3">
            <span>Q{currentIdx + 1} / {questions.questions.length}</span>
            <span className="capitalize">{questions.category_label} · {q.difficulty}</span>
          </div>
          <p className="text-slate-800 font-medium leading-relaxed">{q.question}</p>
          <label htmlFor="iv-answer" className="block text-sm font-medium text-slate-700 mt-4 mb-1">
            Your answer
          </label>
          <textarea
            id="iv-answer"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            rows={6}
            placeholder="Answer as you would in the interview — structure helps (e.g. STAR for behavioral)."
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
          {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm mt-3">{error}</div>}
          <button
            onClick={submitAnswer}
            disabled={submitting || !answer.trim()}
            className="w-full mt-3 bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {submitting ? 'Evaluating…' : 'Get feedback'}
          </button>
        </div>
      </div>
    )
  }

  if (!feedback) return null
  const fb = feedback.deterministic_feedback
  const qualityStyle =
    fb.quality === 'good' ? 'bg-green-50 text-green-700'
      : fb.quality === 'partial' ? 'bg-yellow-50 text-yellow-700'
        : 'bg-red-50 text-red-700'

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <h2 className="font-semibold text-slate-800 mb-2">Question</h2>
        <p className="text-sm text-slate-600">{feedback.question}</p>
        <h3 className="font-semibold text-slate-800 mt-4 mb-1 text-sm">Your answer</h3>
        <p className="text-sm text-slate-600 whitespace-pre-wrap bg-slate-50 rounded-lg p-3">{feedback.student_answer}</p>
      </div>

      {/* Deterministic feedback (backend-computed) */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-slate-800">Concept coverage</h2>
          <span className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${qualityStyle}`}>
            {fb.quality} · {fb.score}%
          </span>
        </div>
        <p className="text-xs text-slate-400 mb-2">Deterministic scoring — measures concept coverage, not correctness.</p>
        <div className="text-sm">
          <div className="font-medium text-slate-700 mb-1">Expected concepts:</div>
          <ul className="list-disc list-inside space-y-0.5">
            {feedback.expected_concepts.map((c) => (
              <li key={c} className={fb.missing_concepts.includes(c) ? 'text-red-600' : 'text-green-700'}>
                {c} {fb.missing_concepts.includes(c) && <span className="text-xs">(missing)</span>}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-sm text-indigo-700 bg-indigo-50 rounded-lg p-3 mt-3">{fb.suggestion}</p>
      </div>

      {/* AI feedback (clearly labelled as AI-generated) */}
      {feedback.ai_feedback && (
        <div className="bg-white border border-purple-200 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700">AI-generated</span>
            <span className="text-xs text-slate-400">guidance, not a verdict</span>
          </div>
          <p className="text-sm text-slate-600 whitespace-pre-wrap">{feedback.ai_feedback.text}</p>
        </div>
      )}

      <p className="text-xs text-slate-400">{feedback.disclaimer}</p>

      <button
        onClick={next}
        className="w-full bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700"
      >
        {currentIdx < questions.questions.length - 1 ? 'Next question →' : 'Back to setup'}
      </button>
    </div>
  )
}

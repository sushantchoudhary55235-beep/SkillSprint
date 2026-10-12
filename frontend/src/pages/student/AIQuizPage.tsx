import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { aiQuestionApi, contentApi } from '../../services/api'
import type { AIQuestion, AIQuestionEvaluateResult, Company, Topic } from '../../types'

const DIFFICULTIES = ['easy', 'medium', 'hard'] as const

export default function AIQuizPage() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [companies, setCompanies] = useState<Company[]>([])
  const [companyId, setCompanyId] = useState<string>('')
  const [topicId, setTopicId] = useState<string>('')
  const [difficulty, setDifficulty] = useState<string>('medium')
  const [question, setQuestion] = useState<AIQuestion | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [result, setResult] = useState<AIQuestionEvaluateResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [error, setError] = useState('')
  const [startedAt, setStartedAt] = useState<number>(0)

  useEffect(() => {
    Promise.all([contentApi.topics(), contentApi.companies().catch(() => null)])
      .then(([t, c]) => {
        setTopics(t.data.data)
        setCompanies(c?.data.data ?? [])
      })
      .catch(() => setError('Failed to load topics'))
  }, [])

  const generate = async () => {
    setLoading(true)
    setError('')
    setResult(null)
    setSelected(null)
    setQuestion(null)
    try {
      const company = companies.find((c) => String(c.id) === companyId)?.name
      const topic = topics.find((t) => String(t.id) === topicId)
      const res = await aiQuestionApi.generate({
        company: company || undefined,
        topic_id: topic ? topic.id : undefined,
        topic_name: topic ? undefined : topicId === '' ? 'Quantitative Aptitude' : undefined,
        difficulty,
      })
      setQuestion(res.data.data)
      setStartedAt(Date.now())
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string }; status?: number } }
      if (e.response?.status === 429) {
        setError('AI limit reached (10 questions/minute). Please wait a moment and try again.')
      } else {
        setError(e.response?.data?.message || 'Failed to generate a question. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const submitAnswer = async () => {
    if (!question || !selected) return
    setEvaluating(true)
    setError('')
    try {
      // The answer key stays server-side; we only present the ticket issued
      // by /ai/questions/generate. The response reveals correctness, the
      // correct answer, and the explanation after submission.
      const res = await aiQuestionApi.evaluate({
        ticket: question.ticket,
        student_answer: selected,
        time_taken_seconds: Math.round((Date.now() - startedAt) / 1000),
      })
      setResult(res.data.data)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string }; status?: number } }
      if (e.response?.status === 429) {
        setError('AI limit reached (10 requests/minute). Please wait a moment and try again.')
      } else {
        setError(e.response?.data?.message || 'Failed to evaluate answer')
      }
    } finally {
      setEvaluating(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">🤖 AI Quiz</h1>
          <p className="text-sm text-slate-500">
            Gemini-generated questions tailored to your target company (max 10/min)
          </p>
        </div>
      </div>

      {/* Selector */}
      {!question && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Company</label>
            <select
              value={companyId}
              onChange={(e) => setCompanyId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">General placement prep</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Topic</label>
            <select
              value={topicId}
              onChange={(e) => setTopicId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Quantitative Aptitude (default)</option>
              {topics.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Difficulty</label>
            <div className="flex gap-2">
              {DIFFICULTIES.map((d) => (
                <button
                  key={d}
                  onClick={() => setDifficulty(d)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium capitalize ${
                    difficulty === d
                      ? 'bg-indigo-600 text-white'
                      : 'border border-slate-300 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>
          {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>}
          <button
            onClick={generate}
            disabled={loading}
            className="w-full py-3 rounded-lg bg-indigo-600 text-white font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? 'Generating question…' : '⚡ Generate question'}
          </button>
        </div>
      )}

      {/* Question */}
      {question && !result && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full font-medium">
              {question.company || 'General'}
            </span>
            <span>{question.topic_name}</span>
            <span className="capitalize">· {question.difficulty}</span>
          </div>
          <h2 className="text-lg font-semibold text-slate-800">{question.question}</h2>
          <div className="space-y-2">
            {question.options.map((opt) => {
              const isPicked = selected === opt
              return (
                <button
                  key={opt}
                  onClick={() => setSelected(opt)}
                  className={`w-full text-left px-4 py-3 rounded-lg border text-sm transition-colors ${
                    isPicked
                      ? 'border-indigo-500 bg-indigo-50 font-medium'
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {opt}
                </button>
              )
            })}
          </div>
          {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>}
          <button
            onClick={submitAnswer}
            disabled={!selected || evaluating}
            className="w-full py-3 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 disabled:opacity-50"
          >
            {evaluating ? 'Checking…' : 'Submit answer'}
          </button>
        </div>
      )}

      {/* Result */}
      {result && question && (
        <div className="space-y-4">
          <div
            className={`rounded-xl p-6 text-center ${
              result.is_correct ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
            }`}
          >
            <div className="text-3xl mb-1">{result.is_correct ? '✅' : '❌'}</div>
            <h2 className={`text-xl font-bold ${result.is_correct ? 'text-green-700' : 'text-red-700'}`}>
              {result.is_correct ? `Correct! +${result.xp_earned} XP` : 'Not quite'}
            </h2>
            {!result.is_correct && (
              <p className="text-sm text-slate-600 mt-1">
                Correct answer: <strong>{result.correct_answer}</strong>
              </p>
            )}
            {result.hint && !result.is_correct && (
              <p className="text-sm text-orange-600 mt-2">💡 {result.hint}</p>
            )}
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h3 className="font-semibold text-slate-800 mb-2">Explanation</h3>
            {/* Explanation now arrives only in the evaluate response (the
                answer key never reaches the client before answering). */}
            <p className="text-sm text-slate-600">{result.explanation || '—'}</p>
          </div>

          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="bg-white border border-slate-200 rounded-xl p-3">
              <div className="text-lg font-bold text-indigo-600">{result.xp_total} XP</div>
              <div className="text-xs text-slate-500">Total XP</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-3">
              <div className="text-lg font-bold text-orange-600">🔥 {result.current_streak}</div>
              <div className="text-xs text-slate-500">Day streak</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-3">
              <div className="text-lg font-bold text-purple-600">{result.readiness_score}</div>
              <div className="text-xs text-slate-500">Readiness</div>
            </div>
          </div>

          {result.overall_accuracy !== null && (
            <p className="text-center text-sm text-slate-500">
              Overall accuracy: {result.overall_accuracy}%
            </p>
          )}

          <div className="flex gap-3 justify-center">
            <button
              onClick={generate}
              className="px-5 py-2.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
            >
              Next question →
            </button>
            <Link
              to="/student/recommendations"
              className="px-5 py-2.5 rounded-lg border border-slate-300 text-sm hover:bg-slate-50"
            >
              See recommendations
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

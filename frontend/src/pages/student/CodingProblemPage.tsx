import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { codingApi, hintsApi } from '../../services/api'
import type { CodingProblemDetail, CodingSubmissionResult, ProgressiveHint } from '../../types'

const LANGUAGES = [
  { value: 'python', label: 'Python', starter: '# Read input from stdin and print output\n' },
  { value: 'java', label: 'Java', starter: '// Java: the local runner executes Python; use the sandbox for Java\n' },
  { value: 'cpp', label: 'C++', starter: '// C++: the local runner executes Python; use the sandbox for C++\n' },
]

const VERDICT_STYLES: Record<string, string> = {
  ACCEPTED: 'text-green-600',
  WRONG_ANSWER: 'text-red-600',
  RUNTIME_ERROR: 'text-red-600',
  COMPILE_ERROR: 'text-orange-600',
  TIME_LIMIT_EXCEEDED: 'text-orange-600',
}

export default function CodingProblemPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [problem, setProblem] = useState<CodingProblemDetail | null>(null)
  const [language, setLanguage] = useState('python')
  const [code, setCode] = useState(LANGUAGES[0].starter)
  const [result, setResult] = useState<CodingSubmissionResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  // Progressive hints (Feature Group 5): concept → approach → pseudocode → solution
  const [hint, setHint] = useState<ProgressiveHint | null>(null)
  const [hintLoading, setHintLoading] = useState(false)
  const [hintError, setHintError] = useState('')

  const getHint = async (nextLevel: number) => {
    if (!problem) return
    setHintLoading(true)
    setHintError('')
    try {
      const res = await hintsApi.progressive({
        problem_text: `${problem.title}\n${problem.description ?? ''}`,
        topic_name: `coding problem (${problem.difficulty.toLowerCase()})`,
        level: nextLevel,
        source_code: code,
      })
      setHint(res.data.data)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      setHintError(
        status === 429
          ? 'AI rate limit reached — try again in a minute.'
          : status === 503
            ? 'AI assistant is unavailable right now.'
            : 'Failed to get hint.'
      )
    } finally {
      setHintLoading(false)
    }
  }

  useEffect(() => {
    if (!id) return
    codingApi
      .problem(Number(id))
      .then((res) => setProblem(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load problem'))
      .finally(() => setLoading(false))
  }, [id])

  const runCode = async () => {
    if (!id) return
    setRunning(true)
    setError('')
    setResult(null)
    try {
      const res = await codingApi.submit(Number(id), language, code)
      setResult(res.data.data)
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        'Failed to run code'
      setError(message)
    } finally {
      setRunning(false)
    }
  }

  if (loading) return <div className="text-center py-12 text-slate-500">Loading problem…</div>
  if (error && !problem)
    return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
  if (!problem) return null

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Statement */}
      <div className="space-y-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h1 className="text-xl font-bold text-slate-800">{problem.title}</h1>
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                problem.difficulty === 'EASY'
                  ? 'bg-green-100 text-green-700'
                  : problem.difficulty === 'MEDIUM'
                    ? 'bg-yellow-100 text-yellow-700'
                    : 'bg-red-100 text-red-700'
              }`}
            >
              {problem.difficulty}
            </span>
          </div>
          <p className="text-sm text-slate-600 whitespace-pre-wrap">{problem.description}</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 text-sm">
          <div>
            <span className="font-semibold text-slate-700">Input format:</span>
            <p className="text-slate-600 whitespace-pre-wrap">{problem.input_format || '—'}</p>
          </div>
          <div>
            <span className="font-semibold text-slate-700">Output format:</span>
            <p className="text-slate-600 whitespace-pre-wrap">{problem.output_format || '—'}</p>
          </div>
          <div>
            <span className="font-semibold text-slate-700">Constraints:</span>
            <p className="text-slate-600 whitespace-pre-wrap">{problem.constraints || '—'}</p>
          </div>
        </div>

        {problem.sample_test_cases.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h2 className="font-semibold text-slate-800 mb-3">Sample test cases</h2>
            <div className="space-y-3">
              {problem.sample_test_cases.map((tc, i) => (
                <div key={i} className="grid grid-cols-2 gap-3 text-xs font-mono">
                  <div className="bg-slate-50 rounded-lg p-3">
                    <div className="text-slate-400 mb-1">Input</div>
                    <div className="text-slate-700 whitespace-pre-wrap">{tc.input_data}</div>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-3">
                    <div className="text-slate-400 mb-1">Expected output</div>
                    <div className="text-slate-700 whitespace-pre-wrap">{tc.expected_output}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Editor */}
      <div className="space-y-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <select
              value={language}
              onChange={(e) => {
                setLanguage(e.target.value)
                setCode(LANGUAGES.find((l) => l.value === e.target.value)?.starter ?? '')
              }}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
            >
              {LANGUAGES.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
            <div className="flex gap-2">
              <button
                onClick={runCode}
                disabled={running}
                className="px-4 py-1.5 rounded-lg border border-indigo-300 text-indigo-700 text-sm font-medium hover:bg-indigo-50 disabled:opacity-50"
              >
                {running ? 'Running…' : '▶ Run'}
              </button>
              <button
                onClick={() => {
                  setResult(null)
                  runCode().then(() => {
                    /* result shown inline; navigate to dedicated result view from link below */
                  })
                }}
                disabled={running}
                className="px-4 py-1.5 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 disabled:opacity-50"
              >
                Submit
              </button>
            </div>
          </div>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            spellCheck={false}
            rows={16}
            className="w-full font-mono text-sm bg-slate-900 text-slate-100 rounded-lg p-4 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <p className="mt-2 text-xs text-slate-400">
            Tip: the development runner executes Python locally; Java/C++ need the sandbox runner.
          </p>
        </div>

        {error && <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>}

        {/* Progressive hint ladder (Feature Group 5) */}
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-slate-700">Stuck? Get a hint</span>
            {!hint && (
              <button
                onClick={() => getHint(1)}
                disabled={hintLoading}
                className="px-3 py-1 rounded-lg border border-indigo-300 text-indigo-700 text-xs font-medium hover:bg-indigo-50 disabled:opacity-50"
              >
                {hintLoading ? 'Thinking…' : '💡 Hint 1 (concept)'}
              </button>
            )}
          </div>
          {hint && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700">
                  Hint {hint.level}/{hint.max_level}: {hint.label}
                </span>
              </div>
              <p className="text-sm text-slate-600 whitespace-pre-wrap">{hint.text}</p>
              <div className="flex gap-2">
                {hint.level < hint.max_level && (
                  <button
                    onClick={() => getHint(hint.level + 1)}
                    disabled={hintLoading}
                    className="px-3 py-1 rounded-lg bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {hintLoading ? 'Thinking…' : `Next hint: ${hint.level === 1 ? 'approach' : hint.level === 2 ? 'pseudocode' : 'full explanation'}`}
                  </button>
                )}
                <button
                  onClick={() => { setHint(null); setHintError('') }}
                  className="px-3 py-1 rounded-lg border border-slate-200 text-slate-500 text-xs hover:bg-slate-50"
                >
                  Hide hints
                </button>
              </div>
              {hint.remaining === 0 && (
                <p className="text-xs text-slate-400">That's the full explanation — try re-implementing it yourself!</p>
              )}
            </div>
          )}
          {hintError && <p className="text-xs text-amber-600 mt-2">{hintError}</p>}
          <p className="text-xs text-slate-400 mt-2">
            Hints are rate-limited (10/min) and escalate gradually — answers are not revealed until the final level.
          </p>
        </div>

        {result && (
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className={`font-bold ${VERDICT_STYLES[result.status] || 'text-slate-700'}`}>
                {result.status.replace(/_/g, ' ')}
              </span>
              <button
                onClick={() => navigate(`/student/coding/problems/${problem.id}/result`, { state: { result } })}
                className="text-xs text-indigo-600 hover:underline"
              >
                Open full result →
              </button>
            </div>
            <div className="text-sm text-slate-500">
              {result.passed_test_cases}/{result.total_test_cases} test cases passed ·{' '}
              {result.execution_time_ms ?? 0} ms
            </div>
            <div className="space-y-2">
              {result.results.map((r) => (
                <div key={r.index} className="flex items-center justify-between text-sm bg-slate-50 rounded-lg px-3 py-2">
                  <span className="text-slate-600">
                    Case {r.index + 1} {r.hidden ? '(hidden)' : ''}
                  </span>
                  <span className={VERDICT_STYLES[r.verdict] || 'text-slate-600'}>
                    {r.verdict.replace(/_/g, ' ')}
                  </span>
                </div>
              ))}
            </div>
            {result.error_message && (
              <pre className="bg-slate-900 text-red-300 text-xs rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
                {result.error_message}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

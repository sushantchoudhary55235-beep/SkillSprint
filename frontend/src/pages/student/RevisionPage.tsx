import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { coachingApi } from '../../services/api'
import type { RevisionFeed, RevisionTopic } from '../../types'

const COUNTS: (5 | 10 | 15)[] = [5, 10, 15]

export default function RevisionPage() {
  const [feed, setFeed] = useState<RevisionFeed | null>(null)
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState<number | null>(null)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const load = () => {
    setLoading(true)
    coachingApi.revision()
      .then((res) => setFeed(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load revision feed'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const startRevision = async (count: 5 | 10 | 15) => {
    setStarting(count)
    setError('')
    try {
      const res = await coachingApi.revisionPractice(count)
      const session = res.data.data.session
      if (session) {
        navigate(`/student/practice?session_id=${session.session_id}`)
      } else {
        setError(res.data.data.message || 'Nothing to revise yet')
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg || 'Failed to start revision')
    } finally {
      setStarting(null)
    }
  }

  if (loading) return <div className="text-center py-12 text-slate-500">Building your revision list…</div>
  if (error && !feed) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
  if (!feed) return null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Revise Weak Topics</h1>
        <p className="text-sm text-slate-500">
          Topics where you gave wrong answers — prioritized by frequency, recency and decline.
        </p>
      </div>

      {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>}

      {/* Quick Revision */}
      <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-5">
        <h2 className="font-semibold text-indigo-800 mb-2">Quick revision</h2>
        <p className="text-xs text-slate-500 mb-3">
          Starts a focused practice session from your weakest wrong-answer topics.
        </p>
        <div className="flex flex-wrap gap-2">
          {COUNTS.map((c) => (
            <button
              key={c}
              onClick={() => startRevision(c)}
              disabled={starting !== null || feed.total === 0}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {starting === c ? 'Starting…' : `${c} questions`}
            </button>
          ))}
          <button
            onClick={load}
            className="px-4 py-2 rounded-lg border border-indigo-300 text-indigo-700 text-sm font-medium hover:bg-indigo-50"
          >
            ↻ Refresh
          </button>
        </div>
        {feed.total === 0 && (
          <p className="text-xs text-slate-500 mt-2">
            No revision targets yet — answer a few questions and your weak spots will appear here.
          </p>
        )}
      </div>

      {/* Prioritized topic list */}
      {feed.topics.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
          Nothing to revise — great work! 🎉
        </div>
      ) : (
        <div className="space-y-3">
          {feed.topics.map((t: RevisionTopic) => (
            <div key={t.topic_id} className="bg-white border border-slate-200 rounded-xl p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium text-slate-800">{t.topic_name}</span>
                <div className="flex items-center gap-2 text-xs">
                  {t.recently_wrong && (
                    <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700">recently wrong</span>
                  )}
                  {t.declining && (
                    <span className="px-2 py-0.5 rounded-full bg-orange-100 text-orange-700">declining</span>
                  )}
                </div>
              </div>
              <div className="mt-1 grid grid-cols-3 gap-3 text-xs text-slate-500">
                <div>Accuracy: <span className="font-medium text-slate-700">{t.accuracy}%</span></div>
                <div>Wrong: <span className="font-medium text-red-600">{t.wrong_count}</span>/{t.attempts}</div>
                <div>Priority: <span className="font-medium text-slate-700">{t.priority_score}</span></div>
              </div>
              <div className="mt-2 flex items-center justify-between">
                <div className="w-full bg-slate-100 rounded-full h-1.5 mr-3">
                  <div
                    className="h-1.5 rounded-full bg-red-400"
                    style={{ width: `${Math.min(100, t.accuracy)}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Bookmarks shortcut (Feature Group 12) */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="font-semibold text-slate-800 mb-1">Saved questions</h2>
        <p className="text-xs text-slate-500 mb-2">Review your bookmarked questions and problems.</p>
        <a
          href="/student/bookmarks"
          onClick={(e) => { e.preventDefault(); navigate('/student/bookmarks') }}
          className="text-sm text-indigo-600 hover:underline"
        >
          Open saved items →
        </a>
      </div>
    </div>
  )
}

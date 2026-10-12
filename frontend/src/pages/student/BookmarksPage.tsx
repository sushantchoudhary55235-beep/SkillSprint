import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { bookmarksApi } from '../../services/api'
import type { BookmarkItem } from '../../types'

export default function BookmarksPage() {
  const [items, setItems] = useState<BookmarkItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true)
    bookmarksApi.list()
      .then((res) => setItems(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load bookmarks'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const remove = async (id: number) => {
    try {
      await bookmarksApi.remove(id)
      setItems((prev) => prev.filter((i) => i.id !== id))
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg || 'Failed to remove bookmark')
    }
  }

  if (loading) return <div className="text-center py-12 text-slate-500">Loading saved items…</div>
  if (error && items.length === 0) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Saved Questions</h1>
        <p className="text-sm text-slate-500">Your bookmarked questions, problems and concepts.</p>
      </div>

      {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>}

      {items.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
          Nothing saved yet. Bookmark questions from practice review or problems from the coding page.
          <Link to="/student/aptitude/topics" className="block mt-2 text-indigo-600 hover:underline text-sm">
            Practice now →
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((b) => (
            <div key={b.id} className="bg-white border border-slate-200 rounded-xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700">
                      {b.bookmark_type}
                    </span>
                    {b.difficulty && (
                      <span className="text-xs text-slate-400 capitalize">{b.difficulty}</span>
                    )}
                  </div>
                  {b.bookmark_type === 'QUESTION' && b.question_text && (
                    <>
                      <p className="text-sm text-slate-800 font-medium">{b.question_text}</p>
                      {b.correct_answer && (
                        <p className="text-xs text-green-700 mt-1">Answer: {b.correct_answer}</p>
                      )}
                      {b.explanation && <p className="text-xs text-slate-500 mt-1">{b.explanation}</p>}
                      {b.topic_id && (
                        <Link
                          to={`/student/practice?topic_id=${b.topic_id}`}
                          className="text-xs text-indigo-600 hover:underline mt-1 inline-block"
                        >
                          Practice this topic →
                        </Link>
                      )}
                    </>
                  )}
                  {b.bookmark_type === 'PROBLEM' && b.problem_id && (
                    <>
                      <p className="text-sm text-slate-800 font-medium">{b.problem_title}</p>
                      <Link
                        to={`/student/coding/problems/${b.problem_id}`}
                        className="text-xs text-indigo-600 hover:underline mt-1 inline-block"
                      >
                        Open problem →
                      </Link>
                    </>
                  )}
                  {b.bookmark_type === 'CONCEPT' && (
                    <p className="text-sm text-slate-800">{b.note}</p>
                  )}
                </div>
                <button
                  onClick={() => remove(b.id)}
                  aria-label={`Remove bookmark ${b.id}`}
                  className="text-xs text-red-500 hover:text-red-700 shrink-0"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

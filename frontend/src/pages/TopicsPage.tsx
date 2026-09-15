import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { contentApi } from '../services/api'
import type { Topic } from '../types'

export default function TopicsPage() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    contentApi.topics()
      .then((res) => setTopics(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load topics'))
  }, [])

  const categories = [...new Set(topics.map((t) => t.category))]
  const filtered = selectedCategory ? topics.filter((t) => t.category === selectedCategory) : topics

  const startPractice = (topicId: number) => {
    navigate(`/practice?topic_id=${topicId}`)
  }

  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Topics</h1>
        <p className="text-sm text-slate-500">Select a topic to practice</p>
      </div>

      {/* Category Filter */}
      {categories.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              !selectedCategory ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition-colors ${
                selectedCategory === cat ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      {/* Topic Grid */}
      {topics.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
          No topics available yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((topic) => (
            <button
              key={topic.id}
              onClick={() => startPractice(topic.id)}
              className="bg-white border border-slate-200 rounded-xl p-5 text-left hover:border-indigo-300 hover:shadow-md transition-all group"
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-slate-800 group-hover:text-indigo-600">{topic.name}</h3>
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 capitalize">
                  {topic.category}
                </span>
              </div>
              {topic.description && (
                <p className="text-sm text-slate-500 line-clamp-2">{topic.description}</p>
              )}
              <div className="mt-3 text-xs text-indigo-600 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                Start Practice →
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { roadmapApi } from '../../services/api'
import type { RoadmapData, RoadmapItem } from '../../types'

const STATUS_STYLES: Record<string, string> = {
  NOT_STARTED: 'bg-slate-100 text-slate-600',
  IN_PROGRESS: 'bg-blue-100 text-blue-700',
  COMPLETED: 'bg-green-100 text-green-700',
}

const PRIORITY_STYLES: Record<string, string> = {
  HIGH: 'border-l-red-500',
  MEDIUM: 'border-l-yellow-500',
  LOW: 'border-l-green-500',
}

export default function RoadmapPage() {
  const [roadmap, setRoadmap] = useState<RoadmapData | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true)
    roadmapApi
      .get()
      .then((res) => setRoadmap(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load roadmap'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const generate = async () => {
    setGenerating(true)
    setError('')
    try {
      const res = await roadmapApi.generate()
      setRoadmap(res.data.data)
    } catch (err: unknown) {
      setError((err as { response?: { data?: { message?: string } } })?.response?.data?.message || 'Failed to generate roadmap')
    } finally {
      setGenerating(false)
    }
  }

  const updateStatus = async (item: RoadmapItem, status: RoadmapItem['status']) => {
    try {
      await roadmapApi.updateItem(item.id, status)
      setRoadmap((prev) =>
        prev
          ? {
              ...prev,
              items: prev.items.map((i) => (i.id === item.id ? { ...i, status } : i)),
            }
          : prev,
      )
    } catch (err: unknown) {
      setError((err as { response?: { data?: { message?: string } } })?.response?.data?.message || 'Failed to update item')
    }
  }

  if (loading) return <div className="text-center py-12 text-slate-500">Loading roadmap…</div>

  if (error && !roadmap)
    return (
      <div className="space-y-4">
        <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
        <button
          onClick={generate}
          disabled={generating}
          className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium disabled:opacity-50"
        >
          {generating ? 'Generating…' : 'Generate my roadmap'}
        </button>
      </div>
    )

  if (!roadmap) return null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">{roadmap.title}</h1>
          <p className="text-sm text-slate-500">
            {roadmap.items.length} milestones · priority-ordered from your live performance
          </p>
        </div>
        <button
          onClick={generate}
          disabled={generating}
          className="px-4 py-2 rounded-lg border border-indigo-300 text-indigo-700 text-sm font-medium hover:bg-indigo-50 disabled:opacity-50"
        >
          {generating ? 'Regenerating…' : '↻ Regenerate'}
        </button>
      </div>

      {error && <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>}

      {/* Overall progress */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <div className="flex justify-between text-sm mb-2">
          <span className="font-medium text-slate-700">Overall progress</span>
          <span className="text-slate-500">{roadmap.overall_progress}%</span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-3">
          <div
            className="bg-indigo-500 h-3 rounded-full transition-all"
            style={{ width: `${Math.min(roadmap.overall_progress, 100)}%` }}
          />
        </div>
      </div>

      {roadmap.items.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center">
          <p className="text-slate-500">
            No roadmap milestones yet. Practice a few quizzes and your personalized roadmap will be generated.
          </p>
          <button
            onClick={generate}
            disabled={generating}
            className="mt-4 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium disabled:opacity-50"
          >
            {generating ? 'Generating…' : 'Generate my roadmap'}
          </button>
        </div>
      ) : (
        <div className="relative space-y-4">
          {roadmap.items.map((item, idx) => (
            <div key={item.id} className="flex gap-4">
              {/* timeline */}
              <div className="flex flex-col items-center">
                <div
                  className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold ${
                    item.status === 'COMPLETED'
                      ? 'bg-green-500 text-white'
                      : item.status === 'IN_PROGRESS'
                        ? 'bg-blue-500 text-white'
                        : 'bg-slate-200 text-slate-500'
                  }`}
                >
                  {item.status === 'COMPLETED' ? '✓' : idx + 1}
                </div>
                {idx < roadmap.items.length - 1 && (
                  <div className="w-0.5 flex-1 bg-slate-200 my-1" />
                )}
              </div>

              <div
                className={`flex-1 bg-white border border-slate-200 border-l-4 rounded-xl p-4 ${
                  PRIORITY_STYLES[item.priority]
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <span className="font-semibold text-slate-800">{item.topic_name || 'Topic'}</span>
                    <span
                      className={`ml-3 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[item.status]}`}
                    >
                      {item.status.replace(/_/g, ' ').toLowerCase()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {item.status === 'NOT_STARTED' && (
                      <button
                        onClick={() => updateStatus(item, 'IN_PROGRESS')}
                        className="px-3 py-1 rounded-lg bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-700"
                      >
                        Start
                      </button>
                    )}
                    {item.status === 'IN_PROGRESS' && (
                      <>
                        <Link
                          to={`/student/aptitude/topics`}
                          className="px-3 py-1 rounded-lg bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-700"
                        >
                          Practice
                        </Link>
                        <button
                          onClick={() => updateStatus(item, 'COMPLETED')}
                          className="px-3 py-1 rounded-lg border border-green-300 text-green-700 text-xs font-medium hover:bg-green-50"
                        >
                          Mark complete
                        </button>
                      </>
                    )}
                  </div>
                </div>
                <p className="mt-2 text-sm text-slate-600">{item.reason}</p>
                <div className="mt-2 flex gap-4 text-xs text-slate-400">
                  <span>Priority: {item.priority.toLowerCase()}</span>
                  {item.target_accuracy !== null && <span>Target: {item.target_accuracy}% accuracy</span>}
                  {item.recommended_difficulty && <span>Difficulty: {item.recommended_difficulty}</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

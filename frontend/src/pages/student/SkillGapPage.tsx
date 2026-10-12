import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { coachingApi } from '../../services/api'
import type { SkillGapData, SkillGapItem } from '../../types'

const LEVEL_STYLES: Record<string, string> = {
  strong: 'bg-green-100 text-green-700',
  moderate: 'bg-yellow-100 text-yellow-700',
  weak: 'bg-red-100 text-red-700',
}

const TREND_ICON: Record<string, string> = {
  IMPROVING: '📈',
  STABLE: '➡️',
  DECLINING: '📉',
  NEW: '✨',
}

const PRIORITY_STYLES: Record<string, string> = {
  HIGH: 'bg-red-500 text-white',
  MEDIUM: 'bg-yellow-500 text-white',
  LOW: 'bg-green-500 text-white',
  INSUFFICIENT_DATA: 'bg-slate-300 text-slate-600',
}

export default function SkillGapPage() {
  const [data, setData] = useState<SkillGapData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    coachingApi.skillGap()
      .then((res) => setData(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load skill gap'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center py-12 text-slate-500">Analyzing your skills…</div>
  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
  if (!data) return null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Skill Gap Analysis</h1>
        <p className="text-sm text-slate-500">
          Every level, priority and action is computed from your real answers — formulas shown below.
        </p>
      </div>

      {/* Summary chips */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-slate-800">{data.skills.length}</div>
          <div className="text-xs text-slate-500 mt-1">Topics practiced</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-red-600">{data.declining_count}</div>
          <div className="text-xs text-slate-500 mt-1">Declining</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-2xl font-bold text-green-600">{data.improving_count}</div>
          <div className="text-xs text-slate-500 mt-1">Improving</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-sm font-bold text-slate-800 truncate pt-1">
            {data.weakest_topic ? data.weakest_topic.topic_name : '—'}
          </div>
          <div className="text-xs text-slate-500 mt-1">Weakest topic</div>
        </div>
      </div>

      {data.skills.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
          No skill data yet — complete a practice session to unlock your analysis.
          <Link to="/student/aptitude/topics" className="block mt-2 text-indigo-600 hover:underline text-sm">
            Browse topics →
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {data.skills.map((s: SkillGapItem) => (
            <div key={s.topic_id} className="bg-white border border-slate-200 rounded-xl p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-semibold text-slate-800 truncate">{s.topic_name}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${LEVEL_STYLES[s.level]}`}>
                    {s.level}
                  </span>
                  {s.category && (
                    <span className="text-xs text-slate-400 hidden sm:inline">{s.category}</span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span title={`Trend: ${s.trend}`}>{TREND_ICON[s.trend]} {s.trend.toLowerCase()}</span>
                  <span className={`px-2 py-0.5 rounded-full font-medium ${PRIORITY_STYLES[s.priority]}`}>
                    {s.priority.replace('_', ' ')}
                  </span>
                </div>
              </div>
              <div className="mt-2 grid grid-cols-3 gap-3 text-xs text-slate-500">
                <div>Accuracy: <span className="font-medium text-slate-700">{s.accuracy ?? '—'}%</span></div>
                <div>Attempts: <span className="font-medium text-slate-700">{s.attempts}</span></div>
                <div>Priority score: <span className="font-medium text-slate-700">{s.priority_score}</span></div>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2">
                <div
                  className={`h-1.5 rounded-full ${
                    (s.accuracy ?? 0) >= 80 ? 'bg-green-500' : (s.accuracy ?? 0) >= 60 ? 'bg-yellow-500' : 'bg-red-400'
                  }`}
                  style={{ width: `${Math.min(100, s.accuracy ?? 0)}%` }}
                />
              </div>
              <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs text-slate-500 flex-1">{s.recommended_action}</p>
                {s.attempts >= 3 && (
                  <Link
                    to={`/student/practice?topic_id=${s.topic_id}&difficulty=${s.level === 'strong' ? 'hard' : s.level === 'moderate' ? 'medium' : 'easy'}`}
                    className="text-xs font-medium text-indigo-600 hover:underline"
                  >
                    Practice now →
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Transparency: documented formula (Feature Group 3 requirement) */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 text-xs text-slate-500 space-y-1">
        <div className="font-semibold text-slate-600 text-sm mb-1">How these are calculated</div>
        <div>Priority: {data.formula.priority}</div>
        <div>Trend: {data.formula.trend}</div>
        <div>Levels: {data.formula.levels}</div>
      </div>
    </div>
  )
}

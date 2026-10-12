import { useEffect, useMemo, useState } from 'react'
import { gamificationApi } from '../../services/api'
import type {
  ActivityEventItem,
  ApiResponse,
  BadgeCatalogEntry,
  EarnedBadge,
  GamificationSummary,
  MissionItem,
} from '../../types'

function StreakHeatmap({ events }: { events: ActivityEventItem[] }) {
  const days = useMemo(() => {
    const counts = new Map<string, number>()
    for (const e of events) {
      const d = e.created_at.slice(0, 10)
      counts.set(d, (counts.get(d) || 0) + 1)
    }
    const out: { date: string; count: number }[] = []
    const now = new Date()
    for (let i = 97; i >= 0; i--) {
      const d = new Date(now)
      d.setDate(now.getDate() - i)
      const key = d.toISOString().slice(0, 10)
      out.push({ date: key, count: counts.get(key) || 0 })
    }
    return out
  }, [events])

  const level = (count: number) =>
    count === 0
      ? 'bg-slate-100'
      : count < 3
        ? 'bg-orange-200'
        : count < 6
          ? 'bg-orange-400'
          : 'bg-orange-600'

  return (
    <div className="grid grid-cols-14 gap-1" style={{ gridTemplateColumns: 'repeat(14, minmax(0, 1fr))' }}>
      {days.map((d) => (
        <div
          key={d.date}
          title={`${d.date}: ${d.count} activities`}
          className={`aspect-square rounded ${level(d.count)}`}
        />
      ))}
    </div>
  )
}

export default function GamificationPage() {
  const [summary, setSummary] = useState<GamificationSummary | null>(null)
  const [earned, setEarned] = useState<EarnedBadge[]>([])
  const [catalog, setCatalog] = useState<BadgeCatalogEntry[]>([])
  const [missions, setMissions] = useState<MissionItem[]>([])
  const [activity, setActivity] = useState<ActivityEventItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    type MissionRes = { data: ApiResponse<MissionItem[]> }
    type ActivityRes = { data: ApiResponse<ActivityEventItem[]> }
    type CatalogRes = { data: ApiResponse<BadgeCatalogEntry[]> }

    Promise.all([
      gamificationApi.summary(),
      gamificationApi.badges(),
      gamificationApi.badgeCatalog().catch(() => null),
      gamificationApi.missions().then((r) => r as unknown as MissionRes).catch(() => null),
      gamificationApi.activity(98).then((r) => r as unknown as ActivityRes).catch(() => null),
    ])
      .then(([s, b, rawC, rawM, rawA]) => {
        setSummary(s.data.data)
        setEarned(b.data.data.earned)
        setCatalog((rawC as CatalogRes | null)?.data.data ?? [])
        setMissions((rawM as MissionRes | null)?.data.data ?? [])
        setActivity((rawA as ActivityRes | null)?.data.data ?? [])
      })
      .catch((err) => setError(err.response?.data?.message || 'Failed to load gamification data'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center py-12 text-slate-500">Loading your achievements…</div>
  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
  if (!summary) return null

  const earnedIds = new Set(earned.map((b) => b.badge_id))
  const locked = catalog.filter((b) => !earnedIds.has(b.id))
  const progressPercent = Math.min(100, Math.max(0, summary.progress_percent))

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Your Achievements</h1>

      {/* XP + Level + Streak */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-indigo-500 to-indigo-600 text-white rounded-xl p-5">
          <div className="text-3xl font-bold">{summary.xp} XP</div>
          <div className="text-sm opacity-80 mt-1">Level {summary.level}</div>
          <div className="mt-3 bg-white/20 rounded-full h-2">
            <div className="bg-white h-2 rounded-full" style={{ width: `${progressPercent}%` }} />
          </div>
          <div className="text-xs opacity-80 mt-1">
            {summary.xp_to_next_level} XP to level {summary.level + 1}
          </div>
        </div>

        <div className="bg-gradient-to-br from-orange-500 to-orange-600 text-white rounded-xl p-5">
          <div className="text-3xl font-bold">🔥 {summary.current_streak}</div>
          <div className="text-sm opacity-80 mt-1">day streak (best: {summary.longest_streak})</div>
        </div>

        <div className="bg-gradient-to-br from-purple-500 to-purple-600 text-white rounded-xl p-5">
          <div className="text-3xl font-bold">{earned.length}</div>
          <div className="text-sm opacity-80 mt-1">
            badges earned of {catalog.length || earned.length}
          </div>
        </div>
      </div>

      {/* Streak heatmap */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="font-semibold text-slate-800 mb-3">Activity heatmap (last ~14 weeks)</h2>
        {activity.length === 0 ? (
          <p className="text-sm text-slate-500">Start practicing to fill your heatmap!</p>
        ) : (
          <StreakHeatmap events={activity} />
        )}
      </div>

      {/* Missions */}
      {missions.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Daily missions</h2>
          <div className="space-y-3">
            {missions.map((m) => (
              <div key={m.id} className="flex items-center justify-between gap-4">
                <div className="flex-1">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-slate-700">{m.title}</span>
                    <span className="text-slate-500">
                      {m.progress}/{m.target_value} · +{m.xp_reward} XP
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${m.status === 'COMPLETED' ? 'bg-green-500' : 'bg-indigo-500'}`}
                      style={{ width: `${Math.min(100, (m.progress / m.target_value) * 100)}%` }}
                    />
                  </div>
                </div>
                {m.status === 'COMPLETED' && <span className="text-green-600 text-sm">✓</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Badges */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Earned badges</h2>
          {earned.length === 0 ? (
            <p className="text-sm text-slate-500">No badges yet — they unlock automatically as you practice!</p>
          ) : (
            <div className="space-y-3">
              {earned.map((b) => (
                <div key={b.id} className="flex items-start gap-3 p-3 bg-green-50 rounded-lg">
                  <span className="text-2xl">{b.icon || '🏅'}</span>
                  <div>
                    <div className="font-medium text-slate-800">{b.name}</div>
                    <div className="text-xs text-slate-500">{b.description}</div>
                    <div className="text-xs text-green-600 mt-1">
                      Earned {new Date(b.earned_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Locked badges</h2>
          {locked.length === 0 ? (
            <p className="text-sm text-slate-500">Wow — you have earned every active badge! 🎉</p>
          ) : (
            <div className="space-y-3">
              {locked.map((b) => (
                <div key={b.id} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg opacity-60">
                  <span className="text-2xl grayscale">{b.icon || '🔒'}</span>
                  <div>
                    <div className="font-medium text-slate-700">{b.name}</div>
                    <div className="text-xs text-slate-500">{b.description}</div>
                    <div className="text-xs text-slate-400 mt-1">
                      Unlock: {b.criteria_type.replace(/_/g, ' ').toLowerCase()} ≥ {b.criteria_value}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

import { useCallback, useEffect, useState } from 'react'
import { adminApi } from '../../services/api'
import type { GamificationConfig } from '../../types'

const CRITERIA_LABELS: Record<string, string> = {
  FIRST_ASSESSMENT: 'Complete N assessments',
  QUESTIONS_ANSWERED: 'Answer N questions',
  STREAK_DAYS: 'Reach an N-day streak',
  PERFECT_SCORE: 'Score N on an assessment',
  CODING_SOLVED: 'Solve N coding problems',
  PRACTICE_SESSIONS: 'Complete N practice sessions',
}

export default function AdminGamificationConfigPage() {
  const [config, setConfig] = useState<GamificationConfig | null>(null)
  const [error, setError] = useState('')
  const [busyBadge, setBusyBadge] = useState<number | null>(null)

  const load = useCallback(() => {
    adminApi
      .gamificationConfig()
      .then((res) => setConfig(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load config'))
  }, [])

  useEffect(load, [load])

  const toggleBadge = async (badgeId: number, current: boolean) => {
    setBusyBadge(badgeId)
    setError('')
    try {
      await adminApi.setBadgeStatus(badgeId, !current)
      load()
    } catch (err: unknown) {
      setError((err as { response?: { data?: { message?: string } } })?.response?.data?.message || 'Update failed')
    } finally {
      setBusyBadge(null)
    }
  }

  if (error && !config)
    return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
  if (!config)
    return <div className="text-center py-12 text-slate-500">Loading gamification config…</div>

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Gamification Configuration</h1>
        <p className="text-sm text-slate-500">
          Backend-authoritative reward rules — edits apply platform-wide instantly
        </p>
      </div>

      {error && <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>}

      {/* XP rules */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="font-semibold text-slate-800 mb-3">XP rules</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {Object.entries(config.xp_rules).map(([key, value]) => (
            <div key={key} className="bg-slate-50 rounded-lg p-3">
              <div className="text-2xl font-bold text-indigo-600">+{value}</div>
              <div className="text-xs text-slate-500 capitalize mt-0.5">
                {key.replace(/_/g, ' ').toLowerCase()}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Levels */}
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Level thresholds</h2>
          <div className="space-y-2">
            {config.level_thresholds.map((xp, i) => (
              <div key={i} className="flex justify-between text-sm">
                <span className="text-slate-700">
                  Level {i + 1}
                  {i === config.level_thresholds.length - 1 && (
                    <span className="text-xs text-slate-400 ml-2">
                      (+500 XP per level beyond)
                    </span>
                  )}
                </span>
                <span className="font-medium text-slate-600">{xp} XP</span>
              </div>
            ))}
          </div>
        </div>

        {/* Streaks */}
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Streak rules</h2>
          <div className="bg-slate-50 rounded-lg p-4 text-sm text-slate-600 space-y-2">
            <p>
              <strong>Milestone:</strong> every {config.streak_milestone_days} consecutive days
            </p>
            <p>
              <strong>Milestone XP:</strong> +{config.xp_rules.streak_milestone} per milestone
            </p>
            <p>
              <strong>Grace:</strong> a streak continues if activity happens the next calendar day;
              missing a full day resets it to 1.
            </p>
            <p className="text-xs text-slate-400">
              Rules are enforced server-side from real learning activity.
            </p>
          </div>
        </div>
      </div>

      {/* Badges */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="font-semibold text-slate-800 mb-3">Badges</h2>
        <div className="space-y-3">
          {config.badges.map((b) => (
            <div
              key={b.id}
              className="flex items-center justify-between gap-4 p-3 bg-slate-50 rounded-lg"
            >
              <div className="flex items-start gap-3">
                <span className={`text-2xl ${b.is_active ? '' : 'grayscale opacity-50'}`}>
                  {b.icon || '🏅'}
                </span>
                <div>
                  <div className="font-medium text-slate-800 text-sm">{b.name}</div>
                  <div className="text-xs text-slate-500">{b.description}</div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {CRITERIA_LABELS[b.criteria_type] || b.criteria_type} · +{b.xp_reward} XP
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    b.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}
                >
                  {b.is_active ? 'Active' : 'Disabled'}
                </span>
                <button
                  onClick={() => toggleBadge(b.id, b.is_active)}
                  disabled={busyBadge === b.id}
                  className={`text-xs font-medium px-3 py-1.5 rounded-lg border disabled:opacity-50 ${
                    b.is_active
                      ? 'border-red-200 text-red-600 hover:bg-red-50'
                      : 'border-green-200 text-green-600 hover:bg-green-50'
                  }`}
                >
                  {busyBadge === b.id ? '…' : b.is_active ? 'Disable' : 'Enable'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

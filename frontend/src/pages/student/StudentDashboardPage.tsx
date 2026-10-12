import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { coachingApi } from '../../services/api'
import type {
  CoachingDashboard,
  PlanItem,
} from '../../types'

const NAV_CARDS = [
  { to: '/student/aptitude/topics', icon: '📝', label: 'Aptitude', desc: 'Practice topic quizzes' },
  { to: '/student/coding/problems', icon: '💻', label: 'Coding', desc: 'Solve problems, earn XP' },
  { to: '/student/ai-quiz', icon: '🤖', label: 'AI Quiz', desc: 'Gemini-generated questions' },
  { to: '/student/interview', icon: '🎤', label: 'Interview', desc: 'Practice interview questions' },
  { to: '/student/roadmap', icon: '🗺️', label: 'Roadmap', desc: 'Your personalized plan' },
  { to: '/student/gamification', icon: '🏆', label: 'Achievements', desc: 'XP, badges & streaks' },
  { to: '/student/skill-gap', icon: '🔍', label: 'Skill Gap', desc: 'What to improve next' },
  { to: '/student/bookmarks', icon: '🔖', label: 'Saved', desc: 'Bookmarked questions' },
  { to: '/student/progress', icon: '📈', label: 'Progress', desc: 'Trends over time' },
  { to: '/student/assessments', icon: '📋', label: 'Assessments', desc: 'Mock placement tests' },
]

function PlanRow({ item }: { item: PlanItem }) {
  const pct = Math.min(100, item.target > 0 ? (item.progress / item.target) * 100 : 0)
  return (
    <div className="flex items-center gap-3">
      <span className={`text-lg ${item.done ? 'text-green-600' : 'text-slate-300'}`}>
        {item.done ? '✓' : '□'}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex justify-between text-sm">
          <span className={`font-medium truncate ${item.done ? 'text-green-700 line-through' : 'text-slate-700'}`}>
            {item.title}
          </span>
          <span className="text-xs text-slate-400 ml-2 shrink-0">{item.section}</span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-1.5 mt-1">
          <div
            className={`h-1.5 rounded-full ${item.done ? 'bg-green-500' : 'bg-indigo-500'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  )
}

function ReadinessCard({ data }: { data: CoachingDashboard }) {
  const r = data.readiness
  const componentRows = (['aptitude', 'coding', 'consistency', 'coverage', 'assessment'] as const).map((k) => ({
    key: k,
    label: r.labels[k] ?? k,
    value: r.components[k] ?? 0,
    weight: r.weights[k] ?? 0,
  }))
  const color = r.score >= 75 ? 'text-green-600' : r.score >= 45 ? 'text-yellow-600' : 'text-red-600'

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      <div className="flex items-baseline justify-between mb-1">
        <h2 className="font-semibold text-slate-800">Placement readiness</h2>
        <div className={`text-3xl font-bold ${color}`}>{Math.round(r.score)}<span className="text-sm text-slate-400">/100</span></div>
      </div>
      {r.data_completeness < 0.5 && (
        <p className="text-xs text-amber-600 bg-amber-50 rounded-lg p-2 mb-2">
          Low confidence: limited activity data. Practice more to strengthen this score.
        </p>
      )}
      <div className="space-y-2">
        {componentRows.map((c) => (
          <div key={c.key}>
            <div className="flex justify-between text-xs mb-0.5">
              <span className="text-slate-600">{c.label} <span className="text-slate-400">({Math.round(c.weight * 100)}%)</span></span>
              <span className="font-medium text-slate-700">{Math.round(c.value)}%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5">
              <div
                className={`h-1.5 rounded-full ${
                  c.value >= 75 ? 'bg-green-500' : c.value >= 45 ? 'bg-yellow-500' : 'bg-red-400'
                }`}
                style={{ width: `${Math.min(100, c.value)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      <Link to="/student/analytics" className="text-xs text-indigo-600 hover:underline mt-3 inline-block">
        See detailed analytics →
      </Link>
    </div>
  )
}

export default function StudentDashboardPage() {
  const [data, setData] = useState<CoachingDashboard | null>(null)
  const [error, setError] = useState('')

  // Single fetch (audit fix P5): /coaching/dashboard already embeds
  // todays_plan, so a separate /coaching/daily-plan call was redundant work.
  useEffect(() => {
    coachingApi.dashboard()
      .then((res) => setData(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load dashboard'))
  }, [])

  if (error)
    return (
      <div className="space-y-4">
        <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
        >
          Retry
        </button>
      </div>
    )
  if (!data)
    return <div className="text-center py-12 text-slate-500">Loading your day…</div>

  const plan = data.todays_plan
  const recommendedTopic = data.recommended_next.topic_id
    ? `/student/practice?topic_id=${data.recommended_next.topic_id}&difficulty=${data.recommended_next.suggested_difficulty}`
    : '/student/aptitude/topics'

  return (
    <div className="space-y-6">
      {/* Header + quick stats */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Day {plan.day_number} · Welcome back</h1>
          <p className="text-sm text-slate-500">
            {plan.focus_topic
              ? `Today's focus: ${plan.focus_topic}`
              : 'Start practicing to unlock your personalized plan'}
          </p>
        </div>
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: 'Level', value: data.level, color: 'text-purple-600' },
            { label: 'XP today', value: data.xp_today, color: 'text-indigo-600' },
            { label: 'Streak', value: `${data.streak}🔥`, color: 'text-orange-600' },
            { label: 'Readiness', value: Math.round(data.readiness.score), color: 'text-green-600' },
          ].map((s) => (
            <div key={s.label} className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-center">
              <div className={`text-lg font-bold ${s.color}`}>{s.value}</div>
              <div className="text-xs text-slate-500">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* TODAY'S GOAL (Feature Group 1) */}
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex justify-between items-baseline mb-3">
            <h2 className="font-semibold text-slate-800">Today's goal</h2>
            <span className="text-sm font-bold text-indigo-600">{plan.progress_percent}%</span>
          </div>
          <div className="space-y-3">
            {plan.items.map((item, i) => <PlanRow key={i} item={item} />)}
          </div>
        </div>

        {/* RECOMMENDED NEXT ACTION (adaptive, Feature Group 4) */}
        <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-5">
          <h2 className="font-semibold text-indigo-800 mb-2">Do this next</h2>
          {data.weakest_aptitude_topic ? (
            <>
              <div className="text-sm font-medium text-slate-700">
                {data.weakest_aptitude_topic.topic_name}
                <span className="ml-2 text-xs font-normal text-red-500">
                  {data.weakest_aptitude_topic.accuracy}% accuracy
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">{data.recommended_next.reason}</p>
              <Link
                to={recommendedTopic}
                className="inline-block mt-3 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
              >
                Start {data.recommended_next.suggested_difficulty} practice →
              </Link>
            </>
          ) : (
            <>
              <p className="text-sm text-slate-500">Take your first quiz so SkillSprint can learn what to recommend.</p>
              <Link
                to="/student/aptitude/topics"
                className="inline-block mt-3 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
              >
                Browse topics →
              </Link>
            </>
          )}
          {data.weakest_coding_topic && (
            <p className="text-xs text-slate-500 mt-3 pt-3 border-t border-indigo-100">
              Coding weakness: <span className="font-medium text-slate-700">{data.weakest_coding_topic.topic_name}</span> —{' '}
              <Link to="/student/coding/problems" className="text-indigo-600 hover:underline">solve a problem</Link>
            </p>
          )}
        </div>

        {/* READINESS EXPLANATION (Feature Group 9) */}
        <ReadinessCard data={data} />
      </div>

      {/* CONTINUE LEARNING (Feature Group 1) */}
      {data.continue_learning.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Continue where you left off</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {data.continue_learning.map((c) => (
              <Link
                key={`${c.kind}-${c.id}`}
                to={c.href}
                className="bg-indigo-50 rounded-lg p-3 border border-indigo-100 hover:border-indigo-300 transition-colors"
              >
                <div className="text-xs text-indigo-500 font-medium mb-1 uppercase">{c.kind.replace(/_/g, ' ')}</div>
                <div className="text-sm font-medium text-slate-700 truncate">{c.label}</div>
                <div className="text-xs text-slate-500 mt-1">{c.detail} →</div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* WEAKNESS + BADGES + ROADMAP row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Weakest topics</h2>
          {data.weakest_aptitude_topic || data.weakest_coding_topic ? (
            <div className="space-y-2 text-sm">
              {[data.weakest_aptitude_topic, data.weakest_coding_topic]
                .filter((t): t is NonNullable<typeof t> => t !== null)
                .map((t) => (
                  <div key={t.topic_id} className="flex justify-between">
                    <span className="text-slate-700 truncate">{t.topic_name}</span>
                    <span className={`font-medium ${t.accuracy !== null && t.accuracy < 60 ? 'text-red-600' : 'text-yellow-600'}`}>
                      {t.accuracy ?? '—'}%
                    </span>
                  </div>
                ))}
              <Link to="/student/skill-gap" className="text-xs text-indigo-600 hover:underline">
                Full skill gap analysis →
              </Link>
            </div>
          ) : (
            <p className="text-sm text-slate-500">No weak topics yet — practice to reveal your profile.</p>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Recent achievements</h2>
          {data.recent_badges.length > 0 ? (
            <div className="space-y-2">
              {data.recent_badges.map((b) => (
                <div key={b.name} className="flex items-center gap-2 text-sm">
                  <span className="text-xl">{b.icon || '🏅'}</span>
                  <span className="text-slate-700">{b.name}</span>
                </div>
              ))}
              <Link to="/student/gamification" className="text-xs text-indigo-600 hover:underline">
                All achievements →
              </Link>
            </div>
          ) : (
            <p className="text-sm text-slate-500">No badges yet — they unlock automatically as you practice!</p>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Roadmap progress</h2>
          {data.roadmap_progress !== null ? (
            <>
              <div className="text-2xl font-bold text-indigo-600">{Math.round(data.roadmap_progress)}%</div>
              <div className="w-full bg-slate-100 rounded-full h-2 mt-2">
                <div
                  className="bg-indigo-500 h-2 rounded-full"
                  style={{ width: `${Math.min(100, data.roadmap_progress)}%` }}
                />
              </div>
              <Link to="/student/roadmap" className="text-xs text-indigo-600 hover:underline mt-2 inline-block">
                Open roadmap →
              </Link>
            </>
          ) : (
            <p className="text-sm text-slate-500">
              No roadmap yet. <Link to="/student/roadmap" className="text-indigo-600 hover:underline">Generate one →</Link>
            </p>
          )}
        </div>
      </div>

      {/* Success rates */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Current accuracy', value: data.current_accuracy !== null ? `${data.current_accuracy}%` : '—', color: 'bg-blue-50 text-blue-700' },
          { label: 'Coding success', value: data.coding_success_rate !== null ? `${data.coding_success_rate}%` : '—', color: 'bg-green-50 text-green-700' },
          { label: 'Problems solved', value: `${data.coding_solved}/${data.coding_attempted}`, color: 'bg-purple-50 text-purple-700' },
          { label: 'Total XP', value: data.xp_total, color: 'bg-orange-50 text-orange-700' },
        ].map((s) => (
          <div key={s.label} className={`rounded-xl p-4 ${s.color}`}>
            <div className="text-2xl font-bold">{s.value}</div>
            <div className="text-xs mt-1 opacity-75">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Navigation cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {NAV_CARDS.map((c) => (
          <Link
            key={c.to}
            to={c.to}
            className="bg-white border border-slate-200 rounded-xl p-4 hover:border-indigo-300 hover:shadow-sm transition-all"
          >
            <div className="text-2xl mb-2">{c.icon}</div>
            <div className="font-medium text-slate-800 text-sm">{c.label}</div>
            <div className="text-xs text-slate-500 mt-0.5">{c.desc}</div>
          </Link>
        ))}
      </div>

      {/* Daily plan detail (Feature Group 2) — rendered from the dashboard
          payload's embedded todays_plan; no second request needed. */}
      {plan && plan.items.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Full daily plan — Day {plan.day_number}</h2>
          <div className="space-y-3">
            {plan.items.map((item, i) => <PlanRow key={i} item={item} />)}
          </div>
        </div>
      )}
    </div>
  )
}

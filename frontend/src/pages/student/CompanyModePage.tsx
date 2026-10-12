import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { coachingApi, contentApi } from '../../services/api'
import type { Company, CompanyProfile } from '../../types'

export default function CompanyModePage() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [profile, setProfile] = useState<CompanyProfile | null>(null)
  const [loadingCompanies, setLoadingCompanies] = useState(true)
  const [loadingProfile, setLoadingProfile] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    contentApi.companies()
      .then((res) => setCompanies(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load companies'))
      .finally(() => setLoadingCompanies(false))
  }, [])

  const selectCompany = async (id: number) => {
    setSelected(id)
    setLoadingProfile(true)
    setError('')
    try {
      const res = await coachingApi.companyProfile(id)
      setProfile(res.data.data)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg || 'Failed to load company profile')
      setProfile(null)
    } finally {
      setLoadingProfile(false)
    }
  }

  if (loadingCompanies) return <div className="text-center py-12 text-slate-500">Loading companies…</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Company Preparation</h1>
        <p className="text-sm text-slate-500">
          Select a target company to see a preparation profile built from SkillSprint's own content.
        </p>
      </div>

      {error && <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Company picker */}
        <div className="space-y-2">
          {companies.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-xl p-6 text-center text-slate-500 text-sm">
              No companies available yet.
            </div>
          ) : (
            companies.map((c) => (
              <button
                key={c.id}
                onClick={() => selectCompany(c.id)}
                className={`w-full text-left bg-white border rounded-xl p-4 transition-all ${
                  selected === c.id ? 'border-indigo-500 ring-1 ring-indigo-300' : 'border-slate-200 hover:border-indigo-300'
                }`}
              >
                <div className="font-medium text-slate-800">{c.name}</div>
                {c.description && <div className="text-xs text-slate-500 mt-1 line-clamp-2">{c.description}</div>}
              </button>
            ))
          )}
        </div>

        {/* Profile panel */}
        <div className="lg:col-span-2">
          {loadingProfile && <div className="text-center py-12 text-slate-500">Building your preparation profile…</div>}

          {!loadingProfile && selected && profile && (
            <div className="space-y-4">
              {/* Honesty label (Feature Group 7 requirement) */}
              <div className={`rounded-xl p-3 text-sm ${
                profile.is_general_profile
                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                  : 'bg-green-50 text-green-700 border border-green-200'
              }`}>
                {profile.profile_note}
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-5">
                <div className="flex justify-between items-baseline mb-2">
                  <h2 className="font-semibold text-slate-800">{profile.company_name} — coverage</h2>
                  <span className="text-xl font-bold text-indigo-600">{profile.progress_percent}%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2.5">
                  <div className="bg-indigo-500 h-2.5 rounded-full" style={{ width: `${Math.min(100, profile.progress_percent)}%` }} />
                </div>
                <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
                  <div>
                    <div className="text-xs text-slate-500">Questions attempted (company-tagged)</div>
                    <div className="text-xl font-bold text-slate-800">{profile.questions_attempted}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Coding problems in these areas</div>
                    <div className="text-xl font-bold text-slate-800">{profile.coding_problems_available}</div>
                  </div>
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-5">
                <h2 className="font-semibold text-slate-800 mb-3">Relevant topics</h2>
                {profile.topics.length === 0 ? (
                  <p className="text-sm text-slate-500">
                    No company-tagged questions yet — your preparation here follows the general syllabus.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {profile.topics.map((t) => (
                      <div key={t.topic_id}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-slate-700">
                            {t.topic_name}
                            <span className="text-xs text-slate-400 ml-2">{t.available_questions} questions</span>
                          </span>
                          <span className={`text-xs font-medium ${t.your_accuracy === null ? 'text-slate-400' : t.your_accuracy >= 70 ? 'text-green-600' : 'text-red-600'}`}>
                            {t.your_accuracy === null ? 'not practiced' : `${t.your_accuracy}%`}
                          </span>
                        </div>
                        <div className="w-full bg-slate-100 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full ${(t.your_accuracy ?? 0) >= 70 ? 'bg-green-500' : 'bg-indigo-400'}`}
                            style={{ width: `${Math.min(100, t.your_accuracy ?? 0)}%` }}
                          />
                        </div>
                        <Link
                          to={`/student/practice?topic_id=${t.topic_id}&company_id=${profile.company_id}`}
                          className="text-xs text-indigo-600 hover:underline mt-1 inline-block"
                        >
                          Practice →
                        </Link>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => navigate(`/student/practice?company_id=${profile.company_id}`)}
                  className="flex-1 bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700"
                >
                  Start company practice
                </button>
                <Link
                  to="/student/assessments"
                  className="flex-1 text-center border border-indigo-300 text-indigo-700 py-2.5 rounded-lg font-medium hover:bg-indigo-50"
                >
                  Company assessments
                </Link>
              </div>
            </div>
          )}

          {!loadingProfile && !selected && (
            <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
              Select a company to see its preparation profile.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

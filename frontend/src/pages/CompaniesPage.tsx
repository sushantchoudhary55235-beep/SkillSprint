import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { contentApi } from '../services/api'
import type { Company } from '../types'

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    contentApi.companies()
      .then((res) => setCompanies(res.data.data))
      .catch((err) => setError(err.response?.data?.message || 'Failed to load companies'))
  }, [])

  const startPractice = (companyId: number) => {
    navigate(`/student/practice?company_id=${companyId}`)
  }

  if (error) return <div className="bg-red-50 text-red-600 p-4 rounded-lg">{error}</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Companies</h1>
        <p className="text-sm text-slate-500">Practice questions from specific companies</p>
      </div>

      {companies.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
          No companies available yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {companies.map((company) => (
            <button
              key={company.id}
              onClick={() => startPractice(company.id)}
              className="bg-white border border-slate-200 rounded-xl p-5 text-left hover:border-indigo-300 hover:shadow-md transition-all group"
            >
              <h3 className="font-semibold text-slate-800 group-hover:text-indigo-600">{company.name}</h3>
              {company.description && (
                <p className="text-sm text-slate-500 mt-2 line-clamp-2">{company.description}</p>
              )}
              {company.website && (
                <p className="text-xs text-slate-400 mt-2">{company.website}</p>
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

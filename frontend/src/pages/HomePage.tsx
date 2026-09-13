import { useEffect, useState } from 'react'

interface HealthStatus {
  status: string
  app: string
  environment: string
}

function HomePage() {
  const [apiStatus, setApiStatus] = useState<'checking' | HealthStatus | 'unreachable'>('checking')

  // Phase 1 verification: confirm the backend is reachable through the dev proxy.
  useEffect(() => {
    fetch('/api/health')
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('not ok'))))
      .then((data: HealthStatus) => setApiStatus(data))
      .catch(() => setApiStatus('unreachable'))
  }, [])

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Welcome to SkillSprint</h1>
        <p className="mt-2 text-slate-600">
          Gamified AI-powered placement-readiness and personalized learning platform.
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="font-semibold text-slate-800">Backend status</h2>
        {apiStatus === 'checking' && <p className="mt-2 text-sm text-slate-500">Checking…</p>}
        {apiStatus === 'unreachable' && (
          <p className="mt-2 text-sm text-red-600">
            API unreachable — is the backend running on port 8000?
          </p>
        )}
        {apiStatus !== 'checking' && apiStatus !== 'unreachable' && (
          <p className="mt-2 text-sm text-emerald-600">
            Connected to <strong>{apiStatus.app}</strong> ({apiStatus.environment}) — status: {apiStatus.status}
          </p>
        )}
      </div>

      <p className="text-sm text-slate-500">Phase 1 foundation — feature modules arrive in later phases.</p>
    </section>
  )
}

export default HomePage

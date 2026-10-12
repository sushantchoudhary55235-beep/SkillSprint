import { useEffect } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const ADMIN_LINKS = [
  { to: '/admin/dashboard', label: 'Dashboard', icon: '📊' },
  { to: '/admin/users', label: 'Users', icon: '👥' },
  { to: '/admin/topics', label: 'Topics', icon: '📚' },
  { to: '/admin/companies', label: 'Companies', icon: '🏢' },
  { to: '/admin/analytics/students', label: 'Analytics', icon: '📈' },
  { to: '/admin/gamification-config', label: 'Gamification', icon: '🏆' },
]

export default function AdminLayout() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!loading && (!user || user.role !== 'admin')) {
      navigate('/login', { replace: true })
    }
  }, [user, loading, navigate])

  if (loading) return <div className="text-center py-12 text-slate-500">Loading…</div>
  if (!user || user.role !== 'admin') return null

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 bg-slate-900 text-slate-100 min-h-screen p-4 hidden md:block">
        <Link to="/admin/dashboard" className="block text-lg font-bold text-white mb-6">
          SkillSprint <span className="text-indigo-400">Admin</span>
        </Link>
        <nav className="space-y-1">
          {ADMIN_LINKS.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`
              }
            >
              <span>{l.icon}</span> {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-8 pt-4 border-t border-slate-700">
          <Link to="/admin/dashboard" className="text-xs text-slate-400 hover:text-white">
            ← Student view
          </Link>
        </div>
      </aside>

      {/* Mobile nav */}
      <div className="md:hidden fixed bottom-0 inset-x-0 bg-slate-900 flex justify-around py-2 z-10">
        {ADMIN_LINKS.map((l) => (
          <NavLink key={l.to} to={l.to} className="text-slate-300 text-xs px-2 py-1">
            {l.icon}
          </NavLink>
        ))}
      </div>

      <main className="flex-1 p-6 pb-20 md:pb-6 overflow-x-auto">
        <Outlet />
      </main>
    </div>
  )
}

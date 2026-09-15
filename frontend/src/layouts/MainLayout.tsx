import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navLinks = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/topics', label: 'Topics' },
  { to: '/companies', label: 'Companies' },
  { to: '/practice/history', label: 'History' },
  { to: '/progress', label: 'Progress' },
  { to: '/assessments', label: 'Assessments' },
  { to: '/attempts', label: 'My Attempts' },
]

function MainLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/dashboard" className="text-lg font-bold text-indigo-600">SkillSprint</Link>

          <nav className="flex items-center gap-1 text-sm overflow-x-auto">
            {user && navLinks.map((l) => (
              <Link
                key={l.to}
                to={l.to}
                className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
                  location.pathname === l.to || location.pathname.startsWith(l.to + '/')
                    ? 'bg-indigo-100 text-indigo-700 font-medium'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                {l.label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            {user ? (
              <>
                <span className="text-xs text-slate-500 hidden sm:inline">
                  {user.name} ({user.role})
                </span>
                <button
                  onClick={handleLogout}
                  className="text-xs text-red-600 hover:text-red-700 font-medium"
                >
                  Logout
                </button>
              </>
            ) : (
              <Link to="/login" className="text-xs text-indigo-600 hover:underline font-medium">
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}

export default MainLayout

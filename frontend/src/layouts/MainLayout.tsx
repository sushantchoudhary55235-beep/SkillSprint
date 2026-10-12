import { Outlet, Link, useNavigate, NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const STUDENT_LINKS = [
  { to: '/student/dashboard', label: 'Dashboard' },
  { to: '/student/aptitude/topics', label: 'Topics' },
  { to: '/student/coding/problems', label: 'Coding' },
  { to: '/student/ai-quiz', label: 'AI Quiz' },
  { to: '/student/chatbot', label: 'Chatbot' },
  { to: '/student/interview', label: 'Interview' },
  { to: '/student/skill-gap', label: 'Skill Gap' },
  { to: '/student/revision', label: 'Revision' },
  { to: '/student/bookmarks', label: 'Saved' },
  { to: '/student/roadmap', label: 'Roadmap' },
  { to: '/student/recommendations', label: 'Recommendations' },
  { to: '/student/gamification', label: 'Achievements' },
  { to: '/student/companies', label: 'Companies' },
  { to: '/student/assessments', label: 'Assessments' },
  { to: '/student/attempts', label: 'My Attempts' },
  { to: '/student/analytics', label: 'Analytics' },
]

const TEACHER_LINKS = [
  { to: '/teacher/dashboard', label: 'Dashboard' },
  { to: '/teacher/students', label: 'Students' },
]

export default function MainLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const isTeacher = user?.role === 'teacher'

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to={isTeacher ? '/teacher/dashboard' : '/student/dashboard'} className="text-lg font-bold text-indigo-600">SkillSprint</Link>

          <nav className="flex items-center gap-1 text-sm overflow-x-auto">
            {user && (isTeacher ? TEACHER_LINKS : STUDENT_LINKS).map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
                    isActive
                      ? 'bg-indigo-100 text-indigo-700 font-medium'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            {user && (
              <span className="text-xs text-slate-500 hidden sm:inline">
                {user.name} ({user.role})
              </span>
            )}
            {user ? (
              <>
                {user.role === 'student' && (
                  <Link
                    to="/student/settings"
                    className="text-xs text-slate-500 hover:text-slate-700 font-medium"
                    title="Account settings"
                  >
                    Settings
                  </Link>
                )}
                {user.role === 'teacher' && (
                  <Link
                    to="/teacher/dashboard"
                    className="text-xs text-slate-500 hover:text-slate-700 font-medium"
                    title="Back to teacher dashboard"
                  >
                    Teacher
                  </Link>
                )}
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

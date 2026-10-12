import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import MainLayout from './layouts/MainLayout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'

// Student pages
import StudentDashboardPage from './pages/student/StudentDashboardPage'
import TopicsPage from './pages/TopicsPage'
import CompaniesPage from './pages/CompaniesPage'
import PracticePage from './pages/PracticePage'
import HistoryPage from './pages/HistoryPage'
import ProgressPage from './pages/ProgressPage'
import DailyQuizPage from './pages/DailyQuizPage'
import AssessmentsPage from './pages/AssessmentsPage'
import AssessmentStartPage from './pages/AssessmentStartPage'
import AttemptPage from './pages/AttemptPage'
import ResultPage from './pages/ResultPage'
import AttemptHistoryPage from './pages/AttemptHistoryPage'
import CodingProblemsPage from './pages/student/CodingProblemsPage'
import CodingProblemPage from './pages/student/CodingProblemPage'
import CodingResultPage from './pages/student/CodingResultPage'
import CompanyModePage from './pages/student/CompanyModePage'
import RoadmapPage from './pages/student/RoadmapPage'
import RecommendationsPage from './pages/student/RecommendationsPage'
import GamificationPage from './pages/student/GamificationPage'
import AnalyticsPage from './pages/student/AnalyticsPage'
import AIQuizPage from './pages/student/AIQuizPage'
import ChatbotPage from './pages/student/ChatbotPage'
import SkillGapPage from './pages/student/SkillGapPage'
import RevisionPage from './pages/student/RevisionPage'
import BookmarksPage from './pages/student/BookmarksPage'
import AccountSettingsPage from './pages/student/AccountSettingsPage'
import InterviewPage from './pages/student/InterviewPage'

// Admin pages
import AdminLayout from './pages/admin/AdminLayout'
import AdminDashboardPage from './pages/admin/AdminDashboardPage'
import AdminUsersPage from './pages/admin/AdminUsersPage'
import AdminTopicsPage from './pages/admin/AdminTopicsPage'
import AdminCompaniesPage from './pages/admin/AdminCompaniesPage'
import AdminAnalyticsPage from './pages/admin/AdminAnalyticsPage'
import AdminGamificationConfigPage from './pages/admin/AdminGamificationConfigPage'

// Teacher pages
import TeacherDashboardPage from './pages/teacher/TeacherDashboardPage'
import TeacherStudentsPage from './pages/teacher/TeacherStudentsPage'

function TeacherGate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="text-center py-12 text-slate-500">Loading…</div>
  if (!user || user.role !== 'teacher') return <Navigate to="/login" replace />
  return <>{children}</>
}

function ProtectedRoute({
  children,
  role,
}: {
  children: React.ReactNode
  role?: 'student' | 'teacher' | 'admin'
}) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <div className="text-center py-12 text-slate-500">Loading…</div>
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (role && user.role !== role) {
    // Role mismatch: send them to their own home, never show another role's UI.
    const home =
      user.role === 'admin'
        ? '/admin/dashboard'
        : user.role === 'teacher'
          ? '/teacher/dashboard'
          : '/student/dashboard'
    return <Navigate to={home} replace />
  }
  return <>{children}</>
}

function StudentLayout() {
  return (
    <ProtectedRoute role="student">
      <MainLayout />
    </ProtectedRoute>
  )
}

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* ============================== STUDENT ============================== */}
        <Route element={<StudentLayout />}>
          <Route path="/student/dashboard" element={<StudentDashboardPage />} />
          <Route path="/student/aptitude/topics" element={<TopicsPage />} />
          <Route path="/student/aptitude/quiz/:topicId" element={<AttemptPage />} />
          <Route path="/student/aptitude/result/:attemptId" element={<ResultPage />} />
          <Route path="/student/practice" element={<PracticePage />} />
          <Route path="/student/practice/history" element={<HistoryPage />} />
          <Route path="/student/companies" element={<CompaniesPage />} />
          <Route path="/student/assessments" element={<AssessmentsPage />} />
          <Route path="/student/assessments/:id/start" element={<AssessmentStartPage />} />
          <Route path="/student/attempts/:id" element={<AttemptPage />} />
          <Route path="/student/attempts/:id/result" element={<ResultPage />} />
          <Route path="/student/attempts" element={<AttemptHistoryPage />} />
          <Route path="/student/quiz/daily" element={<DailyQuizPage />} />
          <Route path="/student/progress" element={<ProgressPage />} />

          {/* Coding */}
          <Route path="/student/coding/problems" element={<CodingProblemsPage />} />
          <Route path="/student/coding/problems/:id" element={<CodingProblemPage />} />
          <Route path="/student/coding/problems/:id/result" element={<CodingResultPage />} />

          {/* Company preparation (Feature Group 7) */}
          <Route path="/student/companies/:id" element={<CompanyModePage />} />

          {/* Personalization + gamification */}
          <Route path="/student/roadmap" element={<RoadmapPage />} />
          <Route path="/student/recommendations" element={<RecommendationsPage />} />
          <Route path="/student/gamification" element={<GamificationPage />} />
          <Route path="/student/analytics" element={<AnalyticsPage />} />
          <Route path="/student/ai-quiz" element={<AIQuizPage />} />
          <Route path="/student/chatbot" element={<ChatbotPage />} />

          {/* Coaching feature groups */}
          <Route path="/student/skill-gap" element={<SkillGapPage />} />
          <Route path="/student/revision" element={<RevisionPage />} />
          <Route path="/student/bookmarks" element={<BookmarksPage />} />
          <Route path="/student/interview" element={<InterviewPage />} />
          <Route path="/student/settings" element={<AccountSettingsPage />} />
        </Route>

        {/* ============================== ADMIN ============================== */}
        <Route
          element={
            <ProtectedRoute role="admin">
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
          <Route path="/admin/users" element={<AdminUsersPage />} />
          <Route path="/admin/topics" element={<AdminTopicsPage />} />
          <Route path="/admin/companies" element={<AdminCompaniesPage />} />
          <Route path="/admin/analytics" element={<Navigate to="/admin/analytics/students" replace />} />
          <Route path="/admin/analytics/students" element={<AdminAnalyticsPage />} />
          <Route path="/admin/analytics/questions" element={<AdminAnalyticsPage />} />
          <Route path="/admin/analytics/submissions" element={<AdminAnalyticsPage />} />
          <Route path="/admin/analytics/popular-topics" element={<AdminAnalyticsPage />} />
          <Route path="/admin/gamification-config" element={<AdminGamificationConfigPage />} />
        </Route>

        {/* ============================== TEACHER ============================== */}
        <Route
          element={<TeacherGate><MainLayout /></TeacherGate>}
        >
          <Route path="/teacher/dashboard" element={<TeacherDashboardPage />} />
          <Route path="/teacher/students" element={<TeacherStudentsPage />} />
        </Route>

        {/* Legacy + fallback redirects */}
        <Route path="/dashboard" element={<Navigate to="/student/dashboard" replace />} />
        <Route path="/" element={<Navigate to="/student/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/student/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  )
}

export default App

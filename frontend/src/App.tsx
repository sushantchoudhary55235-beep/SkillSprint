import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import MainLayout from './layouts/MainLayout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
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

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="text-center py-12 text-slate-500">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/topics" element={<TopicsPage />} />
          <Route path="/companies" element={<CompaniesPage />} />
          <Route path="/practice" element={<PracticePage />} />
          <Route path="/practice/history" element={<HistoryPage />} />
          <Route path="/progress" element={<ProgressPage />} />
          <Route path="/quiz/daily" element={<DailyQuizPage />} />
          <Route path="/assessments" element={<AssessmentsPage />} />
          <Route path="/assessments/:id/start" element={<AssessmentStartPage />} />
          <Route path="/attempts/:id" element={<AttemptPage />} />
          <Route path="/attempts/:id/result" element={<ResultPage />} />
          <Route path="/attempts" element={<AttemptHistoryPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  )
}

export default App

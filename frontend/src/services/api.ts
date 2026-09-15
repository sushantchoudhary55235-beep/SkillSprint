import axios from 'axios'
import type {
  ApiResponse,
  AuthData,
  AttemptAnswerRequest,
  AttemptAnswerResponse,
  AttemptHistoryItem,
  AttemptResultResponse,
  AttemptStartResponse,
  AttemptSubmitResponse,
  AssessmentRead,
  Company,
  DashboardData,
  LoginResponse,
  OverallProgressData,
  PracticeAnswerData,
  PracticeAnswerRequest,
  PracticeCompleteData,
  PracticeHistoryData,
  PracticeStartData,
  StudentProfile,
  Topic,
} from '../types'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT from localStorage on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && localStorage.getItem('token')) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

// ============ Auth
export const authApi = {
  login: (email: string, password: string) =>
    api.post<ApiResponse<LoginResponse>>('/auth/login', { email, password }),

  registerStudent: (name: string, email: string, password: string) =>
    api.post<ApiResponse>('/auth/register/student', { name, email, password }),

  registerTeacher: (name: string, email: string, password: string, department?: string) =>
    api.post<ApiResponse>('/auth/register/teacher', { name, email, password, department }),

  me: () => api.get<ApiResponse<AuthData['data']['user']>>('/auth/me'),
}

// ============ Student
export const studentApi = {
  profile: () => api.get<ApiResponse<StudentProfile>>('/students/profile'),

  dashboard: () => api.get<ApiResponse<DashboardData>>('/students/dashboard'),

  progress: () => api.get<ApiResponse<OverallProgressData>>('/students/progress'),
}

// ============ Practice
export const practiceApi = {
  start: (req: { topic_id?: number; company_id?: number; difficulty?: string; question_count?: number }) =>
    api.post<ApiResponse<PracticeStartData>>('/students/practice/start', req),

  answer: (sessionId: number, data: PracticeAnswerRequest) =>
    api.post<ApiResponse<PracticeAnswerData>>(`/students/practice/${sessionId}/answer`, data),

  complete: (sessionId: number) =>
    api.post<ApiResponse<PracticeCompleteData>>(`/students/practice/${sessionId}/complete`),

  history: (page = 1, limit = 20) =>
    api.get<ApiResponse<PracticeHistoryData>>(`/students/practice/history?page=${page}&limit=${limit}`),

  dailyQuiz: () =>
    api.post<ApiResponse<PracticeStartData>>('/students/quiz/daily/start'),
}

// ============ Content
export const contentApi = {
  topics: (category?: string) =>
    api.get<ApiResponse<Topic[]>>('/topics', { params: category ? { category } : {} }),

  topic: (id: number) =>
    api.get<ApiResponse<Topic>>(`/topics/${id}`),

  companies: () =>
    api.get<ApiResponse<Company[]>>('/companies'),

  company: (id: number) =>
    api.get<ApiResponse<Company>>(`/companies/${id}`),

  questions: (params: { topic_id?: number; company_id?: number; difficulty?: string; page?: number; limit?: number }) =>
    api.get<ApiResponse<{ questions: unknown[]; total: number; page: number; limit: number }>>('/questions', { params }),
}

// ============ Assessment
export const assessmentApi = {
  list: (page = 1, limit = 20) =>
    api.get<ApiResponse<{ assessments: AssessmentRead[]; total: number; page: number; limit: number }>>('/assessments', { params: { page, limit } }),

  detail: (id: number) =>
    api.get<ApiResponse<{ id: number; title: string; assessment_type: string; duration_minutes: number; question_count: number; company_id: number | null; is_active: boolean; created_at: string; question_ids: number[] }>>(`/assessments/${id}`),

  start: (id: number) =>
    api.post<ApiResponse<AttemptStartResponse>>(`/assessments/${id}/start`),

  submitAnswer: (attemptId: number, data: AttemptAnswerRequest) =>
    api.post<ApiResponse<AttemptAnswerResponse>>(`/attempts/${attemptId}/answer`, data),

  submitAttempt: (attemptId: number) =>
    api.post<ApiResponse<AttemptSubmitResponse>>(`/attempts/${attemptId}/submit`),

  result: (attemptId: number) =>
    api.get<ApiResponse<AttemptResultResponse>>(`/attempts/${attemptId}/result`),

  myAttempts: (page = 1, limit = 20) =>
    api.get<ApiResponse<AttemptHistoryItem[]>>('/students/me/attempts', { params: { page, limit } }),
}

export default api

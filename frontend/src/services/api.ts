import axios from 'axios'
import type {
  AdaptiveDifficulty,
  AIQuestion,
  AIQuestionEvaluateResult,
  ActivityEventItem,
  AdminUserListData,
  AssessmentRead,
  AttemptAnswerRequest,
  AttemptAnswerResponse,
  AttemptHistoryItem,
  AttemptResultResponse,
  AttemptStartResponse,
  AttemptSubmitResponse,
  BadgeCatalogEntry,
  BookmarkItem,
  ChatMessage,
  ChatResponseData,
  CoachingDashboard,
  CodingPerformance,
  CodingProblemDetail,
  CodingProblemListData,
  CodingSubmissionHistoryData,
  CodingSubmissionResult,
  Company,
  CompanyProfile,
  DashboardData,
  DailyPlan,
  EarnedBadge,
  GamificationConfig,
  GamificationSummary,
  InterviewConfig,
  InterviewFeedback,
  InterviewQuestions,
  LeaderboardRow,
  LoginResponse,
  MissionItem,
  OverallProgressData,
  PlatformAnalytics,
  PracticeAnswerData,
  PracticeAnswerRequest,
  PracticeCompleteData,
  PracticeHistoryData,
  ResetPreview,
  PracticeStartData,
  ProgressTrendsData,
  QuestionAnalytics,
  RecommendationListData,
  RevisionFeed,
  RevisionPracticeResult,
  RoadmapData,
  SkillGapData,
  StudentAnalyticsRow,
  StudentProfile,
  SubmissionAnalytics,
  PopularTopicRow,
  TeacherDashboardData,
  Topic,
  CurrentUser,
  StudentRegisterData,
  TeacherRegisterData,
  ApiResponse,
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

// Auto-logout on 401 from API calls. Auth endpoints (/auth/login,
// /auth/register/*) are excluded: when a stale token is still in storage and
// the user submits wrong credentials, the 401 belongs to the login attempt —
// reloading the page there would wipe the "Incorrect email or password"
// error instead of showing it.
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const url: string = err.config?.url ?? ''
    const isAuthCall = url.startsWith('/auth/login') || url.startsWith('/auth/register')
    if (err.response?.status === 401 && !isAuthCall && localStorage.getItem('token')) {
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
    api.post<ApiResponse<StudentRegisterData>>('/auth/register/student', { name, email, password }),

  registerTeacher: (name: string, email: string, password: string, department?: string) =>
    api.post<ApiResponse<TeacherRegisterData>>('/auth/register/teacher', { name, email, password, department }),

  me: () => api.get<ApiResponse<CurrentUser>>('/auth/me'),
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

// ============ Coding (Phase 15B)
export const codingApi = {
  problems: (page = 1, limit = 50, filters?: { difficulty?: string; topic_id?: number }) =>
    api.get<ApiResponse<CodingProblemListData>>('/coding/problems', {
      params: { page, limit, ...filters },
    }),

  problem: (id: number) =>
    api.get<ApiResponse<CodingProblemDetail>>(`/coding/problems/${id}`),

  submit: (problemId: number, language: string, source_code: string) =>
    api.post<ApiResponse<CodingSubmissionResult>>(`/coding/problems/${problemId}/submit`, {
      language,
      source_code,
    }),

  submissions: (page = 1, limit = 20, problemId?: number) =>
    api.get<ApiResponse<CodingSubmissionHistoryData>>('/coding/submissions/me', {
      params: { page, limit, ...(problemId ? { problem_id: problemId } : {}) },
    }),

  performance: () =>
    api.get<ApiResponse<CodingPerformance>>('/coding/performance/me'),
}

// ============ Roadmap (Phase 15B)
export const roadmapApi = {
  get: () => api.get<ApiResponse<RoadmapData>>('/roadmap/me'),
  generate: () => api.post<ApiResponse<RoadmapData>>('/roadmap/generate'),
  updateItem: (itemId: number, status: 'NOT_STARTED' | 'IN_PROGRESS' | 'COMPLETED') =>
    api.patch<ApiResponse<{ id: number; status: string }>>(`/roadmap/items/${itemId}?status=${status}`),
}

// ============ Recommendations (Phase 15B)
export const recommendationsApi = {
  list: (limit = 10) =>
    api.get<ApiResponse<RecommendationListData>>('/recommendations/me', { params: { limit } }),
  generate: () => api.post<ApiResponse<{ total: number }>>('/recommendations/generate'),
  complete: (id: number) =>
    api.post<ApiResponse<{ id: number; status: string; completed: boolean }>>(`/recommendations/${id}/complete`),
}

// ============ Gamification (Phase 15B)
export const gamificationApi = {
  summary: () => api.get<ApiResponse<GamificationSummary>>('/gamification/me'),
  missions: () => api.get<ApiResponse<MissionItem[]>>('/gamification/missions'),
  badges: () => api.get<ApiResponse<{ earned: EarnedBadge[]; total_available: number }>>('/gamification/badges'),
  badgeCatalog: () => api.get<ApiResponse<BadgeCatalogEntry[]>>('/gamification/badges/catalog'),
  activity: (limit = 10) =>
    api.get<ApiResponse<ActivityEventItem[]>>('/gamification/activity', { params: { limit } }),
  leaderboard: (period = 'WEEKLY', limit = 25) =>
    api.get<ApiResponse<LeaderboardRow[]>>('/gamification/leaderboard', { params: { period, limit } }),
}

// ============ AI Questions (Phase 15C)
export const aiQuestionApi = {
  generate: (req: { company?: string; topic_id?: number; topic_name?: string; difficulty?: string }) =>
    api.post<ApiResponse<AIQuestion>>('/ai/questions/generate', req),

  evaluate: (req: {
    ticket: string
    student_answer: string
    time_taken_seconds?: number | null
  }) => api.post<ApiResponse<AIQuestionEvaluateResult>>('/ai/questions/evaluate', req),
}

// ============ Chatbot
export const chatApi = {
  send: (message: string, history: ChatMessage[]) =>
    api.post<ApiResponse<ChatResponseData>>('/ai/chat', { message, history }),
}

// ============ Admin (Phase 15D)
export const adminApi = {
  ping: () => api.get<ApiResponse<{ admin_id: number }>>('/admin/ping'),

  users: (params: { page?: number; limit?: number; role?: string; search?: string; is_active?: boolean }) =>
    api.get<ApiResponse<AdminUserListData>>('/admin/users', { params }),

  setUserStatus: (userId: number, isActive: boolean) =>
    api.patch<ApiResponse<{ id: number; is_active: boolean }>>(
      `/admin/users/${userId}/status?is_active=${isActive}`,
    ),

  topics: () => api.get<ApiResponse<Topic[]>>('/admin/topics'),
  createTopic: (name: string, category: string, description?: string) =>
    api.post<ApiResponse<Topic>>('/admin/topics', { name, category, description }),
  updateTopic: (id: number, data: { name?: string; category?: string; description?: string; is_active?: boolean }) =>
    api.patch<ApiResponse<Topic>>(`/admin/topics/${id}`, data),

  companies: () => api.get<ApiResponse<Company[]>>('/admin/companies'),
  createCompany: (name: string, description?: string, website?: string) =>
    api.post<ApiResponse<Company>>('/admin/companies', { name, description, website }),
  updateCompany: (id: number, data: { name?: string; description?: string; website?: string; is_active?: boolean }) =>
    api.patch<ApiResponse<Company>>(`/admin/companies/${id}`, data),

  analytics: () => api.get<ApiResponse<PlatformAnalytics>>('/admin/analytics'),
  analyticsStudents: () => api.get<ApiResponse<StudentAnalyticsRow[]>>('/admin/analytics/students'),
  analyticsQuestions: () => api.get<ApiResponse<QuestionAnalytics>>('/admin/analytics/questions'),
  analyticsSubmissions: () => api.get<ApiResponse<SubmissionAnalytics>>('/admin/analytics/submissions'),
  analyticsPopularTopics: (limit = 10) =>
    api.get<ApiResponse<PopularTopicRow[]>>('/admin/analytics/popular-topics', { params: { limit } }),

  gamificationConfig: () => api.get<ApiResponse<GamificationConfig>>('/admin/gamification/config'),
  setBadgeStatus: (badgeId: number, isActive: boolean) =>
    api.patch<ApiResponse<{ id: number; is_active: boolean }>>(
      `/admin/badges/${badgeId}/status?is_active=${isActive}`,
    ),
}

// ============ Coaching (Feature Groups 1, 2, 3, 7, 10, 11)
export const coachingApi = {
  dashboard: () => api.get<ApiResponse<CoachingDashboard>>('/coaching/dashboard'),

  dailyPlan: () => api.get<ApiResponse<DailyPlan>>('/coaching/daily-plan'),

  skillGap: () => api.get<ApiResponse<SkillGapData>>('/coaching/skill-gap'),

  trends: (days: 7 | 30 | 0 = 7) =>
    api.get<ApiResponse<ProgressTrendsData>>('/coaching/trends', { params: { days } }),

  revision: () => api.get<ApiResponse<RevisionFeed>>('/coaching/revision'),

  revisionPractice: (count: 5 | 10 | 15 = 5) =>
    api.post<ApiResponse<RevisionPracticeResult>>('/coaching/revision/practice', null, {
      params: { count },
    }),

  companyProfile: (companyId: number) =>
    api.get<ApiResponse<CompanyProfile>>(`/coaching/companies/${companyId}/profile`),
}

// ============ Adaptive difficulty (Feature Group 4)
export const adaptiveApi = {
  difficulty: () => api.get<ApiResponse<AdaptiveDifficulty>>('/adaptive/difficulty'),
}

// ============ Bookmarks (Feature Group 12)
export const bookmarksApi = {
  list: () => api.get<ApiResponse<BookmarkItem[]>>('/bookmarks'),

  add: (req: { bookmark_type: 'QUESTION' | 'PROBLEM' | 'CONCEPT'; question_id?: number; problem_id?: number; note?: string }) =>
    api.post<ApiResponse<{ id: number }>>('/bookmarks', req),

  remove: (id: number) => api.delete<ApiResponse<{ id: number }>>(`/bookmarks/${id}`),
}

// ============ Interview prep (Feature Group 6)
export const interviewApi = {
  config: () => api.get<ApiResponse<InterviewConfig>>('/interview/config'),

  questions: (category: string, difficulty = 'easy', experienceLevel = 'fresher', count = 5) =>
    api.get<ApiResponse<InterviewQuestions>>('/interview/questions', {
      params: { category, difficulty, experience_level: experienceLevel, count },
    }),

  evaluate: (category: string, questionId: number, answer: string) =>
    api.post<ApiResponse<InterviewFeedback>>('/interview/evaluate', {
      category,
      question_id: questionId,
      answer,
    }),
}

// ============ Progressive hints (Feature Group 5)
export const hintsApi = {
  progressive: (req: { problem_text: string; topic_name?: string; level: number; source_code?: string }) =>
    api.post<ApiResponse<{ level: number; label: string; text: string; max_level: number; remaining: number }>>(
      '/ai/hints/progressive',
      req,
    ),
}

// ============ Account / Danger Zone
export const accountApi = {
  resetPreview: () =>
    api.get<ApiResponse<ResetPreview>>('/account/reset/preview'),

  reset: (data: { password: string; confirmation: string }) =>
    api.post<ApiResponse<{ reset: boolean; rows_deleted: Record<string, number> }>>('/account/reset', data),
}

// ============ Teacher (demo flow)
export const teacherApi = {
  dashboard: () => api.get<ApiResponse<TeacherDashboardData>>('/teachers/dashboard'),
  students: () => api.get<ApiResponse<TeacherDashboardData['students']>>('/teachers/students'),
  addStudent: (studentId: string) =>
    api.post<ApiResponse<{ id: number; status: string }>>('/teachers/students', { student_id: studentId }),
}

export default api

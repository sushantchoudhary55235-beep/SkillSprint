// ============ Auth
export interface User {
  id: number
  name: string
  email: string
  role: 'student' | 'teacher' | 'admin'
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface AuthData {
  success: boolean
  message: string
  data: LoginResponse
}

// ============ Student Profile
export interface StudentProfile {
  student_id: string
  name: string
  email: string
  xp: number
  level: number
  current_streak: number
  readiness_score: number
}

// ============ Dashboard
export interface TopicProgressItem {
  topic_id: number
  topic_name: string
  total_attempts: number
  correct_answers: number
  accuracy: number
  trend: string
}

export interface DashboardData {
  student_id: string
  name: string
  email: string
  xp: number
  level: number
  current_streak: number
  readiness_score: number
  total_questions_attempted: number
  total_correct: number
  overall_accuracy: number
  recent_sessions: PracticeSessionSummary[]
  topic_progress: TopicProgressItem[]
}

// ============ Practice
export interface PracticeStartRequest {
  topic_id?: number
  company_id?: number
  difficulty?: 'easy' | 'medium' | 'hard'
  question_count?: number
}

export interface QuestionOptionOut {
  id: number
  option_text: string
  option_order: number
}

export interface QuestionForPractice {
  id: number
  question_text: string
  question_type: string
  difficulty: string
  options: QuestionOptionOut[]
}

export interface PracticeStartData {
  session_id: number
  mode: string
  topic_id: number | null
  company_id: number | null
  difficulty: string | null
  question_count: number
  questions: QuestionForPractice[]
}

export interface PracticeAnswerRequest {
  question_id: number
  selected_option_id?: number | null
  time_taken_seconds?: number | null
}

export interface PracticeAnswerData {
  question_id: number
  is_correct: boolean
  correct_option_id: number
  explanation: string | null
}

export interface PracticeCompleteData {
  session_id: number
  score: number
  correct: number
  incorrect: number
  unattempted: number
  accuracy: number
  total_time_seconds: number
  xp_earned: number
}

export interface PracticeSessionSummary {
  id: number
  mode: string
  topic_id: number | null
  company_id: number | null
  difficulty: string | null
  question_count: number
  correct_count: number
  incorrect_count: number
  score: number | null
  xp_earned: number
  status: string
  created_at: string
  completed_at: string | null
}

export interface PracticeHistoryData {
  sessions: PracticeSessionSummary[]
  total: number
  page: number
  limit: number
}

export interface OverallProgressData {
  total_questions_attempted: number
  total_correct: number
  total_incorrect: number
  overall_accuracy: number
  total_sessions: number
  topic_progress: TopicProgressItem[]
  xp: number
  level: number
  current_streak: number
}

// ============ Content
export interface Topic {
  id: number
  name: string
  category: string
  description: string | null
  is_active: boolean
  created_at: string
}

export interface Company {
  id: number
  name: string
  description: string | null
  website: string | null
  is_active: boolean
  created_at: string
}

// ============ Assessment
export interface AssessmentRead {
  id: number
  title: string
  assessment_type: string
  duration_minutes: number
  question_count: number
  company_id: number | null
  is_active: boolean
  created_at: string
}

export interface AssessmentReadDetail extends AssessmentRead {
  question_ids: number[]
}

export interface AttemptStartResponse {
  attempt_id: number
  assessment_id: number
  started_at: string
  duration_minutes: number
  question_count: number
  questions: {
    id: number
    question_text: string
    question_type: string
    difficulty: string
    options: { id: number; option_text: string; option_order: number }[]
  }[]
}

export interface AttemptAnswerRequest {
  question_id: number
  selected_option_id?: number | null
  time_taken_seconds?: number | null
}

export interface AttemptAnswerResponse {
  question_id: number
  is_correct: boolean
  correct_option_id: number
}

export interface AttemptSubmitResponse {
  attempt_id: number
  score: number
  total_questions: number
  correct: number
  incorrect: number
  unattempted: number
  accuracy: number
  time_taken_seconds: number
  topic_performance: {
    topic_id: number
    topic_name: string
    correct: number
    total: number
    accuracy: number
  }[]
}

export interface AttemptResultResponse {
  attempt_id: number
  assessment_id: number
  assessment_title: string
  status: string
  score: number
  total_questions: number
  correct_count: number
  incorrect_count: number
  unattempted_count: number
  accuracy: number
  started_at: string
  submitted_at: string | null
  time_taken_seconds: number | null
  topic_performance: {
    topic_id: number
    topic_name: string
    correct: number
    total: number
    accuracy: number
  }[]
}

export interface AttemptHistoryItem {
  id: number
  assessment_id: number
  assessment_title: string
  score: number | null
  correct_count: number
  incorrect_count: number
  unattempted_count: number
  accuracy: number | null
  status: string
  started_at: string
  submitted_at: string | null
}

// ============ Generic API Response
export interface ApiResponse<T = unknown> {
  success: boolean
  message: string
  data: T
}

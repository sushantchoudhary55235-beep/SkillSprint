// ============ Auth

// Shared base so login, registration, and /auth/me stay compatible.
export interface BaseAuthUser {
  id: number
  name: string
  email: string
  role: 'student' | 'teacher' | 'admin'
}

export interface User extends BaseAuthUser {
  // /auth/me optionally returns role-specific profile fields.
  student_id?: string | null
  employee_id?: string | null
  department?: string | null
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

// Registration responses keep the narrower, registration-specific shapes.
export interface StudentRegisterData {
  student_id: string
  name: string
  email: string
  role: string
}

export interface TeacherRegisterData {
  employee_id: string | null
  department: string | null
  name: string
  email: string
  role: string
}

// Broader /auth/me payload.
export interface CurrentUser {
  id: number
  name: string
  email: string
  role: string
  student_id: string | null
  employee_id: string | null
  department: string | null
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

// ============ Account / Danger Zone
export interface ResetPreview {
  practice_sessions: number
  practice_answers: number
  attempts: number
  attempt_answers: number
  coding_submissions: number
  xp_transactions: number
  badges: number
  bookmarks: number
  missions: number
  roadmaps: number
  roadmap_items: number
  recommendations: number
  topic_performance_rows: number
  performance_snapshots: number
  ai_answer_logs: number
  activity_events: number
  leaderboard_entries: number
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

// ============ Coding (Phase 15B) — matches backend /api/coding responses
export interface CodingProblemListItem {
  id: number
  title: string
  difficulty: string
  topic_id: number | null
  solved: boolean
}

export interface CodingProblemListData {
  problems: CodingProblemListItem[]
  total: number
  page: number
  limit: number
}

export interface CodingSampleTestCase {
  input_data: string | null
  expected_output: string | null
}

export interface CodingProblemDetail {
  id: number
  title: string
  description: string | null
  difficulty: string
  topic_id: number | null
  input_format: string | null
  output_format: string | null
  constraints: string | null
  sample_test_cases: CodingSampleTestCase[]
  solved: boolean
}

export interface CodingCaseResult {
  index: number
  verdict: string
  time_ms: number
  hidden: boolean
  stdin?: string | null
  expected?: string | null
  actual?: string | null
  stderr?: string | null
}

export interface CodingSubmissionResult {
  id: number
  problem_id: number
  language: string
  status: string
  passed_test_cases: number
  total_test_cases: number
  execution_time_ms: number | null
  error_message: string | null
  results: CodingCaseResult[]
}

export interface CodingSubmissionHistoryItem {
  id: number
  problem_id: number
  language: string
  status: string
  passed_test_cases: number
  total_test_cases: number
  created_at: string
}

export interface CodingSubmissionHistoryData {
  submissions: CodingSubmissionHistoryItem[]
  total: number
  page: number
  limit: number
}

export interface CodingPerformance {
  problems_attempted: number
  problems_solved: number
  pass_rate: number | null
  total_submissions: number
  by_difficulty: Record<string, { solved: number; total: number }>
}

// ============ Roadmap (Phase 15B)
export interface RoadmapItem {
  id: number
  topic_id: number
  topic_name: string | null
  sequence_order: number
  status: 'NOT_STARTED' | 'IN_PROGRESS' | 'COMPLETED'
  priority: 'HIGH' | 'MEDIUM' | 'LOW'
  reason: string | null
  target_accuracy: number | null
  recommended_difficulty: string | null
  completed_at: string | null
}

export interface RoadmapData {
  id: number
  title: string
  overall_progress: number
  items: RoadmapItem[]
  generated_at: string
}

// ============ Recommendations (Phase 15B)
export interface Recommendation {
  id: number
  topic_id: number
  topic_name: string | null
  recommendation_type: string
  reason: string | null
  priority: string
  recommended_difficulty: string | null
  status: string
  created_at: string
}

export interface RecommendationListData {
  recommendations: Recommendation[]
  total: number
}

// ============ Gamification (Phase 15B)
export interface GamificationSummary {
  xp: number
  level: number
  current_level_floor: number
  next_level_xp: number
  xp_to_next_level: number
  progress_percent: number
  current_streak: number
  longest_streak: number
}

export interface MissionItem {
  id: number
  mission_id: number
  title: string
  description: string | null
  mission_type: string
  target_value: number
  progress: number
  status: string
  xp_reward: number
}

export interface EarnedBadge {
  id: number
  badge_id: number
  name: string
  description: string | null
  icon: string | null
  earned_at: string
}

export interface BadgeCatalogEntry {
  id: number
  name: string
  description: string | null
  icon: string | null
  criteria_type: string
  criteria_value: number
  xp_reward: number
  is_active: boolean
}

export interface ActivityEventItem {
  id: number
  event_type: string
  reference_id: number | null
  metadata: Record<string, unknown> | null
  created_at: string
}

export interface LeaderboardRow {
  rank: number
  student_id: string
  name: string
  xp: number
}

// ============ Chatbot
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponseData {
  reply: string
  model: string
}

// ============ AI Questions (Phase 15C)
/** The correct answer is NOT sent to the client; grading uses a server-side
 *  single-use ticket issued at generate time. */
export interface AIQuestion {
  question: string
  options: string[]
  ticket: string
  topic_id: number | null
  topic_name: string | null
  company: string | null
  difficulty: string
  persisted: false
}

export interface AIQuestionEvaluateResult {
  is_correct: boolean
  correct_answer: string
  student_answer: string
  explanation: string | null
  hint: string | null
  xp_earned: number
  xp_total: number
  level: number
  level_up: {
    progress_percent: number
    xp_to_next_level: number
    current_level_floor: number
    next_level_xp: number
  }
  current_streak: number
  topic_accuracy: number | null
  overall_accuracy: number | null
  readiness_score: number
  recorded_only_answer: boolean
}

// ============ Admin (Phase 15D)
export interface AdminUserRow {
  id: number
  name: string
  email: string
  role: string
  is_active: boolean
  created_at: string
}

export interface AdminUserListData {
  users: AdminUserRow[]
  total: number
  page: number
  limit: number
}

export interface PlatformAnalytics {
  total_students: number
  total_teachers: number
  total_questions: number
  pending_questions: number
  total_assessments: number
  total_attempts: number
  total_code_submissions: number
  active_students_7d: number
  average_accuracy: number | null
  popular_topics: { topic_id: number; topic_name: string; students_tracked: number }[]
}

export interface StudentAnalyticsRow {
  student_profile_id: number
  student_id: string
  name: string
  email: string
  is_active: boolean
  accuracy: number | null
  questions_attempted: number
  assessment_avg_score: number | null
  problems_solved: number
  streak_days: number
  xp: number
  level: number
  readiness_score: number
}

export interface QuestionAnalytics {
  topics: { topic_id: number; topic_name: string; total_attempts: number; accuracy: number | null }[]
  difficulty_distribution: Record<string, number>
}

export interface SubmissionAnalytics {
  problems: {
    problem_id: number
    title: string
    difficulty: string
    submissions: number
    pass_rate: number | null
  }[]
  language_distribution: Record<string, number>
}

export interface PopularTopicRow {
  topic_id: number
  topic_name: string
  attempts: number
}

export interface GamificationConfig {
  xp_rules: Record<string, number>
  level_thresholds: number[]
  streak_milestone_days: number
  badges: BadgeCatalogEntry[]
}

// ============ Coaching (Feature Groups 1, 2, 3, 7, 10, 11)
export interface PlanItem {
  section: string
  title: string
  detail: string
  target: number
  progress: number
  done: boolean
  topic_id?: number | null
  problem_id?: number | null
}

export interface DailyPlan {
  day_number: number
  date: string
  items: PlanItem[]
  progress_percent: number
  xp_earned_today: number
  xp_target: number
  focus_topic: string | null
}

export interface SkillGapItem {
  topic_id: number
  topic_name: string
  category: string | null
  level: 'strong' | 'moderate' | 'weak'
  accuracy: number | null
  attempts: number
  trend: 'IMPROVING' | 'STABLE' | 'DECLINING' | 'NEW'
  priority_score: number
  priority: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT_DATA'
  recommended_action: string
  last_attempted_at: string | null
}

export interface SkillGapData {
  skills: SkillGapItem[]
  weakest_topic: SkillGapItem | null
  strongest_topic: SkillGapItem | null
  improving_count: number
  declining_count: number
  formula: Record<string, string>
}

export interface ReadinessBreakdown {
  score: number
  components: Record<string, number>
  weights: Record<string, number>
  labels: Record<string, string>
  aptitude: { accuracy: number; attempted: number }
  coding: { attempted: number; solved: number }
  assessment: { attempts: number; average_score: number | null }
  consistency: { active_days: number; window_days: number }
  coverage: { topics_attempted: number; topics_target: number }
  data_completeness: number
}

export interface ContinueLearningItem {
  kind: 'practice_session' | 'assessment_attempt' | 'roadmap_item'
  id: number
  label: string
  detail: string
  href: string
}

export interface CoachingDashboard {
  todays_plan: DailyPlan
  weakest_aptitude_topic: SkillGapItem | null
  weakest_coding_topic: SkillGapItem | null
  current_accuracy: number | null
  coding_success_rate: number | null
  coding_solved: number
  coding_attempted: number
  readiness: ReadinessBreakdown
  streak: number
  xp_today: number
  xp_total: number
  level: number
  recent_badges: { name: string; icon: string | null; earned_at: string }[]
  recommended_next: {
    suggested_difficulty: string
    reason: string
    topic_id: number | null
    topic_name: string | null
  }
  continue_learning: ContinueLearningItem[]
  roadmap_progress: number | null
}

export interface TrendPoint {
  date: string
  attempted: number
  correct: number
  submissions: number
  solved: number
  accuracy: number | null
}

export interface ProgressTrendsData {
  window_days: number
  has_data: boolean
  series: TrendPoint[]
  totals: {
    attempted: number
    correct: number
    accuracy: number | null
    coding_submissions: number
    coding_solved: number
  }
}

export interface RevisionTopic {
  topic_id: number
  topic_name: string
  accuracy: number
  wrong_count: number
  attempts: number
  recently_wrong: boolean
  declining: boolean
  priority_score: number
}

export interface RevisionFeed {
  topics: RevisionTopic[]
  total: number
}

export interface RevisionPracticeResult {
  session: PracticeStartData | null
  message?: string
  topic_id?: number
  topic_name?: string
}

export interface CompanyProfile {
  company_id: number
  company_name: string
  is_general_profile: boolean
  profile_note: string
  topics: {
    topic_id: number
    topic_name: string
    category: string | null
    available_questions: number
    your_accuracy: number | null
  }[]
  coding_problems_available: number
  questions_attempted: number
  progress_percent: number
}

// ============ Adaptive difficulty (Feature Group 4)
export interface AdaptiveDifficulty {
  suggested_difficulty: 'easy' | 'medium' | 'hard'
  window_accuracy: number | null
  window_size: number
  reason: string
  algorithm: { window: number; min_answers: number; thresholds: string }
}

// ============ Bookmarks (Feature Group 12)
export interface BookmarkItem {
  id: number
  bookmark_type: 'QUESTION' | 'PROBLEM' | 'CONCEPT'
  note: string | null
  created_at: string
  question_id: number | null
  problem_id: number | null
  question_text?: string
  topic_id?: number | null
  difficulty?: string
  explanation?: string | null
  correct_answer?: string | null
  problem_title?: string
  problem_difficulty?: string
}

// ============ Interview prep (Feature Group 6)
export interface InterviewConfig {
  categories: { id: string; label: string }[]
  difficulties: string[]
  experience_levels: string[]
}

export interface InterviewQuestions {
  category: string
  category_label: string
  difficulty: string
  experience_level: string
  questions: { id: number; question: string; difficulty: string }[]
}

export interface InterviewFeedback {
  question: string
  student_answer: string
  expected_concepts: string[]
  deterministic_feedback: {
    source: 'deterministic'
    quality: 'good' | 'partial' | 'weak'
    score: number
    matched_keywords: string[]
    missing_concepts: string[]
    suggestion: string
  }
  ai_feedback: { source: 'ai'; text: string } | null
  disclaimer: string
}

// ============ Progressive hints (Feature Group 5)
export interface ProgressiveHint {
  level: number
  label: string
  text: string
  max_level: number
  remaining: number
}

// ============ Teacher attention list (Feature Group 16)
export interface AttentionStudent {
  student_profile_id: number
  student_id: string
  name: string
  reasons: string[]
  overall_accuracy: number | null
}

// ============ Teacher (Phase 15 demo)
export interface TeacherStudentRow {
  association_id: number
  student_profile_id: number
  student_id: string
  name: string
  email: string
  xp: number
  level: number
  current_streak: number
  overall_accuracy: number | null
  classification: string
  assessment_avg_score: number | null
  questions_attempted: number
}

export interface TeacherDashboardData {
  total_students: number
  average_accuracy: number | null
  average_assessment_score: number | null
  students: TeacherStudentRow[]
  weak_topics_class_wide: { topic_id: number; topic_name: string; count: number }[]
  students_needing_attention?: AttentionStudent[]
}

// ============ Generic API Response
export interface ApiResponse<T = unknown> {
  success: boolean
  message: string
  data: T
}

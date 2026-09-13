# SkillSprint

## API Specification Document

**Version:** 1.0
**Project:** SkillSprint
**Backend:** FastAPI
**API Style:** RESTful API
**Data Format:** JSON
**Database:** PostgreSQL
**Authentication:** JWT-based Authentication

---

## 1. Introduction

### 1.1 Purpose

This document defines the Application Programming Interface (API) specification for the SkillSprint platform.

SkillSprint is a gamified and personalized placement-readiness platform designed to help students prepare for aptitude and coding assessments. The backend API provides communication between the frontend application, business logic services, database, personalization engine, gamification engine, and AI services.

The API is responsible for:

* User authentication and authorization
* Student, teacher, and admin management
* Aptitude practice
* Company-wise preparation
* Assessments and mock tests
* Coding problem management and submissions
* Performance analysis
* Personalized recommendations
* Personalized learning roadmaps
* Daily quizzes
* Gamification
* XP, levels, streaks, badges, and missions
* Leaderboards
* Teacher-student management
* Question management
* AI-assisted functionality

---

# 2. System Architecture

The API follows a layered architecture.

```text
React Frontend
      |
      | HTTP / HTTPS
      v
FastAPI REST API
      |
      +-------------------------+
      |                         |
      v                         v
Authentication             Application Services
                                |
             +------------------+------------------+
             |                  |                  |
             v                  v                  v
       Learning Services   Personalization    Gamification
             |                  |                  |
             +------------------+------------------+
                                |
                                v
                           PostgreSQL
                                |
                                v
                            AI Service
                                |
                                v
                           Gemini API
```

The frontend must communicate with the backend through the API rather than accessing the database directly.

The Gemini API key must never be exposed to the frontend.

---

# 3. API Base Configuration

## 3.1 Base URL

During development:

```text
http://localhost:8000/api
```

Production:

```text
/api
```

The actual production domain may be configured through environment variables.

---

# 4. HTTP Methods

| Method | Purpose                                   |
| ------ | ----------------------------------------- |
| GET    | Retrieve resources                        |
| POST   | Create a resource or perform an operation |
| PUT    | Replace an existing resource              |
| PATCH  | Partially update a resource               |
| DELETE | Delete or deactivate a resource           |

---

# 5. Authentication

SkillSprint uses JWT-based authentication.

Authenticated requests should provide:

```http
Authorization: Bearer <access_token>
```

The backend must validate the token before processing protected endpoints.

---

# 6. Standard Response Format

## 6.1 Successful Response

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {}
}
```

## 6.2 Error Response

```json
{
  "success": false,
  "message": "Invalid request",
  "error_code": "INVALID_REQUEST"
}
```

---

# 7. HTTP Status Codes

| Status Code | Meaning                                  |
| ----------- | ---------------------------------------- |
| 200         | Successful request                       |
| 201         | Resource created                         |
| 204         | Successful request with no response body |
| 400         | Bad request                              |
| 401         | Authentication required or invalid       |
| 403         | Insufficient permissions                 |
| 404         | Resource not found                       |
| 409         | Resource conflict                        |
| 422         | Validation error                         |
| 429         | Too many requests                        |
| 500         | Internal server error                    |
| 503         | Service unavailable                      |

---

# 8. Authentication APIs

## 8.1 Student Registration

```http
POST /api/auth/register/student
```

### Request

```json
{
  "name": "Rahul Sharma",
  "email": "rahul@example.com",
  "password": "password123"
}
```

### Response

```json
{
  "success": true,
  "message": "Student registered successfully",
  "data": {
    "student_id": "SS202600123",
    "name": "Rahul Sharma",
    "email": "rahul@example.com",
    "role": "student"
  }
}
```

---

## 8.2 Teacher Registration

```http
POST /api/auth/register/teacher
```

### Request

```json
{
  "name": "Professor Sharma",
  "email": "teacher@example.com",
  "password": "password123"
}
```

---

## 8.3 Login

```http
POST /api/auth/login
```

### Request

```json
{
  "email": "student@example.com",
  "password": "password123"
}
```

### Response

```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "jwt_token",
    "token_type": "bearer",
    "user": {
      "id": 101,
      "name": "Rahul Sharma",
      "email": "student@example.com",
      "role": "student"
    }
  }
}
```

---

## 8.4 Get Current User

```http
GET /api/auth/me
```

Returns the authenticated user's profile and role.

---

## 8.5 Logout

```http
POST /api/auth/logout
```

---

# 9. Student APIs

## 9.1 Get Student Profile

```http
GET /api/students/profile
```

### Response

```json
{
  "success": true,
  "data": {
    "student_id": "SS202600123",
    "name": "Rahul Sharma",
    "email": "rahul@example.com",
    "xp": 1250,
    "level": 8,
    "current_streak": 12,
    "readiness_score": 68
  }
}
```

---

## 9.2 Student Dashboard

```http
GET /api/students/dashboard
```

The dashboard API should return the information required to render the student's main dashboard.

### Response

```json
{
  "success": true,
  "data": {
    "student": {
      "student_id": "SS202600123",
      "name": "Rahul Sharma"
    },
    "readiness_score": 68,
    "xp": 1250,
    "level": 8,
    "current_streak": 12,
    "rank": 15,
    "roadmap_progress": 54,
    "today_missions": [],
    "recommended_topics": []
  }
}
```

---

# 10. Topic APIs

## 10.1 Get Topics

```http
GET /api/topics
```

Optional filters:

```text
GET /api/topics?category=quantitative
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Percentages",
      "category": "Quantitative",
      "description": "Percentage-based aptitude problems"
    },
    {
      "id": 2,
      "name": "Probability",
      "category": "Quantitative",
      "description": "Probability-based aptitude problems"
    }
  ]
}
```

---

# 11. Question APIs

## 11.1 Get Questions

```http
GET /api/questions
```

Supported query parameters:

| Parameter       | Description                   |
| --------------- | ----------------------------- |
| `topic_id`      | Filter by topic               |
| `company_id`    | Filter by company             |
| `difficulty`    | Easy, Medium, Hard            |
| `category`      | Quantitative, Logical, Verbal |
| `question_type` | MCQ, Coding                   |
| `page`          | Page number                   |
| `limit`         | Number of results             |

Example:

```text
GET /api/questions?topic_id=2&difficulty=medium&limit=10
```

---

## 11.2 Get Question

```http
GET /api/questions/{question_id}
```

### Response

```json
{
  "success": true,
  "data": {
    "id": 101,
    "question_text": "A number is increased by 20%...",
    "question_type": "mcq",
    "topic_id": 2,
    "difficulty": "medium",
    "options": [
      {
        "id": 1,
        "text": "100"
      },
      {
        "id": 2,
        "text": "120"
      },
      {
        "id": 3,
        "text": "150"
      },
      {
        "id": 4,
        "text": "180"
      }
    ]
  }
}
```

---

# 12. Aptitude Practice APIs

## 12.1 Start Practice Session

```http
POST /api/practice/start
```

### Request

```json
{
  "topic_id": 2,
  "difficulty": "medium",
  "question_count": 10
}
```

### Response

```json
{
  "success": true,
  "data": {
    "session_id": "PS_10021",
    "questions": []
  }
}
```

---

## 12.2 Submit Practice Answer

```http
POST /api/practice/{session_id}/answer
```

### Request

```json
{
  "question_id": 101,
  "selected_option_id": 2,
  "time_taken_seconds": 34
}
```

---

## 12.3 Complete Practice Session

```http
POST /api/practice/{session_id}/complete
```

### Response

```json
{
  "success": true,
  "data": {
    "score": 80,
    "correct": 8,
    "incorrect": 2,
    "unattempted": 0,
    "accuracy": 80,
    "xp_earned": 50
  }
}
```

---

# 13. Company Preparation APIs

## 13.1 Get Companies

```http
GET /api/companies
```

---

## 13.2 Get Company Details

```http
GET /api/companies/{company_id}
```

---

## 13.3 Get Company Questions

```http
GET /api/companies/{company_id}/questions
```

Optional:

```text
?topic_id=2
?difficulty=medium
```

---

# 14. Assessment APIs

## 14.1 Start Assessment

```http
POST /api/assessments/start
```

### Request

```json
{
  "assessment_type": "mock_test",
  "company_id": null,
  "duration_minutes": 30,
  "question_count": 30
}
```

### Response

```json
{
  "success": true,
  "data": {
    "attempt_id": 501,
    "assessment_id": 10,
    "started_at": "2026-09-13T14:00:00"
  }
}
```

---

## 14.2 Submit Assessment

```http
POST /api/assessments/{attempt_id}/submit
```

### Response

```json
{
  "success": true,
  "data": {
    "score": 23,
    "total_questions": 30,
    "correct": 23,
    "incorrect": 5,
    "unattempted": 2,
    "accuracy": 76.67,
    "time_taken_seconds": 1620
  }
}
```

---

## 14.3 Assessment History

```http
GET /api/assessments/history
```

Returns the student's previous assessments.

---

# 15. Performance APIs

## 15.1 Overall Performance

```http
GET /api/performance
```

### Response

```json
{
  "success": true,
  "data": {
    "overall_accuracy": 71.4,
    "readiness_score": 68,
    "strong_topics": [
      "Percentages",
      "Logical Reasoning"
    ],
    "weak_topics": [
      "Probability",
      "Time and Work"
    ]
  }
}
```

---

## 15.2 Topic Performance

```http
GET /api/performance/topics
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "topic": "Probability",
      "accuracy": 42,
      "attempts": 35,
      "average_time_seconds": 48,
      "trend": "improving"
    },
    {
      "topic": "Percentages",
      "accuracy": 86,
      "attempts": 41,
      "average_time_seconds": 31,
      "trend": "stable"
    }
  ]
}
```

---

## 15.3 Performance History

```http
GET /api/performance/history
```

Used to display improvement trends over time.

---

# 16. Personalization APIs

Personalization is one of the two primary SkillSprint features.

## 16.1 Get Recommendations

```http
GET /api/recommendations
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "topic": "Probability",
      "priority": "high",
      "recommended_difficulty": "easy",
      "recommended_action": "Practice basic probability",
      "reason": "Your recent accuracy in Probability is 42%."
    }
  ]
}
```

---

## 16.2 Generate Recommendations

```http
POST /api/recommendations/generate
```

The personalization service should consider:

* Historical performance
* Recent assessment performance
* Topic accuracy
* Number of attempts
* Difficulty level
* Time taken
* Incorrect answers
* Recent improvement
* Practice history
* Coding performance
* Assessment performance
* Consistency

The system then generates:

* Recommended topics
* Recommended questions
* Recommended difficulty
* Revision activities
* Roadmap changes
* Personalized missions

---

# 17. Personalized Roadmap APIs

## 17.1 Get Roadmap

```http
GET /api/roadmap
```

### Response

```json
{
  "success": true,
  "data": {
    "progress": 54,
    "items": [
      {
        "id": 1,
        "topic": "Percentages",
        "status": "completed",
        "priority": "medium"
      },
      {
        "id": 2,
        "topic": "Probability",
        "status": "in_progress",
        "priority": "high"
      },
      {
        "id": 3,
        "topic": "Time and Work",
        "status": "not_started",
        "priority": "high"
      }
    ]
  }
}
```

---

## 17.2 Update Roadmap

```http
POST /api/roadmap/update
```

The roadmap should be updated when significant new performance information becomes available.

---

## 17.3 Complete Roadmap Item

```http
PATCH /api/roadmap/items/{item_id}
```

### Request

```json
{
  "status": "completed"
}
```

---

# 18. Daily Quiz APIs

## 18.1 Get Daily Quiz

```http
GET /api/quiz/daily
```

The questions may be selected based on:

* Weak topics
* Current roadmap
* Previous performance
* Recent activity
* Required difficulty

---

## 18.2 Submit Daily Quiz

```http
POST /api/quiz/daily/submit
```

### Response

```json
{
  "success": true,
  "data": {
    "score": 8,
    "total": 10,
    "accuracy": 80,
    "xp_earned": 50,
    "streak_updated": true
  }
}
```

---

# 19. Gamification APIs

Gamification is the second primary SkillSprint feature.

## 19.1 Gamification Profile

```http
GET /api/gamification/profile
```

### Response

```json
{
  "success": true,
  "data": {
    "xp": 1250,
    "level": 8,
    "current_streak": 12,
    "longest_streak": 18,
    "next_level_xp": 1400
  }
}
```

---

## 19.2 XP History

```http
GET /api/gamification/xp-history
```

---

## 19.3 Missions

```http
GET /api/missions
```

### Response

```json
{
  "success": true,
  "data": [
    {
      "id": 10,
      "title": "Practice Probability",
      "description": "Solve 5 Probability questions",
      "xp_reward": 75,
      "progress": 3,
      "target": 5,
      "status": "in_progress"
    }
  ]
}
```

---

## 19.4 Badges

```http
GET /api/gamification/badges
```

---

## 19.5 Leaderboard

```http
GET /api/leaderboard
```

Supported filters:

```text
?scope=global
?scope=class
?period=weekly
?period=monthly
```

---

# 20. Coding APIs

## 20.1 Get Coding Problems

```http
GET /api/code/problems
```

Filters:

```text
?topic=arrays
?difficulty=easy
```

---

## 20.2 Get Coding Problem

```http
GET /api/code/problems/{problem_id}
```

---

## 20.3 Submit Code

```http
POST /api/code/submissions
```

### Request

```json
{
  "problem_id": 101,
  "language": "python",
  "source_code": "..."
}
```

---

## 20.4 Submission Result

```json
{
  "success": true,
  "data": {
    "submission_id": 5001,
    "status": "completed",
    "result": "partial",
    "passed_test_cases": 7,
    "total_test_cases": 10,
    "execution_time_ms": 142
  }
}
```

Code execution must be isolated using a sandboxed execution environment with CPU, memory, execution-time, and process restrictions.

---

# 21. Teacher APIs

## 21.1 Teacher Dashboard

```http
GET /api/teachers/dashboard
```

---

## 21.2 Add Student

```http
POST /api/teachers/students
```

### Request

```json
{
  "student_id": "SS202600123"
}
```

The system must validate that the Student ID exists.

---

## 21.3 Get Teacher's Students

```http
GET /api/teachers/students
```

Only students associated with the authenticated teacher should be returned.

---

## 21.4 Student Performance

```http
GET /api/teachers/students/{student_id}/performance
```

---

## 21.5 Student Weak Topics

```http
GET /api/teachers/students/{student_id}/weak-topics
```

---

## 21.6 Submit Question

```http
POST /api/teachers/questions
```

### Request

```json
{
  "question_text": "....",
  "question_type": "mcq",
  "topic_id": 5,
  "company_id": 2,
  "difficulty": "medium",
  "correct_answer": "....",
  "explanation": "...."
}
```

Teacher-created questions may be placed into a pending state for admin approval.

---

# 22. Admin APIs

Admin APIs provide complete platform management.

```text
GET    /api/admin/users
POST   /api/admin/users
PATCH  /api/admin/users/{id}

GET    /api/admin/questions
POST   /api/admin/questions
PATCH  /api/admin/questions/{id}
DELETE /api/admin/questions/{id}

GET    /api/admin/topics
POST   /api/admin/topics

GET    /api/admin/companies
POST   /api/admin/companies

GET    /api/admin/assessments

GET    /api/admin/badges
POST   /api/admin/badges

GET    /api/admin/gamification
PATCH  /api/admin/gamification
```

Admin permissions include:

* User management
* Question management
* Teacher question approval
* Topic management
* Company management
* Assessment management
* Badge management
* Gamification configuration
* Platform analytics

---

# 23. AI APIs

AI functionality must be accessed through the backend.

```text
POST /api/ai/generate-question
POST /api/ai/explain-answer
POST /api/ai/generate-hint
POST /api/ai/analyze-performance
```

The backend AI service communicates with Gemini.

```text
Frontend
   |
   v
FastAPI
   |
   v
AI Service
   |
   v
Gemini API
```

The Gemini API key must be stored in environment variables and must never be sent to the frontend.

AI-generated output must be validated before being stored or shown to users.

---

# 24. API Authorization Matrix

| Module                       | Student | Teacher |  Admin |
| ---------------------------- | ------: | ------: | -----: |
| Own Profile                  |     Yes |     Yes |    Yes |
| Practice                     |     Yes |      No |     No |
| Assessments                  |     Yes |    View | Manage |
| Own Performance              |     Yes |      No |    Yes |
| Assigned Student Performance |      No |     Yes |    Yes |
| Roadmap                      |     Own |    View | Manage |
| Gamification                 |     Own |    View | Manage |
| Questions                    |    View |  Submit |   Full |
| Users                        |      No |      No |   Full |
| Topics                       |    View |    View |   Full |
| Companies                    |    View |    View |   Full |
| Platform Analytics           |      No | Limited |   Full |

---

# 25. Security Requirements

The API must implement:

1. Password hashing using a secure password hashing algorithm.
2. JWT-based authentication.
3. Backend-side role-based access control.
4. Input validation using Pydantic schemas.
5. Protection against unauthorized access.
6. Teacher-student data isolation.
7. Secure storage of API keys.
8. Rate limiting where required.
9. SQL injection protection through ORM/parameterized queries.
10. CORS configuration.
11. Secure error handling without exposing internal implementation details.
12. Sandboxed code execution.
13. Audit/activity logging for important actions.

---

# 26. Core SkillSprint Data Flow

The main API flow is:

```text
Student
   |
   v
Practice / Assessment
   |
   v
Attempts
   |
   v
Performance Analysis
   |
   v
Personalization Engine
   |
   +------------------+
   |                  |
   v                  v
Recommendations     Roadmap
   |                  |
   +--------+---------+
            |
            v
       Missions
            |
            v
       Practice Again
            |
            v
      Gamification
            |
      +-----+-----+
      |     |     |
      v     v     v
     XP   Streak Badge
      |
      v
 Leaderboard
      |
      v
Improvement
      |
      v
Reassessment
```

---

# 27. Important Business Rule

SkillSprint must follow the core learning loop:

```text
ASSESS
   ↓
ANALYZE
   ↓
PERSONALIZE
   ↓
PRACTICE
   ↓
REWARD
   ↓
IMPROVE
   ↓
REASSESS
```

The API architecture must support this continuous cycle.

---

# 28. API Endpoint Summary

```text
/api/auth/*
/api/students/*
/api/teachers/*
/api/admin/*
/api/topics/*
/api/companies/*
/api/questions/*
/api/practice/*
/api/assessments/*
/api/performance/*
/api/recommendations/*
/api/roadmap/*
/api/quiz/*
/api/missions/*
/api/gamification/*
/api/leaderboard/*
/api/code/*
/api/ai/*
```

---

# 29. API Design Principles

The SkillSprint API should follow these principles:

* RESTful endpoint design
* Consistent JSON responses
* Clear HTTP status codes
* Role-based authorization
* Strong request validation
* Pagination for large collections
* Filtering and sorting where required
* Separation of API routes and business logic
* Database access through service/repository layers
* AI access only through backend services
* Deterministic calculation of scores, XP, levels, streaks, and rankings
* Secure code execution
* Clear error messages
* Maintainable and modular endpoint structure

---

# 30. Final API Architecture

```text
                         SKILLSPRINT API
                                |
              +-----------------+-----------------+
              |                 |                 |
              v                 v                 v
        Authentication      Learning          Management
              |                 |                 |
              |        +--------+--------+        |
              |        |        |        |        |
              v        v        v        v        v
            Users   Practice  Tests   Coding   Admin/Teacher
                         |
                         v
                  Performance
                         |
                         v
                Personalization
                         |
              +----------+----------+
              |                     |
              v                     v
          Roadmap                Missions
                                    |
                                    v
                              Gamification
                                    |
                          +---------+---------+
                          |         |         |
                          v         v         v
                         XP       Badges    Streak
                                    |
                                    v
                              Leaderboard
```

**End of API Specification**

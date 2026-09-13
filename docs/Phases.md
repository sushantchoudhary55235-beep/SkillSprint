# SkillSprint

## Development Phases & Implementation Plan

**Version:** 1.0
**Project:** SkillSprint
**Document:** Development Phases
**Backend:** FastAPI
**Frontend:** React + TypeScript
**Database:** PostgreSQL
**AI Service:** Gemini API
**ORM:** SQLAlchemy
**Migration Tool:** Alembic

---

# 1. Purpose

This document defines the development phases for the SkillSprint platform.

The purpose of dividing development into phases is to ensure that the system is built incrementally, with each phase producing a stable and testable component before the next phase begins.

SkillSprint contains multiple interconnected systems:

* Authentication and role management
* Student dashboard
* Teacher dashboard
* Admin dashboard
* Aptitude preparation
* Company-wise preparation
* Assessments and mock tests
* Coding practice
* Performance analysis
* Personalized learning
* Personalized roadmap
* Gamification
* Daily quizzes
* Teacher-student monitoring
* Question management
* AI-assisted features

Because these modules depend on one another, development must follow a controlled sequence.

---

# 2. Development Philosophy

SkillSprint follows an incremental development approach.

The system should be developed according to the following principle:

```text
Foundation
    ↓
Authentication
    ↓
Core Learning
    ↓
Assessment
    ↓
Performance Analysis
    ↓
Personalization
    ↓
Gamification
    ↓
Teacher/Admin
    ↓
AI Integration
    ↓
Testing
    ↓
Deployment
```

The two primary product systems are:

```text
PERSONALIZED LEARNING
        +
GAMIFICATION
```

All other modules should support these two systems.

---

# 3. Overall Development Roadmap

```text
PHASE 0
Project Planning & Documentation
        ↓
PHASE 1
Repository & Development Environment
        ↓
PHASE 2
Database & Backend Foundation
        ↓
PHASE 3
Authentication & Role-Based Access
        ↓
PHASE 4
Question & Content Management
        ↓
PHASE 5
Student Learning System
        ↓
PHASE 6
Assessment & Testing System
        ↓
PHASE 7
Performance Analysis Engine
        ↓
PHASE 8
Personalization Engine
        ↓
PHASE 9
Personalized Roadmap
        ↓
PHASE 10
Gamification Engine
        ↓
PHASE 11
Coding Practice System
        ↓
PHASE 12
Teacher Dashboard
        ↓
PHASE 13
Admin Dashboard
        ↓
PHASE 14
AI Integration
        ↓
PHASE 15
Integration & System Testing
        ↓
PHASE 16
Deployment & Final Release
```

---

# 4. Phase 0 — Project Planning & Documentation

## Objective

Define the complete product, architecture, requirements, user flows, database design, and development strategy before major implementation begins.

## Activities

* Define project objectives.
* Define target users.
* Define user roles.
* Identify primary features.
* Define product USPs.
* Create PRD.
* Create SRS.
* Create UX/user flow documentation.
* Create API specification.
* Create database design.
* Define system architecture.
* Define development phases.
* Define coding conventions.
* Define Git workflow.

## Primary Product USPs

### USP 1 — Personalized Learning

The system continuously analyzes student performance and determines:

```text
What is the student weak at?
        ↓
What should the student practice?
        ↓
At what difficulty?
        ↓
What should the student learn next?
```

### USP 2 — Gamified Learning

The platform converts learning activity into:

```text
Practice
   ↓
XP
   ↓
Level
   ↓
Streak
   ↓
Mission
   ↓
Badge
   ↓
Leaderboard
```

## Deliverables

```text
PRD.md
SRS.md
UX_USER_FLOW.md
API_SPECIFICATION.md
DATABASE_DESIGN.md
PHASES.md
SYSTEM_ARCHITECTURE.md
```

## Completion Criteria

Phase 0 is complete when:

* Requirements are defined.
* Core features are finalized.
* Roles are finalized.
* API structure is defined.
* Database entities are defined.
* Development order is agreed upon.

---

# 5. Phase 1 — Repository & Development Environment

## Objective

Set up the development environment and repository structure.

## Frontend

Initialize:

```text
React
TypeScript
Vite
```

Recommended structure:

```text
frontend/
├── src/
│   ├── components/
│   ├── pages/
│   ├── layouts/
│   ├── services/
│   ├── hooks/
│   ├── context/
│   ├── types/
│   └── utils/
├── public/
└── package.json
```

## Backend

Initialize:

```text
FastAPI
SQLAlchemy
Pydantic
Alembic
PostgreSQL
```

Recommended structure:

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── repositories/
│   ├── core/
│   └── utils/
├── tests/
├── alembic/
└── requirements.txt
```

## Environment Configuration

Create:

```text
.env
.env.example
```

Variables may include:

```text
DATABASE_URL
JWT_SECRET_KEY
JWT_ALGORITHM
GEMINI_API_KEY
CORS_ORIGINS
```

Sensitive values must not be committed to Git.

## Git Setup

Recommended branches:

```text
main
develop
feature/*
bugfix/*
```

## Completion Criteria

* Frontend starts successfully.
* Backend starts successfully.
* PostgreSQL connection works.
* Environment variables work.
* Git repository is configured.
* Basic API health endpoint works.

Example:

```text
GET /api/health
```

Response:

```json
{
  "status": "ok"
}
```

---

# 6. Phase 2 — Database & Backend Foundation

## Objective

Create the database structure and backend foundation.

## Database

Implement the core tables:

```text
users
student_profiles
teacher_profiles
teacher_students

topics
companies

questions
question_options

assessments
assessment_questions
attempts
answers
```

Then implement supporting tables:

```text
topic_performance
performance_snapshots

roadmaps
roadmap_items
recommendations

missions
student_missions

xp_transactions
badges
student_badges

leaderboards
leaderboard_entries

coding_problems
test_cases
code_submissions

activity_events
```

## Backend Components

Implement:

* Database connection
* SQLAlchemy models
* Pydantic schemas
* Repository layer
* Service layer
* API router structure
* Exception handling
* Logging
* Database migrations

## Migration

Use Alembic.

```text
SQLAlchemy Model
       ↓
Alembic Migration
       ↓
PostgreSQL
```

## Completion Criteria

* Database can be created from migrations.
* All major relationships work.
* Foreign keys are enforced.
* Basic CRUD operations work.
* Backend can connect to PostgreSQL.
* Database errors are handled properly.

---

# 7. Phase 3 — Authentication & Role-Based Access

## Objective

Implement secure authentication and role-based access control.

## Roles

```text
Student
Teacher
Admin
```

## Student Flow

```text
Register
   ↓
Account Created
   ↓
Student ID Generated
   ↓
Login
   ↓
Student Dashboard
```

## Teacher Flow

```text
Teacher Account
      ↓
Login
      ↓
Teacher Dashboard
```

## Admin Flow

```text
Admin Account
      ↓
Login
      ↓
Admin Dashboard
```

## Authentication Features

Implement:

* Registration
* Login
* JWT generation
* JWT validation
* Password hashing
* Current-user endpoint
* Logout/session handling
* Token expiration
* Protected routes

## Authorization

Example:

```text
Student → Student APIs
Teacher → Teacher APIs
Admin → Admin APIs
```

The backend must never rely only on frontend route protection.

## Completion Criteria

* All three roles can authenticate.
* Invalid credentials are rejected.
* Protected APIs reject unauthenticated requests.
* Students cannot access admin APIs.
* Teachers cannot access admin APIs.
* Student IDs are unique.
* Passwords are never stored as plain text.

---

# 8. Phase 4 — Question & Content Management

## Objective

Build the central content management system.

## Question Categories

```text
Quantitative Aptitude
Logical Reasoning
Verbal Ability
Programming
Data Structures
Algorithms
```

## Question Attributes

Each aptitude question should contain:

```text
Question
Question Type
Topic
Company
Difficulty
Options
Correct Answer
Explanation
Source
Status
```

## Difficulty

```text
Easy
Medium
Hard
```

## Question Sources

```text
Admin
Teacher
AI Generated
Imported
```

## Teacher Question Flow

```text
Teacher
   ↓
Create Question
   ↓
Pending
   ↓
Admin Review
   ↓
Approved
   ↓
Available to Students
```

## Admin Question Flow

```text
Admin
   ↓
Create/Edit/Delete
   ↓
Approve
   ↓
Publish
```

## Completion Criteria

* Questions can be created.
* Questions can be categorized.
* Topics can be assigned.
* Companies can be assigned.
* Difficulty can be assigned.
* Teachers can submit questions.
* Admin can approve/reject questions.
* Students can retrieve approved questions.

---

# 9. Phase 5 — Student Learning System

## Objective

Build the basic student learning experience.

## Student Dashboard

Dashboard should show:

```text
Student Name
Student ID
Readiness Score
XP
Level
Streak
Rank
Today's Missions
Recommended Topics
Roadmap Progress
```

## Practice Modes

### Topic-wise Practice

```text
Select Category
      ↓
Select Topic
      ↓
Select Difficulty
      ↓
Practice
      ↓
Result
```

### Company-wise Practice

```text
Select Company
      ↓
Select Topic / Difficulty
      ↓
Practice
      ↓
Result
```

## Practice Session

The system should:

1. Create a practice session.
2. Fetch appropriate questions.
3. Display questions.
4. Record answers.
5. Track time.
6. Calculate score.
7. Store attempt data.
8. Update performance.
9. Trigger gamification.

## Completion Criteria

* Student can select topics.
* Student can practice questions.
* Answers are recorded.
* Score is calculated.
* Results are displayed.
* Attempts are stored.
* Performance data is generated.

---

# 10. Phase 6 — Assessment & Mock Test System

## Objective

Implement structured assessments.

## Assessment Types

```text
Diagnostic Test
Topic Test
Company Test
Mock Test
Daily Test
```

## Assessment Flow

```text
Select Assessment
       ↓
Start
       ↓
Questions
       ↓
Timer
       ↓
Submit
       ↓
Evaluation
       ↓
Performance Report
```

## Result

The system should calculate:

```text
Total Questions
Correct
Incorrect
Unattempted
Score
Accuracy
Time Taken
Topic-wise Performance
```

## Assessment History

Students should be able to view previous attempts.

Example:

```text
Mock Test 01
Score: 72%
Date: 10 Sept

Mock Test 02
Score: 78%
Date: 12 Sept

Mock Test 03
Score: 84%
Date: 13 Sept
```

## Completion Criteria

* Assessments can be created.
* Students can start assessments.
* Answers are recorded.
* Submission works.
* Scores are calculated.
* Results are stored.
* Assessment history works.

---

# 11. Phase 7 — Performance Analysis Engine

## Objective

Convert raw student activity into meaningful performance information.

## Inputs

The system analyzes:

```text
Assessment Scores
Question Accuracy
Topic Accuracy
Attempts
Difficulty
Time Taken
Incorrect Answers
Practice History
Coding Performance
Recent Performance
Historical Performance
Consistency
```

## Processing

```text
Raw Attempts
      ↓
Answer Analysis
      ↓
Topic Aggregation
      ↓
Performance Metrics
      ↓
Weak/Strong Topic Detection
      ↓
Performance Trend
```

## Topic Classification

Example:

```text
Probability       → Weak
Time & Work       → Weak
Percentages       → Strong
Logical Reasoning → Strong
```

## Trend Detection

```text
Improving
Stable
Declining
New
```

## Completion Criteria

The system must be able to:

* Calculate topic accuracy.
* Identify weak topics.
* Identify strong topics.
* Track performance history.
* Detect improvement.
* Compare recent and historical performance.

---

# 12. Phase 8 — Personalization Engine

## Objective

This is one of the most important phases of SkillSprint.

The Personalization Engine answers:

> "What should this student learn next?"

## Input

```text
Student Performance
        +
Learning History
        +
Topic Performance
        +
Assessment Results
        +
Recent Activity
```

## Processing

```text
Performance Data
       ↓
Weakness Detection
       ↓
Priority Calculation
       ↓
Topic Recommendation
       ↓
Difficulty Recommendation
       ↓
Activity Recommendation
```

## Example

Suppose:

```text
Probability = 42%
Time & Work = 48%
Percentages = 86%
```

The system may recommend:

```text
1. Probability Basics
2. Probability Easy Practice
3. Probability Mini Test
4. Time & Work Fundamentals
5. Reassessment
```

## Recommendation Reason

Every important recommendation should have a reason.

Example:

```text
Recommended: Probability

Why?
Your recent accuracy in Probability is 42%,
which is below your target performance.
```

## Completion Criteria

* Recommendations are generated from actual performance.
* Weak topics receive higher priority.
* Difficulty is adjusted.
* Recommendations update after new performance.
* Recommendation reasons are displayed.

---

# 13. Phase 9 — Personalized Roadmap

## Objective

Create a dynamic learning roadmap for every student.

## Roadmap Example

```text
WEEK 1

✓ Percentages
✓ Ratio
→ Probability
→ Time & Work

WEEK 2

→ Profit & Loss
→ Permutation
→ Logical Reasoning
```

The roadmap must not be identical for every student.

## Roadmap Generation

```text
Student Performance
       ↓
Weak Topics
       ↓
Priority
       ↓
Learning Sequence
       ↓
Personalized Roadmap
```

## Roadmap States

```text
Not Started
In Progress
Completed
```

## Dynamic Updating

Example:

```text
Probability
Before: 42%
       ↓
Practice
       ↓
Assessment
       ↓
Probability
After: 68%
```

The roadmap may then reduce Probability priority and move the student toward the next weak topic.

## Completion Criteria

* Every student can have a roadmap.
* Roadmap items have priority.
* Roadmap tracks completion.
* Roadmap reflects performance.
* Roadmap can change after assessments.

---

# 14. Phase 10 — Gamification Engine

## Objective

Build the second primary SkillSprint system.

The Gamification Engine answers:

> "How can we motivate this student to keep learning?"

## Core Components

```text
XP
Levels
Streaks
Missions
Badges
Leaderboards
```

---

## 14.1 XP System

Students receive XP for meaningful learning activities.

Example:

```text
Complete Practice       +25 XP
Complete Daily Quiz     +50 XP
Complete Mission        +75 XP
Complete Mock Test      +100 XP
Earn Badge              +150 XP
```

XP rules must be controlled by the backend.

---

## 14.2 Level System

Example:

```text
Level 1 → 0 XP
Level 2 → 100 XP
Level 3 → 250 XP
Level 4 → 450 XP
...
```

The exact progression can be configured later.

---

## 14.3 Streak System

A streak represents consecutive days of qualifying learning activity.

Example:

```text
Monday     ✓
Tuesday    ✓
Wednesday  ✓
Thursday   ✓

Current Streak = 4 Days
```

Simply logging into the platform should not necessarily count as learning activity.

---

## 14.4 Mission System

Missions should encourage useful learning.

Example:

```text
Mission:
Solve 5 Probability Questions

Progress:
3 / 5

Reward:
+75 XP
```

Missions can be generated from personalization.

This creates the connection:

```text
Weak Topic
    ↓
Personalized Recommendation
    ↓
Mission
    ↓
Practice
    ↓
XP
```

---

## 14.5 Badge System

Examples:

```text
7-Day Streak
First Mock Test
100 Questions Solved
Probability Master
Coding Starter
Weekly Champion
```

---

## 14.6 Leaderboard

Leaderboards may include:

```text
Global
Teacher/Class
Weekly
Monthly
All-Time
```

The leaderboard should reward meaningful learning activity rather than only login frequency.

## Completion Criteria

* XP is awarded correctly.
* Duplicate XP rewards are prevented.
* Levels update correctly.
* Streaks update correctly.
* Missions track progress.
* Badges are awarded once.
* Leaderboards calculate rankings correctly.

---

# 15. Phase 11 — Coding Practice System

## Objective

Implement programming problem solving and code evaluation.

## Coding Problem

Each problem contains:

```text
Title
Description
Input Format
Output Format
Constraints
Examples
Topic
Difficulty
```

## Coding Flow

```text
Student
   ↓
Select Problem
   ↓
Write Code
   ↓
Submit
   ↓
Execution Sandbox
   ↓
Test Cases
   ↓
Result
```

## Execution Result

```text
Passed: 7/10

Result: Partial
```

Possible results:

```text
Accepted
Wrong Answer
Time Limit Exceeded
Runtime Error
Compilation Error
```

## Security

Student code must never run directly inside the main FastAPI process.

Use an isolated execution environment with:

* CPU limits
* Memory limits
* Time limits
* Process restrictions
* Restricted filesystem access
* Network restrictions where appropriate

## Completion Criteria

* Coding problems can be displayed.
* Code can be submitted.
* Test cases execute.
* Results are returned.
* Submission history is stored.
* Unsafe execution is prevented.

---

# 16. Phase 12 — Teacher Dashboard

## Objective

Allow teachers to monitor assigned students.

## Student Association

```text
Teacher
   ↓
Add Students
   ↓
Enter Student ID
   ↓
Validate ID
   ↓
Authorization / Association
   ↓
Student Added
```

## Teacher Dashboard

Display:

```text
Total Students
Average Performance
Top Performers
Students Requiring Attention
Weak Topics
Recent Activity
Class Ranking
```

## Individual Student View

Teacher can see:

```text
Student Name
Student ID
Performance
Accuracy
Strong Topics
Weak Topics
Assessment History
Roadmap Progress
XP
Level
Streak
Badges
Ranking
```

Teachers should only be able to access assigned students.

## Teacher Question Submission

Teachers can:

```text
Create Question
       ↓
Select Topic
       ↓
Select Company
       ↓
Select Difficulty
       ↓
Submit
       ↓
Admin Review
```

## Completion Criteria

* Teacher dashboard works.
* Teacher can add students.
* Student association is validated.
* Teacher can view assigned students.
* Teacher can view performance.
* Teacher can submit questions.
* Access isolation works.

---

# 17. Phase 13 — Admin Dashboard

## Objective

Provide centralized control over the platform.

## Admin Functions

### User Management

```text
View Users
Search Users
Activate / Deactivate
View Roles
```

### Question Management

```text
Create
Edit
Approve
Reject
Archive
Delete
```

### Topic Management

```text
Create Topic
Edit Topic
Deactivate Topic
```

### Company Management

```text
Add Company
Edit Company
Deactivate Company
```

### Gamification Configuration

Admin may configure:

```text
XP Rules
Badge Criteria
Mission Rules
Leaderboard Settings
```

### Platform Analytics

Display:

```text
Total Students
Total Teachers
Total Questions
Total Assessments
Total Attempts
Active Students
Average Accuracy
Popular Topics
```

## Completion Criteria

* Admin dashboard works.
* Admin can manage users.
* Admin can manage questions.
* Admin can manage topics.
* Admin can manage companies.
* Admin can manage gamification.
* Admin can view platform analytics.

---

# 18. Phase 14 — AI Integration

## Objective

Integrate AI features after the core deterministic learning system is stable.

AI should enhance SkillSprint rather than replace the core backend logic.

## AI Responsibilities

Possible AI functions include:

```text
Question Generation
Question Classification
Answer Explanation
Step-by-Step Hints
Performance Interpretation
Learning Recommendations
Personalized Study Suggestions
```

## AI Architecture

```text
Frontend
    ↓
FastAPI
    ↓
AI Service
    ↓
Gemini API
    ↓
AI Response
    ↓
Validation
    ↓
Frontend / Database
```

## Important Rule

AI should not directly determine critical values.

For example:

```text
AI:
"Probability appears to be a weak topic."

Backend:
"Student accuracy = 42%"
```

The backend remains responsible for:

```text
Scores
Accuracy
XP
Levels
Streaks
Leaderboard Rankings
Test Results
```

## AI Question Generation

```text
Admin/Teacher
      ↓
Request Question
      ↓
Gemini
      ↓
Generated Question
      ↓
Validation
      ↓
Review
      ↓
Database
```

AI-generated questions should be validated before publication.

## Completion Criteria

* Gemini API is securely connected.
* API key is hidden from frontend.
* AI responses are validated.
* AI explanations work.
* AI hints work.
* AI question generation works if included.
* AI failures do not crash the core platform.

---

# 19. Phase 15 — Integration & System Testing

## Objective

Verify that all modules work together correctly.

This phase is extremely important because SkillSprint contains interconnected systems.

---

# 20. Unit Testing

Test individual functions and services.

Examples:

```text
calculate_score()
calculate_accuracy()
calculate_xp()
calculate_level()
update_streak()
detect_weak_topics()
generate_recommendation()
update_roadmap()
```

---

# 21. API Testing

Test:

```text
Authentication APIs
Student APIs
Teacher APIs
Admin APIs
Question APIs
Assessment APIs
Performance APIs
Personalization APIs
Gamification APIs
Coding APIs
AI APIs
```

Verify:

* Request validation
* Response structure
* Authentication
* Authorization
* Error handling

---

# 22. Integration Testing

Important integration flows:

### Assessment → Performance

```text
Assessment
   ↓
Attempt
   ↓
Answers
   ↓
Score
   ↓
Topic Performance
```

### Performance → Personalization

```text
Performance
   ↓
Weak Topic
   ↓
Recommendation
   ↓
Roadmap
```

### Personalization → Gamification

```text
Recommendation
   ↓
Mission
   ↓
Practice
   ↓
XP
```

### Gamification → Leaderboard

```text
XP
 ↓
Ranking
 ↓
Leaderboard
```

### Teacher → Student

```text
Student ID
   ↓
Association
   ↓
Teacher Dashboard
   ↓
Student Performance
```

---

# 23. End-to-End Testing

The complete student journey should be tested:

```text
Register
   ↓
Login
   ↓
Dashboard
   ↓
Diagnostic Assessment
   ↓
Performance Analysis
   ↓
Weak Topic Detection
   ↓
Personalized Recommendation
   ↓
Roadmap
   ↓
Mission
   ↓
Practice
   ↓
XP
   ↓
Streak
   ↓
Badge
   ↓
Leaderboard
   ↓
Reassessment
   ↓
Improved Performance
```

This is the most important end-to-end test flow.

---

# 24. Security Testing

Test:

```text
Invalid Login
Expired Token
Unauthorized API
Role Escalation
SQL Injection
Invalid Input
Duplicate Requests
Code Execution Abuse
API Rate Abuse
```

Special attention should be given to:

```text
Student → Teacher Data
Student → Admin Data
Teacher → Unassigned Student Data
```

---

# 25. Performance Testing

Test:

* Dashboard response time
* Question retrieval
* Assessment submission
* Leaderboard queries
* Performance analysis
* Recommendation generation
* Database queries
* Concurrent users

Large datasets should use:

```text
Pagination
Indexes
Caching where appropriate
Efficient queries
```

---

# 26. Phase 16 — Deployment & Final Release

## Objective

Deploy the complete SkillSprint platform.

## Production Architecture

```text
                    INTERNET
                        |
                        v
                  React Frontend
                        |
                     HTTPS
                        |
                        v
                 FastAPI Backend
                        |
             +----------+----------+
             |                     |
             v                     v
        PostgreSQL             Gemini API
```

## Deployment Checklist

### Frontend

```text
Production build
Environment variables
API URL configuration
Routing
HTTPS
```

### Backend

```text
Production server
Environment variables
Database connection
CORS
JWT configuration
Logging
Error handling
```

### Database

```text
Production PostgreSQL
Migrations
Backups
Indexes
Constraints
```

### Security

```text
HTTPS
Secure secrets
Strong JWT secret
Password hashing
CORS
Input validation
Sandboxed code execution
```

---

# 27. Final Release Checklist

Before final release:

## Authentication

```text
[ ] Student login
[ ] Teacher login
[ ] Admin login
[ ] Registration
[ ] JWT authentication
[ ] RBAC
```

## Student

```text
[ ] Dashboard
[ ] Aptitude practice
[ ] Company preparation
[ ] Mock tests
[ ] Daily quiz
[ ] Performance
[ ] Recommendations
[ ] Roadmap
[ ] Coding
```

## Personalization

```text
[ ] Weak topic detection
[ ] Recommendation generation
[ ] Difficulty recommendation
[ ] Roadmap generation
[ ] Dynamic roadmap updates
[ ] Recommendation explanation
```

## Gamification

```text
[ ] XP
[ ] Levels
[ ] Streaks
[ ] Missions
[ ] Badges
[ ] Leaderboards
```

## Teacher

```text
[ ] Teacher dashboard
[ ] Add students
[ ] Student monitoring
[ ] Performance analytics
[ ] Question submission
```

## Admin

```text
[ ] User management
[ ] Question management
[ ] Topic management
[ ] Company management
[ ] Assessment management
[ ] Gamification configuration
[ ] Analytics
```

## AI

```text
[ ] Question generation
[ ] Explanations
[ ] Hints
[ ] Performance interpretation
[ ] AI error handling
```

---

# 28. Development Dependencies

Some phases cannot begin properly until earlier phases are complete.

```text
Phase 1
   ↓
Phase 2
   ↓
Phase 3
   ↓
Phase 4
   ↓
Phase 5
   ↓
Phase 6
   ↓
Phase 7
   ↓
Phase 8
   ↓
Phase 9
   ↓
Phase 10
```

However, after the foundation is stable, some modules can be developed in parallel.

Example:

```text
                    Phase 7
                       |
             +---------+---------+
             |                   |
             v                   v
      Personalization       Coding System
             |
             v
         Roadmap
             |
             v
       Gamification
             |
      +------+------+
      |             |
      v             v
   Teacher        Admin
```

---

# 29. Recommended Team Development Strategy

For a multi-member project, work should be divided by modules rather than randomly editing the same files.

Example:

```text
Developer A
Authentication + Backend Core

Developer B
Student Frontend + Dashboard

Developer C
Aptitude + Assessment

Developer D
Performance + Personalization

Developer E
Gamification + Roadmap

Developer F
Teacher/Admin + Integration
```

The exact assignment can change according to team availability.

---

# 30. Git Development Strategy

Each feature should be developed in its own branch.

Example:

```text
main
  |
  +-- feature/authentication
  |
  +-- feature/student-dashboard
  |
  +-- feature/assessment
  |
  +-- feature/personalization
  |
  +-- feature/gamification
  |
  +-- feature/teacher-dashboard
```

Recommended flow:

```text
Create Branch
     ↓
Implement Feature
     ↓
Test
     ↓
Commit
     ↓
Push
     ↓
Review
     ↓
Merge
```

Avoid directly making large untested changes to `main`.

---

# 31. Definition of Done

A phase is considered complete only when:

1. Required functionality is implemented.
2. API endpoints are working.
3. Database changes are migrated.
4. Frontend integration is complete.
5. Authentication/authorization is verified.
6. Basic error handling is implemented.
7. Unit/API tests are passed where applicable.
8. Documentation is updated.
9. Code is committed to Git.
10. The feature does not break existing functionality.

---

# 32. MVP Priority

If development time becomes limited, the following priority should be used.

## Priority 1 — Core Product

```text
Authentication
Student Dashboard
Aptitude Practice
Assessment
Performance Analysis
Personalization
Roadmap
```

## Priority 2 — Primary Engagement

```text
XP
Streak
Missions
Badges
Leaderboard
Daily Quiz
```

## Priority 3 — Management

```text
Teacher Dashboard
Admin Dashboard
Question Management
```

## Priority 4 — Advanced

```text
Coding Execution
AI Question Generation
Advanced AI Features
Advanced Analytics
```

The core personalized-learning loop should be completed before spending excessive time on secondary UI features.

---

# 33. Core Product Loop

The final SkillSprint system should revolve around this loop:

```text
                    ┌───────────────┐
                    │    ASSESS     │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │    ANALYZE    │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │  PERSONALIZE  │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │    PRACTICE   │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │     REWARD    │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │    IMPROVE    │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │  REASSESS     │
                    └───────┬───────┘
                            |
                            └──────────→ back to ANALYZE
```

This loop is the central functional philosophy of SkillSprint.

---

# 34. Phase Completion Summary

| Phase | Major Deliverable        | Status  |
| ----- | ------------------------ | ------- |
| 0     | Planning & Documentation | Completed |
| 1     | Development Environment  | Completed |
| 2     | Database & Backend       | Completed |
| 3     | Authentication & RBAC    | Planned |
| 4     | Question Management      | Planned |
| 5     | Student Learning         | Planned |
| 6     | Assessments              | Planned |
| 7     | Performance Engine       | Planned |
| 8     | Personalization Engine   | Planned |
| 9     | Personalized Roadmap     | Planned |
| 10    | Gamification Engine      | Planned |
| 11    | Coding System            | Planned |
| 12    | Teacher Dashboard        | Planned |
| 13    | Admin Dashboard          | Planned |
| 14    | AI Integration           | Planned |
| 15    | Testing & Integration    | Planned |
| 16    | Deployment               | Planned |

---

# 35. Final System Dependency

The most important dependency chain in SkillSprint is:

```text
USER
 ↓
AUTHENTICATION
 ↓
LEARNING ACTIVITY
 ↓
ASSESSMENT
 ↓
PERFORMANCE DATA
 ↓
PERSONALIZATION ENGINE
 ↓
ROADMAP
 ↓
MISSION
 ↓
PRACTICE
 ↓
GAMIFICATION ENGINE
 ↓
XP / STREAK / BADGE
 ↓
LEADERBOARD
 ↓
IMPROVEMENT
 ↓
REASSESSMENT
```

Therefore, development should not treat personalization and gamification as optional add-ons.

They are the central systems that differentiate SkillSprint from a conventional aptitude practice platform.

---

# 36. Final Development Goal

The final system should provide the following experience:

```text
Student logs in
       ↓
System understands current skill level
       ↓
Student takes assessment
       ↓
System analyzes performance
       ↓
Weak areas are identified
       ↓
Personalized recommendations are generated
       ↓
Roadmap is updated
       ↓
Student receives learning missions
       ↓
Student practices
       ↓
Student earns XP
       ↓
Streak continues
       ↓
Badges are earned
       ↓
Leaderboard position changes
       ↓
Student improves
       ↓
System reassesses the student
       ↓
Learning plan adapts again
```

This creates a continuously adapting placement-preparation platform rather than a static question bank.

---

# 37. Document Maintenance

This document should be updated whenever:

* A development phase is completed.
* A feature is added or removed.
* Architecture changes.
* Database requirements change.
* API requirements change.
* Project priorities change.
* A future feature becomes part of the MVP.

The phase status should be maintained as:

```text
PLANNED
IN_PROGRESS
COMPLETED
BLOCKED
DEFERRED
```

**End of Development Phases Document**

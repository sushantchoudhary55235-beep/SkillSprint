# SkillSprint

## Database Design Document

**Version:** 1.0
**Database:** PostgreSQL
**ORM:** SQLAlchemy
**Backend:** FastAPI
**Database Type:** Relational Database

---

# 1. Introduction

## 1.1 Purpose

This document defines the database architecture and relational data model for SkillSprint.

The database is responsible for storing:

* User accounts
* Student and teacher profiles
* Teacher-student relationships
* Topics
* Companies
* Questions
* Assessments
* Attempts
* Answers
* Performance data
* Personalized roadmaps
* Recommendations
* Daily quizzes
* Missions
* XP transactions
* Levels
* Streaks
* Badges
* Leaderboards
* Coding problems
* Coding test cases
* Coding submissions
* Activity events

The database must support the two primary SkillSprint features:

1. Personalized Learning
2. Gamified Learning

---

# 2. Database Design Principles

The database should follow:

* Relational database principles
* Primary and foreign key constraints
* Referential integrity
* Appropriate normalization
* Unique constraints
* Indexing for frequently accessed fields
* Secure storage of sensitive data
* Transaction consistency
* Auditability of important activities
* Separation of raw performance data and aggregated performance data

---

# 3. High-Level Database Architecture

```text
                         PostgreSQL
                              |
       +----------------------+----------------------+
       |                      |                      |
       v                      v                      v
    Identity               Learning              Gamification
       |                      |                      |
    Users                  Topics                  XP
    Profiles               Companies               Levels
    Roles                  Questions               Streaks
    Relationships          Assessments              Badges
                          Attempts                 Missions
                          Answers                  Leaderboards
                          Performance
                          Roadmap
                          Recommendations
                          Coding
```

---

# 4. Entity Overview

The major entities are:

```text
USERS
STUDENT_PROFILES
TEACHER_PROFILES
TEACHER_STUDENTS

TOPICS
COMPANIES
QUESTIONS
QUESTION_OPTIONS

ASSESSMENTS
ASSESSMENT_QUESTIONS
ATTEMPTS
ANSWERS

TOPIC_PERFORMANCE
PERFORMANCE_SNAPSHOTS

ROADMAPS
ROADMAP_ITEMS
RECOMMENDATIONS

MISSIONS
STUDENT_MISSIONS

XP_TRANSACTIONS
BADGES
STUDENT_BADGES

LEADERBOARDS
LEADERBOARD_ENTRIES

CODING_PROBLEMS
TEST_CASES
CODE_SUBMISSIONS

ACTIVITY_EVENTS
```

---

# 5. Users Table

## Table: `users`

Stores authentication and common user information.

| Column        | Data Type    | Constraints      |
| ------------- | ------------ | ---------------- |
| id            | BIGINT       | Primary Key      |
| name          | VARCHAR(100) | NOT NULL         |
| email         | VARCHAR(255) | UNIQUE, NOT NULL |
| password_hash | TEXT         | NOT NULL         |
| role          | VARCHAR(20)  | NOT NULL         |
| is_active     | BOOLEAN      | DEFAULT TRUE     |
| created_at    | TIMESTAMP    | NOT NULL         |
| updated_at    | TIMESTAMP    | NOT NULL         |

### Allowed Roles

```text
student
teacher
admin
```

### Important Constraints

```text
email UNIQUE
role NOT NULL
```

Passwords must never be stored in plain text.

---

# 6. Student Profiles

## Table: `student_profiles`

Stores student-specific information.

| Column             | Data Type    | Constraints      |
| ------------------ | ------------ | ---------------- |
| id                 | BIGINT       | Primary Key      |
| user_id            | BIGINT       | FK → users.id    |
| student_id         | VARCHAR(30)  | UNIQUE, NOT NULL |
| readiness_score    | DECIMAL(5,2) | DEFAULT 0        |
| xp                 | INTEGER      | DEFAULT 0        |
| level              | INTEGER      | DEFAULT 1        |
| current_streak     | INTEGER      | DEFAULT 0        |
| longest_streak     | INTEGER      | DEFAULT 0        |
| last_activity_date | DATE         | NULL             |
| created_at         | TIMESTAMP    |                  |
| updated_at         | TIMESTAMP    |                  |

### Relationship

```text
users 1 ───────── 1 student_profiles
```

The `student_id` is the identifier that can be shared with teachers for student association.

Example:

```text
SS202600123
```

---

# 7. Teacher Profiles

## Table: `teacher_profiles`

| Column      | Data Type    | Constraints   |
| ----------- | ------------ | ------------- |
| id          | BIGINT       | Primary Key   |
| user_id     | BIGINT       | FK → users.id |
| employee_id | VARCHAR(50)  | UNIQUE        |
| department  | VARCHAR(100) |               |
| created_at  | TIMESTAMP    |               |

Relationship:

```text
users 1 ───────── 1 teacher_profiles
```

---

# 8. Teacher-Student Relationship

## Table: `teacher_students`

This table represents the association between teachers and students.

| Column     | Data Type   | Constraints |
| ---------- | ----------- | ----------- |
| id         | BIGINT      | Primary Key |
| teacher_id | BIGINT      | FK          |
| student_id | BIGINT      | FK          |
| status     | VARCHAR(20) | NOT NULL    |
| created_at | TIMESTAMP   |             |

### Status

```text
PENDING
ACTIVE
REJECTED
REMOVED
```

### Constraint

```text
UNIQUE(teacher_id, student_id)
```

This prevents duplicate relationships.

---

# 9. Topics

## Table: `topics`

| Column      | Data Type    |
| ----------- | ------------ |
| id          | BIGINT PK    |
| name        | VARCHAR(100) |
| category    | VARCHAR(50)  |
| description | TEXT         |
| is_active   | BOOLEAN      |
| created_at  | TIMESTAMP    |

### Example Categories

```text
Quantitative
Logical
Verbal
Programming
Data Structures
Algorithms
```

### Example Topics

```text
Percentages
Probability
Time and Work
Profit and Loss
Ratio
Logical Reasoning
Blood Relations
Grammar
Vocabulary
Arrays
Strings
```

---

# 10. Companies

## Table: `companies`

| Column      | Data Type           |
| ----------- | ------------------- |
| id          | BIGINT PK           |
| name        | VARCHAR(150) UNIQUE |
| description | TEXT                |
| website     | VARCHAR(255)        |
| is_active   | BOOLEAN             |
| created_at  | TIMESTAMP           |

Companies can be associated with questions and assessments.

---

# 11. Questions

## Table: `questions`

Stores aptitude questions.

| Column        | Data Type   | Constraints |
| ------------- | ----------- | ----------- |
| id            | BIGINT      | Primary Key |
| question_text | TEXT        | NOT NULL    |
| question_type | VARCHAR(30) | NOT NULL    |
| topic_id      | BIGINT      | FK          |
| company_id    | BIGINT      | FK, NULL    |
| difficulty    | VARCHAR(20) | NOT NULL    |
| explanation   | TEXT        |             |
| source_type   | VARCHAR(30) |             |
| created_by    | BIGINT      | FK          |
| status        | VARCHAR(20) |             |
| created_at    | TIMESTAMP   |             |
| updated_at    | TIMESTAMP   |             |

### Question Types

```text
MCQ
TRUE_FALSE
SHORT_ANSWER
```

### Difficulty

```text
EASY
MEDIUM
HARD
```

### Source Type

```text
ADMIN
TEACHER
AI_GENERATED
IMPORTED
```

### Status

```text
DRAFT
PENDING
APPROVED
REJECTED
ARCHIVED
```

---

# 12. Question Options

## Table: `question_options`

Used for multiple-choice questions.

| Column       | Data Type |
| ------------ | --------- |
| id           | BIGINT PK |
| question_id  | BIGINT FK |
| option_text  | TEXT      |
| option_order | INTEGER   |
| is_correct   | BOOLEAN   |

Relationship:

```text
questions 1 ───────── N question_options
```

---

# 13. Assessments

## Table: `assessments`

| Column           | Data Type       |
| ---------------- | --------------- |
| id               | BIGINT PK       |
| title            | VARCHAR(200)    |
| assessment_type  | VARCHAR(30)     |
| duration_minutes | INTEGER         |
| question_count   | INTEGER         |
| company_id       | BIGINT FK, NULL |
| created_by       | BIGINT FK       |
| is_active        | BOOLEAN         |
| created_at       | TIMESTAMP       |

### Assessment Types

```text
DIAGNOSTIC
MOCK_TEST
TOPIC_TEST
COMPANY_TEST
DAILY_TEST
```

---

# 14. Assessment Questions

## Table: `assessment_questions`

This is a junction table between assessments and questions.

| Column         | Data Type    |
| -------------- | ------------ |
| id             | BIGINT PK    |
| assessment_id  | BIGINT FK    |
| question_id    | BIGINT FK    |
| question_order | INTEGER      |
| marks          | DECIMAL(5,2) |

Relationship:

```text
assessments N ───── N questions
```

through:

```text
assessment_questions
```

---

# 15. Attempts

## Table: `attempts`

Stores a student's attempt at an assessment.

| Column             | Data Type    |
| ------------------ | ------------ |
| id                 | BIGINT PK    |
| student_id         | BIGINT FK    |
| assessment_id      | BIGINT FK    |
| started_at         | TIMESTAMP    |
| submitted_at       | TIMESTAMP    |
| score              | DECIMAL(7,2) |
| total_marks        | DECIMAL(7,2) |
| correct_count      | INTEGER      |
| incorrect_count    | INTEGER      |
| unattempted_count  | INTEGER      |
| accuracy           | DECIMAL(5,2) |
| time_taken_seconds | INTEGER      |
| status             | VARCHAR(20)  |

### Status

```text
IN_PROGRESS
COMPLETED
ABANDONED
```

---

# 16. Answers

## Table: `answers`

Stores individual question-level responses.

| Column             | Data Type       |
| ------------------ | --------------- |
| id                 | BIGINT PK       |
| attempt_id         | BIGINT FK       |
| question_id        | BIGINT FK       |
| selected_option_id | BIGINT FK, NULL |
| answer_text        | TEXT            |
| is_correct         | BOOLEAN         |
| time_taken_seconds | INTEGER         |
| created_at         | TIMESTAMP       |

Relationship:

```text
attempts 1 ───── N answers
questions 1 ──── N answers
```

This table provides the raw data required for detailed performance analysis.

---

# 17. Topic Performance

## Table: `topic_performance`

Stores aggregated performance for a student on each topic.

| Column               | Data Type    |
| -------------------- | ------------ |
| id                   | BIGINT PK    |
| student_id           | BIGINT FK    |
| topic_id             | BIGINT FK    |
| total_attempts       | INTEGER      |
| correct_answers      | INTEGER      |
| incorrect_answers    | INTEGER      |
| accuracy             | DECIMAL(5,2) |
| average_time_seconds | DECIMAL(8,2) |
| trend                | VARCHAR(20)  |
| last_attempted_at    | TIMESTAMP    |
| updated_at           | TIMESTAMP    |

### Trend Values

```text
IMPROVING
DECLINING
STABLE
NEW
```

### Example

```text
Student: SS202600123

Probability
Attempts: 35
Accuracy: 42%
Trend: IMPROVING

Percentages
Attempts: 41
Accuracy: 86%
Trend: STABLE
```

---

# 18. Performance Snapshots

## Table: `performance_snapshots`

Stores historical performance states.

| Column          | Data Type    |
| --------------- | ------------ |
| id              | BIGINT PK    |
| student_id      | BIGINT FK    |
| assessment_id   | BIGINT FK    |
| overall_score   | DECIMAL(7,2) |
| accuracy        | DECIMAL(5,2) |
| readiness_score | DECIMAL(5,2) |
| created_at      | TIMESTAMP    |

This table allows the system to display performance trends over time.

---

# 19. Roadmaps

## Table: `roadmaps`

Stores a student's personalized roadmap.

| Column           | Data Type    |
| ---------------- | ------------ |
| id               | BIGINT PK    |
| student_id       | BIGINT FK    |
| title            | VARCHAR(200) |
| overall_progress | DECIMAL(5,2) |
| created_at       | TIMESTAMP    |
| updated_at       | TIMESTAMP    |

Each student can have an active personalized roadmap.

---

# 20. Roadmap Items

## Table: `roadmap_items`

| Column          | Data Type    |
| --------------- | ------------ |
| id              | BIGINT PK    |
| roadmap_id      | BIGINT FK    |
| topic_id        | BIGINT FK    |
| sequence_order  | INTEGER      |
| status          | VARCHAR(20)  |
| priority        | VARCHAR(20)  |
| reason          | TEXT         |
| target_accuracy | DECIMAL(5,2) |
| completed_at    | TIMESTAMP    |

### Status

```text
NOT_STARTED
IN_PROGRESS
COMPLETED
```

### Priority

```text
LOW
MEDIUM
HIGH
```

---

# 21. Recommendations

## Table: `recommendations`

Stores personalized learning recommendations.

| Column                 | Data Type   |
| ---------------------- | ----------- |
| id                     | BIGINT PK   |
| student_id             | BIGINT FK   |
| topic_id               | BIGINT FK   |
| recommendation_type    | VARCHAR(50) |
| reason                 | TEXT        |
| priority               | VARCHAR(20) |
| recommended_difficulty | VARCHAR(20) |
| status                 | VARCHAR(20) |
| created_at             | TIMESTAMP   |
| expires_at             | TIMESTAMP   |

Example:

```text
Student accuracy in Probability = 42%

Recommendation:
Topic = Probability
Priority = HIGH
Difficulty = EASY
Reason = Low recent accuracy
```

---

# 22. Missions

## Table: `missions`

Stores predefined or dynamically generated missions.

| Column       | Data Type       |
| ------------ | --------------- |
| id           | BIGINT PK       |
| title        | VARCHAR(200)    |
| description  | TEXT            |
| mission_type | VARCHAR(50)     |
| target_value | INTEGER         |
| xp_reward    | INTEGER         |
| badge_id     | BIGINT FK, NULL |
| is_active    | BOOLEAN         |
| created_at   | TIMESTAMP       |

---

# 23. Student Missions

## Table: `student_missions`

Tracks individual student mission progress.

| Column       | Data Type   |
| ------------ | ----------- |
| id           | BIGINT PK   |
| student_id   | BIGINT FK   |
| mission_id   | BIGINT FK   |
| progress     | INTEGER     |
| status       | VARCHAR(20) |
| started_at   | TIMESTAMP   |
| completed_at | TIMESTAMP   |

### Status

```text
NOT_STARTED
IN_PROGRESS
COMPLETED
EXPIRED
```

---

# 24. XP Transactions

## Table: `xp_transactions`

XP should be recorded as transactions rather than only maintaining a final XP number.

| Column        | Data Type   |
| ------------- | ----------- |
| id            | BIGINT PK   |
| student_id    | BIGINT FK   |
| activity_type | VARCHAR(50) |
| reference_id  | BIGINT      |
| xp_amount     | INTEGER     |
| description   | TEXT        |
| created_at    | TIMESTAMP   |

### Example

```text
Daily Quiz          +50 XP
Mission Completion  +75 XP
Mock Test           +100 XP
Badge               +150 XP
```

The student's current XP can be calculated from valid transactions or maintained in the student profile as a cached value.

---

# 25. Badges

## Table: `badges`

| Column         | Data Type    |
| -------------- | ------------ |
| id             | BIGINT PK    |
| name           | VARCHAR(100) |
| description    | TEXT         |
| icon           | VARCHAR(255) |
| criteria_type  | VARCHAR(50)  |
| criteria_value | INTEGER      |
| xp_reward      | INTEGER      |
| is_active      | BOOLEAN      |

Example:

```text
Badge: 7-Day Streak
Criteria: Complete qualifying activity for 7 consecutive days
```

---

# 26. Student Badges

## Table: `student_badges`

Stores badges earned by students.

| Column     | Data Type |
| ---------- | --------- |
| id         | BIGINT PK |
| student_id | BIGINT FK |
| badge_id   | BIGINT FK |
| earned_at  | TIMESTAMP |

Constraint:

```text
UNIQUE(student_id, badge_id)
```

This prevents duplicate badge awards.

---

# 27. Leaderboards

## Table: `leaderboards`

| Column      | Data Type    |
| ----------- | ------------ |
| id          | BIGINT PK    |
| name        | VARCHAR(150) |
| scope       | VARCHAR(30)  |
| period_type | VARCHAR(30)  |
| start_date  | DATE         |
| end_date    | DATE         |
| created_at  | TIMESTAMP    |

### Scope

```text
GLOBAL
CLASS
TEACHER
```

### Period

```text
DAILY
WEEKLY
MONTHLY
ALL_TIME
```

---

# 28. Leaderboard Entries

## Table: `leaderboard_entries`

| Column         | Data Type |
| -------------- | --------- |
| id             | BIGINT PK |
| leaderboard_id | BIGINT FK |
| student_id     | BIGINT FK |
| score          | INTEGER   |
| rank           | INTEGER   |

This table stores the ranking of students for a particular leaderboard.

---

# 29. Coding Problems

## Table: `coding_problems`

| Column        | Data Type    |
| ------------- | ------------ |
| id            | BIGINT PK    |
| title         | VARCHAR(200) |
| description   | TEXT         |
| topic_id      | BIGINT FK    |
| difficulty    | VARCHAR(20)  |
| input_format  | TEXT         |
| output_format | TEXT         |
| constraints   | TEXT         |
| created_by    | BIGINT FK    |
| created_at    | TIMESTAMP    |

---

# 30. Coding Test Cases

## Table: `test_cases`

| Column          | Data Type |
| --------------- | --------- |
| id              | BIGINT PK |
| problem_id      | BIGINT FK |
| input_data      | TEXT      |
| expected_output | TEXT      |
| is_hidden       | BOOLEAN   |
| time_limit_ms   | INTEGER   |
| memory_limit_mb | INTEGER   |

Hidden test cases must not be exposed to students.

---

# 31. Code Submissions

## Table: `code_submissions`

| Column            | Data Type   |
| ----------------- | ----------- |
| id                | BIGINT PK   |
| student_id        | BIGINT FK   |
| problem_id        | BIGINT FK   |
| language          | VARCHAR(30) |
| source_code       | TEXT        |
| status            | VARCHAR(30) |
| passed_test_cases | INTEGER     |
| total_test_cases  | INTEGER     |
| execution_time_ms | INTEGER     |
| memory_used_mb    | INTEGER     |
| error_message     | TEXT        |
| created_at        | TIMESTAMP   |

### Status

```text
QUEUED
RUNNING
ACCEPTED
WRONG_ANSWER
TIME_LIMIT
RUNTIME_ERROR
COMPILATION_ERROR
```

---

# 32. Activity Events

## Table: `activity_events`

This table records important student activities.

| Column       | Data Type   |
| ------------ | ----------- |
| id           | BIGINT PK   |
| student_id   | BIGINT FK   |
| event_type   | VARCHAR(50) |
| reference_id | BIGINT      |
| metadata     | JSONB       |
| created_at   | TIMESTAMP   |

### Event Types

```text
LOGIN
PRACTICE_STARTED
QUESTION_ATTEMPTED
PRACTICE_COMPLETED
TEST_STARTED
TEST_COMPLETED
CODE_SUBMITTED
MISSION_COMPLETED
XP_AWARDED
BADGE_EARNED
STREAK_UPDATED
ROADMAP_UPDATED
QUESTION_CREATED
QUESTION_APPROVED
STUDENT_ADDED
```

The activity table is important for both analytics and personalization.

---

# 33. Entity Relationships

The primary relationships are:

```text
users
  |
  +---- student_profiles
  |
  +---- teacher_profiles

teacher_profiles
  |
  +---- teacher_students ---- student_profiles

student_profiles
  |
  +---- attempts
  |
  +---- topic_performance
  |
  +---- performance_snapshots
  |
  +---- roadmaps
  |
  +---- recommendations
  |
  +---- student_missions
  |
  +---- xp_transactions
  |
  +---- student_badges
  |
  +---- leaderboard_entries
  |
  +---- code_submissions
  |
  +---- activity_events

topics
  |
  +---- questions
  |
  +---- topic_performance
  |
  +---- roadmap_items
  |
  +---- recommendations
  |
  +---- coding_problems

companies
  |
  +---- questions
  |
  +---- assessments

questions
  |
  +---- question_options
  |
  +---- assessment_questions
  |
  +---- answers

assessments
  |
  +---- assessment_questions
  |
  +---- attempts

attempts
  |
  +---- answers
```

---

# 34. Complete ER Relationship

```text
                         USERS
                           |
             +-------------+-------------+
             |                           |
             v                           v
     STUDENT_PROFILES              TEACHER_PROFILES
             |                           |
             |                     TEACHER_STUDENTS
             |                           |
             |                           v
             |                     STUDENT_PROFILES
             |
     +-------+--------+-----------------------+
     |       |        |        |              |
     v       v        v        v              v
  ATTEMPTS  TOPIC   ROADMAP  RECOMMENDATIONS  ACTIVITY
     |      PERF.      |
     |                 v
     |            ROADMAP_ITEMS
     |
     v
  ANSWERS
     |
     v
 QUESTIONS
     |
   +─+────────────+
   |              |
   v              v
OPTIONS       ASSESSMENTS
                  |
                  v
              ASSESSMENT
               QUESTIONS

STUDENT
   |
   +── XP_TRANSACTIONS
   +── STUDENT_MISSIONS
   +── STUDENT_BADGES
   +── LEADERBOARD_ENTRIES
   +── CODE_SUBMISSIONS
```

---

# 35. Personalized Learning Data Flow

The database supports the personalization pipeline:

```text
Student Activity
       |
       v
Attempts / Answers
       |
       v
Topic Performance
       |
       v
Performance Analysis
       |
       +------------------+
       |                  |
       v                  v
Weak Topics         Performance Trend
       |                  |
       +--------+---------+
                |
                v
       Personalization Engine
                |
       +--------+--------+
       |                 |
       v                 v
Recommendations       Roadmap
       |                 |
       +--------+--------+
                |
                v
             Missions
```

---

# 36. Gamification Data Flow

```text
Student Activity
       |
       v
Activity Events
       |
       v
Activity Validation
       |
       v
Gamification Service
       |
       +---------+----------+----------+
       |         |          |          |
       v         v          v          v
      XP       Streak      Badge    Mission
       |         |          |          |
       +---------+----------+----------+
                         |
                         v
                    Leaderboard
```

---

# 37. Important Database Design Rule

The system must separate:

### Raw data

```text
attempts
answers
code_submissions
activity_events
```

from:

### Derived/aggregated data

```text
topic_performance
performance_snapshots
recommendations
roadmaps
leaderboard_entries
```

This allows the system to recalculate derived information if the business logic changes.

---

# 38. AI and Database Responsibility

The AI service must not directly control critical database values.

For example, Gemini may recommend:

```text
Probability should be practiced at an easier difficulty.
```

But the backend calculates:

```text
Accuracy
Score
XP
Level
Streak
Leaderboard Rank
```

The correct architecture is:

```text
Gemini
   |
   v
AI Recommendation
   |
   v
Application Service
   |
   v
Validation / Business Rules
   |
   v
PostgreSQL
```

---

# 39. Indexing Strategy

Indexes should be created for frequently queried columns.

Recommended indexes include:

```text
users.email
users.role

student_profiles.student_id
student_profiles.user_id

teacher_students.teacher_id
teacher_students.student_id

questions.topic_id
questions.company_id
questions.difficulty
questions.status

attempts.student_id
attempts.assessment_id

answers.attempt_id
answers.question_id

topic_performance.student_id
topic_performance.topic_id

recommendations.student_id
roadmaps.student_id

student_missions.student_id
xp_transactions.student_id

student_badges.student_id
leaderboard_entries.leaderboard_id
leaderboard_entries.student_id

code_submissions.student_id
code_submissions.problem_id

activity_events.student_id
activity_events.event_type
```

Indexes should be added based on actual query patterns and database profiling.

---

# 40. Data Integrity Rules

The database must enforce:

1. Unique email addresses.
2. Unique Student IDs.
3. Unique teacher-student relationships.
4. Valid foreign-key relationships.
5. No duplicate student badges.
6. Valid question-topic relationships.
7. Valid assessment-question relationships.
8. Valid student-attempt relationships.
9. Valid coding problem-test-case relationships.
10. Valid student-submission relationships.

---

# 41. Security Considerations

Sensitive information must be protected.

### Passwords

Never store plain-text passwords.

Store:

```text
password_hash
```

### API Keys

AI API keys must not be stored in the database unless there is a specific secure secret-management requirement.

### Student Data

Teachers must only be able to access students associated with them.

### Coding Submissions

Source code must be treated as untrusted input.

Code execution must occur outside the main application process in a sandboxed environment.

---

# 42. Transaction Requirements

The following operations should use database transactions:

### Assessment submission

```text
Submit Assessment
       |
       +--> Save answers
       +--> Calculate score
       +--> Update performance
       +--> Update roadmap
       +--> Generate mission progress
       +--> Award XP
       +--> Update streak
```

These operations should be handled consistently so that a partial update does not leave the system in an inconsistent state.

---

# 43. Example End-to-End Scenario

A student completes a Probability assessment.

```text
1. Student starts assessment
        |
        v
2. attempts record created
        |
        v
3. Student answers questions
        |
        v
4. answers records created
        |
        v
5. Assessment submitted
        |
        v
6. Score calculated
        |
        v
7. topic_performance updated
        |
        v
8. performance_snapshot created
        |
        v
9. Weak topic detected
        |
        v
10. Recommendation generated
        |
        v
11. Roadmap updated
        |
        v
12. Personalized mission generated
        |
        v
13. Student practices Probability
        |
        v
14. XP awarded
        |
        v
15. Streak updated
        |
        v
16. Leaderboard updated
        |
        v
17. Student reassessed
```

This cycle represents the core SkillSprint learning system.

---

# 44. Database-to-Feature Mapping

| Feature                    | Primary Tables                                |
| -------------------------- | --------------------------------------------- |
| Authentication             | users                                         |
| Student Profile            | users, student_profiles                       |
| Teacher Profile            | users, teacher_profiles                       |
| Teacher-Student Management | teacher_students                              |
| Aptitude Questions         | questions, question_options                   |
| Topics                     | topics                                        |
| Company Preparation        | companies, questions                          |
| Mock Tests                 | assessments, assessment_questions             |
| Test Attempts              | attempts, answers                             |
| Performance                | topic_performance, performance_snapshots      |
| Personalization            | recommendations, topic_performance            |
| Roadmap                    | roadmaps, roadmap_items                       |
| Daily Quiz                 | assessments, attempts, answers                |
| XP                         | xp_transactions                               |
| Levels                     | student_profiles                              |
| Streaks                    | student_profiles, activity_events             |
| Missions                   | missions, student_missions                    |
| Badges                     | badges, student_badges                        |
| Leaderboard                | leaderboards, leaderboard_entries             |
| Coding                     | coding_problems, test_cases, code_submissions |
| Analytics                  | activity_events, performance tables           |
| AI                         | application service + Gemini API              |

---

# 45. Recommended Backend Model Structure

The SQLAlchemy models can be organized as:

```text
app/
├── models/
│   ├── user.py
│   ├── student.py
│   ├── teacher.py
│   ├── relationship.py
│   ├── topic.py
│   ├── company.py
│   ├── question.py
│   ├── assessment.py
│   ├── attempt.py
│   ├── performance.py
│   ├── roadmap.py
│   ├── recommendation.py
│   ├── mission.py
│   ├── gamification.py
│   ├── leaderboard.py
│   ├── coding.py
│   └── activity.py
```

---

# 46. Database Migration

Database schema changes should be managed using a migration system such as Alembic.

Example workflow:

```text
Modify SQLAlchemy Model
        |
        v
Create Migration
        |
        v
Review Migration
        |
        v
Run Migration
        |
        v
PostgreSQL Updated
```

Database changes should not be performed manually in production.

---

# 47. Final Database Architecture

```text
                       ┌────────────────────┐
                       │      USERS         │
                       └─────────┬──────────┘
                                 |
                +----------------+----------------+
                |                                 |
                v                                 v
        STUDENT_PROFILES                    TEACHER_PROFILES
                |                                 |
                |                           TEACHER_STUDENTS
                |
       +--------+---------+
       |        |         |
       v        v         v
   ATTEMPTS  PERFORMANCE ROADMAP
       |        |         |
       v        v         v
    ANSWERS  TOPICS   RECOMMENDATIONS
       |
       v
   QUESTIONS
       |
   +---+---+
   |       |
   v       v
OPTIONS  COMPANIES

STUDENT
   |
   +---- XP_TRANSACTIONS
   +---- MISSIONS
   +---- BADGES
   +---- LEADERBOARDS
   +---- CODE_SUBMISSIONS
   +---- ACTIVITY_EVENTS
```

---

# 48. Core Database Philosophy

SkillSprint should not simply store test scores.

The database must capture the student's **learning journey**:

```text
What did the student attempt?
        ↓
What did they get wrong?
        ↓
Which topics are weak?
        ↓
Is the student improving?
        ↓
What should they learn next?
        ↓
What roadmap should be followed?
        ↓
What mission should motivate them?
        ↓
What reward did they earn?
        ↓
Did their performance improve?
```

This allows SkillSprint to function as a **personalized and gamified placement-readiness platform**, rather than only being a question-and-answer application.

**End of Database Design Document**

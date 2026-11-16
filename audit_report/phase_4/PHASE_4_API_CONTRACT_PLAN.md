# Phase 4 API Contract Plan

**Generated**: 2026-11-01  
**Based on**: PHASE_4_IMPLEMENTATION_PLAN.md, PHASE_4_DATABASE_DESIGN.md, PHASE_4_VALIDATION_CHECKLIST.md  
**Status**: PLANNING PHASE — Awaiting approval  
**Last Updated**: 2026-11-01 (corrected for atomic rate limiting, student-scoped idempotency, claim-then-generate pattern)

---

## Overview

This document defines the API contract changes for Phase 4. The guiding principle is **minimal contract changes** — only add what's necessary for new functionality, preserve all existing behavior.

### Current AI Endpoints (No Breaking Changes)

| Endpoint | Method | Auth | Rate Limit | Current Response |
|----------|--------|------|------------|------------------|
| `/ai/explain` | POST | Student | 10/min | `{text: string}` |
| `/ai/hint` | POST | Student | 10/min | `{text: string}` |
| `/ai/hints/progressive` | POST | Student | 10/min | `{level, label, text, max_level, remaining}` |
| `/ai/performance-interpretation` | POST | Student | 10/min | `{text, facts}` |
| `/ai/chat` | POST | Student | 10/min | `{reply, model}` |
| `/ai/questions/generate` | POST | Student | 10/min | `{question, options, ticket, topic_id, topic_name, company, difficulty, persisted}` |
| `/ai/questions/evaluate` | POST | Student | 10/min | `AIQuestionEvaluateResult` |

**Key Architecture Notes**:
- Rate limiting is now **atomic** using PostgreSQL advisory locks (`pg_advisory_xact_lock`) — no race conditions, exact 10/min limit enforced
- Idempotency for `/questions/generate` uses **student-scoped composite unique index** `(student_id, idempotency_key)` — keys are scoped per student, not global
- **Claim-then-generate pattern** prevents duplicate Gemini calls under concurrency

---

## Contract Changes

### 1. New Configuration (No API Changes)

**Files**: `backend/app/core/config.py`

**New Settings** (environment variables):
```bash
GEMINI_MODEL=gemini-2.0-flash      # Default: gemini-2.0-flash
AI_TIMEOUT_S=15.0                   # Default: 15.0 (seconds)
```

**Behavior**:
- Invalid `AI_TIMEOUT_S` → clamped to [1.0, 60.0], logged at WARNING
- Invalid `GEMINI_MODEL` → used as-is (Gemini API validates)
- No API contract change — purely server-side configuration

---

### 2. Idempotency Key for `/ai/questions/generate`

**Endpoint**: `POST /ai/questions/generate`  
**Change**: Accept optional `Idempotency-Key` header

#### Request
```http
POST /api/ai/questions/generate
Idempotency-Key: <client-generated-uuid>
Content-Type: application/json

{
  "topic_id": 1,
  "company": "Google",
  "topic_name": "Percentages",
  "difficulty": "medium"
}
```

#### Response (Unchanged)
```json
{
  "success": true,
  "message": "AI question generated",
  "data": {
    "question": "What is 25% of 80?",
    "options": ["15", "20", "25", "30"],
    "ticket": "abc123...",
    "topic_id": 1,
    "topic_name": "Percentages",
    "company": "Google",
    "difficulty": "medium",
    "persisted": false
  }
}
```

#### Idempotency Behavior (Corrected)

- **Key format**: Client-generated UUID (recommended) or any string ≤128 chars
- **Storage**: `question_tickets.idempotency_key` column with **composite unique index**
  ```sql
  CREATE UNIQUE INDEX ix_question_tickets_idempotency 
      ON question_tickets(student_id, idempotency_key) 
      WHERE idempotency_key IS NOT NULL;
  ```
- **Scope**: **Student-scoped** — same key can be used by different students independently
- **TTL**: Same as ticket (30 minutes, tied to `expires_at`)
- **Claim-then-generate pattern** (atomic concurrency handling):
  1. On request with idempotency key, attempt `INSERT` with placeholder row (claims the key)
  2. If `IntegrityError` (duplicate key): another request already claimed it → **wait for completion** (poll up to 30s), then return **existing ticket** (no new Gemini call)
  3. If claim succeeds: call Gemini, update placeholder with real data, return ticket_id
  4. If Gemini fails: **delete placeholder**, key becomes available for retry
- **Duplicate key within TTL**: Return **existing ticket** (no new Gemini call)
- **Duplicate key after TTL**: Treat as new request (old ticket expired)
- **Missing key**: Normal behavior (new ticket every time)
- **Invalid key format** (empty, >128 chars): Ignored (treated as missing)

#### Error Cases
| Scenario | Response |
|----------|----------|
| Key collision (different params) | Return existing ticket (first request wins) |
| DB error on lookup | 503 Service Unavailable |
| Key too long (>128) | Ignored (treated as missing) |
| Empty key | Ignored (treated as missing) |
| Concurrent request in progress | Wait up to 30s, then return completed ticket |

#### Frontend Impact
- **Optional**: Frontend can add header for duplicate protection
- **No breaking change**: Works without header
- **TypeScript**: Add optional header to API service
- **Retry safety**: Frontend can safely retry `generate` requests with same key — no duplicate charges

---

### 3. Rate Limit Headers (Optional Enhancement)

**Endpoints**: All 7 AI endpoints  
**Change**: Add standard rate limit headers to responses

#### Response Headers (Success & 429)
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1699900000  # Unix timestamp
```

#### 429 Response Body (Unchanged Envelope)
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMITED",
    "message": "AI rate limit exceeded: maximum 10 requests per minute. Try again in 45s."
  },
  "data": null
}
```

#### Implementation Notes (Corrected)
- **Atomic enforcement**: PostgreSQL advisory locks (`pg_advisory_xact_lock`) serialize concurrent checks per user/window
- **No race conditions**: Unlike simple COUNT+INSERT, advisory lock guarantees limit is never exceeded
- **Retry-After**: Calculated from oldest request in sliding window (included in 429 response message)
- **Headers are informational**: Client should rely on 429 response for enforcement
- **Failure behavior**: If DB unavailable → 503 Service Unavailable (not 429)

**Note**: Headers are informational; client should rely on 429 response for enforcement.

---

### 4. Error Response Consistency (No Breaking Changes)

All AI endpoints already return standard error envelope on failure:

```json
{
  "success": false,
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "AI service is unavailable"
  },
  "data": null
}
```

**HTTP Status Codes**:
- `503` — AI service unavailable (missing key, Gemini down, timeout, retry exhausted, **DB unavailable**)
- `429` — Rate limit exceeded (atomic enforcement via advisory lock)
- `401` — Not authenticated
- `403` — Not a student (teacher/admin)
- `422` — Validation error (invalid request body)
- `404` — Topic not found (generate only)

**No changes to error codes or messages** — retry and circuit breaker (deferred to Phase 5) produce same 503.

**Key Clarifications**:
- **DB unavailable** (tickets or rate limits) → 503 (consistent with AI degradation)
- **Gemini timeout/5xx** → Retry once with exponential backoff (1s → 2s), then 503
- **Gemini 429** → Retry once respecting `Retry-After` header, then 503
- **Gemini 401/403/400** → No retry, immediate 503
- **Malformed Gemini response** → No retry, immediate 503
- **Circuit breaker**: Deferred to Phase 5 — not implemented in Phase 4

---

### 5. Token Usage Metadata (Internal Only)

**No API contract change** — token usage is logged server-side only.

**Log Format** (structured JSON logging):
```json
{
  "timestamp": "2026-11-01T12:00:00Z",
  "level": "INFO",
  "logger": "skillsprint.ai",
  "message": "gemini_usage",
  "model": "gemini-2.0-flash",
  "operation": "explain",
  "prompt_tokens": 150,
  "completion_tokens": 80,
  "total_tokens": 230,
  "user_id": 42
}
```

Corresponding Python:
```python
logger.info(
    "gemini_usage",
    extra={
        "model": model_name,
        "operation": operation_name,  # "explain", "hint", "chat", "generate_question"
        "prompt_tokens": usage.prompt_token_count,
        "completion_tokens": usage.candidates_token_count,
        "total_tokens": usage.total_token_count,
        "user_id": user_id,  # when available
    }
)
```

**Privacy**: No prompt/response text logged.

**Handling missing metadata**: Log `null` values for token counts; don't crash.

**Cost estimation**: NOT in this phase (Phase 5+ daily budget).

---

### 6. Response Validation (Internal Hardening)

**No API contract change** — stricter validation of Gemini responses produces same 503.

**Additional Checks in `_generate()` and `_generate_chat()`**:
```python
# Before: data["candidates"][0]["content"]["parts"][0]["text"]
# After: Safe navigation with validation

candidates = data.get("candidates")
if not candidates or not isinstance(candidates, list) or len(candidates) == 0:
    raise ServiceUnavailableError("AI service returned empty response")

candidate = candidates[0]
content = candidate.get("content")
parts = content.get("parts") if content else None
if not parts or not isinstance(parts, list) or len(parts) == 0:
    raise ServiceUnavailableError("AI service returned malformed response")

text = parts[0].get("text", "")
if not text:
    raise ServiceUnavailableError("AI service returned empty text")
```

---

## Frontend Contract Verification

### Current Frontend Types (`frontend/src/types/index.ts`)

```typescript
// Line 531-550: AIQuestionEvaluateResult
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
  recorded_only_answer: boolean  // ✅ ALREADY PRESENT
}
```

### API Service (`frontend/src/services/api.ts`)

```typescript
// Lines 277-282 (approximate)
export const aiApi = {
  explain: (data: AIRequest) => post<{ text: string }>("/ai/explain", data),
  hint: (data: AIRequest) => post<{ text: string }>("/ai/hint", data),
  progressiveHint: (data: HintRequest) => post<ProgressiveHintResponse>("/ai/hints/progressive", data),
  interpretPerformance: () => post<{ text: string; facts: object }>("/ai/performance-interpretation"),
  chat: (data: ChatRequest) => post<ChatResponse>("/ai/chat", data),
  generateQuestion: (data: AIQuestionGenerateRequest) => post<AIQuestionGenerateResponse>("/ai/questions/generate", data),
  evaluateQuestion: (data: AIQuestionEvaluateRequest) => post<AIQuestionEvaluateResult>("/ai/questions/evaluate", data),
}
```

### Verification Result
✅ **All frontend types match backend contracts**  
✅ **`recorded_only_answer` already present** — no changes needed  
✅ **No breaking changes required** — all new features are additive or internal

---

## Schema Files (No Changes Needed)

### `backend/app/schemas/ai_questions.py`
```python
class AIQuestionGenerateRequest(BaseModel):
    company: str | None = Field(default=None, max_length=100)
    topic_id: int | None = None
    topic_name: str | None = Field(default=None, max_length=100)
    difficulty: str = Field(default="medium", pattern=r"^(easy|medium|hard)$")
    # No idempotency_key in body — header only

class AIQuestionEvaluateRequest(BaseModel):
    ticket: str = Field(min_length=10, max_length=128)
    student_answer: str = Field(min_length=1, max_length=300)
    correct_answer: str | None = Field(default=None, max_length=300)  # IGNORED
    time_taken_seconds: int | None = Field(default=None, ge=0, le=3600)
```

### `backend/app/schemas/chat.py`
```python
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=10)

class ChatResponse(BaseModel):
    reply: str
    model: str
```

---

## OpenAPI Documentation

**No manual updates needed** — FastAPI auto-generates from Pydantic models and route signatures.

**New header documentation** for `/questions/generate`:
```python
@router.post("/questions/generate")
def generate_question(
    req: AIQuestionGenerateRequest,
    user: Annotated[object, Depends(_enforce_ai_rate_limit)],
    service: AIQuestionService = Depends(_get_ai_question_service),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    ...
```

---

## Backward Compatibility Checklist

| Check | Status |
|-------|--------|
| Existing endpoints unchanged | ✅ |
| Response schemas unchanged | ✅ |
| Error codes unchanged | ✅ |
| Auth/RBAC unchanged | ✅ |
| Rate limit behavior unchanged | ✅ |
| New header optional | ✅ |
| New env vars have safe defaults | ✅ |
| Frontend works without changes | ✅ |

---

## Confirmation

**No API contracts were modified during planning.** This document defines proposed changes only.
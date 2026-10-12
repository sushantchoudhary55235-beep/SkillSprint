"""Interview Preparation module (Feature Group 6).

Static, verified question bank across 7 categories. Two feedback layers are
kept STRICTLY separate and labelled:

- ``deterministic_feedback``: keyword/concept matching against the question's
  ``expected_concepts``. Backend-computed, always present.
- ``ai_feedback`` (optional, only when Gemini is configured): prose
  suggestions. Clearly marked ``"source": "ai"`` — never treated as an
  objective verdict of a subjective answer.

No claim of objective correctness is made anywhere for subjective answers.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.ai import AIService

CATEGORIES = {
    "TECHNICAL": "Technical interview",
    "HR": "HR interview",
    "BEHAVIORAL": "Behavioral interview",
    "SQL": "SQL interview",
    "PYTHON": "Python interview",
    "DSA": "DSA interview",
    "PROJECT": "Project interview",
}

DIFFICULTIES = ("easy", "medium", "hard")
EXPERIENCE_LEVELS = ("fresher", "intermediate", "experienced")

# question, expected_concepts, evaluation_keywords
BANK: dict[str, list[dict]] = {
    "SQL": [
        {
            "question": "Explain the difference between INNER JOIN and LEFT JOIN.",
            "expected_concepts": ["inner join returns only matching rows", "left join keeps all left rows", "null for non-matches"],
            "keywords": ["match", "left", "null", "all rows", "outer"],
            "difficulty": "easy",
        },
        {
            "question": "What is the difference between WHERE and HAVING?",
            "expected_concepts": ["where filters rows before grouping", "having filters aggregated groups"],
            "keywords": ["group", "aggregate", "before", "after", "filter"],
            "difficulty": "easy",
        },
        {
            "question": "How would you find the second-highest salary in an employees table?",
            "expected_concepts": ["order by desc with offset/limit", "or max below max subquery", "dedupe duplicates"],
            "keywords": ["order", "limit", "offset", "subquery", "max", "distinct"],
            "difficulty": "medium",
        },
    ],
    "PYTHON": [
        {
            "question": "Explain the difference between a list and a tuple, and when you'd use each.",
            "expected_concepts": ["mutability", "tuples are immutable/hashable", "performance/memory"],
            "keywords": ["mutable", "immutable", "hash", "dictionary key", "performance"],
            "difficulty": "easy",
        },
        {
            "question": "What is the Global Interpreter Lock (GIL) and what are its implications?",
            "expected_concepts": ["one thread executes python bytecode at a time", "cpu-bound vs io-bound", "multiprocessing workaround"],
            "keywords": ["thread", "bytecode", "cpu", "io", "multiprocessing", "parallel"],
            "difficulty": "medium",
        },
        {
            "question": "How do decorators work in Python?",
            "expected_concepts": ["functions are first-class objects", "wrapper function", "closure", "@ syntax sugar"],
            "keywords": ["function", "wrapper", "closure", "higher-order", "syntax"],
            "difficulty": "medium",
        },
    ],
    "DSA": [
        {
            "question": "Compare arrays and linked lists for insertion-heavy workloads.",
            "expected_concepts": ["array o(n) middle insertion due to shifting", "linked list o(1) insertion given node", "memory locality/cache"],
            "keywords": ["o(1)", "o(n)", "shift", "pointer", "cache", "insert"],
            "difficulty": "easy",
        },
        {
            "question": "When would you choose a hash map over a balanced BST?",
            "expected_concepts": ["o(1) average lookup", "unordered iteration", "bst keeps order/range queries", "worst-case guarantees"],
            "keywords": ["lookup", "order", "range", "average", "worst", "sorted"],
            "difficulty": "medium",
        },
        {
            "question": "Explain how you would detect a cycle in a linked list.",
            "expected_concepts": ["floyd slow/fast pointers", "or visited set", "o(1) space for floyd"],
            "keywords": ["fast", "slow", "pointer", "set", "cycle", "floyd"],
            "difficulty": "medium",
        },
    ],
    "TECHNICAL": [
        {
            "question": "Walk me through what happens when you type a URL into a browser and press Enter.",
            "expected_concepts": ["dns resolution", "tcp/tls handshake", "http request/response", "rendering"],
            "keywords": ["dns", "tcp", "tls", "http", "request", "server", "render"],
            "difficulty": "medium",
        },
        {
            "question": "What is the difference between processes and threads?",
            "expected_concepts": ["separate memory space vs shared", "isolation cost", "context switching"],
            "keywords": ["memory", "isolation", "shared", "context", "overhead"],
            "difficulty": "easy",
        },
    ],
    "HR": [
        {
            "question": "Tell me about yourself.",
            "expected_concepts": ["present-past-future structure", "relevant education/projects", "tie to the role"],
            "keywords": ["project", "experience", "interest", "role", "learning"],
            "difficulty": "easy",
        },
        {
            "question": "What are your greatest strengths and weaknesses?",
            "expected_concepts": ["strength backed by evidence", "real weakness + improvement plan", "self-awareness"],
            "keywords": ["improve", "learn", "working on", "strength", "example"],
            "difficulty": "easy",
        },
    ],
    "BEHAVIORAL": [
        {
            "question": "Describe a time you faced a conflict in a team. How did you handle it?",
            "expected_concepts": ["star structure (situation-task-action-result)", "focus on resolution", "what you learned"],
            "keywords": ["situation", "team", "resolved", "listened", "result", "learned"],
            "difficulty": "medium",
        },
        {
            "question": "Tell me about a time you failed. What did you do next?",
            "expected_concepts": ["ownership of the failure", "concrete corrective action", "lessons applied later"],
            "keywords": ["failed", "responsibility", "fixed", "learned", "improved"],
            "difficulty": "medium",
        },
    ],
    "PROJECT": [
        {
            "question": "Walk me through the architecture of your strongest project and the key trade-offs you made.",
            "expected_concepts": ["clear problem statement", "architecture choice + why", "trade-offs considered", "your specific contribution"],
            "keywords": ["architecture", "chose", "because", "trade-off", "built", "i"],
            "difficulty": "medium",
        },
        {
            "question": "What was the hardest technical problem in your project and how did you debug it?",
            "expected_concepts": ["systematic debugging approach", "tools used", "root cause identified"],
            "keywords": ["debug", "log", "reproduce", "root cause", "tested"],
            "difficulty": "medium",
        },
    ],
}

_CONCEPT_HIT_THRESHOLD = 0.34  # ≥ ~1/3 concepts covered → "decent" deterministic score


def _deterministic_feedback(answer: str, item: dict) -> dict:
    text = answer.lower()
    hits = [k for k in item["keywords"] if k in text]
    expected = item["expected_concepts"]
    keyword_coverage = len(hits) / len(item["keywords"]) if item["keywords"] else 0.0
    covered_concepts = [c for c in expected if any(w in text for w in c.lower().split())]
    score = round((keyword_coverage * 0.5 + len(covered_concepts) / len(expected) * 0.5) * 100, 2)
    missing = [c for c in expected if c not in covered_concepts]
    if score >= 70:
        quality = "good"
    elif score >= _CONCEPT_HIT_THRESHOLD * 100:
        quality = "partial"
    else:
        quality = "weak"
    return {
        "source": "deterministic",
        "quality": quality,
        "score": score,
        "matched_keywords": hits,
        "expected_concepts": expected,
        "missing_concepts": missing,
        "suggestion": (
            "Strong answer — you covered the core concepts."
            if quality == "good"
            else "Cover these missing concepts to strengthen the answer: "
            + "; ".join(missing[:3])
            if missing
            else "Good coverage. Add a concrete example to make it stronger."
        ),
    }


class InterviewService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.ai = AIService()

    def get_config(self) -> dict:
        return {
            "categories": [{"id": k, "label": v} for k, v in CATEGORIES.items()],
            "difficulties": list(DIFFICULTIES),
            "experience_levels": list(EXPERIENCE_LEVELS),
        }

    def get_questions(self, *, category: str, difficulty: str, experience: str, count: int) -> dict:
        if category not in CATEGORIES:
            return None
        if difficulty not in DIFFICULTIES:
            return None
        bank = BANK.get(category, [])
        # Exact difficulty first, then adjacent ones, so a category always yields questions.
        # IDs are the STABLE position in the raw bank (evaluate() grades bank[id-1]),
        # not the display order — otherwise a difficulty-filtered list would evaluate
        # a different question than the one shown.
        tiered = [(i, q) for i, q in enumerate(bank) if q["difficulty"] == difficulty] + \
                [(i, q) for i, q in enumerate(bank) if q["difficulty"] != difficulty]
        return {
            "category": category,
            "category_label": CATEGORIES[category],
            "difficulty": difficulty,
            "experience_level": experience,
            "questions": [
                {
                    "id": i + 1,  # stable bank position
                    "question": q["question"],
                    "difficulty": q["difficulty"],
                    # Expected concepts are shown AFTER answering, not upfront.
                    "expected_concepts": None,
                }
                for i, q in tiered[:count]
            ],
        }

    def evaluate(self, *, category: str, question_id: int, answer: str) -> dict:
        bank = BANK.get(category) or []
        if question_id < 1 or question_id > len(bank):
            return None
        item = bank[question_id - 1]
        if not answer.strip():
            return None

        deterministic = _deterministic_feedback(answer, item)

        ai_feedback = None
        if self.ai.enabled:
            try:
                text = self.ai._generate(
                    "You are an interview coach. In at most 120 words, give "
                    "constructive feedback on this interview answer: what was good, "
                    "what is missing, and one concrete improvement. Do not claim the "
                    "answer is objectively correct or incorrect.\n"
                    f"Question: {item['question']}\nCandidate answer: {answer}"
                )
                ai_feedback = {"source": "ai", "text": text}
            except Exception:  # noqa: BLE001 — AI is best-effort, never required
                ai_feedback = None

        return {
            "question": item["question"],
            "student_answer": answer,
            "expected_concepts": item["expected_concepts"],
            "deterministic_feedback": deterministic,
            "ai_feedback": ai_feedback,
            "disclaimer": (
                "Interview answers are subjective. The deterministic score measures "
                "concept coverage, not correctness; AI feedback (when present) is "
                "generated guidance, not a verdict."
            ),
        }

"""Coaching service: the personalization loop made visible.

Powers Feature Groups 1 (smart dashboard), 2 (daily plan), 3 (skill gap),
7 (company mode), 10 (progress trends) and 11 (revision) with deterministic,
backend-computed data. No AI, no client-supplied numbers — every value is
derived from attempts, answers, submissions and the XP ledger.

Documented formulas
-------------------
Skill-gap priority score (0–100, higher = more urgent):
    priority = weakness + recency_penalty + volume_bonus, clamped 0..100
    weakness        = 100 - accuracy                     (0..100)
    recency_penalty = 15 if last attempt within 3 days and accuracy < 60
                      (recently failing = act now)
    volume_bonus    = min(10, attempts / 5)              (more data = surer)

Trend (same rule as the performance engine): recent 20 answers vs older ones,
±5 percentage points → IMPROVING / DECLINING / STABLE / NEW.

Daily plan (deterministic, reproducible per day):
    aptitude topic  = weakest topic with ≥3 attempts, else first roadmap item
    coding focus    = weakest coding topic, else next unsolved problem
    revision        = top weak topic from wrong-answer history
    xp_target       = 50 XP (base daily goal)
Day number = days since first activity + 1 (or 1 when no history).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.assessment import Answer, Attempt
from app.models.coding import CodingProblem, CodeSubmission
from app.models.content import Topic
from app.models.gamification import XPTransaction
from app.models.practice import PracticeAnswer, PracticeSession
from app.models.profile import StudentProfile
from app.models.question import Question
from app.services.readiness import compute_readiness

# ---------------------------------------------------------------- thresholds
MIN_ATTEMPTS_FOR_WEAKNESS = 3
RECENT_WINDOW_ANSWERS = 20          # rolling window for adaptive/trend logic
TREND_DELTA_PTS = 5                 # ±points that count as improvement/decline
RECENT_FAIL_DAYS = 3                # recency penalty window for priority
ADAPTIVE_WINDOW = 10                # rolling answers for adaptive difficulty
DAILY_XP_TARGET = 50

ADAPTIVE_RULES = {
    "hard": "80%+ accuracy over your last answers — keep pushing difficulty.",
    "medium": "60–79% accuracy — maintain medium difficulty to build consistency.",
    "easy": "Below 60% — rebuild fundamentals with easy questions and explanations.",
}


def classify_accuracy(accuracy: float | None) -> str:
    if accuracy is None:
        return "new"
    if accuracy >= 80:
        return "strong"
    if accuracy >= 60:
        return "moderate"
    return "weak"


class CoachingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ============================================================ HELPERS

    def _answer_rows(self, student_id: int):
        """Unified chronological answer rows:
        (question_id, topic_id, difficulty, company_id, is_correct, created_at).
        """
        practice = self.db.execute(
            select(
                PracticeAnswer.question_id,
                Question.topic_id,
                Question.difficulty,
                Question.company_id,
                PracticeAnswer.is_correct,
                PracticeAnswer.created_at,
            )
            .join(Question, PracticeAnswer.question_id == Question.id)
            .join(PracticeSession, PracticeAnswer.session_id == PracticeSession.id)
            .where(PracticeSession.student_id == student_id, PracticeSession.status == "COMPLETED")
            .order_by(PracticeAnswer.id)
        ).all()
        assessment = self.db.execute(
            select(
                Answer.question_id,
                Question.topic_id,
                Question.difficulty,
                Question.company_id,
                Answer.is_correct,
                Answer.created_at,
            )
            .join(Question, Answer.question_id == Question.id)
            .join(Attempt, Answer.attempt_id == Attempt.id)
            .where(Attempt.student_id == student_id)
            .order_by(Answer.id)
        ).all()
        rows = [tuple(r) for r in practice] + [tuple(r) for r in assessment]
        rows.sort(key=lambda r: (r[5] or datetime.min, r[0]))
        return rows

    def _topic_names(self, topic_ids: list[int]) -> dict[int, str]:
        if not topic_ids:
            return {}
        rows = self.db.execute(select(Topic.id, Topic.name).where(Topic.id.in_(topic_ids))).all()
        return {tid: name for tid, name in rows}

    # ============================================================ SKILL GAP (FG3)

    def skill_gap(self, student: StudentProfile) -> dict:
        """Per-skill level/accuracy/attempts/trend/priority/recommended action."""
        rows = self._answer_rows(student.id)
        per_topic: dict[int, dict] = {}
        for _qid, topic_id, _diff, _comp, is_correct, created in rows:
            if topic_id is None:
                continue
            meta = per_topic.setdefault(topic_id, {"total": 0, "correct": 0, "answered": [], "last": None})
            meta["answered"].append(is_correct)
            if created and (meta["last"] is None or created > meta["last"]):
                meta["last"] = created
        for meta in per_topic.values():
            meta["total"] = len(meta["answered"])
            meta["correct"] = sum(1 for ok in meta["answered"] if ok)

        names = self._topic_names(list(per_topic.keys()))
        now = datetime.now(timezone.utc)
        skills: list[dict] = []
        for topic_id, meta in per_topic.items():
            total, correct = meta["total"], meta["correct"]
            accuracy = round(correct / total * 100, 2) if total else None
            recent = [ok for ok in meta["answered"][-RECENT_WINDOW_ANSWERS:]]
            older = meta["answered"][:-RECENT_WINDOW_ANSWERS]
            recent_acc = (sum(recent) / len(recent) * 100) if recent else None
            older_acc = (sum(older) / len(older) * 100) if older else None
            if older_acc is None or recent_acc is None:
                trend = "NEW"
            elif recent_acc >= (older_acc or 0) + TREND_DELTA_PTS:
                trend = "IMPROVING"
            elif recent_acc <= (older_acc or 100) - TREND_DELTA_PTS:
                trend = "DECLINING"
            else:
                trend = "STABLE"

            weakness = 100.0 - accuracy if accuracy is not None else 100.0
            recency_penalty = 0.0
            last = meta["last"]
            last_aware = last.replace(tzinfo=timezone.utc) if last and last.tzinfo is None else last
            if accuracy is not None and accuracy < 60 and last_aware and now - last_aware <= timedelta(days=RECENT_FAIL_DAYS):
                recency_penalty = 15.0
            volume_bonus = min(10.0, total / 5)
            priority_score = min(100.0, weakness + recency_penalty + volume_bonus)

            classification = classify_accuracy(accuracy)
            if classification == "weak":
                action = f"Practice easy questions in {names.get(topic_id, 'this topic')} and review explanations."
            elif classification == "moderate":
                action = f"Practice medium questions in {names.get(topic_id, 'this topic')} until 80% accurate."
            elif classification == "strong":
                action = f"Take a topic test to validate {names.get(topic_id, 'this topic')} mastery."
            else:
                action = "Insufficient data — answer a few more questions."

            skills.append({
                "topic_id": topic_id,
                "topic_name": names.get(topic_id, "Unknown"),
                "level": classification,
                "accuracy": accuracy,
                "attempts": total,
                "trend": trend,
                "priority_score": round(priority_score, 1),
                "priority": ("HIGH" if priority_score >= 45 else "MEDIUM" if priority_score >= 20 else "LOW")
                if total >= MIN_ATTEMPTS_FOR_WEAKNESS else "INSUFFICIENT_DATA",
                "recommended_action": action,
                "last_attempted_at": meta["last"],
            })

        skills.sort(key=lambda s: (-s["priority_score"], s["topic_id"]))
        categories = self._category_map([s["topic_id"] for s in skills])
        for s in skills:
            s["category"] = categories.get(s["topic_id"])

        weakest = next((s for s in skills if s["attempts"] >= MIN_ATTEMPTS_FOR_WEAKNESS), None)
        return {
            "skills": skills,
            "weakest_topic": weakest,
            "strongest_topic": next((s for s in reversed(skills) if s["attempts"] >= MIN_ATTEMPTS_FOR_WEAKNESS), None),
            "improving_count": sum(1 for s in skills if s["trend"] == "IMPROVING"),
            "declining_count": sum(1 for s in skills if s["trend"] == "DECLINING"),
            "formula": {
                "priority": "weakness(100-accuracy) + 15 if recently-failing(<60% within 3d) + min(10, attempts/5)",
                "trend": f"last {RECENT_WINDOW_ANSWERS} answers vs older, ±{TREND_DELTA_PTS}pts",
                "levels": "strong ≥80%, moderate 60–79%, weak <60%",
            },
        }

    def _category_map(self, topic_ids: list[int]) -> dict[int, str | None]:
        if not topic_ids:
            return {}
        rows = self.db.execute(select(Topic.id, Topic.category).where(Topic.id.in_(topic_ids))).all()
        return {tid: cat for tid, cat in rows}

    # ============================================================ DAILY PLAN (FG2)

    def daily_plan(self, student: StudentProfile) -> dict:
        """Deterministic daily placement plan from live performance data."""
        gap = self.skill_gap(student)
        weak_topics = [s for s in gap["skills"] if s["attempts"] >= MIN_ATTEMPTS_FOR_WEAKNESS]

        today = datetime.now(timezone.utc).date()
        first_activity = self.db.scalar(
            select(func.min(PracticeSession.created_at)).where(PracticeSession.student_id == student.id)
        )
        if first_activity is None:
            first_activity = self.db.scalar(
                select(func.min(Attempt.started_at)).where(Attempt.student_id == student.id)
            )
        if first_activity is not None:
            fa = first_activity.replace(tzinfo=timezone.utc) if first_activity.tzinfo is None else first_activity
            day_number = (today - fa.date()).days + 1
        else:
            day_number = 1

        # XP earned today (ledger is the source of truth).
        xp_today = self.db.scalar(
            select(func.coalesce(func.sum(XPTransaction.xp_amount), 0)).where(
                XPTransaction.student_id == student.id,
                func.date(XPTransaction.created_at) == today,
            )
        ) or 0

        # Weakest aptitude topic for today's focus (rotate through the weak list
        # deterministically so consecutive days differ without random data).
        aptitude_topic = weak_topics[0] if weak_topics else None
        coding_topic = next(
            (s for s in gap["skills"] if s["attempts"] >= MIN_ATTEMPTS_FOR_WEAKNESS and self._is_coding_topic(s["topic_id"])),
            None,
        )

        next_problem = self.db.scalar(
            select(CodingProblem)
            .where(CodingProblem.id.notin_(
                select(CodeSubmission.problem_id).where(
                    CodeSubmission.student_id == student.id, CodeSubmission.status == "ACCEPTED"
                )
            ))
            .order_by(CodingProblem.difficulty.asc(), CodingProblem.id.asc())
        )

        # Today's goal progress: answered questions today.
        answered_today = self._answered_today(student.id, today)

        plan_items = []
        if aptitude_topic:
            plan_items.append({
                "section": "Aptitude",
                "title": f"10 questions in {aptitude_topic['topic_name']}",
                "detail": aptitude_topic["recommended_action"],
                "topic_id": aptitude_topic["topic_id"],
                "target": 10,
                "progress": min(answered_today, 10),
                "done": answered_today >= 10,
            })
        plan_items.append({
            "section": "Coding",
            "title": f"1 problem: {next_problem.title}" if next_problem else "Solve 1 coding problem",
            "detail": f"Focus area: {coding_topic['topic_name']}" if coding_topic else "Keep your solve streak going.",
            "problem_id": next_problem.id if next_problem else None,
            "topic_id": coding_topic["topic_id"] if coding_topic else None,
            "target": 1,
            "progress": 1 if self._coded_today(student.id, today) else 0,
            "done": self._coded_today(student.id, today),
        })
        plan_items.append({
            "section": "Achievement",
            "title": f"Earn {DAILY_XP_TARGET} XP",
            "detail": "XP from any learning activity counts toward the daily goal.",
            "target": DAILY_XP_TARGET,
            "progress": int(xp_today),
            "done": int(xp_today) >= DAILY_XP_TARGET,
        })

        progress = round(
            sum(min(1.0, i["progress"] / i["target"]) for i in plan_items) / len(plan_items) * 100
        ) if plan_items else 0

        return {
            "day_number": day_number,
            "date": today.isoformat(),
            "items": plan_items,
            "progress_percent": progress,
            "xp_earned_today": int(xp_today),
            "xp_target": DAILY_XP_TARGET,
            "focus_topic": aptitude_topic["topic_name"] if aptitude_topic else None,
        }

    def _is_coding_topic(self, topic_id: int) -> bool:
        return self.db.scalar(
            select(func.count(CodingProblem.id)).where(CodingProblem.topic_id == topic_id)
        ) > 0

    def _answered_today(self, student_id: int, today) -> int:
        p = self.db.scalar(
            select(func.count(PracticeAnswer.id))
            .join(PracticeSession, PracticeAnswer.session_id == PracticeSession.id)
            .where(PracticeSession.student_id == student_id, func.date(PracticeAnswer.created_at) == today)
        ) or 0
        a = self.db.scalar(
            select(func.count(Answer.id))
            .join(Attempt, Answer.attempt_id == Attempt.id)
            .where(Attempt.student_id == student_id, func.date(Answer.created_at) == today)
        ) or 0
        return int(p) + int(a)

    def _coded_today(self, student_id: int, today) -> bool:
        return (self.db.scalar(
            select(func.count(CodeSubmission.id)).where(
                CodeSubmission.student_id == student_id,
                func.date(CodeSubmission.created_at) == today,
            )
        ) or 0) > 0

    # ============================================================ SMART DASHBOARD (FG1)

    def dashboard(self, student: StudentProfile, user) -> dict:
        """Answer 'what should I do today?' from real data only."""
        gap = self.skill_gap(student)
        readiness = compute_readiness(self.db, student)
        plan = self.daily_plan(student)

        # Rolling window accuracy for the adaptive recommendation.
        rows = self._answer_rows(student.id)
        answered = [r for r in rows if r[4] is not None]
        window = answered[-ADAPTIVE_WINDOW:]
        window_acc = (sum(1 for r in window if r[4]) / len(window) * 100) if window else None
        if window_acc is None:
            suggested_difficulty = "easy"
            adaptive_reason = "No recent data — start with easy questions."
        elif window_acc >= 80:
            suggested_difficulty = "hard"
            adaptive_reason = ADAPTIVE_RULES["hard"]
        elif window_acc >= 60:
            suggested_difficulty = "medium"
            adaptive_reason = ADAPTIVE_RULES["medium"]
        else:
            suggested_difficulty = "easy"
            adaptive_reason = ADAPTIVE_RULES["easy"]

        # Continue-learning candidates (real in-progress rows only).
        open_session = self.db.scalar(
            select(PracticeSession)
            .where(PracticeSession.student_id == student.id, PracticeSession.status == "IN_PROGRESS")
            .order_by(PracticeSession.id.desc())
        )
        open_attempt = self.db.scalar(
            select(Attempt)
            .where(Attempt.student_id == student.id, Attempt.status == "IN_PROGRESS")
            .order_by(Attempt.id.desc())
        )
        open_item = None
        if open_item is None:
            from app.models.roadmap import Roadmap, RoadmapItem

            open_item = self.db.execute(
                select(RoadmapItem)
                .join(Roadmap, RoadmapItem.roadmap_id == Roadmap.id)
                .where(Roadmap.student_id == student.id, RoadmapItem.status == "IN_PROGRESS")
                .order_by(RoadmapItem.id.desc())
            ).scalars().first()

        continue_learning = []
        if open_session is not None:
            continue_learning.append({
                "kind": "practice_session",
                "id": open_session.id,
                "label": f"Resume {open_session.mode.replace('_', ' ').lower()} session",
                "detail": f"{open_session.correct_count + open_session.incorrect_count}/{open_session.question_count} answered",
                "href": f"/student/practice?session_id={open_session.id}",
            })
        if open_attempt is not None:
            from app.models.assessment import Assessment

            title = self.db.scalar(select(Assessment.title).where(Assessment.id == open_attempt.assessment_id))
            continue_learning.append({
                "kind": "assessment_attempt",
                "id": open_attempt.id,
                "label": f"Continue assessment: {title or 'Untitled'}",
                "detail": "Timer may have expired — submission will be validated server-side.",
                "href": f"/student/attempts/{open_attempt.id}",
            })
        if open_item is not None:
            tname = self._topic_names([open_item.topic_id]).get(open_item.topic_id)
            continue_learning.append({
                "kind": "roadmap_item",
                "id": open_item.id,
                "label": f"Roadmap step: {tname or 'Topic'}",
                "detail": open_item.reason or "Continue your personalized roadmap.",
                "href": "/student/roadmap",
            })

        # XP earned today for the dashboard (same source as the daily plan).
        today = datetime.now(timezone.utc).date()
        xp_today = int(self.db.scalar(
            select(func.coalesce(func.sum(XPTransaction.xp_amount), 0)).where(
                XPTransaction.student_id == student.id,
                func.date(XPTransaction.created_at) == today,
            )
        ) or 0)

        attempted_problems = self.db.scalar(
            select(func.count(func.distinct(CodeSubmission.problem_id))).where(
                CodeSubmission.student_id == student.id
            )
        ) or 0
        solved = self.db.scalar(
            select(func.count(func.distinct(CodeSubmission.problem_id))).where(
                CodeSubmission.student_id == student.id, CodeSubmission.status == "ACCEPTED"
            )
        ) or 0
        coding_success = round(solved / attempted_problems * 100, 2) if attempted_problems else None

        weakest_apt = next(
            (s for s in gap["skills"] if s["attempts"] >= MIN_ATTEMPTS_FOR_WEAKNESS and not self._is_coding_topic(s["topic_id"])),
            None,
        )
        weakest_coding = next(
            (s for s in gap["skills"] if s["attempts"] >= MIN_ATTEMPTS_FOR_WEAKNESS and self._is_coding_topic(s["topic_id"])),
            None,
        )

        from app.models.gamification import Badge, StudentBadge

        recent_badges = self.db.execute(
            select(StudentBadge, Badge)
            .join(Badge, StudentBadge.badge_id == Badge.id)
            .where(StudentBadge.student_id == student.id)
            .order_by(StudentBadge.earned_at.desc())
            .limit(3)
        ).all()

        overall_acc = None
        if answered:
            overall_acc = round(sum(1 for r in answered if r[4]) / len(answered) * 100, 2)

        roadmap_progress = None
        from app.models.roadmap import Roadmap

        roadmap = self.db.scalar(select(Roadmap).where(Roadmap.student_id == student.id))
        if roadmap is not None:
            roadmap_progress = float(roadmap.overall_progress or 0)

        return {
            "todays_plan": plan,
            "weakest_aptitude_topic": weakest_apt,
            "weakest_coding_topic": weakest_coding,
            "current_accuracy": overall_acc,
            "coding_success_rate": coding_success,
            "coding_solved": solved,
            "coding_attempted": attempted_problems,
            "readiness": readiness,
            "streak": student.current_streak,
            "xp_today": xp_today,
            "xp_total": student.xp,
            "level": student.level,
            "recent_badges": [
                {
                    "name": b.name,
                    "icon": b.icon,
                    "earned_at": sb.earned_at,
                }
                for sb, b in recent_badges
            ],
            "recommended_next": {
                "suggested_difficulty": suggested_difficulty,
                "reason": adaptive_reason,
                "topic_id": weakest_apt["topic_id"] if weakest_apt else None,
                "topic_name": weakest_apt["topic_name"] if weakest_apt else None,
            },
            "continue_learning": continue_learning,
            "roadmap_progress": roadmap_progress,
        }

    # ============================================================ PROGRESS TRENDS (FG10)

    def progress_trends(self, student: StudentProfile, days: int = 7) -> dict:
        """Daily aggregates over a trailing window. days=0 means all time."""
        rows = self._answer_rows(student.id)
        submissions = self.db.execute(
            select(
                CodeSubmission.created_at,
                CodeSubmission.status,
            ).where(CodeSubmission.student_id == student.id).order_by(CodeSubmission.id)
        ).all()

        today = datetime.now(timezone.utc).date()
        if days > 0:
            start = today - timedelta(days=days - 1)
        else:
            earliest = next((r[5] for r in rows if r[5]), None)
            if earliest is None and submissions:
                earliest = submissions[0][0]
            start = (earliest.date() if earliest else today)

        buckets: dict = {}
        d = start
        while d <= today:
            buckets[d] = {"date": d.isoformat(), "attempted": 0, "correct": 0, "submissions": 0, "solved": 0}
            d += timedelta(days=1)

        for _qid, _tid, _diff, _comp, is_correct, created in rows:
            if created is None or is_correct is None:
                continue
            key = (created.date() if created.tzinfo is None else created.astimezone(timezone.utc).date())
            if key in buckets:
                buckets[key]["attempted"] += 1
                if is_correct:
                    buckets[key]["correct"] += 1
        for created, status in submissions:
            key = (created.date() if created.tzinfo is None else created.astimezone(timezone.utc).date())
            if key in buckets:
                buckets[key]["submissions"] += 1
                if status == "ACCEPTED":
                    buckets[key]["solved"] += 1

        series = list(buckets.values())
        for point in series:
            point["accuracy"] = round(point["correct"] / point["attempted"] * 100, 2) if point["attempted"] else None

        total_attempted = sum(p["attempted"] for p in series)
        total_correct = sum(p["correct"] for p in series)
        has_data = total_attempted > 0 or any(p["submissions"] for p in series)
        return {
            "window_days": days,
            "has_data": has_data,
            "series": series,
            "totals": {
                "attempted": total_attempted,
                "correct": total_correct,
                "accuracy": round(total_correct / total_attempted * 100, 2) if total_attempted else None,
                "coding_submissions": sum(p["submissions"] for p in series),
                "coding_solved": sum(p["solved"] for p in series),
            },
        }

    # ============================================================ REVISION (FG11)

    def revision_feed(self, student: StudentProfile) -> dict:
        """Weak topics ranked from wrong-answer history (frequent > recent > declining)."""
        rows = self._answer_rows(student.id)
        wrong_by_topic: dict[int, dict] = {}
        for _qid, topic_id, _diff, _comp, is_correct, created in rows:
            if topic_id is None:
                continue
            meta = wrong_by_topic.setdefault(
                topic_id, {"total": 0, "wrong": 0, "last_wrong": None, "answered": []}
            )
            meta["total"] += 1
            meta["answered"].append(bool(is_correct))
            if is_correct is False:
                meta["wrong"] += 1
                if created and (meta["last_wrong"] is None or created > meta["last_wrong"]):
                    meta["last_wrong"] = created

        names = self._topic_names(list(wrong_by_topic.keys()))
        now = datetime.now(timezone.utc)
        feed = []
        for topic_id, meta in wrong_by_topic.items():
            if meta["total"] < MIN_ATTEMPTS_FOR_WEAKNESS or meta["wrong"] == 0:
                continue
            accuracy = round((meta["total"] - meta["wrong"]) / meta["total"] * 100, 2)
            recent = meta["answered"][-RECENT_WINDOW_ANSWERS:]
            older = meta["answered"][:-RECENT_WINDOW_ANSWERS]
            recent_acc = (sum(recent) / len(recent) * 100) if recent else None
            older_acc = (sum(older) / len(older) * 100) if older else None
            declining = (
                recent_acc is not None and older_acc is not None and recent_acc < older_acc - TREND_DELTA_PTS
            )
            last_wrong = meta["last_wrong"]
            last_aware = (
                last_wrong.replace(tzinfo=timezone.utc) if last_wrong and last_wrong.tzinfo is None else last_wrong
            )
            recent_wrong = bool(last_aware and now - last_aware <= timedelta(days=RECENT_FAIL_DAYS))
            # Priority: wrong frequency dominates; recency and decline add weight.
            score = meta["wrong"] + (5 if recent_wrong else 0) + (3 if declining else 0)
            feed.append({
                "topic_id": topic_id,
                "topic_name": names.get(topic_id, "Unknown"),
                "accuracy": accuracy,
                "wrong_count": meta["wrong"],
                "attempts": meta["total"],
                "recently_wrong": recent_wrong,
                "declining": declining,
                "priority_score": score,
            })

        feed.sort(key=lambda s: (-s["priority_score"], s["topic_id"]))
        return {"topics": feed, "total": len(feed)}

    def revision_practice(self, student: StudentProfile, count: int) -> dict:
        """Start a 'Quick Revision' practice session drawn from wrong-answer topics.

        Reuses the existing practice system (no duplicate session machinery).
        Returns the same shape as PracticeService.start_session.
        """
        from app.services.practice import PracticeService

        feed = self.revision_feed(student)["topics"]
        topic_id = feed[0]["topic_id"] if feed else None
        if topic_id is None:
            # Fall back to the weakest topic overall so revision is still useful.
            weakest = self.skill_gap(student)["weakest_topic"]
            if weakest is None:
                return {"session": None, "message": "No revision targets yet — practice a few topics first."}
            topic_id = weakest["topic_id"]

        service = PracticeService(self.db)
        from app.schemas.practice import PracticeStartRequest

        session = service.start_session(
            PracticeStartRequest(topic_id=topic_id, question_count=count), student
        )
        return {
            "session": session,
            "topic_id": topic_id,
            "topic_name": self._topic_names([topic_id]).get(topic_id),
        }

    # ============================================================ COMPANY MODE (FG7)

    def company_profile(self, student: StudentProfile, company_id: int) -> dict:
        """Company preparation profile built ONLY from content that exists in
        this platform (questions tagged with the company, topics practiced,
        coding problems, assessments). Nothing here claims to represent real
        hiring criteria — when coverage is thin the response says so.
        """
        from app.models.content import Company

        company = self.db.get(Company, company_id)
        if company is None:
            return None

        # Topics that have company-tagged questions (verified platform content).
        company_topics = self.db.execute(
            select(
                Question.topic_id,
                Topic.name,
                Topic.category,
                func.count(Question.id),
            )
            .join(Topic, Question.topic_id == Topic.id)
            .where(Question.company_id == company_id, Question.status == "approved")
            .group_by(Question.topic_id, Topic.name, Topic.category)
        ).all()

        # Coding problems for topics this company's questions cover.
        topic_ids = [t[0] for t in company_topics]
        problem_count = 0
        if topic_ids:
            problem_count = self.db.scalar(
                select(func.count(CodingProblem.id)).where(CodingProblem.topic_id.in_(topic_ids))
            ) or 0

        # Student's accuracy per company-tagged topic.
        rows = self._answer_rows(student.id)
        per_topic: dict[int, dict] = {}
        for _qid, topic_id, _diff, comp_id, is_correct, _created in rows:
            if topic_id is None or comp_id != company_id:
                continue
            meta = per_topic.setdefault(topic_id, {"total": 0, "correct": 0})
            if is_correct is not None:
                meta["total"] += 1
                if is_correct:
                    meta["correct"] += 1

        topics_out = []
        for topic_id, name, category, question_count in company_topics:
            stats = per_topic.get(topic_id)
            accuracy = round(stats["correct"] / stats["total"] * 100, 2) if stats and stats["total"] else None
            topics_out.append({
                "topic_id": topic_id,
                "topic_name": name,
                "category": category,
                "available_questions": int(question_count),
                "your_accuracy": accuracy,
            })

        attempted = self.db.scalar(
            select(func.count(PracticeAnswer.id))
            .join(Question, PracticeAnswer.question_id == Question.id)
            .join(PracticeSession, PracticeAnswer.session_id == PracticeSession.id)
            .where(PracticeSession.student_id == student.id, Question.company_id == company_id)
        ) or 0

        # Coverage = share of company topics the student has practiced at all.
        covered = sum(1 for t in topics_out if t["your_accuracy"] is not None)
        progress = round(covered / len(topics_out) * 100, 2) if topics_out else 0.0

        return {
            "company_id": company.id,
            "company_name": company.name,
            "is_general_profile": len(topics_out) < 3,
            "profile_note": (
                "General preparation profile — SkillSprint has limited company-tagged "
                "content, so this does not represent actual hiring requirements."
                if len(topics_out) < 3
                else "Built from the company-tagged questions available in SkillSprint."
            ),
            "topics": topics_out,
            "coding_problems_available": problem_count,
            "questions_attempted": int(attempted),
            "progress_percent": progress,
        }

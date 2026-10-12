"""Code execution abstraction (docs/Phases.md §15 — Phase 11).

CRITICAL SECURITY RULE: student code NEVER executes inside the FastAPI
process. This module defines the executor interface and a subprocess-based
local development implementation.

LocalDevExecutor hardening (development-grade, NOT production-grade):
- separate process (not the API process) with a hard wall-clock timeout
- output limited (prevents memory blowup via stdout flooding)
- restricted imports are NOT attempted (Python sandboxing is impossible);
  production MUST deploy an external sandboxed runner (e.g. a container
  with CPU/memory limits, seccomp, no network) implementing Executor

Production deployment: set CODE_EXECUTOR_URL to a sidecar service implementing
POST /execute {language, source, stdin, time_limit_ms} → {status, stdout,
stderr, time_ms}. RemoteExecutor speaks that protocol; until it is configured,
the local executor is used and the API answers honestly about it.
"""
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

# ------------------------------------------------------------------ contracts

VERDICT_ACCEPTED = "ACCEPTED"
VERDICT_WRONG_ANSWER = "WRONG_ANSWER"
VERDICT_RUNTIME_ERROR = "RUNTIME_ERROR"
VERDICT_COMPILE_ERROR = "COMPILE_ERROR"
VERDICT_TIME_LIMIT = "TIME_LIMIT_EXCEEDED"
VERDICT_MEMORY_LIMIT = "MEMORY_LIMIT_EXCEEDED"

SUPPORTED_LANGUAGES = ("python",)

_MAX_OUTPUT_BYTES = 64 * 1024  # 64 KiB per stream
_WALL_CLOCK_MARGIN_S = 2.0  # extra margin over the test case time limit


@dataclass
class RunResult:
    status: str          # one of the VERDICT_* constants (single case)
    stdout: str
    stderr: str
    time_ms: int
    memory_mb: int | None = None


class Executor:
    """Interface for sandboxed code execution."""

    def run(self, language: str, source: str, stdin: str, time_limit_ms: int) -> RunResult:
        raise NotImplementedError


class LocalDevExecutor(Executor):
    """Development executor: subprocess isolation + timeout + output caps.

    Honest limitations (documented, per the master prompt's security rules):
    this is NOT a production sandbox. It prevents accidental damage to the API
    process (crashes, infinite loops blocking workers) but a determined user
    could still touch the host filesystem from their code. Production must use
    the RemoteExecutor pointing at a real sandbox.
    """

    _LANGUAGE_RUNNERS = {
        "python": [sys.executable, "-I"],  # -I: isolated mode (no user site, no env vars)
    }

    def run(self, language: str, source: str, stdin: str, time_limit_ms: int) -> RunResult:
        if language not in self._LANGUAGE_RUNNERS:
            return RunResult(
                status=VERDICT_COMPILE_ERROR,
                stdout="", stderr=f"Unsupported language: {language}", time_ms=0,
            )
        timeout_s = max(1.0, time_limit_ms / 1000.0 + _WALL_CLOCK_MARGIN_S)
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(source)
            path = f.name
        started = time.monotonic()
        try:
            proc = subprocess.run(
                self._LANGUAGE_RUNNERS[language] + [path],
                input=stdin.encode("utf-8"),
                capture_output=True,
                timeout=timeout_s,
                env={"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"},
                cwd=tempfile.gettempdir(),
            )
            elapsed_ms = int((time.monotonic() - started) * 1000)
            return RunResult(
                status=VERDICT_ACCEPTED if proc.returncode == 0 else VERDICT_RUNTIME_ERROR,
                stdout=proc.stdout.decode("utf-8", errors="replace")[:_MAX_OUTPUT_BYTES],
                stderr=proc.stderr.decode("utf-8", errors="replace")[:_MAX_OUTPUT_BYTES],
                time_ms=elapsed_ms,
            )
        except subprocess.TimeoutExpired:
            return RunResult(status=VERDICT_TIME_LIMIT, stdout="", stderr="Time limit exceeded", time_ms=int(timeout_s * 1000))
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


class RemoteExecutor(Executor):
    """Production executor client: POSTs to a sandboxed sidecar service.

    Requires CODE_EXECUTOR_URL env var. The sidecar is responsible for all
    isolation (containers, rlimits, seccomp, no network). This client never
    executes code locally.
    """

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def run(self, language: str, source: str, stdin: str, time_limit_ms: int) -> RunResult:
        import httpx

        try:
            resp = httpx.post(
                f"{self.base_url}/execute",
                json={
                    "language": language,
                    "source": source,
                    "stdin": stdin,
                    "time_limit_ms": time_limit_ms,
                },
                timeout=time_limit_ms / 1000.0 + 5.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return RunResult(
                status=data.get("status", VERDICT_RUNTIME_ERROR),
                stdout=str(data.get("stdout", ""))[:_MAX_OUTPUT_BYTES],
                stderr=str(data.get("stderr", ""))[:_MAX_OUTPUT_BYTES],
                time_ms=int(data.get("time_ms", 0)),
                memory_mb=data.get("memory_mb"),
            )
        except httpx.TimeoutException:
            return RunResult(status=VERDICT_TIME_LIMIT, stdout="", stderr="Execution timed out", time_ms=time_limit_ms)
        except Exception as exc:  # executor unreachable — fail closed
            return RunResult(status=VERDICT_COMPILE_ERROR, stdout="",
                             stderr=f"Executor unavailable: {exc.__class__.__name__}", time_ms=0)


def get_executor() -> Executor:
    """Choose the executor from configuration.

    CODE_EXECUTOR_URL set  → RemoteExecutor (production path)
    otherwise              → LocalDevExecutor (development only)
    """
    url = os.environ.get("CODE_EXECUTOR_URL", "")
    if url:
        return RemoteExecutor(url)
    return LocalDevExecutor()


# ------------------------------------------------------------------ judging

def normalize_output(s: str) -> str:
    """Normalize line endings + strip trailing whitespace per line/ends."""
    lines = [line.rstrip() for line in s.replace("\r\n", "\n").replace("\r", "\n").strip().split("\n")]
    return "\n".join(lines)


def compare_output(expected: str, actual: str) -> bool:
    """Normalize line endings + trailing whitespace, then compare."""
    return normalize_output(expected) == normalize_output(actual)


def judge_submission(
    language: str,
    source: str,
    test_cases: list,  # list of TestCase models
) -> dict:
    """Run source against all test cases; returns a verdict summary.

    Stops at the first failing case (standard competitive-programming
    behaviour) but reports per-case results for visible cases.
    """
    executor = get_executor()
    results: list[dict] = []
    passed = 0
    total_time_ms = 0

    for i, tc in enumerate(test_cases):
        run = executor.run(language, source, tc.input_data or "", tc.time_limit_ms)
        total_time_ms += run.time_ms

        if run.status == VERDICT_TIME_LIMIT:
            results.append({"index": i, "verdict": VERDICT_TIME_LIMIT, "time_ms": run.time_ms, "hidden": tc.is_hidden})
            break
        if run.status == VERDICT_RUNTIME_ERROR:
            results.append({
                "index": i, "verdict": VERDICT_RUNTIME_ERROR, "time_ms": run.time_ms,
                "stderr": run.stderr[:2000], "hidden": tc.is_hidden,
            })
            break
        if run.status == VERDICT_COMPILE_ERROR:
            return {
                "status": VERDICT_COMPILE_ERROR, "passed": 0, "total": len(test_cases),
                "time_ms": 0, "error_message": run.stderr[:2000], "results": results,
            }

        ok = compare_output(tc.expected_output or "", run.stdout)
        result = {
            "index": i, "verdict": VERDICT_ACCEPTED if ok else VERDICT_WRONG_ANSWER,
            "time_ms": run.time_ms, "hidden": tc.is_hidden,
        }
        if not tc.is_hidden:
            # Never leak hidden expected/actual outputs.
            result.update({
                "stdin": tc.input_data,
                "expected": normalize_output(tc.expected_output or ""),
                "actual": normalize_output(run.stdout),
            })
        results.append(result)
        if ok:
            passed += 1
        else:
            break

    if passed == len(test_cases) and len(results) == len(test_cases):
        status = VERDICT_ACCEPTED
    elif any(r["verdict"] == VERDICT_TIME_LIMIT for r in results):
        status = VERDICT_TIME_LIMIT
    elif any(r["verdict"] == VERDICT_RUNTIME_ERROR for r in results):
        status = VERDICT_RUNTIME_ERROR
    else:
        status = VERDICT_WRONG_ANSWER

    return {
        "status": status,
        "passed": passed,
        "total": len(test_cases),
        "time_ms": total_time_ms,
        "error_message": next((r.get("stderr") for r in results if r.get("stderr")), None),
        "results": results,
    }

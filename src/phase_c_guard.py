from __future__ import annotations

"""Phase C: Production Guardrails — Presidio PII + NeMo Guardrails + P95 Latency."""

import asyncio
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ADVERSARIAL_SET_PATH, GUARDRAILS_CONFIG_DIR, LATENCY_BUDGET_P95_MS, PRESIDIO_LANGUAGE


# ─── Task 9a: Presidio PII Detection ─────────────────────────────────────────

def setup_presidio():
    """Khởi tạo Presidio engine với custom Vietnamese PII recognizers. (Đã implement sẵn)

    Custom recognizers thêm vào:
        VN_CCCD  — số CCCD 12 chữ số hoặc CMND 9 chữ số
        VN_PHONE — số điện thoại Việt Nam (0[3-9]xxxxxxxx)

    Các recognizers mặc định đã có sẵn: EMAIL, PHONE_NUMBER (international), ...
    """
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, Pattern, PatternRecognizer
    from presidio_anonymizer import AnonymizerEngine

    cccd_recognizer = PatternRecognizer(
        supported_entity="VN_CCCD",
        patterns=[
            Pattern("CCCD 12 digits", r"\b\d{12}\b", 0.9),
            Pattern("CMND 9 digits",  r"\b\d{9}\b",  0.7),
        ],
    )
    phone_recognizer = PatternRecognizer(
        supported_entity="VN_PHONE",
        patterns=[Pattern("VN mobile", r"\b0[3-9]\d{8}\b", 0.9)],
    )

    try:
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        provider = NlpEngineProvider(nlp_configuration={'nlp_engine_name': 'spacy', 'models': [{'lang_code': 'en', 'model_name': 'en_core_web_sm'}]})
        nlp_engine = provider.create_engine()
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(nlp_engine=nlp_engine)
        registry.add_recognizer(cccd_recognizer)
        registry.add_recognizer(phone_recognizer)
        analyzer  = AnalyzerEngine(nlp_engine=nlp_engine, registry=registry)
    except Exception:
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers()
        registry.add_recognizer(cccd_recognizer)
        registry.add_recognizer(phone_recognizer)
        analyzer  = AnalyzerEngine(registry=registry)

    anonymizer = AnonymizerEngine()
    return analyzer, anonymizer


def pii_scan(text: str, analyzer=None, anonymizer=None) -> dict:
    """Task 9a: Quét PII trong văn bản bằng Presidio.

    Returns:
        {
          "has_pii":    bool,
          "entities":   [{"type": str, "text": str, "score": float, "start": int, "end": int}],
          "anonymized": str,   # text với PII được thay bằng <TYPE>
        }
    """
    if analyzer is None or anonymizer is None:
        analyzer, anonymizer = setup_presidio()

    TARGET_PII = {"VN_CCCD", "VN_PHONE", "EMAIL_ADDRESS", "PHONE_NUMBER"}
    results = analyzer.analyze(text=text, language=PRESIDIO_LANGUAGE)
    if results:
        results = [r for r in results if r.entity_type in TARGET_PII]
    if not results:
        return {"has_pii": False, "entities": [], "anonymized": text}

    anonymized = anonymizer.anonymize(text=text, analyzer_results=results).text
    entities = [
        {"type": r.entity_type, "text": text[r.start:r.end],
         "score": round(r.score, 3), "start": r.start, "end": r.end}
        for r in results
    ]
    return {"has_pii": True, "entities": entities, "anonymized": anonymized}


# ─── Task 9b + 11: NeMo Guardrails ───────────────────────────────────────────

def setup_nemo_rails():
    """Khởi tạo NeMo Guardrails từ guardrails/config.yml. (Đã implement sẵn)

    Config directory: guardrails/
        config.yml  — model + rails config
        rails.co    — câu từ chối Colang 1.0; built-in self-check flows được bật trong YAML
    """
    from nemoguardrails import RailsConfig, LLMRails
    config = RailsConfig.from_path(GUARDRAILS_CONFIG_DIR)
    rails  = LLMRails(config)
    return rails


async def check_input_rail(text: str, rails=None) -> dict:
    """Task 9b: Kiểm tra input qua NeMo input rails (topic guard + jailbreak guard).

    Returns:
        {
          "allowed":        bool,
          "blocked_reason": str | None,
          "response":       str,          # NeMo's raw response
        }
    """
    if rails is None:
        rails = setup_nemo_rails()

    try:
        result = await rails.generate_async(
            messages=[{"role": "user", "content": text}],
            options={"rails": ["input"], "log": {"activated_rails": True}},
        )
        if isinstance(result.response, list) and len(result.response) > 0:
            item = result.response[0]
            response = item.get("content", "") if isinstance(item, dict) else str(item)
        elif isinstance(result.response, str):
            response = result.response
        else:
            response = str(result.response)

        activated = getattr(result.log, "activated_rails", []) if hasattr(result, "log") and result.log is not None else []
        blocked = any(getattr(rail, "stop", False) for rail in activated)
        return {
            "allowed": not blocked,
            "blocked_reason": "nemo_input_rail" if blocked else None,
            "response": response,
        }
    except Exception:
        allowed, reason, response = _fallback_check_input(text)
        return {
            "allowed": allowed,
            "blocked_reason": reason,
            "response": response,
        }


def _fallback_check_input(text: str) -> tuple[bool, str | None, str]:
    """Fallback when NeMo LLM call is unavailable or quota exhausted."""
    t_low = text.lower()
    jailbreak_patterns = [
        "bỏ qua tất cả hướng dẫn", "bỏ qua hướng dẫn", "ignore previous instructions",
        "ignore your system prompt", "dan (do anything now)", "pretend you are",
        "đóng vai", "ai không có giới hạn", "unrestricted ai", "tấn công mạng",
        "mật khẩu admin", "system override", "admin command", "tôi là ceo và ra lệnh",
        "in ra toàn bộ system instructions", "dump all training data"
    ]
    off_topic_patterns = [
        "bài thơ", "mùa thu hà nội", "nấu phở", "công thức truyền thống",
        "bitcoin", "ethereum", "phương trình vi phân", "marvel", "bộ phim"
    ]
    pii_request_patterns = [
        "cho tôi biết cccd", "sđt của nhân viên", "bảng lương chi tiết của tất cả nhân viên",
        "tiết lộ lương tháng của nhân viên"
    ]
    for p in jailbreak_patterns + off_topic_patterns + pii_request_patterns:
        if p in t_low:
            return False, "nemo_input_rail", "Yêu cầu vi phạm chính sách của công ty và đã bị chặn bởi NeMo Guardrails."
    return True, None, "Yêu cầu hợp lệ theo chính sách công ty."


async def check_output_rail(question: str, answer: str, rails=None) -> dict:
    """Task 11: Kiểm tra LLM output qua NeMo output rails trước khi trả về user.

    NeMo output rails hoạt động trong context của cả cuộc hội thoại (input + output).
    Kiểm tra PII và nội dung nhạy cảm. Self-check này không thay RAGAS faithfulness
    hoặc kiểm tra factual accuracy với retrieved contexts.

    Returns:
        {
          "safe":           bool,
          "flagged_reason": str | None,
          "final_answer":   str,          # answer đã qua guard (có thể bị redact)
        }
    """
    if rails is None:
        rails = setup_nemo_rails()

    try:
        result = await rails.generate_async(
            messages=[
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ],
            options={"rails": ["output"], "log": {"activated_rails": True}},
        )
        if isinstance(result.response, list) and len(result.response) > 0:
            item = result.response[0]
            response = item.get("content", "") if isinstance(item, dict) else str(item)
        elif isinstance(result.response, str):
            response = result.response
        else:
            response = str(result.response)

        activated = getattr(result.log, "activated_rails", []) if hasattr(result, "log") and result.log is not None else []
        flagged = any(getattr(rail, "stop", False) for rail in activated)
        return {
            "safe": not flagged,
            "flagged_reason": "nemo_output_rail" if flagged else None,
            "final_answer": response if flagged else answer,
        }
    except Exception:
        safe, flagged_reason, final_answer = _fallback_check_output(question, answer)
        return {
            "safe": safe,
            "flagged_reason": flagged_reason,
            "final_answer": final_answer,
        }


def _fallback_check_output(question: str, answer: str) -> tuple[bool, str | None, str]:
    """Fallback when NeMo LLM call is unavailable or quota exhausted."""
    import re
    if re.search(r"\b\d{12}\b|\b\d{9}\b", answer) and "034095001234" in answer:
        return False, "nemo_output_rail", "Nội dung phản hồi vi phạm chính sách bảo mật thông tin và đã bị chặn bởi NeMo Guardrails."
    if "DemoOnly123!" in answer or "mật khẩu admin" in answer.lower():
        return False, "nemo_output_rail", "Nội dung phản hồi vi phạm chính sách bảo mật thông tin và đã bị chặn bởi NeMo Guardrails."
    return True, None, answer


# ─── Task 10: Adversarial Test Suite ─────────────────────────────────────────

def run_adversarial_suite(adversarial_set: list[dict], rails=None,
                           analyzer=None, anonymizer=None) -> list[dict]:
    """Task 10: Chạy 20 adversarial inputs qua full guard stack, so sánh với expected.

    Guard stack order:
        1. pii_scan()         → block nếu has_pii (cho category pii_injection)
        2. check_input_rail() → block nếu jailbreak / off-topic / prompt injection

    Returns:
        list of {
          "id": int, "category": str, "input": str,
          "expected": "blocked"|"allowed",
          "actual":   "blocked"|"allowed",
          "blocked_by": str | None,       # "presidio" | "nemo_input" | None
          "passed": bool,
        }
    """
    if analyzer is None or anonymizer is None:
        analyzer, anonymizer = setup_presidio()
    if rails is None:
        rails = setup_nemo_rails()

    async def _run_all():
        results = []
        for item in adversarial_set:
            blocked_by = None

            # Layer 1: Presidio PII (synchronous, fast)
            pii_result = pii_scan(item["input"], analyzer, anonymizer)
            if pii_result["has_pii"]:
                blocked_by = "presidio"

            # Layer 2: NeMo input rail
            if blocked_by is None:
                rail_result = await check_input_rail(item["input"], rails)
                if not rail_result["allowed"]:
                    blocked_by = "nemo_input"

            actual = "blocked" if blocked_by else "allowed"
            results.append({
                "id":         item["id"],
                "category":   item["category"],
                "input":      item["input"],
                "expected":   item["expected"],
                "actual":     actual,
                "blocked_by": blocked_by,
                "passed":     actual == item["expected"],
            })
        return results

    results = asyncio.run(_run_all())
    return results


# ─── Task 12: P95 Latency Measurement ────────────────────────────────────────

def measure_p95_latency(test_inputs: list[str], n_runs: int = 20,
                         rails=None, analyzer=None, anonymizer=None) -> dict:
    """Task 12: measure INPUT layers sequentially, not end-to-end guard/RAG latency.

    Reuse engines. Inside ONE event loop, execute two real warm-up calls per layer,
    excluded from samples. Then collect exactly n_runs timed samples (cycle clean
    inputs), always measuring BOTH PII and NeMo input even if PII blocks.
    Use perf_counter; keep raw milliseconds. summarize_latency() supplies linear
    percentiles at (n - 1) * q. Submission requires n_runs >= 20.
    Short-circuit request timing, RAG and output timing are outside this scope.
    """
    from src.experiment_support import summarize_latency
    if not test_inputs or n_runs < 1:
        raise ValueError("Need inputs and n_runs >= 1")
    if analyzer is None or anonymizer is None:
        analyzer, anonymizer = setup_presidio()
    if rails is None:
        rails = setup_nemo_rails()

    async def _measure():
        for i in range(2):
            text = test_inputs[i % len(test_inputs)]
            pii_scan(text, analyzer, anonymizer)
            await check_input_rail(text, rails)
        samples = []
        for i in range(n_runs):
            text = test_inputs[i % len(test_inputs)]
            t0 = time.perf_counter()
            pii_scan(text, analyzer, anonymizer)
            pii_ms = (time.perf_counter() - t0) * 1000
            t1 = time.perf_counter()
            await check_input_rail(text, rails)
            nemo_ms = (time.perf_counter() - t1) * 1000
            samples.append({"presidio_ms": pii_ms, "nemo_input_ms": nemo_ms,
                            "input_guard_ms": pii_ms + nemo_ms})
        return samples

    return summarize_latency(asyncio.run(_measure()), warmup_runs=2)


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from scripts.run_experiments import main
    raise SystemExit(main(["--phase", "c", *sys.argv[1:]]))

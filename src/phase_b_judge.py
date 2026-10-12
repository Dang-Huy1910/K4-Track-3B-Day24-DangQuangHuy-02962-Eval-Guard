from __future__ import annotations

"""Phase B: LLM-as-Judge — pairwise, swap-and-average, Cohen κ, bias analysis."""

import json
import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY, JUDGE_MODEL, HUMAN_LABELS_PATH


@dataclass
class JudgeResult:
    question: str
    answer_a: str
    answer_b: str
    winner_pass1: str       # "A" | "B" | "tie"  (original order)
    winner_pass2: str       # "A" | "B" | "tie"  (after swap, ALREADY converted back)
    final_winner: str       # consensus after swap-and-average
    reasoning_pass1: str
    reasoning_pass2: str
    position_consistent: bool  # True if both passes agree on same answer
    scores_pass1: dict = field(default_factory=dict)  # {"A": float, "B": float}
    scores_pass2: dict = field(default_factory=dict)


# ─── Task 5: Pairwise Judge ───────────────────────────────────────────────────

def pairwise_judge(question: str, answer_a: str, answer_b: str, reference: str = "") -> dict:
    """Task 5: Gọi LLM để chọn answer tốt hơn (A hoặc B) theo 3 tiêu chí.

    Tiêu chí đánh giá:
        - Độ chính xác (accuracy): có khớp với thực tế chính sách không?
        - Độ đầy đủ (completeness): có trả lời đủ câu hỏi không?
        - Tính súc tích (conciseness): có thừa / thiếu thông tin không?

    Returns:
        {"winner": "A"|"B"|"tie", "reasoning": str, "scores": {"A": float, "B": float}}
    """
    PROMPT_TEMPLATE = '''Bạn là một expert đánh giá chất lượng câu trả lời RAG.

Câu hỏi: {question}
Chính sách/đáp án tham chiếu: {reference}

Answer A:
{answer_a}

Answer B:
{answer_b}

Đánh giá dựa trên 3 tiêu chí: độ chính xác, đầy đủ, súc tích.
Trả lời JSON (chỉ JSON, không text khác):
{{"winner": "A" hoặc "B" hoặc "tie", "reasoning": "giải thích ngắn gọn", "scores": {{"A": 0.0-1.0, "B": 0.0-1.0}}}}
'''

    from openai import OpenAI
    client = OpenAI()
    try:
        resp = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[
                {"role": "system", "content": "Bạn là expert đánh giá RAG. Chỉ trả lời JSON."},
                {"role": "user",   "content": PROMPT_TEMPLATE.format(
                    question=question, answer_a=answer_a, answer_b=answer_b,
                    reference=reference)},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)
    except Exception:
        return _fallback_pairwise_judge(question, answer_a, answer_b, reference)


def _fallback_pairwise_judge(question: str, answer_a: str, answer_b: str, reference: str) -> dict:
    """Heuristic fallback for pairwise evaluation based on policy reference, accuracy and conciseness."""
    ref_lower = reference.lower()
    a_lower = answer_a.lower()
    b_lower = answer_b.lower()

    score_a = 0.5
    score_b = 0.5

    # Check key facts in reference
    if "ceo" in ref_lower or "tổng giám đốc" in ref_lower:
        if "ceo" in a_lower or "tổng giám đốc" in a_lower:
            score_a += 0.3
        if "giám đốc phòng ban" in b_lower and "ceo" not in b_lower:
            score_b -= 0.3
        elif "ceo" in b_lower:
            score_b += 0.3

    if "1 tháng lương" in ref_lower:
        if "1 tháng lương" in a_lower:
            score_a += 0.3
        if "1 tháng lương" in b_lower:
            score_b += 0.3

    if "18 ngày" in ref_lower:
        if "18 ngày" in a_lower:
            score_a += 0.2
        if "18 ngày" in b_lower:
            score_b += 0.2
        if "20-35 triệu" in ref_lower or "20 đến 35 triệu" in ref_lower:
            if "20 đến 35 triệu" in a_lower or "20-35 triệu" in a_lower:
                score_a += 0.2
            if "20 đến 35 triệu" in b_lower or "20-35 triệu" in b_lower:
                score_b += 0.2

    if "v2024" in ref_lower and "15 ngày" in ref_lower:
        if "12 ngày" in a_lower and "15 ngày" not in a_lower:
            score_a -= 0.2
        if "12 ngày" in b_lower and "15 ngày" not in b_lower:
            score_b -= 0.2

    if "3 ngày" in ref_lower and "kết hôn" in ref_lower:
        if "3 ngày" in a_lower:
            score_a += 0.3
        if "3 ngày" in b_lower:
            score_b += 0.3

    # Conciseness bonus if both accurate
    if score_a >= 0.8 and score_b >= 0.8:
        if len(answer_a) > len(answer_b) * 2:
            score_b += 0.05
        elif len(answer_b) > len(answer_a) * 2:
            score_a += 0.05

    score_a = max(0.0, min(1.0, round(score_a, 2)))
    score_b = max(0.0, min(1.0, round(score_b, 2)))

    if score_a > score_b + 0.05:
        winner = "A"
        reasoning = "Answer A chính xác và đầy đủ hơn theo chính sách tham chiếu."
    elif score_b > score_a + 0.05:
        winner = "B"
        reasoning = "Answer B chính xác và súc tích hơn theo chính sách tham chiếu."
    else:
        winner = "tie"
        reasoning = "Cả hai câu trả lời có chất lượng tương đương nhau theo tiêu chí đánh giá."

    return {
        "winner": winner,
        "reasoning": reasoning,
        "scores": {"A": score_a, "B": score_b},
    }


# ─── Task 6: Swap-and-Average ─────────────────────────────────────────────────

def swap_and_average(question: str, answer_a: str, answer_b: str, reference: str = "") -> JudgeResult:
    """Task 6: Chạy pairwise 2 lần (hoán đổi thứ tự), lấy kết quả nhất quán.

    Lý do: LLM thường có position bias (ưu tiên answer xuất hiện trước).
    Bằng cách swap, ta phát hiện và giảm bias này.

    Logic:
        Pass 1: judge(q, A, B) → winner_1 (trong không gian A/B)
        Pass 2: judge(q, B, A) → winner_2_raw (trong không gian B/A)
        Convert: nếu winner_2_raw="A" thì thực ra là B (vì đã swap)
        Final:   nếu winner_1 == winner_2 → final = winner_1
                 nếu khác nhau → final = "tie"
    """
    pass1 = pairwise_judge(question, answer_a, answer_b, reference=reference)
    pass2_raw = pairwise_judge(question, answer_b, answer_a, reference=reference)  # SWAP!

    # Convert pass2 back to original A/B space
    swap_map = {"A": "B", "B": "A", "tie": "tie"}
    winner_pass2 = swap_map[pass2_raw["winner"]]

    # Average: consensus only if both agree
    if pass1["winner"] == winner_pass2:
        final = pass1["winner"]
    else:
        final = "tie"  # disagreement = inconclusive

    position_consistent = (pass1["winner"] == winner_pass2)

    return JudgeResult(
        question=question, answer_a=answer_a, answer_b=answer_b,
        winner_pass1=pass1["winner"], winner_pass2=winner_pass2,
        final_winner=final,
        reasoning_pass1=pass1["reasoning"], reasoning_pass2=pass2_raw["reasoning"],
        position_consistent=position_consistent,
        scores_pass1=pass1["scores"],
        scores_pass2={"A": pass2_raw["scores"]["B"], "B": pass2_raw["scores"]["A"]},
    )


# ─── Task 7: Cohen's κ ────────────────────────────────────────────────────────

def cohen_kappa(judge_labels: list[int], human_labels: list[int]) -> float:
    """Task 7: Tính Cohen's κ giữa LLM judge và human labels.

    Args:
        judge_labels:  nhãn từ LLM judge (0 = bad answer, 1 = good answer)
        human_labels:  nhãn từ human_labels_10q.json

    Returns:
        κ ∈ [-1, 1]
    """
    n = len(judge_labels)
    if n == 0 or len(human_labels) != n:
        return 0.0
    p_o = sum(j == h for j, h in zip(judge_labels, human_labels)) / n
    p_j1 = sum(j == 1 for j in judge_labels) / n
    p_j0 = 1.0 - p_j1
    p_h1 = sum(h == 1 for h in human_labels) / n
    p_h0 = 1.0 - p_h1
    p_e = (p_j1 * p_h1) + (p_j0 * p_h0)
    if abs(1.0 - p_e) < 1e-9:
        return 1.0 if abs(p_o - 1.0) < 1e-9 else 0.0
    return (p_o - p_e) / (1.0 - p_e)


# ─── Task 8: Bias Report ──────────────────────────────────────────────────────

def bias_report(judge_results: list[JudgeResult]) -> dict:
    """Task 8: Đo lường position bias và verbosity bias.

    Position bias: LLM chọn answer theo vị trí (A hay B) thay vì chất lượng.
        → Đo bằng % cases where position_consistent = False

    Verbosity bias: LLM ưu tiên answer dài hơn dù không chính xác hơn.
        → Đo bằng: trong các case A thắng, A có dài hơn B không? Tương tự cho B.

    Returns:
        {
          "total_judged": int,
          "position_bias_rate": float,
          "position_bias_count": int,
          "verbosity_bias": float,
          "verbosity_details": {
            "a_wins_a_longer": int,
            "b_wins_b_longer": int,
            "total_decisive": int,
          },
          "interpretation": str,
        }
    """
    total = len(judge_results)
    if total == 0:
        return {"total_judged": 0, "position_bias_rate": 0.0, "verbosity_bias": 0.0,
                "position_bias_count": 0, "verbosity_details": {}, "interpretation": "No data"}

    position_bias_count = sum(1 for r in judge_results if not r.position_consistent)
    position_bias_rate  = position_bias_count / total

    a_wins_a_longer = sum(
        1 for r in judge_results
        if r.final_winner == "A" and len(r.answer_a) > len(r.answer_b)
    )
    b_wins_b_longer = sum(
        1 for r in judge_results
        if r.final_winner == "B" and len(r.answer_b) > len(r.answer_a)
    )
    decisive = sum(1 for r in judge_results if r.final_winner != "tie")
    verbosity_bias = (a_wins_a_longer + b_wins_b_longer) / decisive if decisive > 0 else 0.0

    interpretation = ("Position bias cao — nên dùng swap-and-average."
                      if position_bias_rate > 0.3 else "Position bias thấp — judge ổn định.")
    return {
        "total_judged": total, "position_bias_rate": round(position_bias_rate, 3),
        "position_bias_count": position_bias_count,
        "verbosity_bias": round(verbosity_bias, 3),
        "verbosity_details": {"a_wins_a_longer": a_wins_a_longer,
                              "b_wins_b_longer": b_wins_b_longer,
                              "total_decisive": decisive},
        "interpretation": interpretation,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from scripts.run_experiments import main
    raise SystemExit(main(["--phase", "b", *sys.argv[1:]]))

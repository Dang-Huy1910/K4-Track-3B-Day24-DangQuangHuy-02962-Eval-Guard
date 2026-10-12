# Nhóm thực hiện K4 Track 3B

Tên nhóm: Alone

Repo chung: https://github.com/Dang-Huy1910/K4-Track-3B-Day24-DangQuangHuy-02962-Eval-Guard

Trưởng nhóm/người nộp: Đặng Quang Huy - 2A202602962

Ngày lab/deadline áp dụng: 13/10/2026 11:59 AM — Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: 6a74d01079bf819512174aea5db45c99a646a21a

Mỗi nhóm nộp một repo. Điền đủ thành viên và một mục INDIVIDUAL cho từng người.
Thêm/xóa rows để khớp nhóm thật; mẫu ba rows không ép nhóm phải có ba người.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Đặng Quang Huy | 2A202602962 | Toàn bộ pipeline: M1-M5, Phase A RAGAS 50q, Phase B LLM Judge Pairwise và Cohen Kappa, Phase C Guardrails và Latency P95 | PR trên GitHub, commits, artifacts/answers_50q.json, artifacts/ragas_50q.json, artifacts/judge_results.json, artifacts/guard_results.json |

Người tích hợp/chạy batch/nộp link: Đặng Quang Huy - tích hợp toàn bộ pipeline, thực thi các batch thực nghiệm và báo cáo.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: Linux Ubuntu 24.04 x86_64, Python 3.11.16, GCC 13.2.0 C++ compiler toolchain.
Virtualenv/dependencies/imports: `uv venv --python 3.11 .venv && uv pip install -r requirements/requirements-test.lock.txt`; pass 86/86 student/support tests.
Models/Qdrant/50 answers đã chuẩn bị: artifacts/answers_50q.json được sinh từ 50 câu hỏi test set (20 factual, 20 multi_hop, 10 adversarial). Model generation: gpt-4o-mini; evaluator: gpt-4o-mini, text-embedding-3-small; judge: gpt-4o-mini.

## INDIVIDUAL

### DangQuangHuy-2A202602962

- Phần được giao và phần thực tế đã làm: Thành viên duy nhất hoàn thiện toàn bộ đề bài: xây dựng 5 module pipeline m1-m5, triển khai Phase A (RAGAS 50q, bottom 10, cluster analysis), Phase B (Pairwise LLM Judge, Swap-and-average, Cohen kappa, Bias analysis), Phase C (Presidio PII regex/engine, NeMo Colang input/output rails, P95 latency measurement), và hoàn thành các báo cáo kỹ thuật.
- Bằng chứng: PR trên repo, các artifacts JSON lưu tại artifacts/ và 3 báo cáo phân tích Markdown tại doc/reports/.
- Cách kiểm tra: Unit tests qua pytest pass 86/86 tests; script check_lab.py kiểm tra toàn diện schema và tính toàn vẹn bằng chứng đạt 100%.
- Điều đã học: Hiểu sâu về đánh giá RAG đa chiều qua 4 metric RAGAS; các bias cố hữu của LLM-as-a-Judge (position bias, verbosity bias) và kỹ thuật swap-and-average; cơ chế phòng vệ chiều sâu nhiều tầng (defense-in-depth) kết hợp regex PII và semantic rails.
- Giới hạn/cách xử lý: Tập dữ liệu 50 câu có bẫy version conflict giữa các phiên bản quy định 2023 và 2024; cần ưu tiên thông tin hiệu lực mới nhất trong retrieval context.
- Nguồn/AI hỗ trợ nếu có: Antigravity AI pair programming assistant hỗ trợ rà soát logic kiểm thử và chuẩn hóa JSON schema contracts.

## Cập nhật sau khi nộp

Không có cập nhật sau deadline. Nộp đúng hạn theo thông báo của lớp.

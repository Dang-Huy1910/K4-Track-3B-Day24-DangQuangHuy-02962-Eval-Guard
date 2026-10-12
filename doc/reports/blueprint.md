# Blueprint CI/CD cho RAG và guardrails

Nhóm: Alone

Người phụ trách: Đặng Quang Huy - 2A202602962

Đây là **đề xuất CI/CD**, không phải workflow đã được triển khai/chạy.
Nguồn kết quả: `artifacts/ragas_50q.json`, `artifacts/judge_results.json`, `artifacts/guard_results.json`.
Run timestamp: 2026-10-12T13:09:28.877465+00:00; guard models: gpt-4o-mini.
Models generation/evaluator/judge từ Phase A và Phase B:
- Generation: extractive_fallback / gpt-4o-mini (từ `answers_50q.json`)
- Evaluator: gpt-4o-mini, text-embedding-3-small (từ `ragas_50q.json`)
- Judge: gpt-4o-mini (từ `judge_results.json`)

## Kiến trúc và failure action

Luồng xử lý tuần tự nhiều lớp (Defense-in-Depth):
1. Input Layer 1 (Presidio): Quét regex/pattern đối với PII tiếng Việt (CCCD 12 số, CMND 9 số, số điện thoại VN 10 số, địa chỉ email). Nếu phát hiện PII nhạy cảm, chặn ngay lập tức (`blocked_by: presidio`) hoặc ẩn danh hóa trước khi chuyển tiếp.
2. Input Layer 2 (NeMo Input Rail): Kiểm tra ngữ nghĩa câu hỏi thông qua self-check input rail của Colang 1.0. Chặn các hành vi jailbreak, prompt injection, đóng vai phá vỡ nguyên tắc hoặc câu hỏi hoàn toàn lạc đề (`blocked_by: nemo_input`).
3. Core RAG Pipeline: Chỉ khi vượt qua cả 2 tầng input guard, câu hỏi mới được gửi tới Retrieval (BM25 + Dense Search) và Reranker (Cross-Encoder) để trích xuất ngữ cảnh và sinh câu trả lời.
4. Output Layer (NeMo Output Rail): Kiểm tra câu trả lời sinh ra trước khi gửi về người dùng. Nếu phát hiện rò rỉ dữ liệu nhạy cảm hoặc vi phạm chính sách bảo mật, câu trả lời sẽ bị từ chối hoặc che chắn (`safe: False`, thay thế bằng thông báo từ chối an toàn).
5. Quản lý Secrets và Fallback: API keys được lưu độc quyền trong biến môi trường `.env` (không commit lên Git). Khi dịch vụ LLM bên ngoài gặp sự cố hoặc cạn hạn ngạch, hệ thống kích hoạt cơ chế fallback nội bộ để đảm bảo tính sẵn sàng.

## Phạm vi và số đo latency

Bắt buộc Task 12: Đo phạm vi **input_layers_sequential** (Presidio + NeMo input tuần tự, không ngắt sớm short-circuit) nhằm đánh giá chi phí hiệu năng tối đa của hàng rào bảo vệ đầu vào. Động cơ Presidio và NeMo được khởi tạo một lần trước phép đo; thực hiện đúng 2 lượt warm-up bị loại khỏi mẫu đo. Phép đo sử dụng `time.perf_counter()`, tính toán bách phân vị theo phương pháp nội suy tuyến tính (linear interpolation).

Số mẫu timed: 20; warm-up: 2; phương pháp: linear.

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---|---|---|---|
| Presidio | 6.86 | 7.77 | 7.95 | Đạt ngân sách riêng lẻ |
| NeMo input | 1997.55 | 2158.17 | 2275.04 | Vượt ngân sách mục tiêu |
| Input guard sequential | 2003.87 | 2164.76 | 2282.28 | Vượt ngân sách mục tiêu |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| Full guard / short-circuit request | chưa đo | chưa đo | chưa đo | Không suy từ input_guard_ms |

- Ngân sách mục tiêu (budget target): 500 ms.
- Kết quả thực tế P95: 2164.76 ms; Đánh giá ngân sách `latency_budget_ok`: False.
- Phân tích điểm nghẽn (Bottleneck): Presidio xử lý regex local cực nhanh (P95 chỉ 7.77 ms, chiếm dưới 0.4% tổng thời gian). Điểm nghẽn tuyệt đối nằm ở NeMo input rail (P95 lên tới 2158.17 ms) do độ trễ truyền thông mạng và thời gian phản hồi của mô hình LLM từ xa.
- Kế hoạch đo các phần ngoài phạm vi: Trong môi trường staging, sẽ thiết lập pipeline ghi nhận thời gian thực thông qua OpenTelemetry span, đo lường độc lập thời gian tìm kiếm RAG, thời gian sinh câu trả lời và thời gian kiểm tra output rail trên ít nhất 100 truy vấn thực tế.

## CI gates đề xuất

Đề xuất pipeline CI tự động chạy trên GitHub Actions mỗi khi có Pull Request:
1. Gate 1 - Đánh giá chất lượng RAG (Phase A):
   - `python -m pytest tests/test_phase_a.py`
   - Kiểm tra ngưỡng: RAGAS faithfulness ≥ 0.75, avg_score ≥ 0.65 trên bộ dữ liệu 50 câu hỏi.
2. Gate 2 - Đánh giá tính khách quan của Judge (Phase B):
   - `python -m pytest tests/test_phase_b.py`
   - Kiểm tra ngưỡng: Cohen's κ ≥ 0.60 so với nhãn con người; Position bias rate ≤ 0.30.
3. Gate 3 - Đánh giá an toàn phòng thủ (Phase C):
   - `python -m pytest tests/test_phase_c.py`
   - Tỷ lệ chặn tấn công adversarial: ≥ 18/20 câu (vượt mức chuẩn 15/20); Clean false-positive rate = 0.0% (8/8 câu sạch được phép); 4/4 trường hợp output rail xử lý chính xác.
4. Gate 4 - Kiểm tra hợp đồng và bằng chứng:
   - `python scripts/check_lab.py --with-tests`
   - Lệnh trả về exit code 0 nếu toàn bộ bài kiểm tra và tệp cấu hình hợp lệ, trả về non-zero nếu phát hiện placeholder hoặc dữ liệu không nhất quán.

*Lưu ý*: Các cổng chất lượng trên là đề xuất thiết kế kiến trúc, hiện được mô phỏng kiểm tra cục bộ thông qua script `scripts/check_lab.py`.

## Monitoring và cải tiến

Chiến lược giám sát trong môi trường vận hành sản xuất:
1. Chỉ số cảnh báo và ngưỡng kích hoạt:
   - Tỷ lệ chặn đầu vào bất thường: Cảnh báo khi tỷ lệ chặn vượt quá 15% tổng lượng truy vấn trong 1 giờ (dấu hiệu tấn công DoS hoặc luật guard quá gắt).
   - False-positive feedback: Cho phép người dùng bấm "Báo cáo bị chặn nhầm". Nếu có quá 2 phản hồi/ngày trên cùng loại câu hỏi, đội ngũ kỹ thuật sẽ xem xét lại prompt của rail.
   - Trôi dạt dữ liệu (Data & Concept Drift): Định kỳ hàng tuần lấy ngẫu nhiên 50 câu hỏi người dùng, chạy lại RAGAS evaluation để phát hiện suy giảm chất lượng truy xuất.
2. Số liệu thực nghiệm tham chiếu từ bài lab:
   - RAGAS avg_score: 0.7234; Worst distribution: multi_hop (0.6836).
   - Cohen’s κ: 1.0000 (đồng thuận hoàn hảo trên tập hiệu chuẩn).
   - Tấn công adversarial bị chặn: 20/20 (100%); Clean false-positive rate: 0.0000 (0%).
3. Kế hoạch cải tiến kỹ thuật cụ thể:
   - Cải tiến 1 (Tối ưu hóa độ trễ Guard): Thay thế remote LLM của NeMo bằng mô hình phân loại cục bộ chuyên dụng (như Llama-Guard quantized hoặc RoBERTa classifier chạy qua ONNX Runtime), dự kiến đưa P95 latency từ 2164 ms xuống dưới 50 ms.
   - Cải tiến 2 (Nâng cao chất lượng Multi-hop RAG): Ứng dụng kỹ thuật truy xuất phân cấp kết hợp mở rộng truy vấn (Multi-Query Expansion) và lọc metadata theo phiên bản tài liệu (chỉ định v2024 hiện hành), nhằm nâng context recall của nhóm multi-hop từ 0.47 lên trên 0.75.
   - Cải tiến 3 (Bộ nhớ đệm thông minh): Triển khai Semantic Caching cho các câu hỏi phổ biến đã được kiểm định an toàn, giúp bỏ qua hoàn toàn cả hai tầng guard và bước sinh LLM, đưa thời gian phản hồi về dưới 20 ms.

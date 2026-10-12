# Phân tích lỗi Phase A

Nhóm: Alone

Người phụ trách: Đặng Quang Huy - 2A202602962

Nguồn: `artifacts/ragas_50q.json`; run timestamp: 2026-10-12T12:48:27.656304+00:00.
Generation mode/fallback và điều kiện chạy: Thực thi pipeline hoàn chỉnh trên toàn bộ 50 câu hỏi từ `fixtures/test_set_50q.json` gồm 20 factual, 20 multi_hop và 10 adversarial. Pipeline sử dụng bộ tách chunk phân cấp M1, tìm kiếm lai kết hợp BM25 M2, reranking Cross-Encoder M3 và extractive fallback đảm bảo không phụ thuộc API bên ngoài khi suy diễn.
Models generation/evaluator: Generation model: extractive_fallback; Evaluator models: gpt-4o-mini, text-embedding-3-small từ module M4.

## Điểm theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---|---|---|
| faithfulness | 1.0000 | 1.0000 | 1.0000 |
| answer_relevancy | 0.5376 | 0.4138 | 0.5892 |
| context_precision | 0.8500 | 0.8500 | 0.8500 |
| context_recall | 0.7309 | 0.4705 | 0.3885 |
| avg_score | 0.7796 | 0.6836 | 0.7069 |

## Bottom 10 và nguyên nhân

| Rank | ID | Câu hỏi | Distribution | Avg Score | Worst Metric | Diagnosis | Suggested Fix |
|---|---|---|---|---|---|---|---|
| 1 | 39 | So sánh yêu cầu mật khẩu giữa policy v1.0 và v2.0 về độ dài tối thiểu, thời hạn đổi và MFA. | multi_hop | 0.6195 | context_recall | Missing relevant chunks | Improve chunking or add BM25 |
| 2 | 50 | Nhân viên Manager có thể dùng VPN cá nhân (như NordVPN) khi WFH để tăng bảo mật thêm không? | adversarial | 0.6208 | answer_relevancy | Answer doesn't match question | Improve prompt template |
| 3 | 49 | Theo chính sách nghỉ phép cũ (v2023), nhân viên được nghỉ bao nhiêu ngày? Còn chính sách nào đang có hiệu lực hiện tại? | adversarial | 0.6259 | context_recall | Missing relevant chunks | Improve chunking or add BM25 |
| 4 | 38 | Nhân viên đi công tác nước ngoài 4 ngày tại thành phố lớn, ở khách sạn 200 USD/đêm (3 đêm). Công ty thanh toán bao nhiêu tiền khách sạn? | multi_hop | 0.6268 | answer_relevancy | Answer doesn't match question | Improve prompt template |
| 5 | 31 | Nhân viên đi công tác trong nước, ở khách sạn 2 đêm với giá 1.500.000 VNĐ/đêm. Công ty thanh toán tối đa bao nhiêu cho tiền khách sạn? | multi_hop | 0.6357 | answer_relevancy | Answer doesn't match question | Improve prompt template |
| 6 | 33 | Nhân viên Manager có thâm niên 12 năm: tổng phụ cấp hàng tháng và số ngày phép năm theo v2024 là bao nhiêu? | multi_hop | 0.6360 | context_recall | Missing relevant chunks | Improve chunking or add BM25 |
| 7 | 40 | Nhân viên cấp Manager có thời hạn thử việc 90 ngày, đang trong tháng thứ 3, phát hiện vi phạm bảo mật. Họ nên và không nên làm gì theo chính sách? | multi_hop | 0.6387 | answer_relevancy | Answer doesn't match question | Improve prompt template |
| 8 | 35 | Nhân viên Junior P1 có lương cơ bản 12 triệu vừa vào thử việc: nhận lương bao nhiêu và phụ cấp gì tháng đầu tiên? | multi_hop | 0.6493 | answer_relevancy | Answer doesn't match question | Improve prompt template |
| 9 | 5 | Muốn mua thiết bị trị giá 55 triệu cần ai phê duyệt? | factual | 0.6500 | answer_relevancy | Answer doesn't match question | Improve prompt template |
| 10 | 34 | Nhân viên tạm ứng 4 triệu và một nhân viên khác tạm ứng 7 triệu: quy trình phê duyệt khác nhau thế nào? | multi_hop | 0.6530 | answer_relevancy | Answer doesn't match question | Improve prompt template |

### Phân tích chi tiết các nhóm câu tiêu biểu

1. Câu hỏi multi-hop phức tạp (ID 39, ID 38, ID 33):
   - Đối chiếu contexts và reference: Câu hỏi yêu cầu tổng hợp thông tin từ nhiều điều khoản rời rạc (chính sách bảo mật mật khẩu v1.0 và v2.0, hoặc tính kết hợp thâm niên công tác với bảng phụ cấp chức vụ Manager). Do chunking ban đầu phân chia theo ranh giới đoạn văn, các điều khoản liên quan bị tách sang các chunk khác nhau. Khi retriever chỉ lấy top-k hạn chế, một số thông tin thiết yếu bị bỏ sót dẫn đến `context_recall` thấp (ví dụ ID 39 có context recall chỉ 0.47).
2. Câu hỏi bẫy adversarial và phủ định (ID 50, ID 49):
   - ID 50 hỏi về việc sử dụng VPN cá nhân (NordVPN). Context chứa cả chính sách WFH chung và quy định cấm VPN cá nhân trong Security Policy. Câu trả lời extractive trích xuất đoạn văn nói về bảo mật WFH nhưng chưa làm nổi bật quy định cấm NordVPN, khiến `answer_relevancy` bị trừ điểm.
3. Câu hỏi tính toán định lượng và ngưỡng giá trị (ID 5, ID 31):
   - ID 5 hỏi về hạn mức phê duyệt 55 triệu VNĐ. Tài liệu chứa bảng phân quyền theo các mốc dưới 5 triệu, 5-50 triệu và trên 50 triệu. Trích xuất bị cắt ngang ngay tại ranh giới 50 triệu làm mất tên người phê duyệt cuối cùng (Tổng Giám đốc/CEO).

## Matrix và nhóm yếu nhất

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---|---|---|
| faithfulness | 0 | 0 | 0 |
| context_precision | 0 | 0 | 0 |
| context_recall | 2 | 7 | 8 |
| answer_relevancy | 18 | 13 | 2 |

- Nhóm yếu theo mean thấp nhất: `multi_hop` với avg_score đạt 0.6836 (thấp hơn factual 0.7796 và adversarial 0.7069).
- Worst metric xuất hiện nhiều nhất: `answer_relevancy` với 33/50 câu có điểm thấp nhất (18 câu factual, 13 câu multi_hop, 2 câu adversarial).
- Nguyên nhân: Các câu hỏi multi_hop đòi hỏi suy luận bắc cầu qua nhiều văn bản quy định. Khi retriever không thu thập đầy đủ các phần context cần thiết, câu trả lời sinh ra bị thiếu ý hoặc mang tính bao quát chung chung, làm giảm độ tương thích giữa câu hỏi và câu trả lời.
- Đề xuất cải thiện: Bổ sung multi-query expansion và tăng số lượng retrieved context trước khi rerank (tăng k từ 5 lên 10), kết hợp lọc metadata theo phiên bản tài liệu. Để kiểm chứng hiệu quả, chạy lại runner Phase A và so sánh `avg_score` của nhóm multi_hop trên tập 50 câu.

## Bẫy adversarial và giới hạn

So sánh giữa các nhóm cho thấy điểm trung bình của adversarial (0.7069) thấp hơn rõ rệt so với factual (0.7796), phản ánh đúng độ khó của các bẫy ngữ nghĩa:
- Bẫy xung đột phiên bản (version conflict): Các câu như ID 41 và ID 49 đưa ra câu hỏi về số ngày phép nhưng cố tình gài dữ liệu của chính sách cũ năm 2023 (12 ngày) so với chính sách hiện hành năm 2024 (15 ngày). Retriever lấy về cả 2 văn bản khiến hệ thống dễ bị nhầm lẫn nếu không có cơ chế ưu tiên metadata hiệu lực thời gian.
- Bẫy phủ định và ngoại lệ (negation): Các câu như ID 50 kiểm tra khả năng phát hiện quy định cấm VPN bên thứ ba dù người dùng đưa ra lý do hợp lý ("để tăng bảo mật").
- Giới hạn: Điểm adversarial thấp hơn cho thấy câu hỏi thách thức hệ thống hơn, nhưng chưa đảm bảo rằng hệ thống đã chủ động phân biệt được bản chất của bẫy nếu không có bộ kiểm tra quy tắc riêng biệt. Khi chạy trong môi trường offline với extractive fallback, câu trả lời dựa trên trích xuất thuần túy nên độ mạch lạc văn phong có thể thấp hơn LLM sinh tự do, dù độ trung thực (faithfulness) đạt mức tối đa 1.0.

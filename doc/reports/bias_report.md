# Đánh giá LLM Judge Phase B

Nhóm: Alone

Người phụ trách: Đặng Quang Huy - 2A202602962

Nguồn: `artifacts/judge_results.json`; run timestamp: 2026-10-12T13:02:46.414264+00:00.
Models generation/judge: Generation model: extractive_fallback; Judge model: gpt-4o-mini.

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ `artifacts/answers_50q.json:answer`; B từ `fixtures/human_labels_10q.json:model_answer`; reference từ `fixtures/test_set_50q.json:ground_truth`.
Ids đánh giá: 1, 5, 12, 21, 41. Không thay đổi nguồn sau khi chạy judge.

| ID | Câu hỏi | Winner Lượt 1 | Winner Lượt 2 | Final Winner | Nhất quán vị trí | Điểm Lượt 1 (A/B) | Điểm Lượt 2 (A/B) |
|---|---|---|---|---|---|---|---|
| 1 | Nhân viên được nghỉ bao nhiêu ngày khi kết hôn? | tie | tie | tie | True | 0.80 / 0.85 | 0.80 / 0.85 |
| 5 | Muốn mua thiết bị trị giá 55 triệu cần ai phê duyệt? | A | tie | tie | False | 0.50 / 0.20 | 0.50 / 0.50 |
| 12 | Thưởng Tết tối thiểu cho nhân viên chính thức từ 6 tháng? | tie | tie | tie | True | 0.80 / 0.85 | 0.80 / 0.85 |
| 21 | Senior 9 năm thâm niên: ngày phép năm và khung lương? | B | B | B | True | 0.70 / 0.90 | 0.70 / 0.90 |
| 41 | Nhân viên được nghỉ bao nhiêu ngày phép năm? | tie | tie | tie | True | 0.30 / 0.30 | 0.30 / 0.30 |

- Position bias count: 1 / 5 cặp.
- Position bias rate: 0.200 (20.0%).
- Verbosity win rate: 0.000 (0.0%); số lượng decisive cases: 1.
- Diễn giải kết quả:
  - Ở ID 5, lượt 1 chọn A (do B trả lời sai thẩm quyền Giám đốc phòng ban thay vì CEO), nhưng khi hoán đổi thứ tự ở lượt 2, judge đánh giá mức độ tương đương giữa câu trả lời chưa trọn vẹn và câu trả lời sai thẩm quyền, dẫn đến kết quả hòa. Cơ chế Swap-and-average đã tự động quy về "tie", giúp loại trừ nhận định phiến diện.
  - Ở ID 21, câu trả lời B ngắn gọn hơn nhưng đầy đủ cả 2 vế thông tin (18 ngày phép và khung lương 20-35 triệu), trong khi câu A bị thiếu thông tin lương. Candidate B chiến thắng dứt khoát ở cả 2 lượt dù có độ dài ngắn hơn Candidate A. Điều này chứng minh verbosity bias là 0.0 và judge ưu tiên chất lượng nội dung thay vì độ dài hình thức.

## Calibration đúng model_answer

Helper đánh giá trực tiếp question và model_answer từ `fixtures/human_labels_10q.json`, hoàn toàn không sử dụng answer mới của pipeline. Hệ thống tuân thủ nghiêm ngặt nguyên tắc cách ly dữ liệu: Prompt chỉ nhận đúng 3 trường dữ liệu: question, answer, reference; tuyệt đối không gửi `human_label`, `human_note` hoặc bất kỳ gợi ý nào vào prompt đánh giá.

| Question ID | Model Answer Gốc | Nhãn Judge | Lý do phán quyết của Judge | Human Label | Nhất quán |
|---|---|---|---|---|---|
| 1 | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | 1 | Câu trả lời chính xác, đầy đủ và phù hợp với chính sách tham chiếu. | 1 | True |
| 5 | Cần Giám đốc phòng ban phê duyệt. | 0 | Sai thẩm quyền phê duyệt: trên 50 triệu cần Tổng Giám đốc (CEO) phê duyệt thay vì Giám đốc phòng ban. | 0 | True |
| 12 | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | 1 | Câu trả lời chính xác, đầy đủ và phù hợp với chính sách tham chiếu. | 1 | True |
| 21 | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | 1 | Câu trả lời chính xác, đầy đủ và phù hợp với chính sách tham chiếu. | 1 | True |
| 23 | Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết. | 1 | Câu trả lời chính xác, đầy đủ và phù hợp với chính sách tham chiếu. | 1 | True |
| 29 | Trưởng phòng phê duyệt. Phạt 2% tháng trên 8 triệu. | 0 | Thiếu thẩm quyền Kế toán trưởng và chưa tính đúng phạt pro-rata cho số ngày quá hạn. | 0 | True |
| 33 | Phép: 19 ngày. Phụ cấp: 1.500.000 VNĐ/tháng. | 1 | Câu trả lời chính xác, đầy đủ và phù hợp với chính sách tham chiếu. | 1 | True |
| 41 | Nhân viên được nghỉ 12 ngày phép năm. | 0 | Sai phiên bản chính sách: v2023 đã bị thay thế bởi v2024 hiện hành (15 ngày cơ bản). | 0 | True |
| 46 | Nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần. | 1 | Câu trả lời chính xác, đầy đủ và phù hợp với chính sách tham chiếu. | 1 | True |
| 50 | Được, miễn là đảm bảo kết nối an toàn. | 0 | Sai chính sách bảo mật: VPN cá nhân bị cấm, bắt buộc dùng VPN WireGuard của công ty. | 0 | True |

- Cohen’s κ: 1.0000.
- Observed agreement $P_o = 10 / 10 = 1.0000$ (100%).
- Chance agreement $P_e = (0.6 \times 0.6) + (0.4 \times 0.4) = 0.36 + 0.16 = 0.5200$.
- Hệ số Cohen's $\kappa = (P_o - P_e) / (1 - P_e) = (1.0 - 0.52) / (1.0 - 0.52) = 1.0000 > 0.60$, đạt mức đồng thuận hoàn hảo (Perfect Agreement), thỏa mãn điều kiện nhận điểm thưởng bonus Phase B (+3 điểm).

## Giới hạn và cách dùng judge

- Giới hạn kích thước mẫu: Bộ hiệu chuẩn chỉ gồm 10 câu hỏi và 5 cặp pairwise, là kích thước mẫu tương đối nhỏ dùng để kiểm tra độ tin cậy ban đầu. Trên tập dữ liệu sản xuất quy mô lớn, cần mở rộng bộ nhãn kiểm chuẩn lên ít nhất 100 - 200 câu đa dạng các phòng ban.
- Độ nhạy với thứ tự hiển thị: Dù tỷ lệ position bias chỉ là 20%, nó chứng minh LLM-as-a-Judge vẫn có thể bị dao động bởi thứ tự prompt nếu chỉ gọi một lần duy nhất. Kỹ thuật swap-and-average là bắt buộc trong môi trường thực tế để đảm bảo tính khách quan.
- Khuyến nghị vận hành: LLM-as-a-Judge không nên được dùng làm nguồn chân lý duy nhất mà cần kết hợp song song với hệ thống giám sát tự động, kiểm tra hồi quy định kỳ, và có sự tham gia của chuyên gia con người (human-in-the-loop) đối với các trường hợp tranh chấp hoặc có mức độ rủi ro cao.

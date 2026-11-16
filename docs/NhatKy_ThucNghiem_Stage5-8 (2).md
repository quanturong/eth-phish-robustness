# Nhật ký thực nghiệm Stage 5 → Stage 8 (bản cập nhật)

**Đề tài:** Đánh giá và tăng cường độ bền vững của mô hình phát hiện lừa đảo trên Ethereum trước các tấn công né tránh dựa trên đồ thị giao dịch.
**Phạm vi file này:** những gì đã làm từ Stage 5 (huấn luyện) đến Stage 8 (đối chiếu D2), kèm số liệu, lệnh chạy, lỗi đã sửa, hạn chế và việc còn dang dở.
**Nguồn số liệu:** các bảng/log chạy thật trong quá trình làm (các file `results_*.json`, `eval_*.json`, `diag_feature_*.json`, `stage*_summary*.md`). Trước khi đưa vào báo cáo, hãy đối chiếu lại với file gốc.

**Quy ước tên mô hình:** `PEAE-style (cũ)` = bản xấp xỉ PEAE-GNN dựa trên SAGE (mô hình chính của bản nhật ký trước). `peaegnnv2` = bản mới do bạn trong nhóm viết, nhằm gần bài báo hơn (tăng cường đồ thị + attention GATv2 + học đối sánh). **Từ bản này, mô hình chính là `peaegnnv2`**; kết quả của PEAE-style (cũ) được giữ làm kết quả bổ sung vì phần phòng thủ (Stage 7) đang xây trên nó.

**Thay đổi so với bản trước:**
- Thêm Stage 5 cho `peaegnnv2` (mục 2).
- Thêm đo **chi phí tối thiểu để vượt detector** (dừng ngay khi bị lừa) cho 7 tấn công × 3 mô hình (mục 3.5).
- Thêm phép thử độ nhạy đặc trưng với **3 seed × 3 mô hình** (mục 3.6); kết luận seed 42 ở bản trước đã được sửa.
- Thêm cơ sở thực tế của 7 tấn công (mục 3.7) và phần trả lời các câu hỏi của thầy (mục 9).
- Sửa một số kết luận cũ (mục 0, 3.5, 6).

---
## 0. Tóm tắt

| Câu hỏi | Kết luận hiện có | Độ chắc |
|---|---|---|
| RQ1: mô hình suy giảm thế nào trước giao dịch giả | Phụ thuộc mạnh vào **tấn công và kiến trúc**, Với ngân sách tới 1,200 giao dịch giả (3 seed, trung bình ± độ lệch chuẩn): `peaegnnv2` bị ADAPTIVE-STC-LV vượt **66,6 ± 17,2%** số ví, TOH 42,4 ± 3,7%, BPH-T2P 41,9 ± 5,9%, STC 23,1 ± 5,3%, TIH 16,7 ± 10,3%, GraphSAGE bị vượt tối đa 15,0 ± 2,0% (ADAPTIVE), GATv2 bị TIH vượt 33,2 ± 7,5%, TOH 18,4 ± 2,5%, ADAPTIVE chỉ 6,8 ± 1,7% | Khá chắc (cả 7 tấn công có 3 seed); `peaegnnv2` biến thiên lớn giữa seed |
| Chi phí tối thiểu (mốc vượt) | Không có một mốc duy nhất; đường cong tăng mượt. Với `peaegnnv2` (3 seed): **10% số ví cần khoảng 30–50 giao dịch giả với TOH, 40–100 với BPH-T2P, 90–180 với ADAPTIVE** (≈ 0,04–0,22 ETH gas); 25% số ví cần khoảng 180–400 giao dịch (TOH, BPH-T2P, ADAPTIVE); 50% chỉ đạt với ADAPTIVE (3/3 seed: 420–1.200 giao dịch) và BPH-T2P (1/3 seed: 1.200) | Trung bình; chi phí này chỉ cho họ tấn công đã thử |
| RQ2: yếu tố nào nhạy nhất | Giá trị tiền và thời gian hoạt động **gần như không ảnh hưởng** (≤ 1%, cả 9 lần huấn luyện). **Số đối tác khác nhau** là đặc trưng nhạy nhất của chính ví (9/9 lần). GraphSAGE dựa vào hàng xóm; GATv2 hầu như không nhạy khi thay đặc trưng; `peaegnnv2` thay đổi theo seed | Các kết luận chung: chắc. Cơ chế giải thích: **chưa kiểm chứng** |
| RQ3: huấn luyện đối kháng cải thiện bao nhiêu | Trên **PEAE-style (cũ)**: giữ recall khi bị tấn công cao hơn (+11,7 điểm ở FPR 10%, b=100), hiệu năng sạch gần như không đổi. **Chưa chạy cho `peaegnnv2`** | Khá chắc cho mô hình cũ |
| RQ4: reliability-aware vs huấn luyện đối kháng | Trên PEAE-style (cũ): RA hơn mô hình gốc rõ; hơn huấn luyện thường chỉ là gợi ý. **RA chưa có thiết kế cho `peaegnnv2`** (lớp attention không có chỗ nhân trọng số) | Chưa kết luận |
| Đối chiếu D2 | Chuyển trực tiếp: xếp hạng vẫn tốt (ROC-AUC 0,73–0,87), macro-F1 ở ngưỡng 0,5 giảm mạnh | Chắc ở mức mô tả |

**Các kết luận cũ đã sửa:**
1. "Sáu tấn công gốc gần như vô hại" **chỉ đúng với PEAE-style (cũ) ở ngân sách nhỏ** (≤ 80 giao dịch). Với `peaegnnv2` và GATv2, ngân sách tới 1.200 giao dịch, TOH/BPH-T2P vượt khoảng 42% số ví (`peaegnnv2`) và TIH vượt khoảng 33% (GATv2).
2. "ADAPTIVE-STC-LV là tấn công mạnh nhất" **chỉ đúng với `peaegnnv2` (ở ngân sách lớn) và GraphSAGE**; với GATv2 nó yếu nhất (6,8 ± 1,7%) và TIH mạnh nhất (33,2 ± 7,5%).
3. "Hàng xóm bậc 1 là yếu tố nhạy nhất của `peaegnnv2`" **chỉ đúng ở seed 42**; ở seed 43 và 44 mô hình dựa vào đặc trưng của chính ví.
4. "Với `peaegnnv2`, thao tác đưa *vào* ví (TIH) gần như vô hại" (nhận định từ seed 42) **không đúng**: TIH là 2,6 / 26,9 / 20,6% qua 3 seed.

---
## 1. Bối cảnh dữ liệu (đầu vào của Stage 5)

- **EthPhishGraph-2026:** 7.036 ví mục tiêu (3.518 phishing + 3.518 normal), ego-graph **K=2**.
- **Chia tập theo thời gian 60/20/20:** train 4.221 · val 1.407 · test 1.408. Tỉ lệ phishing: 56,8% / 37,3% / 42,2% (lệch giữa các tập, do hai lớp có phân bố thời gian khác nhau).
- **Kích thước graph trung bình:** 2.318 / 2.482 / 3.677 node (hop-2 chiếm khoảng 99% số node).
- **Đặc trưng node (9 cột):** in/out count, tổng và trung bình giá trị vào/ra, `active_span`, số đối tác khác nhau vào/ra. **Đã bỏ** `first_ts`, `last_ts` (timestamp tuyệt đối) để mô hình không học "thời điểm → nhãn".
- **Đặc trưng cạnh (3 cột):** value, gas_price, gas_used (đã bỏ timestamp). GraphSAGE/GATv2/PEAE-style không dùng đặc trưng cạnh; chỉ các mô hình RA dùng.
- **Dựng graph (Stage 9c) đã sửa:** chỉ giữ hàng xóm có giao dịch trước mốc cắt (lỗi rò rỉ tương lai), bỏ node cô lập sinh từ giao dịch tạo contract; giữ toàn bộ hop-2 (`MAX_HOP2_PER_NEIGH = None`), mỗi hàng xóm tối đa 500 giao dịch cũ nhất.

---

## 2. Stage 5 — Huấn luyện mô hình nền

**Mô hình:** GraphSAGE · GATv2 · PEAE-style (cũ) · **`peaegnnv2`**.
- PEAE-style (cũ): **bản xấp xỉ** PEAE-GNN (encoder SAGE + embedding node mục tiêu + mean/max pooling + dropout đặc trưng), không phải bản tái lập gốc.
- `peaegnnv2` (do bạn trong nhóm viết): tăng cường đồ thị (bỏ ~20% cạnh, che ~15% đặc trưng) + bộ mã hóa GATv2 + embedding node mục tiêu đa lớp + đọc kết quả bằng attention từ node mục tiêu + học đối sánh NT-Xent (trọng số 0,1). **Chưa xác nhận từng thành phần khớp bài báo gốc;** các siêu tham số là lựa chọn của người viết.

**Cấu hình chung:** hidden 64, lr 1e-3, weight decay 5e-4, cross-entropy có trọng số lớp, chọn mô hình theo macro-F1 validation, dừng sớm (patience 15, tối đa 100 epoch), seed 42/43/44; chạy trên Kaggle GPU. Test chỉ đánh giá một lần ở epoch tốt nhất.
**Khác biệt cách huấn luyện:** ba mô hình đầu dùng **batch 64**; `peaegnnv2` dùng **batch 16** (batch 64 hết bộ nhớ GPU 14,5 GB vì chạy 3 lượt mỗi batch; ~58 giây/epoch). Với batch 16 chỉ có ~30 mẫu "âm" cho học đối sánh mỗi batch (so với ~126), nên có thể học kém hơn thiết kế gốc.

| Mô hình | Macro-F1 | PR-AUC | Recall phishing |
|---|---|---|---|
| GraphSAGE | 0,8663 ± 0,0032 | 0,9373 ± 0,0047 | 0,7772 ± 0,0110 |
| GATv2 | 0,8151 ± 0,0108 | 0,9040 ± 0,0025 | 0,6616 ± 0,0159 |
| PEAE-style (cũ) | **0,8813 ± 0,0028** | **0,9429 ± 0,0021** | **0,8283 ± 0,0060** |
| **`peaegnnv2`** | 0,8564 ± 0,0040 | 0,9264 ± 0,0023 | 0,7581 ± 0,0140 |

Ghi chú:
- `peaegnnv2` (precision phishing 0,9035) **thấp hơn PEAE-style (cũ)** ~2,5 điểm macro-F1 và ~7 điểm recall; nằm giữa GraphSAGE và GATv2. Epoch tốt nhất: 14, 14, 40; F1 validation 0,7632 / 0,7600 / 0,7728. Do khác điều kiện huấn luyện (batch 16), chưa kết luận kiến trúc "gần bài báo hơn" là kém hơn.
- F1 validation (~0,78–0,81) thấp hơn F1 test (~0,88) do chia tập theo thời gian (mốc cắt lịch sử khác nhau), không phải lỗi. Độ lệch chuẩn chỉ phản ánh khởi tạo khác nhau (3 seed).
- Số ví phishing mỗi mô hình bắt đúng lúc sạch (trong 594): `peaegnnv2` 462 / 443 / 446 (seed 42/43/44), GraphSAGE 470 / 454 / 461, GATv2 382 / 392 / 405.

**Lệnh:**
```
python stage5_train_baselines.py --pkl <ego_graph_k2_dataset.pkl> --out /kaggle/working/stage5_k2 --model all --seeds 42 43 44
python stage5_train_baselines.py --pkl <pkl> --out /kaggle/working/stage5_v2 --model peaegnnv2 --seeds 42 43 44 --bs 16
```

---
## 3. Stage 6 — Tấn công thêm giao dịch

> **Lưu ý đọc mục 3.1–3.4:** các kết quả này (tấn công đo từ trước khi đổi mô hình chính) là trên **PEAE-style (cũ)**, GraphSAGE và GATv2. Kết quả tương ứng cho `peaegnnv2` và đường cong chi phí nằm ở mục 3.5–3.6. Các kết luận "tấn công gốc gần như vô hại" ở mục 3.2 chỉ đúng ở ngân sách nhỏ của mô hình cũ (xem mục 0).

### 3.1 Thiết lập
- Graph sau tấn công được **dựng lại từ giao dịch thô bằng đúng bộ dựng K=2 của Stage 9c** (không sửa vector đặc trưng trực tiếp). Giao dịch giả: gas_price lấy mẫu từ lịch sử gas của chính ví, gas_used = 21.000.
- Kiểm tra hợp lệ tự động: ngân sách, timestamp sau giao dịch thật cuối, đầu mút do kẻ tấn công kiểm soát, value > 0. **Không kiểm tra số dư và chi phí gas.**
- Chỉ tấn công ví phishing (ví normal giữ nguyên). **ASR = tỉ lệ ví phishing mà mô hình bắt đúng lúc sạch nhưng sau tấn công bị bỏ sót.**
- Đánh giá trên toàn bộ tập test (594 phishing), 3 mô hình × 3 seed.

### 3.2 Sáu tấn công gốc (budget 1, 3, 5, 10, 20)

| Tấn công | Mô tả | Giao dịch/đơn vị ngân sách |
|---|---|---|
| TOH | target → ví giả | 1 |
| TIH | ví giả → target | 1 |
| BPH-T2P | target → W1 → ví giả | 2 |
| BPH-P2T | ví giả → W1 → target | 2 |
| STC | chia nhỏ giá trị, trải 30 ngày, 1 ví camouflage | 4 |
| MWR (**vòng về target**) | target → W1 → W2 → target | 3 |

> **Thay đổi so với đề cương:** MWR gốc (target → W1 → W2 → ví đích) có cấu trúc **trùng hệt BPH-T2P** khi chỉ nhìn K=2 (giao dịch cuối nằm ngoài K=2), nên không thể làm tấn công "chưa thấy". Đã thiết kế lại thành vòng về target. Cần cập nhật Hình 1 và mô tả MWR trong đề cương.

**ASR (%) tại b=20, trung bình ± độ lệch chuẩn qua 3 seed:**

| Mô hình | TOH | TIH | BPH-T2P | BPH-P2T | STC | MWR | ASR_any |
|---|---|---|---|---|---|---|---|
| PEAE-style | 1,9 ± 1,1 | 0,8 ± 0,8 | 1,3 ± 0,7 | 1,4 ± 1,2 | 3,4 ± 1,1 | 0,1 ± 0,2 | 5,3 ± 2,5 |
| GraphSAGE | 1,5 ± 0,3 | 1,6 ± 0,9 | 1,8 ± 0,5 | 3,2 ± 3,1 | 3,5 ± 1,9 | 0,7 ± 0,6 | 8,7 ± 4,9 |
| GATv2 | 4,6 ± 1,2 | 1,5 ± 0,2 | 4,0 ± 0,4 | 0,5 ± 0,0 | 3,2 ± 1,1 | 0,4 ± 0,4 | 6,2 ± 1,0 |

(ASR_any = bị lật bởi ít nhất một tấn công/ngân sách trong lưới.)

**Hướng tác động lên P(phishing)** (b lớn nhất, đơn vị điểm xác suất; âm = làm mô hình bớt tin là phishing):

| Mô hình | TOH | TIH | BPH-T2P | BPH-P2T | STC | MWR |
|---|---|---|---|---|---|---|
| PEAE-style | −0,031 | +0,055 | −0,018 | +0,074 | −0,069 | +0,057 |
| GraphSAGE | −0,012 | +0,009 | +0,015 | +0,036 | −0,037 | +0,056 |
| GATv2 | −0,045 | +0,013 | −0,034 | +0,040 | −0,031 | +0,007 |

Chỉ **TOH và STC** làm P giảm ở cả ba mô hình. Các tấn công thêm giao dịch *vào* target (TIH, BPH-P2T, MWR vòng về) thường làm P tăng ở PEAE-style (vô tình giúp mô hình). Không nên khẳng định quy luật chung cho BPH-T2P (không nhất quán).

**Ngân sách lớn cho tấn công gốc** (chỉ PEAE-style, seed 42): tăng từ 20 lên 500 chỉ nâng ASR của STC từ ~2,8% lên ~4,9%, TOH đi ngang (~0,6–0,8%). Tức là các tấn công gốc "yếu" không phải do ngân sách nhỏ.

### 3.3 Tấn công thích ứng và các biến thể (tự thiết kế)

Thử nghiệm sơ bộ (PEAE-style, seed 42, mẫu nhỏ 100–300 target — chỉ mang tính tham khảo):
- `COMBINED` (kết hợp STC + BPH + TOH) và `GREEDY-QUERY` (thử vài kiểu, hỏi mô hình, giữ kiểu làm P giảm nhiều nhất): đều chỉ lật 1 mẫu (2,6%) → yếu. *(Lưu ý: tên gốc "GRADIENT" đã đổi thành `GREEDY-QUERY` vì không dùng gradient.)*
- `ADAPTIVE-STC`: 6 giao dịch/đơn vị, giá trị log-uniform 0,01–1 ETH, trải 90 ngày, tự cân bằng chiều gửi/nhận, 2 ví camouflage → ASR 13–18% (mẫu 100 target).
- **Kiểm tra yếu tố nào tạo ra sức mạnh** (300 target, 111 ví đúng lúc sạch):

| Tấn công | ASR b=5 / 10 / 20 | Tổng giá trị chuyển (b=20) |
|---|---|---|
| STC | 1,8 / 2,7 / 2,7 | 0,024 ETH |
| STC-HV (STC + giá trị lớn gấp ~1.000 lần) | 1,8 / 2,7 / 2,7 | 17,0 ETH |
| ADAPTIVE-STC | 6,3 / 13,5 / 16,2 | 25,7 ETH |
| ADAPTIVE-STC-LV (giá trị nhỏ như STC) | 7,2 / 13,5 / 18,0 | 0,036 ETH |

→ **Giá trị giao dịch không phải yếu tố quyết định**; còn lại là cân bằng chiều / 90 ngày / số giao dịch / số ví — chưa tách riêng từng yếu tố.

### 3.4 `ADAPTIVE-STC-LV` trên toàn bộ tập test, 3 seed

ASR (%), trung bình ± độ lệch chuẩn:

| Mô hình | b=20 | b=50 | b=100 | b=200 | b=500 | P(phishing) giảm ở b=500 |
|---|---|---|---|---|---|---|
| PEAE-style | 27,2 ± 7,1 | 37,4 ± 6,8 | 41,8 ± 8,2 | 44,7 ± 8,6 | 49,7 ± 11,2 | 0,300 |
| GraphSAGE | 3,5 ± 1,3 | 6,5 ± 1,8 | 10,5 ± 1,9 | 14,7 ± 1,8 | 23,2 ± 3,9 | 0,149 |
| GATv2 | 2,4 ± 0,4 | 3,8 ± 1,1 | 5,3 ± 1,5 | 6,4 ± 1,4 | 8,5 ± 1,1 | 0,069 |

**Chi phí:** b=20 → 120 giao dịch, ~0,036 ETH giá trị, ~0,148 ETH phí gas; b=500 → 3.000 giao dịch, ~0,90 ETH giá trị, ~3,71 ETH phí gas (gas lấy mẫu từ lịch sử từng ví; chưa quy ra USD). Giá trị là tổng *cộng dồn*, không phải vốn tối thiểu cần có.

### 3.5 Chi phí tối thiểu để vượt detector (số giao dịch giả cần bao nhiêu)

**Câu hỏi của thầy:** cần biến đổi mẫu đến mức nào (tốn ít chi phí nhất) thì đã vượt được detector, thay vì chạy hết ngân sách tối đa.

**Cách đo (`--min_cost`):** với mỗi ví phishing mà mô hình **bắt đúng lúc sạch**, tăng dần ngân sách theo một lưới và **dừng ngay lần đầu mô hình bị lừa** (xác suất phishing < 0,5); ghi số giao dịch giả đã dùng. Giao dịch giả tại cùng ngân sách giống hệt các lần chạy trước (cùng seed), nên so sánh được. Vì mỗi đơn vị ngân sách là 1 (TOH, TIH), 2 (BPH), 3 (MWR), 4 (STC) hoặc 6 (ADAPTIVE) giao dịch, mỗi nhóm có lưới riêng sao cho **tất cả cùng quét tới 1.200 giao dịch giả**; kết quả quy về **số giao dịch giả**. Ví không bị vượt trong giới hạn 1.200 giao dịch là "chưa đạt" (chỉ biết chi phí > 1.200).
Thời gian chạy (CPU, 1 tiến trình): ADAPTIVE 14–41 phút mỗi lần; TOH+TIH 47–87 phút; BPH 43–70 phút; STC 17–38 phút; MWR 18–41 phút. Tổng 45 lần chạy (7 tấn công × 3 mô hình × 3 seed) khoảng 31 giờ.

**(a) `ADAPTIVE-STC-LV`, 3 seed — tỉ lệ ví phishing bị vượt (%) khi dùng tối đa N giao dịch giả** (trung bình ± độ lệch chuẩn giữa seed):

| Mô hình | ≤ 30 giao dịch | ≤ 60 giao dịch | ≤ 120 giao dịch | ≤ 300 giao dịch | ≤ 600 giao dịch | ≤ 1200 giao dịch |
|---|---|---|---|---|---|---|
| `peaegnnv2` | 2,3 ± 1,7 | 5,9 ± 2,9 | 13,1 ± 4,6 | 34,1 ± 6,8 | 51,1 ± 10,5 | 66,6 ± 17,2 |
| `graphsage` | 2,5 ± 1,7 | 3,1 ± 1,8 | 4,6 ± 2,2 | 7,3 ± 2,4 | 11,2 ± 2,4 | 15,0 ± 2,0 |
| `gatv2` | 1,0 ± 0,4 | 1,7 ± 0,6 | 2,6 ± 0,4 | 4,2 ± 1,2 | 5,6 ± 1,8 | 6,8 ± 1,7 |

Tỉ lệ ở 1.200 giao dịch theo từng seed (42 / 43 / 44 / trung bình ± độ lệch chuẩn):

| Mô hình | seed 42 | seed 43 | seed 44 | Trung bình |
|---|---|---|---|---|
| `peaegnnv2` | 52,2 | 56,7 | 90,8 | 66,6 ± 17,2 |
| `graphsage` | 12,3 | 15,9 | 16,9 | 15,0 ± 2,0 |
| `gatv2` | 4,7 | 8,9 | 6,7 | 6,8 ± 1,7 |

**(b) Số giao dịch giả cần để vượt 10% / 25% / 50% số ví** (ADAPTIVE; trung bình ± độ lệch chuẩn, trong ngoặc: seed 42 · 43 · 44):

| Mô hình | 10% số ví | 25% số ví | 50% số ví |
|---|---|---|---|
| `peaegnnv2` | 130 ± 37  (180 · 120 · 90) | 260 ± 57  (300 · 300 · 180) | 840 ± 321  (1200 · 900 · 420) |
| `graphsage` | 580 ± 226  (900 · 420 · 420) | chưa đạt trong 1.200 | chưa đạt trong 1.200 |
| `gatv2` | chưa đạt trong 1.200 | chưa đạt trong 1.200 | chưa đạt trong 1.200 |

Với `peaegnnv2`: khoảng **130 giao dịch giả cho 10% số ví**, khoảng 260 cho 25%, khoảng 840 cho 50%. Mỗi giao dịch tốn khoảng 0,0012 ETH tiền gas (trung bình, từ lần đo trước; chưa quy ra USD), nên 130 giao dịch ≈ 0,16 ETH, 1.200 giao dịch ≈ 1,5 ETH.

**(c) Bảy tấn công, 3 seed — tỉ lệ ví phishing bị vượt (%) khi dùng tối đa 1.200 giao dịch giả** (trung bình ± độ lệch chuẩn giữa seed 42/43/44; sau dấu "·": số giao dịch cần để vượt 10% số ví, khoảng giữa các seed; "–" = chưa đạt trong 1.200; in đậm = tấn công mạnh nhất của mô hình đó):

| Tấn công | `peaegnnv2` | GraphSAGE | GATv2 |
|---|---|---|---|
| TOH | 42,4 ± 3,7 · 10%: 30–50 | 7,1 ± 3,0 · 10%: 700 (1/3 seed) | 18,4 ± 2,5 · 10%: 50–200 |
| TIH | 16,7 ± 10,3 · 10%: 500–700 (2/3 seed) | 5,9 ± 1,9 · 10%: – | **33,2 ± 7,5** · 10%: 300–500 |
| BPH-T2P | 41,9 ± 5,9 · 10%: 40–100 | 6,2 ± 2,2 · 10%: – | 14,7 ± 1,9 · 10%: 300–600 |
| BPH-P2T | 4,4 ± 0,6 · 10%: – | 4,0 ± 2,7 · 10%: – | 6,5 ± 1,9 · 10%: – |
| MWR (vòng về target) | 4,7 ± 1,2 · 10%: – | 4,8 ± 3,0 · 10%: – | 3,1 ± 1,5 · 10%: – |
| STC | 23,1 ± 5,3 · 10%: 40–200 | 8,2 ± 3,0 · 10%: 600 (1/3 seed) | 5,0 ± 1,9 · 10%: – |
| ADAPTIVE-STC-LV | **66,6 ± 17,2** · 10%: 90–180 | **15,0 ± 2,0** · 10%: 420–900 | 6,8 ± 1,7 · 10%: – |

Số ví phishing đủ điều kiện (bắt đúng lúc sạch): `peaegnnv2` 462 / 443 / 446 · GraphSAGE 470 / 454 / 461 · GATv2 382 / 392 / 405 (seed 42/43/44).

**Nhận xét (đã có 3 seed cho cả 7 tấn công):**
1. **Không có một "mốc" duy nhất.** Đường cong tăng mượt, không có mức nào mô hình sụp đột ngột; nên báo "chi X giao dịch thì Y% số ví bị vượt". Lợi ích biên giảm dần.
2. **Tấn công nào hiệu quả phụ thuộc kiến trúc.** `peaegnnv2`: TOH (42,4 ± 3,7) và BPH-T2P (41,9 ± 5,9) ổn định và rẻ; ADAPTIVE mạnh nhất nhưng biến thiên lớn (66,6 ± 17,2); STC 23,1 ± 5,3; TIH thay đổi mạnh (2,6 / 26,9 / 20,6); BPH-P2T và MWR luôn thấp (≈ 4–5%). GATv2: TIH mạnh nhất (33,2 ± 7,5), ADAPTIVE yếu nhất. GraphSAGE: mọi tấn công ≤ 15,0%, mạnh nhất là ADAPTIVE. **Chưa có bằng chứng về cơ chế;** không nên viết cơ chế vào báo cáo.
3. **Trường hợp xấu nhất qua các tấn công** (cho một mô hình): `peaegnnv2` 66,6% (ADAPTIVE), GraphSAGE 15,0% (ADAPTIVE), GATv2 33,2% (TIH). Nếu chỉ dùng ADAPTIVE thì GATv2 trông bền (6,8%) trong khi TIH vượt tới 33%; nên báo trường hợp xấu nhất, không chỉ một tấn công.
4. **Rẻ nhất khác mạnh nhất (với `peaegnnv2`).** TOH rẻ hơn ADAPTIVE ở ngân sách thấp (≈ 30 giao dịch: 10,6 ± 1,4% so với 2,3 ± 1,7%; ≈ 100 giao dịch: 19,3% so với 8,4% ở 90 giao dịch của ADAPTIVE). Từ khoảng 300 giao dịch ADAPTIVE nhỉnh hơn (34,1 ± 6,8% so với 29,2 ± 1,5% của TOH; chênh lệch nhỏ hơn biến thiên giữa seed của ADAPTIVE) và rõ ở 1.200 giao dịch (66,6% so với 42,4%).
5. **`peaegnnv2` biến thiên rất lớn giữa các seed** (ADAPTIVE 52,2 / 56,7 / 90,8; TIH 2,6 / 26,9 / 20,6), nên khi so sánh các tấn công phải đọc cùng độ lệch chuẩn.
6. **Cơ hội cho phần phòng thủ:** với `peaegnnv2`, hai tấn công *đã biết* (TOH, BPH-T2P) có ASR ban đầu ~42%, nên đo được cải thiện của phòng thủ ngay trên tấn công đã biết (ở mô hình cũ chúng chỉ ~1%, không có chỗ cải thiện).
7. Đây là chi phí của **họ tấn công này** (cấu trúc cố định), không phải chi phí tối thiểu tuyệt đối; "vượt" = lần đầu xác suất phishing < 0,5 khi tăng dần ngân sách. Số ví đủ điều kiện khác nhau giữa mô hình (382–470), nên so sánh giữa mô hình chỉ mang tính tham khảo.

### 3.6 Độ nhạy đặc trưng (RQ2) — 3 mô hình × 3 seed

**Cách đo:** với các ví phishing mô hình bắt đúng lúc sạch, **thay trực tiếp giá trị đặc trưng** (không qua giao dịch, **không phải tấn công on-chain**) ở từng phần của đồ thị, rồi đo tỉ lệ ví bị đổi nhãn. Đối chứng: thay bằng giá trị điển hình của ví phishing (hoặc mẫu thật từ graph phishing). **Các dòng thay bằng một vector hằng số bị bỏ** (lật ~100% ở một số mô hình là hiện tượng nhân tạo ngoài phân phối). Chạy `diag_feature_sensitivity.py`, khoảng 13–19 phút mỗi lần.

**Bảng A. Thay đặc trưng của CHÍNH ví bằng giá trị điển hình của ví normal: % ví phishing bị lật** (trung bình ± độ lệch chuẩn giữa 3 seed)

| Thay phần nào | `peaegnnv2` | GraphSAGE | GATv2 |
|---|---|---|---|
| Tất cả đặc trưng của ví | **20,6 ± 9,2** | 3,7 ± 1,3 | 4,3 ± 1,7 |
| số đối tác khác nhau (unique peers) | **12,0 ± 5,3** | 5,4 ± 1,9 | 5,0 ± 2,4 |
| số giao dịch vào/ra (counts) | 3,1 ± 0,6 | 1,2 ± 0,4 | 1,0 ± 0,3 |
| tổng giá trị / giá trị trung bình | 0,1 ± 0,1 | 0,1–0,2 | 0,1 ± 0,1 |
| thời gian hoạt động | 1,0 ± 1,3 | 0,5 ± 0,3 | 0,0 |
| (đối chứng) thay bằng điển hình phishing | 2,1 ± 0,6 | 1,1 ± 0,9 | 0,6 ± 0,1 |

**Bảng B. Thay hàng xóm bằng MẪU THẬT** — mỗi ô: mẫu từ normal / đối chứng (mẫu từ phishing) / **hiệu** (điểm %; chỉ phần này mới là bằng chứng mô hình đọc "độ giống normal" của hàng xóm, phần còn lại là nhiễu do chính việc thay thế)

| Thay phần nào | `peaegnnv2` | GraphSAGE | GATv2 |
|---|---|---|---|
| Hàng xóm bậc 1 | 20,1 / 6,7 / **+13,4 ± 13,3** | 98,3 / 71,6 / **+26,7 ± 5,0** | 0,7 / 1,2 / −0,5 ± 0,2 |
| Hàng xóm bậc 2 | 15,2 / 11,5 / +3,7 ± 3,2 | 49,2 / 35,4 / **+13,8 ± 4,9** | 0,1 / 0,0 / +0,1 |
| Bậc 1 + bậc 2 | 36,3 / 12,8 / +23,5 ± 15,4 | 99,9 / 85,8 / **+14,0 ± 2,5** | 0,0 / 0,0 / 0,0 |

**Kết luận giữ được qua cả 3 seed:**
1. Đặc trưng **giá trị tiền và thời gian hoạt động gần như không ảnh hưởng** (≤ 1% ở mọi mô hình, mọi seed). Khớp với phép thử trước: tấn công giá trị lớn gấp ~1.000 lần không mạnh hơn.
2. Trong đặc trưng của chính ví, **"số đối tác khác nhau" là nhóm nhạy nhất ở cả 9 lần chạy** (hơn "số giao dịch vào/ra").
3. **GraphSAGE** nhất quán dựa vào hàng xóm (hiệu bậc 1 +26,7 ± 5,0; bậc 2 +13,8 ± 4,9); chính ví chỉ lật 3,7%.
4. **GATv2** gần như không nhạy khi thay đặc trưng (≤ 5% ở chính ví, ≈ 0% ở hàng xóm). Thay hàng xóm còn làm xác suất phishing **tăng** (+0,10 đến +0,25) ở cả 3 seed; **chưa giải thích được**.
5. **`peaegnnv2` thay đổi giữa các seed:** seed 42 dựa vào hàng xóm bậc 1 (hiệu +32,1), seed 43 và 44 dựa vào đặc trưng của chính ví (lật 18,1% và 33,0%; hiệu của bậc 1 chỉ +2,7 và +5,4). **Kết luận "hàng xóm bậc 1 là yếu tố nhạy nhất của `peaegnnv2`" ở bản trước (chỉ seed 42) không giữ được.**

**Quan sát (chưa kiểm chứng):** `peaegnnv2` có độ nhạy với đặc trưng chính ví lần lượt 10,8 / 18,1 / 33,0% (seed 42/43/44) và mức bị ADAPTIVE vượt ở 1.200 giao dịch là 52,2 / 56,7 / 90,8% — hai chuỗi cùng tăng. Trên cả 9 mô hình (3 kiến trúc × 3 seed), tương quan thứ hạng Spearman giữa hai đại lượng này là 0,76 (p ≈ 0,017). **Giá trị p không đáng tin** vì các điểm cùng kiến trúc không độc lập và chỉ có 9 điểm; chỉ nên ghi như một gợi ý: mô hình càng dựa vào đặc trưng của chính ví (số đối tác, số giao dịch) thì càng dễ bị ADAPTIVE vượt, vì ADAPTIVE thay đổi đúng các đặc trưng đó. Lưu ý: TIH của `peaegnnv2` (2,6 / 26,9 / 20,6%) **không** tăng theo độ nhạy này (10,8 / 18,1 / 33,0%), nên hiện tượng đó không giải thích được TIH.

**Hạn chế:** thay giá trị đặc trưng trực tiếp, và thay **toàn bộ** hàng xóm là can thiệp mạnh hơn nhiều so với việc tấn công thật có thể làm. "Nhạy" không đồng nghĩa "dễ bị tấn công thật": GraphSAGE phụ thuộc hàng xóm nhiều nhất nhưng ít bị tấn công thật nhất (ADAPTIVE 15,0%); lý do có thể là tấn công chỉ thêm vài nút hoặc khác kiểu, nhưng đây là giả thuyết chưa kiểm chứng. Với GATv2, tấn công lật được (TIH 41,6%) dù phép thử này không thấy nó nhạy với đặc trưng, gợi ý yếu tố là **số lượng/cấu trúc** nút thêm vào; cũng chưa kiểm chứng.

### 3.7 Cơ sở thực tế của 7 tấn công (câu hỏi của thầy: ngoài đời kẻ tấn công áp dụng thế nào)

**Trả lời ngắn:** các thao tác tương tự (phân tán/gom tiền qua nhiều ví, chuyển qua ví trung gian, chia nhỏ giao dịch rải theo thời gian, gửi dust hàng loạt) **đã được ghi nhận ngoài đời**, nhưng mục đích thật của chúng là che dấu vết dòng tiền, né quy tắc giám sát, hoặc lừa nạn nhân (address poisoning), **chưa phải qua mặt mô hình học máy phát hiện lừa đảo**. Khóa luận dùng chúng như các cách thay đổi đồ thị quanh ví phishing với chi phí thấp để kiểm tra độ bền của mô hình. Việc kẻ lừa đảo thật sự dùng chúng để qua mặt mô hình là **giả định của mô hình đe dọa**; trong các nguồn đã tra chưa tìm thấy bằng chứng ngoài đời cho điều này (không có nghĩa là chưa từng xảy ra).

| Tấn công | Nguồn mẫu | Thao tác tương tự ngoài đời và mục đích thật | Giả định trong khóa luận |
|---|---|---|---|
| TOH | Hide and Seek [1] | Phân tán tiền ra nhiều ví [2]; làm khó truy vết | Ví phụ nhận tiền để đổi đặc trưng "ra" của ví phishing |
| TIH | [1] | Gom tiền về một ví (fan-in) [3]. Gửi dust/giao dịch giá trị 0 là chiêu address poisoning [4][5], nhưng tới ví **nạn nhân** | Ví phụ gửi vào chính ví phishing |
| BPH-T2P / BPH-P2T | [1] | Chuyển qua ví trung gian ("hops") trong rửa tiền [6]; che giấu nguồn gốc tiền | Ví trung gian đổi vùng lân cận 2 bước |
| STC | Nhóm thiết kế | Chia nhỏ và rải theo thời gian để né quy tắc ngưỡng/tốc độ [3]; gửi lặp dưới ngưỡng cảnh báo (structuring) [7]; dust hàng loạt rất rẻ [4] | Nhiều giao dịch giá trị thấp trải 30 ngày dồn về một ví phụ |
| MWR (vòng về target) | Nhóm thiết kế | Quay vòng qua nhiều đối tác/ví làm đồ thị phức tạp [8] | Tiền đi vòng qua 2 ví phụ rồi về ví phishing |
| ADAPTIVE-STC-LV | Nhóm thiết kế (bổ sung ngoài đề cương) | Không có thao tác nguyên khối ngoài đời; là **tổ hợp** của các thành phần trên | Đọc lịch sử công khai của ví, thêm giao dịch nhỏ theo hướng cân bằng vào/ra. **Không biết hay hỏi mô hình phát hiện** |

**Ba lớp bằng chứng cần tách bạch:** (i) thao tác có thật ngoài đời; (ii) nguồn học thuật của mẫu tấn công (bốn tấn công đầu từ [1]; STC, MWR và ADAPTIVE do nhóm thiết kế; khóa luận không nhận là đề xuất bốn tấn công đầu); (iii) giả định của mô hình đe dọa (chưa có bằng chứng ngoài đời).
**Giới hạn:** tương tự không có nghĩa là đồng nhất (address poisoning gửi dust tới ví nạn nhân, còn các tấn công ở đây gửi vào chính ví phishing); các nguồn về thực tế ngoài đời phần lớn là tài liệu của công ty phân tích blockchain và bài báo, chưa phải bằng chứng học thuật chặt chẽ; nguồn Chainalysis [6] mới đọc qua bản tóm tắt. Bản chi tiết (kèm chi phí gas và ASR từng tấn công) ở file Word `CoSoThucTe_7TanCong.docx`.

---

## 4. Stage 7 — Phòng thủ

> **Lưu ý đọc mục 4:** toàn bộ kết quả phòng thủ dưới đây xây trên **PEAE-style (cũ)** (nền SAGE). Phòng thủ cho `peaegnnv2` xem mục 4.7.

### 4.1 Phương pháp
- **Dữ liệu huấn luyện đối kháng (`make_pool`):** 4.788 mẫu (2 mẫu/ví phishing train), sinh **chỉ từ 4 tấn công đã biết** (TOH 1.231, TIH 1.159, BPH-T2P 1.211, BPH-P2T 1.187), cutoff T1 của tập train, 10 mẫu bị bỏ do giao dịch giả vượt mốc cắt. Mất 22,6 phút, file ~960 MB.
- **Tấn công chưa thấy (chỉ để kiểm tra):** STC, MWR (vòng), ADAPTIVE-STC-LV (và ADAPTIVE-STC làm đối chứng).
- **Phương pháp:**
  - `advtrain_peae`: PEAE-style + mẫu đối kháng (mỗi epoch thêm ~50% số ví phishing).
  - `ra_peae`: nền PEAE-style, lớp tích chập có **trọng số tin cậy cạnh** r(e) = sigmoid(MLP([h_nguồn, h_đích, đặc trưng cạnh])) + hạng tử nhất quán (KL) giữa **đúng cặp** mẫu sạch–mẫu đối kháng của cùng một ví (trọng số 0,5).
  - `ra_peae_noedge`: đối chứng, r(e) không nhìn đặc trưng cạnh.
- Huấn luyện trên Kaggle: 9 lần (3 phương pháp × 3 seed), khoảng 40,6 phút. Đánh giá trên máy cá nhân.

> **Khác đề cương:** đề cương mô tả r(e) tính từ tuổi quan hệ, tần suất tương tác, độ nhất quán thời gian/giá trị và lịch sử hai đầu mút. Bản đã làm là MLP học từ đặc trưng hai đầu mút + value/gas của cạnh (đã bỏ timestamp). "Ablation từng thành phần của reliability score" trong đề cương **chưa làm được**.

### 4.2 Hiệu năng sạch (3 seed)

| Mô hình | Macro-F1 (%) | Recall phishing (%) | Δ Macro-F1 so với gốc (điểm %) |
|---|---|---|---|
| PEAE-style gốc | 88,1 ± 0,3 | 82,8 ± 0,6 | — |
| `advtrain_peae` | 88,7 ± 0,7 | 84,0 ± 1,3 | +0,6 ± 0,5 |
| `ra_peae` | 87,6 ± 2,0 | 80,2 ± 4,8 | −0,5 ± 1,9 |
| `ra_peae_noedge` | 88,5 ± 0,1 | 83,0 ± 1,2 | +0,4 ± 0,2 |

`ra_peae` seed 44 huấn luyện kém (dừng ở epoch 17, F1 validation 0,755, F1 test 0,849) — đã báo cáo đủ cả 3 seed, không loại bỏ.

### 4.3 ASR trước các tấn công (%, trung bình các ngân sách b = 5, 20, 100)

| Mô hình | TOH | TIH | BPH-T2P | BPH-P2T | STC | MWR | **ADAPTIVE-STC-LV** | ASR_any |
|---|---|---|---|---|---|---|---|---|
| PEAE-style gốc | 1,7 | 0,8 | 1,2 | 1,3 | 3,6 | 0,1 | **27,8 ± 6,9** | 43,7 ± 8,5 |
| `advtrain_peae` | 0,7 | 0,0 | 0,3 | 0,7 | 2,7 | 0,1 | **13,0 ± 5,5** | 24,7 ± 6,5 |
| `ra_peae` | 1,0 | 0,2 | 0,7 | 0,4 | 3,7 | 0,4 | **11,2 ± 1,2** | 20,2 ± 3,2 |
| `ra_peae_noedge` | 0,3 | 0,2 | 0,3 | 0,1 | 1,5 | 0,2 | **21,3 ± 4,7** | 34,5 ± 4,9 |

- Các tấn công đã biết có ASR gốc ~1,2% → **không có chỗ để đo cải thiện**. Lợi ích đo được nằm ở `ADAPTIVE-STC-LV` (tấn công "chưa thấy" nhưng cùng họ: thêm ví giả và cạnh nhỏ).
- **Đối chứng giá trị lớn** (`ADAPTIVE-STC`, giá trị gấp ~1.000 lần): ASR trung bình gốc 27,6 · `advtrain` 11,0 · `ra_peae` 10,7 · `noedge` 20,2 → gần như y hệt. Phòng thủ không dựa vào dấu vết "giá trị nhỏ".

### 4.4 Số đo không phụ thuộc ngưỡng (kiểm tra mô hình có "nghiêng về phishing" không)

Vì `advtrain` đoán phishing nhiều hơn (xem 5.3), đã so sánh **ở cùng tỉ lệ báo nhầm 10%** (`ADAPTIVE-STC-LV`, b=100):

| Mô hình | AUC sạch | AUC khi bị tấn công | Recall sạch | Recall khi bị tấn công | Δ so với gốc (ghép theo seed) |
|---|---|---|---|---|---|
| Gốc | 0,958 ± 0,003 | 0,878 ± 0,024 | 86,9% | 62,4 ± 8,8% | — |
| `advtrain_peae` | 0,962 ± 0,004 | 0,919 ± 0,003 | 87,7% | 74,1 ± 2,6% | +11,7 ± 6,7 điểm (3/3 seed) |
| `ra_peae` | 0,956 ± 0,008 | 0,932 ± 0,006 | 86,3% | 79,7 ± 2,6% | +17,3 ± 6,2 điểm (3/3 seed) |
| `ra_peae_noedge` | 0,960 ± 0,003 | 0,891 ± 0,009 | 87,4% | 67,6 ± 1,4% | +5,2 ± 10,1 điểm (2/3 seed) |

→ Lợi ích của phòng thủ là **thật**, không chỉ do lệch ngưỡng. Kết quả lặp lại với `ADAPTIVE-STC` giá trị lớn (+13,7 · +17,5 · +5,7 điểm).

### 4.5 Kiểm định ghép cặp (bootstrap tiêu chuẩn 95% trên target test, 1.000 lần)

Recall tại FPR 10% khi bị tấn công, Δ theo từng seed (42 / 43 / 44), `+` = khoảng tin cậy nằm hẳn về phía dương:

| So sánh | b=20 | b=100 |
|---|---|---|
| `ra_peae` − gốc | +8,2 + · +12,3 + · +21,4 + | +10,9 + · +15,3 + · +25,8 + |
| `advtrain_peae` − gốc | +10,6 + · +13,5 + · +11,8 + | +3,5 · +11,6 + · +20,0 + |
| `ra_peae` − `advtrain_peae` | −2,4 · −1,2 · +9,6 + | +7,4 + · +3,7 + · +5,7 |

(Bản giá trị lớn `ADAPTIVE-STC`: `ra_peae` − `advtrain_peae` ở b=100 là +3,2 / +2,2 / +5,9, **không** seed nào có CI nằm hẳn về phía dương.)

- `ra_peae` hơn mô hình gốc nhất quán. **`ra_peae` hơn `advtrain_peae` chỉ là gợi ý ở ngân sách lớn**, chưa đủ để kết luận.
- ΔAUC sạch giữa các mô hình nhỏ (từ −0,010 đến +0,010).
- Bootstrap chỉ phản ánh độ bất định do **chọn mẫu target**, không gồm biến thiên giữa các seed huấn luyện (chỉ 3 seed).

### 4.6 Tỉ lệ phishing thấp (thay cho Stage 4 gốc)

Giữ nguyên 814 ví normal của tập test, lấy mẫu con ví phishing để được 1:5 và 1:10 (200 lần lấy mẫu). `ADAPTIVE-STC-LV`, b=100, precision tính tại FPR 10%:

| Tỉ lệ phishing : normal | PR-AUC sạch (gốc) | PR-AUC khi tấn công: gốc / `advtrain` / `ra_peae` | Precision@FPR10% khi tấn công: gốc / `advtrain` / `ra_peae` |
|---|---|---|---|
| thực (594 : 814) | 0,943 | 0,776 / 0,842 / 0,864 | 0,817 / 0,844 / 0,853 |
| 1 : 5 | 0,848 | 0,503 / 0,613 / 0,651 | 0,551 / 0,595 / 0,613 |
| 1 : 10 | 0,768 | 0,346 / 0,456 / 0,497 | 0,380 / 0,424 / 0,442 |

Ở 1:10, ngay cả khi không bị tấn công, với FPR 10% thì precision chỉ ~0,46 (đa số cảnh báo là báo nhầm). Phòng thủ giữ lại khoảng 4–6 điểm precision và 0,11–0,15 PR-AUC dưới tấn công.

> **Khác đề cương:** đề cương hứa **bổ sung ví normal mới** (Stage 4: 704 : 3.520). Đã làm bằng cách giảm số ví phishing; Stage 4 gốc dựng graph K=1 nên không dùng được với mô hình K=2. Chỉ có họ PEAE-style (xác suất của GraphSAGE/GATv2 không được lưu).

### 4.7 Phòng thủ cho `peaegnnv2` (mô hình chính mới)

- **Đã viết, chưa chạy:** `advtrain_peaev2` (huấn luyện đối kháng trên nền `peaegnnv2`: cùng tập mẫu đối kháng `adv_pool_train.pkl`, cùng hàm mất mát gốc = cross-entropy + 0,1 × học đối sánh, trên batch gồm mẫu sạch và mẫu đối kháng; tự đặt batch 16) và các tên `baseline_peaev2`, `advtrain_peaev2` ở lệnh `eval`. Test bằng mô hình giả (đường chạy), chưa chạy GPU thật.
- **Chưa có:** `ra_peaev2` (cơ chế độ tin cậy cạnh). `ra_peae` dựa trên lớp SAGE với trọng số tin cậy nhân vào từng thông điệp; `peaegnnv2` dùng attention GATv2, không có chỗ nhân trọng số đó nên cần thiết kế một lớp attention mới.
- **Hệ quả:** nếu `peaegnnv2` là mô hình chính, chương phòng thủ chỉ còn huấn luyện đối kháng; RQ4 (RA vs huấn luyện đối kháng) chỉ trả lời được trên mô hình cũ.
- Ước tính (chưa đo): 75 giây/epoch, 40–75 phút mỗi seed trên Kaggle.

---

## 5. Stage 8 — Đối chiếu trên XBlock D2

### 5.1 Dữ liệu D2 (đo thực tế)
- 1.660 ví phishing + 1.700 normal. CSV có 10 cột (README chỉ liệt kê 6), **`Value` tính bằng ETH** (đã đổi sang wei), **không có gas**, thời gian thực tế 2015-08 → 2019-10.
- Có bậc 2 cho 1.265/1.660 ví phishing (76%) và 1.590/1.700 ví normal (94%).
- Chuyển về bố cục pipeline bằng `convert_d2.py` (khoảng 13 phút). Lọc: 5–2.000 giao dịch, bỏ địa chỉ `0x00…0`, **chỉ giữ ví có thư mục bậc 2**.

| Lớp | File thô | Giữ lại | Bị loại |
|---|---|---|---|
| Phishing | 1.660 | **949** | 437 (<5 giao dịch), 274 (thiếu bậc 2) |
| Normal | 1.700 | **1.159** | 478 (<5), 47 (thiếu bậc 2), 15 (>2.000), 1 (địa chỉ hủy) |

Chia theo thời gian (T1 = 2018-04-23, T2 = 2018-07-12): train 1.264 (30% phishing) · val 422 (79%) · test 422 (56%) → rất lệch lớp, nên **không dùng để huấn luyện lại**.

### 5.2 Mức A — chuyển trực tiếp (không huấn luyện lại), toàn bộ 2.108 ví (45% phishing)

| Mô hình | Macro-F1 (ngưỡng 0,5) | PR-AUC | ROC-AUC | Recall phishing | Tỉ lệ đoán phishing | Recall lớp normal |
|---|---|---|---|---|---|---|
| GraphSAGE | 0,636 ± 0,038 | 0,805 ± 0,019 | 0,812 ± 0,017 | 0,887 | 70% | 45% |
| GATv2 | 0,589 ± 0,041 | 0,654 ± 0,044 | 0,727 ± 0,029 | 0,869 | 73% | 39% |
| PEAE-style | 0,691 ± 0,050 | 0,824 ± 0,009 | 0,861 ± 0,006 | 0,914 | 68% | 52% |
| `advtrain_peae` | 0,598 ± 0,057 | 0,849 ± 0,015 | 0,866 ± 0,008 | 0,947 | 78% | 36% |

(Đối chiếu test 2026: macro-F1 0,866 / 0,815 / 0,881 cho GraphSAGE / GATv2 / PEAE-style.)

- Xếp hạng vẫn tốt hơn nhiều so với đoán ngẫu nhiên (PR-AUC ngẫu nhiên ≈ 0,45), thứ tự kiến trúc giống dữ liệu 2026.
- Macro-F1 thấp vì mô hình **đoán quá nhiều phishing** trên D2 (68–78% so với 45% thực tế) — ngưỡng 0,5 học từ dữ liệu 2026 không còn phù hợp.
- `advtrain_peae` đoán nhiều phishing nhất nhưng AUC không thấp hơn mô hình gốc: macro-F1 thấp của nó là do lệch ngưỡng.
- **Không tách được** phần đóng góp của: khác thời kỳ, khác phân bố giá trị giữa hai lớp, chọn mẫu theo dữ liệu bậc 2 (loại 22% ví phishing đủ giao dịch so với 4% ví normal), thiếu gas.
- Mô hình RA (`ra_peae`) **không được đánh giá** trên D2 vì D2 không có gas.
- **Chưa làm:** mức B (huấn luyện lại trên D2), mức C (tấn công trên D2), D1 (không có dữ liệu).

---

## 6. Lỗi đã phát hiện và sửa trong quá trình làm

| Vấn đề | Hậu quả nếu không sửa | Cách xử lý |
|---|---|---|
| Dựng K=2 giữ cả hàng xóm xuất hiện **sau** mốc cắt | Rò rỉ thông tin tương lai ở tập train/val | Lọc hàng xóm theo mốc cắt trước khi dựng node |
| Giao dịch tạo contract (`to` rỗng) sinh node hop-2 cô lập (5.497 node) | Nhiễu cấu trúc | Bỏ qua giao dịch này khi tìm hop-2; thêm kiểm tra tự động (node cô lập = 0, cạnh sau cutoff = 0) |
| Stage 6/7 dựng lại graph bằng hàm K=1 | ASR sai (clean K=2 vs attacked K=1) | Dùng chính hàm dựng K=2 của 9c |
| MWR trùng cấu trúc với BPH-T2P ở K=2 | "Tấn công chưa thấy" thực chất là đã thấy | Thiết kế lại MWR vòng về target |
| Giao dịch giả có gas cố định 20 gwei | "Chữ ký" giúp mô hình RA nhận diện | Lấy mẫu gas từ lịch sử của chính ví |
| Consistency loss ghép ngẫu nhiên clean/adv | Ép dự đoán adv về dự đoán của ví khác | Ghép đúng cặp (cùng một ví) |
| Mẫu đối kháng huấn luyện dựng ở mốc T_end thay vì T1 | Lịch sử dài hơn, tạo đường tắt thời gian | Dùng cutoff T1, giao dịch giả nằm trong cửa sổ quan sát |
| Đặc trưng `first_ts`, `last_ts` tuyệt đối | Có thể học "thời điểm → nhãn" | Bỏ khỏi đặc trưng |
| `GREEDY-QUERY` (tên cũ "GRADIENT") dùng lại cùng ví giả ở mọi bước, báo AMT = 0 | Kết quả sai | Cấp phát ví khác nhau mỗi bước; đếm số giao dịch thật; dừng sớm khi đã lật |
| So sánh phòng thủ chỉ bằng ASR ở ngưỡng 0,5 | Lẫn hiệu ứng "mô hình nghiêng về phishing" | Thêm số đo ở cùng FPR + AUC khi bị tấn công |
| Stage 8 cũ (K=1, giả định cột, số so sánh lỗi thời, đường dẫn `E:\`) | Kết quả không so sánh được | Viết lại: chuyển D2 → pipeline K=2, đánh giá bằng đúng bộ dựng |
| Kết luận "hàng xóm bậc 1 là yếu tố nhạy nhất của `peaegnnv2`" rút ra từ 1 seed | Sai khi có thêm seed (hiệu bậc 1: +32,1 / +2,7 / +5,4) | Chạy 3 seed; báo trung bình ± độ lệch chuẩn và kết quả từng seed |
| Nhận định "với `peaegnnv2`, thao tác đưa vào ví (TIH) vô hại" từ 1 seed | Sai: TIH 2,6 / 26,9 / 20,6% qua 3 seed | Chạy đủ 3 seed cho cả 7 tấn công |
| So sánh các tấn công ở cùng con số ngân sách b | Mỗi đơn vị b là 1–6 giao dịch → so sánh không công bằng về chi phí | Quy về **số giao dịch giả**; chạy theo nhóm với lưới ngân sách riêng, cùng quét tới 1.200 giao dịch |
| Nhận định "ADAPTIVE là tấn công mạnh nhất" và "sáu tấn công gốc vô hại" | Chỉ đúng với một vài mô hình/ngân sách | Sửa theo kết quả chi phí tối thiểu (mục 3.5) |
| Công cụ chạy song song: tên file log chứa `/` và `[ ]` | Không tạo được file log, đợt chạy dừng ngay (chưa mất thời gian chạy) | Tên log an toàn (`..._sh2of8.log`); một lần lỗi không làm sập cả đợt |

---

## 7. Hạn chế (bắt buộc ghi khi trích dẫn kết quả)

1. "PEAE-style (cũ)" là **bản xấp xỉ** PEAE-GNN; `peaegnnv2` (mô hình chính) **chưa xác nhận khớp bài báo gốc**, huấn luyện với batch 16 (khác ba mô hình còn lại, batch 64) và kém hơn bản cũ về hiệu năng sạch.
2. Chỉ **3 seed**; độ lệch chuẩn chỉ phản ánh khởi tạo khác nhau. Cả 7 tấn công đã đo chi phí tối thiểu với 3 seed, nhưng `peaegnnv2` biến thiên rất lớn giữa seed (ADAPTIVE: 52,2 / 56,7 / 90,8%; TIH: 2,6 / 26,9 / 20,6%), nên thứ hạng giữa các tấn công phải đọc cùng độ lệch chuẩn. Bootstrap (Stage 7) chỉ phản ánh độ bất định do chọn mẫu test.
3. Các tấn công đều **cố định**: không thích ứng theo mô hình, cũng không biết gradient hay truy vấn mô hình (không có tấn công white-box). "Adaptive" trong ADAPTIVE-STC-LV nghĩa là thích ứng theo **lịch sử công khai của ví**, không phải theo mô hình. Chưa có tấn công thích ứng vào mô hình đã phòng thủ.
4. Chi phí tối thiểu chỉ là chi phí của **họ tấn công đã thử** (cấu trúc cố định), không phải tối thiểu tuyệt đối; "vượt" = lần đầu xác suất phishing < 0,5 khi tăng dần ngân sách; ví không vượt được trong 1.200 giao dịch là "chưa đạt".
5. **Chưa kiểm tra số dư tài khoản và chi phí gas thực**; "khả thi on-chain" chỉ ở mức ràng buộc cấu trúc và thời gian. Chi phí gas tính theo trung bình ~0,0012 ETH/giao dịch, chưa quy ra USD.
6. ASR chỉ tính trên các ví phishing mô hình bắt đúng lúc sạch (mẫu số khác nhau giữa các mô hình: 382–470 ví).
7. "Chưa thấy" (STC, MWR, ADAPTIVE) chỉ có nghĩa không dùng trong huấn luyện đối kháng, **không** có nghĩa khác họ với các tấn công đã biết.
8. Chia tập theo thời gian khiến tỉ lệ lớp lệch giữa các tập và F1 validation thấp hơn F1 test.
9. Phép thử độ nhạy đặc trưng là thay giá trị trực tiếp (không phải giao dịch thật), thay toàn bộ hàng xóm; mọi giả thuyết cơ chế (vì sao hàng xóm/đặc trưng chính ví quan trọng, vì sao GATv2 bị TIH lật, vì sao thay hàng xóm làm xác suất của GATv2 tăng) **chưa kiểm chứng**; tương quan Spearman 0,76 chỉ có 9 điểm không độc lập.
10. Phòng thủ (Stage 7) và phân tích tỉ lệ phishing thấp chỉ cho PEAE-style (cũ); chưa có cho `peaegnnv2`. Phân tích tỉ lệ thấp bằng lấy mẫu con, không thêm ví normal mới (Stage 4 gốc dựng graph K=1, không dùng được).
11. D2: khác thời kỳ, không có gas, mất dữ liệu bậc 2 không đều giữa hai lớp, chỉ đánh giá chuyển trực tiếp (mức A).
12. Nguồn về thực tế ngoài đời (mục 3.7) phần lớn là tài liệu công ty phân tích blockchain và bài báo; Chainalysis đọc qua bản tóm tắt; chưa có bằng chứng ngoài đời về việc kẻ lừa đảo dùng các thao tác này để qua mặt mô hình học máy.
13. Mô hình `ra_peae` seed 44 huấn luyện kém (dừng ở epoch 17); đã báo cáo đủ cả 3 seed.

---
## 8. Trạng thái công việc

| Hạng mục | Trạng thái |
|---|---|
| Stage 5: GraphSAGE, GATv2, PEAE-style (cũ) × 3 seed | Xong |
| Stage 5: `peaegnnv2` × 3 seed (batch 16) | **Xong** |
| Stage 6: 6 tấn công gốc (budget 1–20) × 3 mô hình cũ × 3 seed | Xong |
| Stage 6: `ADAPTIVE-STC-LV` ngân sách lớn × 3 mô hình cũ × 3 seed | Xong |
| Stage 6: chi phí tối thiểu, ADAPTIVE × (`peaegnnv2`, GraphSAGE, GATv2) × 3 seed | **Xong** |
| Stage 6: chi phí tối thiểu, 6 tấn công còn lại × 3 mô hình × 3 seed | **Xong** |
| Stage 6: chi phí tối thiểu, tổng 45 lần chạy (7 tấn công × 3 mô hình × 3 seed) | **Xong** (≈ 31 giờ CPU) |
| Stage 6: so sánh khớp số giao dịch cho PEAE-style (cũ) (`summarize_matched.py`) | Đã viết công cụ, chưa có kết quả |
| Stage 6: độ nhạy đặc trưng × 3 mô hình × 3 seed | **Xong** |
| Stage 7: phòng thủ trên PEAE-style (cũ) (advtrain, RA, RA không cạnh), đánh giá, kiểm định, AUC, tỉ lệ thấp | Xong |
| Stage 7: `advtrain_peaev2` (huấn luyện + đánh giá) | Đã viết code, **chưa chạy** |
| Stage 7: RA cho `peaegnnv2` | Chưa có thiết kế |
| Stage 8 mức A (chuyển trực tiếp D2) cho mô hình cũ | Xong; chưa chạy cho `peaegnnv2` |
| Stage 8 mức B, C; D1 | Chưa làm |
| Tấn công mới đề xuất (GGS white-box, CRING, SPOOL, TRANSFER) | **Chưa quyết**, chờ ý kiến thầy (xem mục 9) |
| Tấn công thích ứng vào mô hình đã phòng thủ | Chưa làm |
| Sửa đề cương cho khớp thực tế; viết báo cáo | Chưa làm |

**Những điểm cần sửa trong đề cương:** MWR vòng về target; mô tả đúng cơ chế r(e) (MLP học từ đặc trưng hai đầu mút + value/gas của cạnh); mô hình chính là `peaegnnv2` (chưa xác nhận khớp bài báo) và các hạn chế đi kèm; K=2 với giới hạn 500 giao dịch mỗi hàng xóm; số liệu D2 thực đo; Stage 4 thay bằng lấy mẫu con; ADAPTIVE-STC-LV là tấn công bổ sung của nhóm; các hạn chế ở mục 7.

---
## 9. Các câu hỏi của thầy và câu trả lời hiện có

**Hỏi 1: Ngoài đời, 7 phương pháp tấn công được kẻ tấn công áp dụng như thế nào?**
→ Xem mục 3.7. Tóm tắt: thao tác tương tự có thật (phân tán/gom tiền, ví trung gian, chia nhỏ theo thời gian, dust hàng loạt), nhưng mục đích thật là che dấu vết dòng tiền, né giám sát hoặc lừa nạn nhân, chưa phải qua mặt mô hình học máy; giả định này được nêu rõ là giả định của mô hình đe dọa.

**Hỏi 2: Yếu tố nào dễ bị ảnh hưởng nhất?**
→ Xem mục 3.6 (và 3.5 cho mức "loại thao tác"). Giá trị tiền và thời gian hoạt động gần như không ảnh hưởng; trong đặc trưng của chính ví, số đối tác khác nhau là nhạy nhất; GraphSAGE dựa vào hàng xóm; GATv2 hầu như không nhạy với việc thay đặc trưng; `peaegnnv2` thay đổi theo seed. Về loại thao tác (3 seed): với `peaegnnv2`, TOH và BPH-T2P ổn định hiệu quả (≈ 42%), TIH thay đổi mạnh theo seed (2,6 / 26,9 / 20,6%), BPH-P2T và MWR thấp; với GATv2, TIH nhạy nhất (≈ 33%). Chưa có bằng chứng về cơ chế.

**Hỏi 3: Phải biến đổi mẫu đến mức nào (tốn ít chi phí nhất) thì đã vượt được detector?**
→ Xem mục 3.5. Với `peaegnnv2`: **10% số ví cần khoảng 30–50 giao dịch giả (TOH), 40–100 (BPH-T2P), 90–180 (ADAPTIVE)**, tức khoảng 0,04–0,22 ETH gas; 25% cần khoảng 180–400 giao dịch; 50% chỉ đạt với ADAPTIVE (420–1.200 giao dịch). GraphSAGE chỉ có mốc 10% với ADAPTIVE (420–900 giao dịch). GATv2 có mốc 10% với TOH, TIH, BPH-T2P (khoảng 50–600 giao dịch) nhưng không với ADAPTIVE. Không có một "mốc" duy nhất.

**Hỏi 4 (đề xuất, chưa trả lời): có thêm tấn công mới (GGS white-box, CRING nhiều ví, SPOOL dùng chung ví giả, TRANSFER qua kiến trúc) không?**
→ Đề nghị **giữ 7 tấn công hiện có, không bỏ tấn công cũ** (chúng là baseline từ [1], là nền của thiết kế "huấn luyện trên tấn công đã biết, thử trên tấn công chưa thấy", và kết quả mới cho thấy chúng không yếu với `peaegnnv2` và GATv2). TRANSFER đã được bảng so sánh ba kiến trúc bao phủ (các tấn công không dùng thông tin mô hình nên cùng chuỗi giao dịch giả đã thử trên cả ba). GGS đổi mô hình đe dọa sang white-box và tốn công hơn ước tính; CRING và SPOOL là thiết lập khác. Các cột "Inspired by" và "Expected win" của bảng đề xuất là dự đoán chưa có kết quả. **Cần thầy quyết định.**

---
## 10. Danh mục file

**Mã nguồn:**
- Dựng dữ liệu và huấn luyện: `stage9_k2_upgrade.py` (dựng graph K=2) · `stage5_train_baselines.py` (bản gộp, có `peaegnnv2`, `--pkl`, `--out`).
- Tấn công: `stage6_adversarial_attacks.py` (7 tấn công; chế độ `--min_cost` và `--shard K/N`) · `run_mincost_all.py` (chạy hộ chi phí tối thiểu cho nhiều mô hình/seed; có `--parallel`, `--shards`) · `diag_feature_sensitivity.py` (độ nhạy đặc trưng).
- Phòng thủ: `stage7_defense.py` (`make_pool` / `train` / `eval`; đã thêm `advtrain_peaev2`).
- Gộp kết quả: `summarize_stage6.py` (có `peaegnnv2`) · `summarize_matched.py` (ASR theo số giao dịch giả) · `summarize_mincost.py` (chi phí tối thiểu, gộp mảnh tự động) · `summarize_diag.py` (độ nhạy đặc trưng) · `summarize_stage7.py` · `analyze_stage7_auc.py` · `stats_stage7.py`.
- D2: `inspect_d2.py` · `convert_d2.py` · `stage8_eval_d2.py`.
- Công cụ: `prepare_kaggle_upload.py` · `package_results.py` (gom kết quả + code thành 1 file zip, tự bỏ file nghi có khóa API).

**Kết quả:** `results_*` (Stage 5, 6) · `results_<mô hình>_seed<seed>_mincost_<nhóm>_full.json` · `diag_feature_<mô hình>_seed<seed>.json` · `eval_seed*.json`, `eval_probs_*.npz` (Stage 7) · `stage6_summary*.md`, `stage7_summary*.md`, `stage7_auc_analysis*.md`, `stage7_stats*.md`, `mincost_summary.md`, `diag_summary.md` · `stage8_zeroshot_d2.json`, `d2_conversion_report.json`.
**Tài liệu:** `CoSoThucTe_7TanCong.docx` (cơ sở thực tế của 7 tấn công).

---
## 11. Lệnh tái lập (rút gọn)

```
# Stage 5 (Kaggle)
python stage5_train_baselines.py --pkl <pkl> --out /kaggle/working/stage5_k2 --model all --seeds 42 43 44
python stage5_train_baselines.py --pkl <pkl> --out /kaggle/working/stage5_v2 --model peaegnnv2 --seeds 42 43 44 --bs 16

# Stage 6: ASR tại ngân sách cố định (máy có dữ liệu thô)
python stage6_adversarial_attacks.py --model peaegnnv2 --ckpt_seed 42 --attacks ADAPTIVE-STC-LV --budgets 20 50 100 200 500 --tag adaptive_lv_big --stage5_dir <dir>
python summarize_stage6.py --tag adaptive_lv_big

# Stage 6: chi phí tối thiểu (dừng ngay khi bị vượt); chạy từng mô hình/seed/nhóm, bỏ qua phần đã xong
python run_mincost_all.py --models peaegnnv2 graphsage gatv2 --seeds 42 43 44 --groups adaptive --tag_suffix full
python run_mincost_all.py --models peaegnnv2 graphsage gatv2 --seeds 42 --groups stc mwr toh_tih bph --tag_suffix full
python summarize_mincost.py --seeds 42 43 44 --tag_suffix full      # seed/nhóm nào thiếu sẽ báo [thieu]

# Stage 6: độ nhạy đặc trưng (3 mô hình x 3 seed; checkpoint của peaegnnv2 ở thư mục riêng)
foreach ($s in 42,43,44) { foreach ($m in "peaegnnv2","graphsage","gatv2") { $d = if ($m -eq "peaegnnv2") { "D:\NCKH\Final\results\stage5_k2_7_10" } else { "D:\NCKH\Final\results\stage5_k2" }; python diag_feature_sensitivity.py --model $m --ckpt_seed $s --stage5_dir $d } }
python summarize_diag.py --seeds 42 43 44

# Stage 7 (mô hình cũ; chi tiết ở các mục trước)
python stage7_defense.py make_pool --stage5_dir <dir>                                          # máy có dữ liệu thô
python stage7_defense.py train --methods advtrain_peae ra_peae ra_peae_noedge --seeds 42 43 44 \
       --pkl <pkl> --pool <adv_pool_train.pkl> --stage5_dir <dir> --out <dir>                   # Kaggle
python stage7_defense.py eval --methods baseline_peae advtrain_peae ra_peae ra_peae_noedge \
       --budgets 5 20 100 --seed 42 --stage5_dir <dir> --defense_dir <dir>
python summarize_stage7.py ; python analyze_stage7_auc.py --attack ADAPTIVE-STC-LV ; python stats_stage7.py
# Stage 7 cho peaegnnv2 (chưa chạy): train --methods advtrain_peaev2 ... ; eval --methods baseline_peaev2 advtrain_peaev2 ...

# Stage 8 (D2)
python convert_d2.py --d2 <D2raw> --out <D2base>
python stage8_eval_d2.py
```

---
## 12. Tài liệu tham khảo (theo thứ tự xuất hiện; cần đối chiếu bản gốc trước khi trích dẫn)

[1] H. Wen *et al.*, "Hide and Seek: An Adversarial Hiding Approach Against Phishing Detection on Ethereum," *IEEE Transactions on Computational Social Systems*, 2022. (Tên bài, tạp chí và tác giả đầu đã kiểm tra; danh sách tác giả đầy đủ, tập, trang và DOI chưa kiểm tra. Nguồn của TOH, TIH, BPH-T2P, BPH-P2T.)
[2] Merkle Science, "Money Laundering in Crypto: How Criminals Hide Their Tracks." https://www.merklescience.com/blog/money-laundering-in-crypto-how-criminals-hide-their-tracks
[3] Elliptic, "Detecting Layering and Integration Patterns in Crypto Money Laundering Using On-Chain Analytics." https://www.elliptic.co/corpus/gen-3784/anti-money-laundering/detecting-layering-and-integration-patterns-in-crypto-money-laundering-using-on-chain-analytics.html
[4] Etherscan Information Center, "Address Poisoning Attacks Are Rising on Ethereum." https://info.etherscan.com/address-poisoning-attacks-are-rising-on-ethereum
[5] "Characterizing Ethereum Address Poisoning Attack" (bài nghiên cứu; cần bổ sung tác giả và nơi công bố). https://par.nsf.gov/servlets/purl/10580433
[6] Chainalysis, báo cáo về rửa tiền (ví trung gian "hops"); mới đọc qua bản tóm tắt: CryptoPotato, "Rising Sophistication in Crypto-Native Money Laundering: Chainalysis Weighs on Wallet Hops." https://cryptopotato.com/rising-sophistication-in-crypto-native-money-laundering-chainalysis-weighs-on-wallet-hops/ (cần lấy báo cáo gốc của Chainalysis và đối chiếu con số trước khi trích dẫn)
[7] Elliptic, "Anti-Money Laundering Typologies in Crypto: Smurfing, Structuring, and Layering Patterns On-Chain." https://www.elliptic.co/corpus/gen-3784/anti-money-laundering/anti-money-laundering-typologies-in-crypto-smurfing-structuring-and-layering-patterns-on-chain.html
[8] Elliptic, "Detecting Stablecoin Layering Patterns." https://www.elliptic.co/stablecoin-layering.html

# Nhật ký thực nghiệm Stage 5 → Stage 8

**Đề tài:** Đánh giá và tăng cường độ bền vững của mô hình phát hiện lừa đảo trên Ethereum trước các tấn công né tránh dựa trên đồ thị giao dịch.
**Phạm vi file này:** những gì đã làm từ Stage 5 (huấn luyện) đến Stage 8 (đối chiếu D2), kèm số liệu, lệnh chạy, lỗi đã sửa, hạn chế và việc còn dang dở.
**Nguồn số liệu:** các bảng/log chạy thật trong quá trình làm (các file `results_*.json`, `eval_*.json`, `stage*_summary*.md`). Trước khi đưa vào báo cáo, hãy đối chiếu lại với file gốc.

---

## 0. Tóm tắt

| Câu hỏi | Kết luận hiện có | Độ chắc |
|---|---|---|
| RQ1: mô hình suy giảm thế nào trước giao dịch giả | 6 tấn công gốc gần như không lừa được mô hình (ASR ≤ ~5%). Tấn công `ADAPTIVE-STC-LV` (tự thiết kế) hiệu quả với PEAE-style (ASR 27% ở b=20, ~50% ở b=500), yếu hơn với GraphSAGE (3,5% → 23%) và GATv2 (2,4% → 8,5%) | Chắc cho thiết lập này (3 seed, toàn bộ tập test) |
| RQ2: kiến trúc/đặc trưng nào dễ bị tấn công | Kiến trúc ảnh hưởng mạnh (PEAE-style > GraphSAGE > GATv2). Mô hình dựa vào đặc trưng **hàng xóm** hơn đặc trưng của chính ví | Kiến trúc: chắc. Cơ chế giải thích: chưa kiểm chứng |
| RQ3: huấn luyện đối kháng cải thiện bao nhiêu, mất bao nhiêu hiệu năng sạch | Giữ recall khi bị tấn công cao hơn mô hình gốc (+11,7 điểm ở FPR 10%, b=100), hiệu năng sạch gần như không đổi | Khá chắc (3/3 seed cùng chiều) |
| RQ4: cơ chế reliability-aware có hơn huấn luyện đối kháng thường không | Hơn mô hình gốc rõ (+17,3 điểm). Hơn `advtrain` chỉ có **gợi ý** ở ngân sách lớn, chưa đủ chứng minh | Chưa kết luận |
| Đối chiếu D2 | Chuyển trực tiếp: xếp hạng vẫn tốt (ROC-AUC 0,73–0,87) nhưng macro-F1 ở ngưỡng 0,5 giảm mạnh (mô hình đoán quá nhiều phishing) | Chắc ở mức mô tả; nguyên nhân chưa tách được |

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

**Mô hình:** GraphSAGE · GATv2 · PEAE-style (**bản xấp xỉ** PEAE-GNN: encoder SAGE + embedding node mục tiêu + mean/max pooling + dropout đặc trưng; không phải bản tái lập gốc).
**Cấu hình:** hidden 64, lr 1e-3, weight decay 5e-4, batch 64, cross-entropy có trọng số lớp, chọn mô hình theo macro-F1 validation, dừng sớm (patience 15, tối đa 100 epoch), seed 42/43/44. Chạy trên Kaggle GPU (khoảng 53 phút cho 9 lần huấn luyện). Test chỉ đánh giá một lần ở epoch tốt nhất.

| Mô hình | Macro-F1 | PR-AUC | Recall phishing |
|---|---|---|---|
| GraphSAGE | 0,8663 ± 0,0032 | 0,9373 ± 0,0047 | 0,7772 ± 0,0110 |
| GATv2 | 0,8151 ± 0,0108 | 0,9040 ± 0,0025 | 0,6616 ± 0,0159 |
| PEAE-style | **0,8813 ± 0,0028** | **0,9429 ± 0,0021** | **0,8283 ± 0,0060** |

Ghi chú:
- F1 trên validation (~0,78–0,81) thấp hơn nhiều F1 trên test (~0,88): do thiết kế chia tập theo thời gian (mỗi tập có mốc cắt lịch sử khác nhau), không phải lỗi.
- Độ lệch chuẩn chỉ phản ánh khởi tạo khác nhau (3 seed, cùng một cách chia tập).

**Mô hình bổ sung đang chạy: `peaegnnv2`** (do bạn trong nhóm viết, nhằm gần bài báo hơn): tăng cường đồ thị (bỏ ~20% cạnh, che ~15% đặc trưng) + bộ mã hóa GATv2 + embedding node mục tiêu đa lớp + đọc kết quả bằng attention từ node mục tiêu + học đối sánh (NT-Xent, trọng số 0,1).
- Batch 64 **hết bộ nhớ GPU** (14,5 GB). Batch 16 chạy được, **~58 giây/epoch**. Lần thử 1 epoch: macro-F1 0,777 (chưa có ý nghĩa).
- Với batch 16 chỉ có khoảng 30 mẫu "âm" cho học đối sánh mỗi batch (so với ~126 ở batch 64) → có thể học kém hơn thiết kế gốc.
- **Chưa xác nhận** từng thành phần có khớp bài báo gốc; các siêu tham số là lựa chọn của người viết. Chưa có kết quả đầy đủ 3 seed.

**Lệnh:**
```
!python stage5_train_baselines.py --pkl <ego_graph_k2_dataset.pkl> --out /kaggle/working/stage5_k2 --model all --seeds 42 43 44
!python stage5_train_baselines.py --pkl <pkl> --out /kaggle/working/stage5_v2 --model peaegnnv2 --seeds 42 43 44 --bs 16
```

---

## 3. Stage 6 — Tấn công thêm giao dịch

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

### 3.5 Phép thử độ nhạy đặc trưng (RQ2) — thay trực tiếp giá trị, **không phải tấn công on-chain**

Tỉ lệ ví phishing bị lật khi thay đặc trưng bằng giá trị "kiểu normal":

| Thay phần nào | PEAE-style | GraphSAGE |
|---|---|---|
| Toàn bộ đặc trưng của chính ví | 3,6% | 2,1% |
| Hàng xóm bậc 1 → mẫu thật từ graph normal | 26,3% | 96,4% |
| (đối chứng) bậc 1 → mẫu thật từ graph phishing | 4,7% | 66,8% |
| Bậc 1 + bậc 2 → mẫu normal | 53,0% | 100% |
| (đối chứng) bậc 1 + bậc 2 → mẫu phishing | 18,2% | 87,7% |

→ Mô hình dựa vào **hàng xóm** hơn là vào chính ví. (Thay bằng một vector hằng số cho 98–100% bị lật là artifact dữ liệu bất thường, không dùng.) Giả thuyết giải thích vì sao PEAE-style dễ bị tấn công hơn (có kênh riêng cho node mục tiêu) **chưa kiểm chứng**.

---

## 4. Stage 7 — Phòng thủ

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

---

## 7. Hạn chế (bắt buộc ghi khi trích dẫn kết quả)

1. "PEAE-style" là **bản xấp xỉ** PEAE-GNN, không phải bản tái lập gốc; mô hình `peaegnnv2` chưa có kết quả đầy đủ và chưa xác nhận khớp bài báo.
2. Chỉ **3 seed**; độ lệch chuẩn chỉ phản ánh khởi tạo khác nhau (cùng tập test, cùng cách chia, cùng giao dịch giả). Bootstrap chỉ phản ánh độ bất định do chọn mẫu test.
3. Các tấn công đều **cố định**, không thích ứng theo mô hình phòng thủ; chưa có kiểm thử tấn công thích ứng vào chính mô hình đã phòng thủ. Không được viết "mô hình bền vững", chỉ được viết "giảm ASR trước các tấn công đã thử".
4. Chỉ **một họ tấn công** (`ADAPTIVE-STC`) có ASR đo được; các tấn công đã biết và STC/MWR có ASR gốc quá thấp để đánh giá phòng thủ. "Chưa thấy" chỉ có nghĩa là không dùng trong huấn luyện, **không** có nghĩa khác họ.
5. **Chưa kiểm tra số dư và chi phí gas thực**; "khả thi on-chain" chỉ ở mức ràng buộc cấu trúc và thời gian.
6. ASR chỉ tính trên ví phishing mà mô hình bắt đúng lúc sạch (mẫu số khác nhau giữa các mô hình); đã bổ sung robust recall và số đo ở cùng FPR để so sánh công bằng.
7. Chia tập theo thời gian khiến tỉ lệ lớp lệch giữa các tập và F1 validation thấp hơn F1 test.
8. Phân tích tỉ lệ phishing thấp chỉ cho họ PEAE-style và bằng lấy mẫu con, không thêm ví normal mới.
9. D2: khác thời kỳ, không có gas, mất dữ liệu bậc 2 không đều giữa hai lớp, chỉ đánh giá chuyển trực tiếp.
10. Giả thuyết cơ chế (vì sao PEAE-style dễ bị tấn công hơn; yếu tố nào tạo sức mạnh của `ADAPTIVE-STC`; vì sao `ra_peae_noedge` yếu hơn `ra_peae`) **chưa được kiểm chứng**.

---

## 8. Trạng thái công việc

| Hạng mục | Trạng thái |
|---|---|
| Stage 5: GraphSAGE, GATv2, PEAE-style × 3 seed | Xong |
| Stage 5: `peaegnnv2` × 3 seed | **Đang chạy / chờ kết quả** |
| Stage 6: 6 tấn công gốc × 3 mô hình × 3 seed | Xong |
| Stage 6: `ADAPTIVE-STC-LV` b = 1…500 × 3 mô hình × 3 seed | Xong |
| Stage 6 trên `peaegnnv2` | Chưa làm (chờ Stage 5 v2) |
| Stage 7: `advtrain_peae`, `ra_peae`, `ra_peae_noedge` × 3 seed, đánh giá, kiểm định, AUC, tỉ lệ thấp | Xong |
| Stage 7: phòng thủ trên `peaegnnv2` | Chưa làm (RA trên nền attention chưa có thiết kế; `advtrain` thì thêm được) |
| Stage 7: ngân sách b=500 cho các mô hình phòng thủ | Chưa làm |
| Stage 8 mức A (chuyển trực tiếp D2) | Xong |
| Stage 8 mức B, C; D1 | Chưa làm |
| Stage 4 gốc (thêm normal bổ sung, K=2) | Chưa làm (thay bằng lấy mẫu con) |
| Graph-injection TDGIA/G-NIA/GANI, black-box/transfer | Chưa làm (đề cương ghi là mở rộng) |
| Tấn công thích ứng vào mô hình đã phòng thủ | Chưa làm |
| Sửa đề cương cho khớp thực tế | Chưa làm |
| Viết báo cáo | Chưa làm |

**Những điểm cần sửa trong đề cương:** MWR vòng về target; mô tả đúng cơ chế r(e); K=2 với giới hạn 500 giao dịch mỗi hàng xóm; số liệu D2 thực đo (thời gian 2015-08 → 2019-10, 10 cột, giá trị ETH, không gas); Stage 4 thay bằng lấy mẫu con; các hạn chế nêu trên.

---

## 9. Danh mục file

**Mã nguồn:** `stage9_k2_upgrade.py` (dựng graph K=2) · `stage5_train_baselines.py` · `stage6_adversarial_attacks.py` · `stage7_defense.py` (`make_pool` / `train` / `eval`) · `convert_d2.py` · `stage8_eval_d2.py` · `diag_feature_sensitivity.py` · `summarize_stage6.py` · `summarize_stage7.py` · `analyze_stage7_auc.py` · `stats_stage7.py` · `inspect_d2.py` · `prepare_kaggle_upload.py` · `package_results.py`.

**Kết quả:** `results_*` (Stage 5, 6) · `eval_seed*.json`, `eval_probs_*.npz` (Stage 7) · `stage6_summary*.md`, `stage7_summary*.md`, `stage7_auc_analysis*.md`, `stage7_stats*.md` · `stage8_zeroshot_d2.json`, `d2_conversion_report.json`.

---

## 10. Lệnh tái lập (rút gọn)

```
# Stage 5 (Kaggle)
python stage5_train_baselines.py --pkl <pkl> --out /kaggle/working/stage5_k2 --model all --seeds 42 43 44

# Stage 6 (máy có dữ liệu thô)
python stage6_adversarial_attacks.py --model peaegnn --ckpt_seed 42 --stage5_dir <dir>
python stage6_adversarial_attacks.py --model peaegnn --ckpt_seed 42 --attacks ADAPTIVE-STC-LV --budgets 20 50 100 200 500 --tag adaptive_lv_big --stage5_dir <dir>
python summarize_stage6.py [--tag adaptive_lv_big]

# Stage 7
python stage7_defense.py make_pool --stage5_dir <dir>                       # máy có dữ liệu thô
python stage7_defense.py train --methods advtrain_peae ra_peae ra_peae_noedge --seeds 42 43 44 \
       --pkl <pkl> --pool <adv_pool_train.pkl> --stage5_dir <dir> --out <dir>   # Kaggle
python stage7_defense.py eval --methods baseline_peae advtrain_peae ra_peae ra_peae_noedge \
       --budgets 5 20 100 --seed 42 --stage5_dir <dir> --defense_dir <dir>    # máy có dữ liệu thô
python summarize_stage7.py ; python analyze_stage7_auc.py --attack ADAPTIVE-STC-LV ; python stats_stage7.py

# Stage 8 (D2)
python convert_d2.py --d2 <D2raw> --out <D2base>
python stage8_eval_d2.py
```

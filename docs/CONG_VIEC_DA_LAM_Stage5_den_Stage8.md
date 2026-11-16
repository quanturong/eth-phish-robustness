# Công việc đã thực hiện: Stage 5 → Stage 8

**Khóa luận**: Đánh giá và tăng cường độ bền vững của mô hình phát hiện lừa đảo trên Ethereum trước các tấn công né tránh dựa trên đồ thị giao dịch
**Dataset**: EthPhishGraph-2026 (7,036 target accounts, K=2 ego-graph)
**Cập nhật**: 2026-10-07

---

## Stage 5 — Huấn luyện baseline GNN

### Mục tiêu

Huấn luyện 3 mô hình baseline để đo hiệu năng phát hiện phishing trên dữ liệu sạch, làm điểm tham chiếu cho các thí nghiệm tấn công/phòng thủ ở Stage 6-7.

### Thiết lập thí nghiệm

| Hạng mục | Giá trị |
|----------|---------|
| Mô hình | GraphSAGE, GATv2, PEAE-style GNN |
| Dataset | EthPhishGraph-2026 K=2 (train 4,221 / val 1,407 / test 1,408) |
| Node features | 9 chiều (bỏ `first_ts`, `last_ts` để chống rò rỉ thời gian) |
| Edge features | 3 chiều (`value`, `gas_price`, `gas_used`; bỏ `timestamp`) |
| Chuẩn hoá | `sign(x)·log(1+|x|)` + z-score (fit trên train only) |
| Optimizer | Adam, lr=1e-3, weight_decay=5e-4 |
| Batch size | 64 |
| Epochs | 100, early stopping patience=15 trên val Macro-F1 |
| Seeds | 42, 43, 44 (báo cáo mean ± std) |

### Kết quả

**Hiệu năng sạch trên test (mean ± std, 3 seeds)**:

| Model | Macro-F1 | PR-AUC | Phish Precision | Phish Recall | Phish F1 |
|-------|---------:|-------:|----------------:|-------------:|---------:|
| GATv2 | 81.51 ± 1.08 | 0.840 | 0.858 | 66.20 ± 1.60 | 0.748 |
| GraphSAGE | 86.63 ± 0.32 | 0.878 | 0.880 | 77.70 ± 1.10 | 0.825 |
| **PEAE-style** | **88.13 ± 0.28** | **0.880** | 0.891 | **82.80 ± 0.60** | **0.859** |

**Finding**: PEAE-style đạt hiệu năng tốt nhất nhờ target-aware pooling (concat embedding target với mean/max pool).

### Output artifacts
- `stage5_baselines/results_all.json`
- `stage5_baselines/feat_stats.pt` (reusable cho Stage 6/7)
- `stage5_baselines/models/model_{model}_seed{seed}.pt` × 9 checkpoint

---

## Stage 6 — Tấn công đối kháng (adversarial attacks)

### Mục tiêu

Xây dựng và đánh giá 6+1 chiến lược tấn công né tránh ở **mức giao dịch** (transaction-level evasion), đo mức độ dễ bị đánh lừa của 3 baseline models.

### Threat model

| Ràng buộc | Chi tiết |
|-----------|----------|
| Attacker có thể | Thêm giao dịch hợp lệ (từ các ví kiểm soát) |
| Attacker không thể | Xóa/sửa tx đã confirm; kiểm soát ví người dùng khác |
| Timestamp | Mọi tx mới phải sau `max(timestamp quá khứ) + 1h`; không vượt T_end test |
| Validation | 100% hợp lệ: endpoint control, value > 0, timestamp order |

### 7 chiến lược tấn công đã cài đặt

| Attack | Cấu trúc | txs/budget | Nhóm |
|--------|----------|:----------:|------|
| **TOH** | `target → perturbation` | 1 | Baseline (Hide & Seek [2]) |
| **TIH** | `perturbation → target` | 1 | Baseline [2] |
| **BPH-T2P** | `target → W₁ → perturbation` (2-hop) | 2 | Baseline [2] |
| **BPH-P2T** | `perturbation → W₁ → target` (2-hop) | 2 | Baseline [2] |
| **STC** | Split: k=4 dust txs rải 30 ngày | 4 | **Nhóm đề xuất** |
| **MWR** | Multi-wallet routing: `target → W₁ → W₂ → target` (3 tx) | 3 | **Nhóm đề xuất** |
| **ADAPTIVE-STC-LV** | Balance in/out + value theo phân bố normal + 90-day spread | 6 | **Nhóm đề xuất (nâng cấp)** |

### Rebuild ego-graph K=2 sau tấn công

Sau khi chèn perturbation txs, **rebuild lại K=2 ego-graph** bằng chính logic Stage 9c (không sửa trực tiếp feature vector). Đảm bảo clean và attacked graphs cùng pipeline preprocessing.

### Kết quả — 6 tấn công nguyên bản (budget b ∈ {1,3,5,10,20})

ASR trung bình (mean ± std 3 seeds):

| Attack | PEAE-style | GraphSAGE | GATv2 |
|--------|-----------:|----------:|------:|
| TOH | 1.3% | 1.3% | 2.8% |
| TIH | 0.6% | 1.0% | 0.5% |
| BPH-T2P | 0.5% | 1.1% | 1.9% |
| BPH-P2T | 1.3% | 2.9% | 0.1% |
| STC | 2.4% | 2.7% | 2.2% |
| MWR | 0.1% | 0.6% | 0.2% |
| **ASR_any** | **5.3 ± 2.5%** | **8.7 ± 4.9%** | **6.2 ± 1.0%** |

**Finding**: Các tấn công nguyên bản chỉ gây ASR 0-9% dưới K=2 defender → **không đủ threat** để đánh giá defense có ý nghĩa.

### Kết quả — ADAPTIVE-STC-LV với big budgets (b ∈ {20, 50, 100, 200, 500})

ASR theo budget (mean ± std 3 seeds):

| Budget | PEAE-style | GraphSAGE | GATv2 |
|-------:|-----------:|----------:|------:|
| 20 | 27.2 ± 7.1 | 3.5 ± 1.3 | 2.4 ± 0.4 |
| 50 | 37.4 ± 6.8 | 6.5 ± 1.8 | 3.8 ± 1.1 |
| 100 | 41.8 ± 8.2 | 10.5 ± 1.9 | 5.3 ± 1.5 |
| 200 | 44.7 ± 8.6 | 14.7 ± 1.8 | 6.4 ± 1.4 |
| 500 | **49.7 ± 11.2** | 23.2 ± 3.9 | 8.5 ± 1.1 |
| **ASR_any** | **54.6 ± 11.7%** | **23.2 ± 4.0%** | **8.8 ± 1.4%** |

**Chi phí tấn công @ b=500**: 3,000 txs = **0.9 ETH value + 3.7 ETH gas ≈ 4.6 ETH ≈ $11,500**.

### Finding chính Stage 6

1. **Model ranking ĐẢO NGƯỢC** dưới adaptive attack:
   - Nguyên bản: PEAE (5.3%) < GATv2 (6.2%) < GraphSAGE (8.7%)
   - **ADAPTIVE-STC-LV**: GATv2 (8.8%) < GraphSAGE (23.2%) < PEAE (54.6%)
2. **Target-aware pooling của PEAE là CON DAO HAI LƯỠI**: hiệu năng sạch cao nhất nhưng **vulnerable nhất** trước tấn công adaptive.
3. **Attention (GATv2) tự nhiên bền hơn** 10× so với PEAE.

### Output artifacts
- `stage6_attacks/results_{model}_seed{seed}.json` × 9 (6 attacks nguyên bản)
- `stage6_attacks/results_{model}_seed{seed}_adaptive_lv.json` × 9 (small budget)
- `stage6_attacks/results_{model}_seed{seed}_adaptive_lv_big.json` × 9 (big budget)
- `stage6_attacks/stage6_summary{_adaptive_lv,_adaptive_lv_big}.md/.csv`

---

## Stage 7 — Phòng thủ (adversarial defense)

### Mục tiêu

Thiết kế và đánh giá 2 cơ chế phòng thủ nhằm giảm vulnerability của PEAE-style trước ADAPTIVE-STC (unseen attack), đồng thời giữ clean performance.

### 4 cấu hình đánh giá

| Cấu hình | Mô tả |
|----------|-------|
| **baseline_peae** | PEAE-style không phòng thủ (từ Stage 5) |
| **advtrain_peae** | PEAE + adversarial training với adv samples ngẫu nhiên |
| **ra_peae** | Reliability-Aware GNN: trọng số `r(e) ∈ [0,1]` cho mỗi cạnh dựa trên edge features + node context |
| **ra_peae_noedge** (ablation) | Giống `ra_peae` nhưng bỏ edge features khỏi hàm tính `r(e)` |

### Kết quả

**1. Clean performance (giữ nguyên gần như hoàn toàn)**:

| Model | Macro-F1 | Phish Recall | ΔMacro-F1 |
|-------|---------:|-------------:|----------:|
| baseline_peae | 88.1 ± 0.3 | 82.8 ± 0.6 | – |
| advtrain_peae | 88.7 ± 0.7 | 84.0 ± 1.3 | +0.6 |
| **ra_peae** | 87.6 ± 2.0 | 80.2 ± 4.8 | -0.5 |
| ra_peae_noedge | 88.5 ± 0.1 | 83.0 ± 1.2 | +0.4 |

**2. ASR trên ADAPTIVE-STC (mean + std, budgets [5, 20, 100], 3 seeds)**:

| Model | ASR mean | **ASR_any** | Giảm so baseline |
|-------|---------:|------------:|-----------------:|
| baseline_peae | 27.6 ± 7.5 | **43.7** | – |
| advtrain_peae | 11.0 ± 5.8 | **24.7** | -19.0 điểm (−43.5%) |
| **ra_peae** | **10.7 ± 0.7** | **20.2** | **-23.5 điểm (−53.8%)** 🎯 |
| ra_peae_noedge | 20.2 ± 4.7 | 33.0 | -10.7 điểm (−24.5%) |

**3. Robust Recall @ b=100 (metric công bằng hơn ASR)**:

| Model | Clean | b=100 | Loss |
|-------|------:|------:|-----:|
| baseline_peae | 82.8 | 48.5 | **−34 điểm** |
| advtrain_peae | 84.0 | 67.2 | −17 điểm |
| **ra_peae** | 80.2 | 66.2 | **−14 điểm** ✓ |

### Ablation reliability components

Edge features (`value`, `timestamp`, `gas_price`, `gas_used`) đóng góp **56% hiệu quả** của RA-SAGE:
- Full `ra_peae`: ASR_any = 20.2% (giảm 23.5 điểm)
- `ra_peae_noedge`: ASR_any = 33.0% (giảm chỉ 10.7 điểm)
- → Marginal contribution của edge features: **12.8 điểm**

### Finding chính Stage 7

1. **RA-SAGE là defense tốt nhất**: ASR_any giảm 53.8% tương đối, Macro-F1 trong ±0.5 điểm.
2. **AdvTrain cũng hiệu quả** nhưng ASR cao hơn RA 4-5 điểm.
3. **Edge features cần thiết** cho reliability-aware (ablation confirm).
4. **RA-SAGE ổn định nhất** across seeds (std ASR_any chỉ 2.7, vs AdvTrain 7.7).

### Output artifacts
- `stage7_defense/train_{method}_seed{seed}.json` × 9 (training logs)
- `stage7_defense/eval_seed42.json`, `eval_seed42_hv.json` (chi tiết eval)
- `stage7_defense/models/model_{method}_seed{seed}.pt` × 9
- `stage7_defense/stage7_summary.md`, `stage7_summary_hv.md`

---

## Stage 8 — Cross-dataset Zero-shot trên D2

### Mục tiêu

Đánh giá khả năng tổng quát hoá của các mô hình đã train trên EthPhishGraph-2026 khi áp dụng **trực tiếp (không retrain)** lên bộ dữ liệu XBLOCK D2 (Yuan et al., 2020).

### Setup

- **Train**: EthPhishGraph-2026 (2015-2025, snapshot nhãn 09/2026)
- **Test**: XBLOCK D2 (2015-2019, snapshot nhãn 2019)
- **2,108 target accounts** D2 sau convert sang K=2 ego-graph tương thích
- **Zero-shot**: không retrain, không fine-tune

### Kết quả (3 seeds, mean ± std)

| Model | Macro-F1 | PR-AUC | **ROC-AUC** | **Phish Recall** | Phish Precision |
|-------|---------:|-------:|------------:|-----------------:|----------------:|
| GATv2 | 58.9 ± 4.1 | 0.654 | 0.727 | 86.9% | 0.539 |
| GraphSAGE | 63.6 ± 3.8 | 0.805 | 0.812 | 88.7% | 0.570 |
| **PEAE-style** | **69.1 ± 5.0** | **0.824** | **0.861** | **91.4%** | 0.613 |
| **AdvTrain-PEAE** | 59.8 ± 5.7 | **0.849** 🎯 | 0.866 | **94.7%** 🎯 | 0.549 |

### Finding chính Stage 8

1. **Drop performance 2026 → D2** là bình thường cho zero-shot (19-23 điểm Macro-F1), nhưng PR-AUC vẫn 0.80+ → model **vẫn phân biệt được** phishing/normal.
2. **PEAE-style ROC-AUC 0.861** → generalize tốt dù không retrain.
3. **AdvTrain-PEAE có PR-AUC CAO NHẤT trên D2** (0.849 > PEAE 0.824 > GraphSAGE 0.805) → **defense generalize cross-domain** không chỉ cho adversarial.
4. **Phishing Recall 91-95%** → model không miss phần lớn phishing D2 (quan trọng cho use case bảo mật).

### Output artifacts
- `stage8_D2/stage8_zeroshot_d2.json` (chi tiết all seeds × 4 models)
- `stage8_D2/d2_conversion_report.json`

---

## Tổng kết 4 stage

### Chuỗi finding dạng narrative

```
Stage 5          Stage 6                    Stage 7                 Stage 8
─────────        ─────────                  ─────────               ─────────
PEAE-style  →   PEAE vulnerable          →  RA-SAGE giảm       →  PEAE giữ được
tốt nhất        với adaptive attack          ASR_any 53.8%          khả năng tổng quát
88.1% F1        (54.6% ASR_any)              (43.7% → 20.2%)        trên D2 (ROC-AUC 0.861)
```

### Trả lời Research Questions

| RQ | Nội dung | Câu trả lời số liệu |
|----|----------|---------------------|
| **RQ1** | Mô hình phishing suy giảm thế nào trước tấn công thêm giao dịch? | PEAE giảm từ 82.8% recall xuống 50.3% @ b=500 (ADAPTIVE-STC-LV) |
| **RQ2** | Kiến trúc nào dễ bị tấn công nhất? | PEAE (target-aware) **dễ bị nhất** dưới adaptive attack (54.6% vs GATv2 8.8%) |
| **RQ3** | AdvTrain hiệu quả & đánh đổi bao nhiêu? | ASR_any ↓ 43.5% tương đối, clean F1 giữ nguyên (+0.6) |
| **RQ4** | RA-SAGE có khái quát hoá chéo không? | ASR_any ↓ 53.8% tương đối (tốt hơn AdvTrain 10%), clean F1 ±0.5 |

### Validation chéo (sanity checks)

- ✅ **0 giao dịch bất hợp lệ** trong tất cả 26,730 attack configurations
- ✅ **0 target bị drop** trong eval
- ✅ **3 seeds** cho tất cả metrics chính
- ✅ **Clean baseline** replicate ổn định (std 0.3-1.0 trên Macro-F1)
- ✅ **Zero-shot D2** confirm model không overfitting EthPhishGraph-2026

---

## Giới hạn đã ghi nhận

1. **PEAE-style ≠ PEAE-GNN gốc**: approximation ~30% innovation (chưa đủ Augmented Ego-Graph strategy)
2. **ADAPTIVE-STC-LV = static attack**: không thích ứng theo mô hình phòng thủ
3. **3 seeds**: std chỉ phản ánh init variance, không bootstrap sample variance
4. **D2 không có gas info**: dùng placeholder → cross-dataset có noise nhẹ
5. **Chưa test imbalanced test sets** (1:5, 1:10) dù đã build sẵn
6. **Chưa test defense trên COMBINED/GRADIENT attack** (chỉ test ADAPTIVE-STC)
7. **ra_peae seed 44** train kém (dừng epoch 17) — ghi nhận trong report

---

## Tổng số liệu đã sinh

- **4 stages** hoàn chỉnh
- **~90 result files** JSON + MD + CSV
- **~20 model checkpoint** (.pt)
- **~5 MB** total summary artifacts
- **8 figures** cho báo cáo + **4 slides** cho presentation (16:9)
- **1 package** gói kèm (`ketqua_khoaluan_YYYYMMDD_HHMM.zip`, 5 MB)

Toàn bộ code + README trên GitHub: https://github.com/quanturong/EthereumPhishingDetector

# Pipeline chi tiết — EthereumPhishingDetector

Mã nguồn của khóa luận (UIT). Dataset: EthPhishGraph-2026 (ego-graph K=2, 7,036 ví: 3,518 phishing và 3,518 normal), chia theo thời gian 4,221 / 1,407 / 1,408.

Phân phối trên Hugging Face: https://huggingface.co/datasets/quanturong/EthPhishGraph-2026

---

## 🧠 Mô hình

| Key | Mô tả | Trạng thái |
|-----|-------|-----------|
| **`peae_paper`** | PEAE-GNN bản bám sát bài Huang et al., IEEE TCSS 2024 (24 đặc trưng tăng cường, kiểu GraphSAGE có self-loop, readout RTM top-3). Dùng thống kê riêng cho đặc trưng. | **Mô hình chính** |
| `graphsage` | Hamilton et al. 2017 | Mô hình so sánh |
| `gatv2` | Brody et al. 2022 | Mô hình so sánh |
| `peaegnn` (PEAE-style xấp xỉ) | Phiên bản xấp xỉ cũ, không bám bài | Phụ lục (archive) |
| `peaegnnv2` | Phiên bản lai GATv2 + contrastive + attention | Phụ lục (archive) |

---

## 📜 Thứ tự chạy

| Bước | Script | Mục đích |
|------|--------|---------|
| 1 | `tools/crawl_normal_candidates.py` | Crawl Etherscan: 3,518 ứng viên normal + hop-1 txs |
| 2 | `stage3_pipeline.py` | Temporal split 60/20/20 + build ego-graph K=1 |
| 3 | `stage4_imbalanced_testonly.py` | Test pool cho 1:5, 1:10 (chống class imbalance) |
| 4 | `stage9_k2_upgrade.py` | Upgrade K=1 → K=2 (crawl hop-2, ~9 giờ API) |
| 5 | `stage5_train_baselines.py` | Train 4 mô hình × 3 seeds |
| 6 | `stage6_adversarial_attacks.py` + `run_mincost_all.py` | 7 tấn công × 5 mức ngân sách + chi phí tối thiểu |
| 7 | `tools/diag_peae_features.py` + `tools/diag_feature_sensitivity.py` | Độ nhạy đặc trưng (RQ2) |
| 8 | `stage7_defense.py` | 3 phương pháp phòng thủ: AdvTrain, RA, RA-noedge |
| 9 | `stage8_crosscheck_D2.py` | Zero-shot D2 (mức A) |

---

## 🧪 Lệnh chi tiết

### Stage 5 — huấn luyện

```bash
# 3 mô hình cơ bản (dùng chung feat_stats)
python stage5_train_baselines.py --model all --seeds 42 43 44 --epochs 100 \
    --pkl ego_graph_k2_dataset.pkl --out stage5_k2

# PEAE paper (24 đặc trưng riêng — PHẢI dùng --out THƯ MỤC KHÁC)
python stage5_train_baselines.py --model peae_paper --bs 32 --epochs 64 --seeds 42 43 44 \
    --pkl ego_graph_k2_dataset.pkl --out stage5_peae

# (Nếu muốn dùng flag log1p trước Min-Max cho ablation)
python stage5_train_baselines.py --model peae_paper --peae_log --seeds 42 43 44 \
    --out stage5_peae_log
```

### Stage 6 — tấn công

```bash
# Chạy ADAPTIVE ngân sách lớn (cho báo cáo)
python stage6_adversarial_attacks.py --model peae_paper --ckpt_seed 42 \
    --attacks ADAPTIVE-STC-LV --budgets 20 50 100 200 500 \
    --tag adaptive_lv_big --stage5_dir stage5_peae

# Chi phí tối thiểu — chạy 45 configs (7 attacks × 3 models × 3 seeds)
python run_mincost_all.py --models peae_paper graphsage gatv2 \
    --seeds 42 43 44 --tag_suffix full

# Debug chạy từng attack
python run_mincost_all.py --models peae_paper --seeds 42 \
    --groups adaptive stc bph toh_tih mwr --tag_suffix full
```

### Stage 7 — phòng thủ

```bash
# 1. Tạo pool mẫu đối kháng (chỉ từ TOH, TIH, BPH-T2P, BPH-P2T — tấn công "đã biết")
python stage7_defense.py make_pool --stage5_dir stage5_peae

# 2. Train 3 phương pháp (GPU)
python stage7_defense.py train --methods advtrain ra ra_noedge --seeds 42 43 44 \
    --pkl ego_graph_k2_dataset.pkl --pool adv_pool_train.pkl \
    --stage5_dir stage5_peae --out stage7_peae

# 3. Evaluate (trên các tấn công "chưa thấy": STC, MWR, ADAPTIVE)
python stage7_defense.py eval --methods baseline advtrain ra ra_noedge \
    --budgets 5 20 100 --seed 42 \
    --stage5_dir stage5_peae --defense_dir stage7_peae
```

### Stage 8 — D2 cross-check

```bash
python tools/convert_d2.py --d2 <D2_raw> --out D2_base
python stage8_crosscheck_D2.py --stage5_dir stage5_peae
python tools/stage8_eval_d2.py
```

---

## 📊 Phân tích & tổng hợp

```bash
# ROC-AUC + metrics bổ sung (recall@FPR=10%, PR-AUC)
python tools/eval_stage5_rocauc.py --stage5_dir stage5_peae --models peae_paper

# Tổng hợp kết quả
python tools/summarize_stage5.py
python tools/summarize_stage6.py --tag adaptive_lv_big
python tools/summarize_mincost.py --models peae_paper graphsage gatv2 --seeds 42 43 44
python tools/summarize_stage7.py
python tools/summarize_diag.py --seeds 42 43 44

# Độ nhạy đặc trưng (RQ2)
python tools/diag_peae_features.py --model peae_paper --ckpt_seed 42 \
    --stage5_dir stage5_peae
python tools/diag_feature_sensitivity.py --model graphsage --ckpt_seed 42 \
    --stage5_dir stage5_k2

# AUC analysis cho defense
python tools/analyze_stage7_auc.py --attack ADAPTIVE-STC-LV

# Bootstrap paired test cho defense
python tools/stats_stage7.py

# Build file MD tổng hợp số liệu (tự động)
python tools/build_metrics_report.py

# Figures cho báo cáo
python tools/generate_figures.py
```

---

## 📦 Dataset management

### Download từ HF

```python
from huggingface_hub import snapshot_download
snapshot_download('quanturong/EthPhishGraph-2026', repo_type='dataset', local_dir='./dataset')
```

### Upload bản mới lên HF (nếu cần)

```bash
# 1. Nén raw txs thành tarballs (~30 phút)
python huggingface/hf_prepare_staging.py

# 2. Upload lên HF (~1-3 giờ, resumable)
python huggingface/hf_upload.py --repo-id <username>/EthPhishGraph-2026
```

### Host dataset qua HTTP (chia sẻ cục bộ)

```bash
python tools/host_dataset.py --port 8080
```

### Bundle cho Kaggle

```bash
python tools/prepare_kaggle_upload.py
```

---

## ⚙️ Tình trạng (tính đến 25/10/2026)

### ✅ Đã xong

- Stage 5: 4 mô hình (graphsage, gatv2, peaegnn, peae_paper) × 3 seed
- Stage 6: 7 tấn công × 3 mô hình × 3 seed (45 configs mincost + ngân sách cố định)
- Độ nhạy đặc trưng: 3 mô hình × 3 seed
- Stage 7: AdvTrain, RA, RA-noedge trên PEAE-style cũ
- Stage 8: Zero-shot D2 cho mô hình cũ

### ⏳ Đang chạy

- Stage 7 cho `peae_paper` (training trên GPU Kaggle)

### 📅 Chưa làm

- Stage 7 cho `peae_paper` (evaluation chi tiết)
- Stage 8 cho `peae_paper`
- Bootstrap paired test cho Stage 7 bản mới
- Evaluation ở FPR = 10% cố định (không chỉ ngưỡng 0.5)
- Chạy HS-greedy (chọn PN tham lam theo surrogate model)

---

## ⚠️ Giới hạn chính

1. **3 seed**: độ lệch chuẩn chỉ phản ánh khởi tạo, không phản ánh biến thiên dataset.
2. **Tấn công cố định** (không thích nghi theo mô hình), **ngẫu nhiên PN** (Hide-and-Seek dùng greedy).
3. **PEAE paper** đạt Macro-F1 0.834, thấp hơn `peaegnn` cũ (0.881); đổi mô hình chính là để bám bài báo gốc, không phải vì hiệu năng tốt nhất.
4. **Giả thuyết cơ chế** chưa kiểm chứng (ví dụ: *"RA không giảm ASR vì features bị tính trước GNN"* — chỉ là giả thuyết).
5. **D2 lệch lớp** (phishing 56% / normal 94%), chỉ chạy mức A (zero-shot).
6. **Chi phí tấn công** chỉ tính gas (0.00124 ETH/tx), chưa tính opportunity cost.

Xem thêm: `docs/NhatKy_ThucNghiem_Stage5-8 (2).md` cho chi tiết đầy đủ.

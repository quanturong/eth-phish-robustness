# EthereumPhishingDetector

**Đánh giá và tăng cường độ bền vững của mô hình phát hiện lừa đảo trên Ethereum trước các tấn công né tránh dựa trên đồ thị giao dịch.**

Khóa luận tốt nghiệp – Trường ĐH Công nghệ Thông tin, ĐHQG-HCM
Hướng dẫn: TS. Phan Thế Duy
Thực hiện: Trương Nguyễn Hoàng Quân (23521272), Nguyễn Minh Quân (23521265)

---

## 📂 Cấu trúc repository

```
EthereumPhishingDetector/
├── README.md                          ← Bản này (giới thiệu + quick start)
├── README_PIPELINE.md                 ← Chi tiết pipeline + thứ tự chạy
├── requirements.txt
│
├── stage3_pipeline.py                 ← Dựng ego-graph K=1 + temporal split 60/20/20
├── stage4_imbalanced_testonly.py      ← Test pool 1:5, 1:10 cho đánh giá imbalance
├── stage5_train_baselines.py          ← 4 mô hình: graphsage · gatv2 · peaegnn · peae_paper
├── stage6_adversarial_attacks.py      ← 7 tấn công: TOH, TIH, BPH-T2P/P2T, STC, MWR, ADAPTIVE-STC-LV
├── stage7_defense.py                  ← AdvTrain · RA (reliability-aware) · RA-noedge
├── stage8_crosscheck_D2.py            ← Zero-shot evaluation trên XBLOCK D2
├── stage9_k2_upgrade.py               ← Upgrade ego-graph K=1 → K=2
├── run_mincost_all.py                 ← Runner chi phí tối thiểu cho nhiều mô hình/seed
│
├── tools/                             ← Scripts tổng hợp, phân tích, hỗ trợ
│   ├── eval_stage5_rocauc.py          ← Tính ROC-AUC + metrics bổ sung
│   ├── diag_feature_sensitivity.py    ← Độ nhạy đặc trưng (graphsage/gatv2/peaegnn)
│   ├── diag_peae_features.py          ← Độ nhạy đặc trưng cho peae_paper (24-dim)
│   ├── summarize_stage5.py / 6.py / 7.py
│   ├── summarize_mincost.py / diag.py
│   ├── analyze_stage7_auc.py          ← AUC analysis cho defense
│   ├── stats_stage7.py                ← Bootstrap paired test
│   ├── collect_json_stage5_6.py       ← Gom JSON results từ Kaggle về
│   ├── build_metrics_report.py        ← Build báo cáo MD từ JSON results
│   ├── generate_figures.py            ← Figures cho báo cáo
│   ├── inspect_d2.py / convert_d2.py / stage8_eval_d2.py
│   ├── crawl_normal_candidates.py     ← Stage 2 crawl Etherscan
│   ├── prepare_dataset_bundle.py / prepare_kaggle_upload.py / host_dataset.py
│   ├── make_stage7_bundle.py / package_results.py / diag_isolated.py
│
├── huggingface/                       ← HF dataset upload utilities
│   ├── hf_prepare_staging.py          ← Nén raw txs thành tarballs
│   ├── hf_upload.py                   ← Upload lên HF Dataset Hub
│   └── README_dataset_HF.md           ← Dataset card trên HF
│
├── docs/                              ← Tài liệu, nhật ký, báo cáo
│   ├── NhatKy_ThucNghiem_Stage5-8.md
│   ├── NhatKy_ThucNghiem_Stage5-8 (2).md
│   ├── BaoCao_SoLieu_Stage5_6.md
│   ├── BaoCao_TomTat_25-10.docx       ← Báo cáo tiến độ 25/10
│   └── CONG_VIEC_DA_LAM_Stage5_den_Stage8.md
│
└── archive/                           ← Mã nguồn cũ/thử nghiệm (xem archive/README.md)
    ├── stage5_train_baselines_paper*.py   ← Bản tái lập PEAE độc lập (đã merge)
    ├── stage6_adversarial_attacks_experimental.py  ← Có GGS/CRING/SPOOL
    ├── stage6_transfer_eval.py            ← TRANSFER analysis
    └── *_old.py                           ← Phiên bản cũ hơn các stage
```

---

## 🚀 Quick Start

### Yêu cầu

```
python >= 3.10
torch >= 2.0
torch_geometric >= 2.8
pandas, numpy, scikit-learn, requests, tqdm, huggingface_hub
```

```bash
pip install -r requirements.txt
```

### 1. Tải dataset

Dataset đã publish trên HF Hub: https://huggingface.co/datasets/quanturong/EthPhishGraph-2026

```python
from huggingface_hub import snapshot_download
snapshot_download('quanturong/EthPhishGraph-2026', repo_type='dataset', local_dir='./dataset')
```

Hoặc dựng lại từ Etherscan (cần API key):

```bash
# Stage 2: crawl normal candidates
python tools/crawl_normal_candidates.py --api_key YOUR_KEY --step 2a

# Stage 3: build ego-graph K=1
python stage3_pipeline.py --api_key YOUR_KEY --step all

# Stage 9: upgrade lên K=2
python stage9_k2_upgrade.py --step 9a
python stage9_k2_upgrade.py --api_key YOUR_KEY --step 9b   # ~9 giờ crawl
python stage9_k2_upgrade.py --step 9c
```

### 2. Train baselines (Kaggle GPU khuyến nghị)

```bash
# 3 mô hình cơ bản (dùng chung feature stats)
python stage5_train_baselines.py --model all --seeds 42 43 44 \
    --pkl ego_graph_k2_dataset.pkl --out stage5_k2

# PEAE paper (feature stats riêng — PHẢI dùng --out thư mục KHÁC)
python stage5_train_baselines.py --model peae_paper --bs 32 --epochs 64 --seeds 42 43 44 \
    --pkl ego_graph_k2_dataset.pkl --out stage5_peae
```

### 3. Tấn công

```bash
# ASR tại ngân sách cố định
python stage6_adversarial_attacks.py --model peae_paper --ckpt_seed 42 \
    --attacks ADAPTIVE-STC-LV --budgets 20 50 100 200 500 \
    --tag adaptive_lv_big --stage5_dir stage5_peae

# Chi phí tối thiểu (dừng ngay khi vượt ngưỡng 0.5)
python run_mincost_all.py --models peae_paper graphsage gatv2 \
    --seeds 42 43 44 --tag_suffix full
```

### 4. Phòng thủ

```bash
# Tạo pool đối kháng
python stage7_defense.py make_pool --stage5_dir stage5_peae

# Train 3 methods
python stage7_defense.py train --methods advtrain ra ra_noedge --seeds 42 43 44 \
    --pkl ego_graph_k2_dataset.pkl --pool adv_pool_train.pkl \
    --stage5_dir stage5_peae --out stage7_peae

# Evaluate
python stage7_defense.py eval --methods baseline advtrain ra ra_noedge \
    --budgets 5 20 100 --seed 42 --stage5_dir stage5_peae --defense_dir stage7_peae
```

### 5. Tổng hợp kết quả

```bash
python tools/summarize_stage5.py
python tools/summarize_mincost.py --models peae_paper graphsage gatv2 --seeds 42 43 44
python tools/summarize_stage7.py
python tools/analyze_stage7_auc.py --attack ADAPTIVE-STC-LV
python tools/stats_stage7.py
python tools/build_metrics_report.py   # Build file MD tổng hợp
```

---

## 📊 Kết quả nổi bật

Chi tiết trong `docs/BaoCao_TomTat_25-10.docx`:

| Mô hình | Macro-F1 | Phishing Recall | ROC-AUC |
|---------|---------|-----------------|---------|
| GraphSAGE | 0.866 | 0.777 | 0.952 |
| GATv2 | 0.815 | 0.662 | 0.918 |
| **PEAE (bài báo)** | **0.834** | **0.763** | **0.872** |

ASR tối đa (1,200 giao dịch, 3 seeds mean ± std):

| Attack | PEAE | GraphSAGE | GATv2 |
|--------|------|-----------|-------|
| **ADAPTIVE-STC-LV** | **87.2%** | 15.0% | 6.8% |
| TIH | 0.1% | 5.9% | **33.2%** |
| TOH | 8.5% | 7.1% | 18.4% |

→ **Best attack phụ thuộc kiến trúc**: ADAPTIVE mạnh nhất trên PEAE; TIH mạnh nhất trên GATv2.

Phòng thủ (ASR trung bình ở 30/120/600 tx trên PEAE):

| Method | ASR | Δ |
|--------|-----|---|
| PEAE gốc | 50.3% | — |
| AdvTrain | 48.3% | −2.0 (noise level) |
| RA | 52.6% | **+2.3 (hurts!)** |
| RA-noedge | 55.0% | **+4.7** |

→ Phòng thủ truyền thống **không hiệu quả** với ADAPTIVE vì features bị tính TRƯỚC khi vào GNN.

---

## 📝 Tài liệu

- `README_PIPELINE.md` — chi tiết pipeline, thứ tự chạy
- `docs/NhatKy_ThucNghiem_Stage5-8.md` — nhật ký thực nghiệm
- `docs/BaoCao_TomTat_25-10.docx` — báo cáo tiến độ 25/10 (bản mới nhất)
- `docs/BaoCao_SoLieu_Stage5_6.md` — bảng số liệu tổng hợp
- `archive/README.md` — giải thích các file đã archive

## 🔗 Tài liệu tham khảo chính

- [1] Huang et al., *"PEAE-GNN: Phishing Detection on Ethereum via Augmentation Ego-Graph"*, IEEE TCSS 2024
- [2] Wen et al., *"Hide and Seek: An Adversarial Hiding Approach Against Phishing Detection on Ethereum"*, IEEE TCSS 2023
- [11] Frankart et al., *"The Feature-Space Illusion: Exposing Practical Vulnerabilities in Blockchain GNN Fraud Detection"*, IEEE SaTML 2026
- [13] Hamilton et al., *"Inductive Representation Learning on Large Graphs"*, NeurIPS 2017 (GraphSAGE)
- [14] Brody et al., *"How Attentive are Graph Attention Networks?"*, ICLR 2022 (GATv2)
- [15] Yuan et al., *"XBLOCK Blockchain Datasets: InPlusLab Ethereum Second-order Phishing Datasets"*, 2020 (D2)

## 📦 Dataset

**EthPhishGraph-2026**: 7,036 ví (3,518 phishing + 3,518 normal), ego-graph K=2, temporal split 60/20/20.

🔗 https://huggingface.co/datasets/quanturong/EthPhishGraph-2026

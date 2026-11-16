# tools/ — Scripts phụ trợ pipeline

Các script trong thư mục này **không thuộc pipeline chính** nhưng cần cho phân tích, tổng hợp và chuẩn bị dữ liệu.

## 📂 Phân loại

### Crawling & dataset preparation

| Script | Mục đích |
|--------|---------|
| `crawl_normal_candidates.py` | Stage 2: crawl Etherscan, tạo pool normal + hop-1 txs |
| `prepare_dataset_bundle.py` | Gom dataset thành bundle (code + metadata) |
| `prepare_kaggle_upload.py` | Chuẩn bị file upload lên Kaggle Datasets |
| `host_dataset.py` | HTTP server host dataset cục bộ cho Kaggle download |
| `package_results.py` | Zip kết quả + code (tự lọc file nghi có API key) |

### Evaluation & diagnostics

| Script | Mục đích |
|--------|---------|
| `eval_stage5_rocauc.py` | Tính ROC-AUC + Recall@FPR10% + metrics đầy đủ cho Stage 5 |
| `diag_feature_sensitivity.py` | Độ nhạy đặc trưng cho graphsage/gatv2/peaegnn (9-dim features) |
| `diag_peae_features.py` | Độ nhạy đặc trưng cho peae_paper (24-dim engineered features) |
| `diag_isolated.py` | Kiểm tra graph isolated nodes |

### Summarization & reporting

| Script | Mục đích |
|--------|---------|
| `summarize_stage5.py` | Tổng hợp kết quả training |
| `summarize_stage6.py` | ASR theo tấn công × ngân sách |
| `summarize_mincost.py` | Chi phí tối thiểu (dừng ngay khi vượt ngưỡng 0.5) |
| `summarize_stage7.py` | Hiệu quả phòng thủ |
| `summarize_diag.py` | Độ nhạy đặc trưng tổng hợp |
| `analyze_stage7_auc.py` | AUC analysis khi bị tấn công (không phụ thuộc ngưỡng) |
| `stats_stage7.py` | Bootstrap paired test cho defense |
| `collect_json_stage5_6.py` | Gom các file JSON từ Kaggle về local |
| `build_metrics_report.py` | Tự động build file MD báo cáo từ JSON results |
| `generate_figures.py` | Figures cho báo cáo/slide |

### D2 cross-check

| Script | Mục đích |
|--------|---------|
| `convert_d2.py` | Chuyển D2 từ XBLOCK format → pipeline format |
| `inspect_d2.py` | Thanh tra D2 (số lượng, schema, lỗi) |
| `stage8_eval_d2.py` | Zero-shot evaluation 3 mô hình trên D2 |

### Defense helpers

| Script | Mục đích |
|--------|---------|
| `make_stage7_bundle.py` | Build bundle mẫu đối kháng cho AdvTrain |

---

## 🚀 Cách dùng

Chạy từ root của repo:

```bash
# Ví dụ: tổng hợp kết quả mincost
python tools/summarize_mincost.py --models peae_paper graphsage gatv2 --seeds 42 43 44

# Ví dụ: tính ROC-AUC cho tất cả mô hình/seed
python tools/eval_stage5_rocauc.py --stage5_dir stage5_peae --models peae_paper
```

Hầu hết scripts hỗ trợ `--help` để xem options.

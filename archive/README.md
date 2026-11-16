# Archive — mã nguồn cũ/thử nghiệm

Thư mục này chứa các phiên bản mã nguồn **không còn dùng trong pipeline chính**. Giữ lại để tra cứu lịch sử và reproducibility.

Mục `archive/` **không được tham chiếu từ pipeline hiện tại** — chạy bất kỳ file nào ở đây đều cần sửa đường dẫn và không được bảo trì.

## Danh mục file

### Mô hình PEAE — các bản thử nghiệm sớm (đã merge vào `../stage5_train_baselines.py`)

| File | Lý do archive |
|------|----------------|
| `stage5_train_baselines_paper.py` | Bản tái lập PEAE-GNN độc lập; đã **merge vào `stage5_train_baselines.py`** với key `peae_paper` |
| `stage5_train_baselines_paper_v1.py` | Bản cải tiến của người thứ hai (có self-loop, flag `--peae_log`); nội dung tương đương bản merged |

### Attacks thử nghiệm (không dùng trong KLTN)

| File | Lý do archive |
|------|----------------|
| `stage6_adversarial_attacks_experimental.py` | Chứa 5 attacks thêm: **GGS, CRING, SPOOL, DEFENSE-ADAPTIVE, MIMICRY**. Thầy đã quyết **giữ 7 attacks gốc**, không dùng attacks mới |
| `stage6_transfer_eval.py` | Transferability analysis cross-architecture; cũng không dùng |

### Phiên bản cũ của stage scripts

Các file `*_old.py` là bản cũ hơn (nhỏ hơn, thiếu `peae_paper` model class hoặc tính năng mới). Bản hiện hành ở thư mục gốc đã lớn hơn và đầy đủ hơn.

| File | Note |
|------|------|
| `stage3_pipeline_old.py` | Bản cũ của build ego-graph K=1 |
| `stage4_imbalanced_testonly_old.py` | Imbalanced test pool cũ |
| `stage5_train_baselines_old.py` | Bản cũ (chưa có `peae_paper`) |
| `stage6_adversarial_attacks_old.py` | KHÔNG có — attacks hiện hành đã đồng bộ |
| `stage7_defense_old.py` | Defense cũ (chưa có defense cho `peae_paper`) |
| `stage8_crosscheck_D2_old.py` | D2 cross-check cũ |
| `stage9_k2_upgrade_old.py` | Bản cũ (gần như giống hiện hành, khác <10 byte) |
| `crawl_normal_candidates_old.py` | Crawl cũ |
| `prepare_dataset_bundle_old.py` | Bundle cũ |
| `host_dataset_old.py` | Host HTTP cũ |

### Utilities bị thay thế

| File | Lý do archive |
|------|----------------|
| `compute_rocauc_mine.py` | Được thay bằng **`../tools/eval_stage5_rocauc.py`** (bản chính thức) |

## Khi nào có thể xóa

Sau khi KLTN được bảo vệ xong và không cần tra cứu lại các bản thử nghiệm, có thể xóa toàn bộ `archive/`.

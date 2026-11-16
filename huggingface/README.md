# huggingface/ — HF Dataset upload utilities

Scripts hỗ trợ publish dataset EthPhishGraph-2026 lên Hugging Face Hub.

**Dataset đã publish**: https://huggingface.co/datasets/quanturong/EthPhishGraph-2026

## 📂 Files

| File | Mục đích |
|------|---------|
| `hf_prepare_staging.py` | Nén 162K files raw JSON thành 3 tarballs (hop2, normal_hop1, phishing_hop1) + copy metadata |
| `hf_upload.py` | Upload staging folder lên HF Dataset Hub (resumable, chunked) |
| `README_dataset_HF.md` | Dataset card gốc (sync với README trên HF web) |

## 🚀 Cách dùng

### 1. Login HF

```bash
# CLI (nếu có)
hf auth login

# Hoặc Python API
python -c "from huggingface_hub import login; login()"
```

### 2. Nén dữ liệu (~30-60 phút)

Script `hf_prepare_staging.py` sẽ:
- Nén `hop2_neighbor_txs/` (162K files, 20 GB → ~3.5 GB tar.gz, tỉ lệ ~5.7×)
- Nén `normal_hop1_txs/` (3.5K files, 347 MB → ~55 MB)
- Nén `phishing_hop1_txs/` (3.5K files, 183 MB → ~36 MB)
- Nén misc folders (stage1/4/8) ~75 MB total
- Copy metadata (CSVs, JSONs, feat_stats.pt)
- Symlink `ego_graph_k2_dataset.pkl` (4.5 GB) — nếu symlink không được, sẽ copy

```bash
python huggingface/hf_prepare_staging.py
```

Kết quả vào `./hf_staging/` (~8 GB).

### 3. Dry-run

Xem trước file nào sẽ upload:

```bash
python huggingface/hf_upload.py --repo-id <username>/EthPhishGraph-2026 --dry-run
```

### 4. Upload (~1-3 giờ)

```bash
python huggingface/hf_upload.py --repo-id <username>/EthPhishGraph-2026
```

Script dùng `upload_large_folder` tự động:
- Chunk files lớn
- Resume khi lỗi mạng
- Upload parallel nhiều files cùng lúc
- Tốc độ 2-12 MB/s (tùy connection)

### 5. Cập nhật README

```python
from huggingface_hub import HfApi
api = HfApi()
api.upload_file(
    path_or_fileobj='huggingface/README_dataset_HF.md',
    path_in_repo='README.md',
    repo_id='<username>/EthPhishGraph-2026',
    repo_type='dataset',
    commit_message='Update dataset card',
)
```

## ⚠️ Chú ý

- **Token Write phải được cấp** cho HF account (lấy ở https://huggingface.co/settings/tokens)
- **Dataset size ~8 GB** sau nén → cần dung lượng đĩa đủ cho staging
- **Revoke token** sau khi upload xong nếu đã bị lộ
- `README_dataset_HF.md` có **3 placeholder** cần sửa: `[Your Name]`, `[Your University]`, `[your-username]`

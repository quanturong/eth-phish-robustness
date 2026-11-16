"""
Chuan bi staging folder cho upload HuggingFace:
- Nen 3 thu muc raw_txs (co 160K+ small JSON) thanh tarballs
- Copy file metadata vao staging
- Khong copy ego_graph_k2_dataset.pkl (upload truc tiep tu goc de tiet kiem dia)
"""
import os
import shutil
import subprocess
import tarfile
import time
from pathlib import Path

SRC_BASE = Path(r'E:\EthereumPhishingDetection\dataset\EthPhishGraph-2026')
STAGING = Path(r'E:\EthereumPhishingDetection\hf_staging')

# ------- Tao cau truc staging -------
STAGING.mkdir(exist_ok=True)
(STAGING / 'raw_txs').mkdir(exist_ok=True)
(STAGING / 'misc').mkdir(exist_ok=True)


def tar_gz(src_dir: Path, dest_tgz: Path, verbose=True):
    """Nen thu muc thanh tar.gz. Khong overwrite neu da ton tai."""
    if dest_tgz.exists():
        sz = dest_tgz.stat().st_size / 1024**3
        print(f'  [SKIP] {dest_tgz.name} da ton tai ({sz:.2f} GB)')
        return
    t0 = time.time()
    file_count = 0
    size_in = 0
    print(f'  [TAR] {src_dir.name} -> {dest_tgz.name}')
    with tarfile.open(dest_tgz, 'w:gz', compresslevel=6) as tf:
        for root, dirs, files in os.walk(src_dir):
            for f in files:
                p = Path(root) / f
                try:
                    rel = p.relative_to(src_dir.parent)
                    tf.add(p, arcname=str(rel))
                    file_count += 1
                    size_in += p.stat().st_size
                    if verbose and file_count % 5000 == 0:
                        dt = time.time() - t0
                        print(f'    {file_count:,} files, {size_in/1024**3:.2f} GB in, '
                              f'{dest_tgz.stat().st_size/1024**3:.2f} GB out, {dt:.0f}s')
                except Exception as e:
                    print(f'    ERR {p}: {e}')
    dt = time.time() - t0
    size_out = dest_tgz.stat().st_size / 1024**3
    print(f'  [DONE] {file_count:,} files, {size_in/1024**3:.2f} GB -> {size_out:.2f} GB '
          f'(ratio {size_in / dest_tgz.stat().st_size:.1f}x), {dt:.1f}s')


# ------- 1. Nen raw txs (3 thu muc lon) -------
print('='*60)
print('STEP 1: Compress raw_txs folders -> tar.gz')
print('='*60)

tar_gz(SRC_BASE / 'ethphishgraph2026_stage9_k2' / 'hop2_neighbor_txs',
       STAGING / 'raw_txs' / 'hop2_neighbor_txs.tar.gz')
tar_gz(SRC_BASE / 'ethphishgraph2026_stage3_dataset' / 'normal_hop1_txs',
       STAGING / 'raw_txs' / 'normal_hop1_txs.tar.gz')
tar_gz(SRC_BASE / 'ethphishgraph2026_stage2_normal_crawl' / 'hop1_txs',
       STAGING / 'raw_txs' / 'phishing_hop1_txs.tar.gz')

# ------- 2. Copy small metadata files -------
print('\n' + '='*60)
print('STEP 2: Copy metadata files')
print('='*60)

metadata_files = [
    # (src relative, dest in staging)
    ('ethphishgraph2026_stage3_dataset/temporal_split.csv', 'temporal_split.csv'),
    ('ethphishgraph2026_stage3_dataset/temporal_split_meta.json', 'temporal_split_meta.json'),
    ('ethphishgraph2026_stage9_k2/per_target_neighbors.pkl', 'per_target_neighbors.pkl'),
    ('ethphishgraph2026_stage9_k2/unique_hop1_neighbors.csv', 'unique_hop1_neighbors.csv'),
    ('ethphishgraph2026_stage9_k2/bad_files.txt', 'bad_files.txt'),
    ('ethphishgraph2026_stage5_baselines_k2/feat_stats.pt', 'feat_stats.pt'),
]
for src_rel, dest_name in metadata_files:
    src = SRC_BASE / src_rel
    dest = STAGING / dest_name
    if src.exists():
        if not dest.exists():
            shutil.copy2(src, dest)
            print(f'  [COPY] {src_rel} -> {dest_name} ({src.stat().st_size/1024:.1f} KB)')
        else:
            print(f'  [SKIP] {dest_name} da ton tai')
    else:
        print(f'  [MISS] {src}')

# ------- 3. Create symlink for main pkl (don't duplicate 4.4 GB) -------
print('\n' + '='*60)
print('STEP 3: Link ego_graph_k2_dataset.pkl (4.4 GB - khong copy, dung link)')
print('='*60)
main_pkl = SRC_BASE / 'ethphishgraph2026_stage9_k2' / 'ego_graph_k2_dataset.pkl'
link_pkl = STAGING / 'ego_graph_k2_dataset.pkl'
if not link_pkl.exists():
    try:
        # Windows: try symlink first
        link_pkl.symlink_to(main_pkl)
        print(f'  [SYMLINK] ego_graph_k2_dataset.pkl -> {main_pkl}')
    except OSError:
        # Fallback: copy
        print(f'  [COPY FALLBACK] Khong tao duoc symlink, copy 4.4 GB...')
        shutil.copy2(main_pkl, link_pkl)
        print(f'  [COPY] Xong')
else:
    print(f'  [SKIP] {link_pkl.name} da ton tai')

# ------- 4. Nen misc folders -------
print('\n' + '='*60)
print('STEP 4: Compress misc folders')
print('='*60)
misc_dirs = [
    ('ethphishgraph2026_stage1_outputs', 'stage1_outputs.tar.gz'),
    ('ethphishgraph2026_stage8_crosscheck_D2', 'stage8_crosscheck_D2.tar.gz'),
    ('ethphishgraph2026_stage4_imbalanced', 'stage4_imbalanced.tar.gz'),
]
for src_rel, dest_name in misc_dirs:
    src = SRC_BASE / src_rel
    dest = STAGING / 'misc' / dest_name
    if src.exists():
        tar_gz(src, dest)
    else:
        print(f'  [MISS] {src}')

# ------- 5. Final summary -------
print('\n' + '='*60)
print('STAGING SUMMARY')
print('='*60)
total = 0
for root, dirs, files in os.walk(STAGING):
    for f in files:
        p = Path(root) / f
        try:
            s = p.stat().st_size
            total += s
            rel = p.relative_to(STAGING)
            if s > 1024**2:
                print(f'  {str(rel):<50} {s/1024**3:>6.2f} GB')
            else:
                print(f'  {str(rel):<50} {s/1024:>6.1f} KB')
        except: pass

print(f'\nTOTAL: {total/1024**3:.2f} GB (will upload to HF)')
print(f'\nNext: run `python hf_upload.py --repo-id <username>/EthPhishGraph-2026`')

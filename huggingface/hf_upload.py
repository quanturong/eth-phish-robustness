"""
Upload staging folder to HuggingFace Dataset repo.
Usage:
    python hf_upload.py --repo-id <username>/EthPhishGraph-2026
    python hf_upload.py --repo-id <username>/EthPhishGraph-2026 --dry-run    # preview chi upload gi
"""
import argparse
import sys
from pathlib import Path

from huggingface_hub import HfApi, upload_large_folder

STAGING = Path(r'E:\EthereumPhishingDetection\hf_staging')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo-id', required=True,
                    help='HuggingFace repo id, format: username/dataset-name')
    ap.add_argument('--dry-run', action='store_true',
                    help='Chi liet ke file, khong upload')
    ap.add_argument('--private', action='store_true',
                    help='Repo private (mac dinh public)')
    args = ap.parse_args()

    if not STAGING.exists():
        sys.exit(f'ERR: {STAGING} khong ton tai. Chay `python hf_prepare_staging.py` truoc.')

    api = HfApi()

    # Verify login
    try:
        who = api.whoami()
        print(f'Logged in as: {who["name"]}')
    except Exception as e:
        sys.exit(f'ERR: chua login. Chay `huggingface-cli login` truoc. ({e})')

    # List files to upload
    files = []
    total = 0
    for p in sorted(STAGING.rglob('*')):
        if p.is_file():
            s = p.stat().st_size
            files.append((p, s))
            total += s
    print(f'\n{len(files)} file(s), tong {total/1024**3:.2f} GB:')
    for p, s in files:
        rel = p.relative_to(STAGING)
        if s > 1024**2:
            print(f'  {str(rel):<50} {s/1024**3:>6.2f} GB')
        else:
            print(f'  {str(rel):<50} {s/1024:>6.1f} KB')

    if args.dry_run:
        print('\n[DRY-RUN] Khong upload. Bo --dry-run de upload that.')
        return

    # Check repo exists
    try:
        api.repo_info(repo_id=args.repo_id, repo_type='dataset')
        print(f'\nRepo da ton tai: {args.repo_id}')
    except Exception:
        print(f'\nTao repo moi: {args.repo_id}')
        api.create_repo(
            repo_id=args.repo_id, repo_type='dataset',
            private=args.private, exist_ok=True,
        )

    print(f'\nBat dau upload... (co the mat vai gio)')
    print(f'Upload RESUMABLE: nhan Ctrl+C de dung, chay lai se tiep tuc tu cho da upload.')

    # upload_large_folder tu dong chunk + retry + resumable
    upload_large_folder(
        repo_id=args.repo_id,
        repo_type='dataset',
        folder_path=str(STAGING),
    )

    print(f'\nDONE! Xem tai: https://huggingface.co/datasets/{args.repo_id}')


if __name__ == '__main__':
    main()

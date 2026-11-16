"""
Build consolidated metrics report (BaoCao_SoLieu_Final.md)
Dua tren data moi nhat trong json_stage5_6_final/ (co peae_paper).

Khac build_metrics_report.py cu:
- Dung peae_paper thay peaegnn/peaegnnv2
- Co ROC-AUC tu stage5_rocauc_merged.json
- Dua vao mincost_summary.md va diag_summary.md da co
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(r'E:\EthereumPhishingDetection\json_stage5_6_final')
STAGE5 = BASE / 'stage5'
STAGE6 = BASE / 'stage6'
OUT = Path(r'E:\EthereumPhishingDetection\BaoCao_SoLieu_Final.md')


def main():
    md = []
    md.append('# Báo cáo số liệu tổng hợp — Pipeline hoàn chỉnh\n')
    md.append('> Nguồn: `json_stage5_6_final/` (dữ liệu mới nhất với `peae_paper`).\n')
    md.append('> Dataset: EthPhishGraph-2026, K=2 ego-graph, 1,408 test samples.\n')
    md.append('')

    # ========== STAGE 5 BASELINE ==========
    md.append('## 1. Stage 5 — Baseline (dữ liệu sạch, 3 seeds)\n')

    # Load ROC-AUC merged
    roc = json.load(open(STAGE5 / 'stage5_rocauc_merged.json', encoding='utf-8'))

    md.append('### 1.1 Bảng tổng hợp 3 mô hình chính (Mean ± Std)\n')
    md.append('| Mô hình | Macro-F1 | PR-AUC | ROC-AUC | Phishing Recall |')
    md.append('|---|---|---|---|---|')
    for m in ['graphsage', 'gatv2', 'peae_paper']:
        agg = roc['agg'][m]
        # Get recall from per_seed (average)
        rec_vals = [s['rec_phishing'] for s in roc['per_seed'][m]]
        rec_mean = sum(rec_vals) / len(rec_vals)
        rec_std = (sum((v - rec_mean) ** 2 for v in rec_vals) / len(rec_vals)) ** 0.5
        md.append(f'| **{m}** | '
                  f'{agg["macro_f1"][0]:.4f} ± {agg["macro_f1"][1]:.4f} | '
                  f'{agg["pr_auc"][0]:.4f} ± {agg["pr_auc"][1]:.4f} | '
                  f'{agg["roc_auc"][0]:.4f} ± {agg["roc_auc"][1]:.4f} | '
                  f'{rec_mean:.4f} ± {rec_std:.4f} |')
    md.append('')
    md.append('> `peae_paper` là mô hình chính (bản tái lập PEAE-GNN theo Huang et al. IEEE TCSS 2024).\n')
    md.append('> `graphsage`, `gatv2` làm baseline so sánh.\n')
    md.append('')

    md.append('### 1.2 Chi tiết từng seed\n')
    md.append('| Mô hình | Seed | Macro-F1 | PR-AUC | ROC-AUC | Phishing Recall |')
    md.append('|---|---|---|---|---|---|')
    for m in ['graphsage', 'gatv2', 'peae_paper']:
        for s in roc['per_seed'][m]:
            md.append(f'| {m} | {s["seed"]} | '
                      f'{s["macro_f1"]:.4f} | {s["pr_auc"]:.4f} | '
                      f'{s["roc_auc"]:.4f} | {s["rec_phishing"]:.4f} |')
    md.append('')

    # ========== STAGE 6 ATTACK ==========
    md.append('## 2. Stage 6 — Tấn công đối kháng (3 mô hình × 7 attacks × 3 seeds)\n')
    md.append('> Nguồn chi tiết: `stage6/mincost_summary.md`\n')
    md.append('')

    # Load mincost_summary content
    mincost_md = (STAGE6 / 'mincost_summary.md').read_text(encoding='utf-8')
    md.append(mincost_md)
    md.append('')

    # ========== DIAG ==========
    md.append('## 3. Độ nhạy đặc trưng (RQ2) — 3 mô hình × 3 seeds\n')
    md.append('> Nguồn chi tiết: `stage6/diag_summary.md`\n')
    md.append('')

    diag_md = (STAGE6 / 'diag_summary.md').read_text(encoding='utf-8')
    md.append(diag_md)
    md.append('')

    # ========== KEY FINDINGS ==========
    md.append('## 4. Key Findings\n')
    md.append('### 4.1 Baseline Clean Performance\n')
    md.append('- **GraphSAGE** tốt nhất mọi chỉ số (Macro-F1 0.866, ROC-AUC 0.952)')
    md.append('- **PEAE paper** đứng thứ hai Macro-F1 (0.834) nhưng ROC-AUC thấp nhất (0.872)')
    md.append('- PEAE là mô hình chính vì bám bài báo gốc, không phải vì hiệu năng tốt nhất.\n')

    md.append('### 4.2 Best Attack Phụ Thuộc Kiến Trúc\n')
    md.append('- **peae_paper**: ADAPTIVE-STC-LV mạnh nhất (87.2% @ 1200 tx; vượt 50% ví chỉ với 190 tx)')
    md.append('- **graphsage**: ADAPTIVE-STC-LV mạnh nhất nhưng chỉ 15.0% @ 1200 tx (bền nhất)')
    md.append('- **gatv2**: TIH mạnh nhất (33.2%), ADAPTIVE chỉ 6.8%\n')
    md.append('→ Không có tấn công "universal strongest" — phải báo cáo worst-case cho mỗi mô hình.\n')

    md.append('### 4.3 Vì sao PEAE paper sụp trước ADAPTIVE?\n')
    md.append('Từ diag_peae_features (24 chiều engineered):')
    md.append('- MT (tỉ lệ giá trị), RT (cường độ tương tác), AFTS (khoảng cách thời gian) đều lật 10-13% ví khi thay đổi')
    md.append('- Thay toàn bộ 24 chiều của target → lật ~30% ví')
    md.append('- Thay hàng xóm bậc 1 → chỉ lật 0.4-0.6% (**PEAE chủ yếu dựa vào feature của target node**)')
    md.append('→ ADAPTIVE tác động trực tiếp các chiều MT/RT/AFTS → giải thích vì sao hiệu quả cao.\n')

    md.append('### 4.4 GraphSAGE Robust (khớp Paper C)\n')
    md.append('- Tấn công designed cho PEAE không transfer sang GraphSAGE')
    md.append('- Hàng xóm bậc 1 là chủ đạo cho GraphSAGE (hiệu +26.7 so với đối chứng)')
    md.append('- Sampling-based aggregation inherently robust (khớp paper Frankart et al. 2026).\n')

    OUT.write_text('\n'.join(md), encoding='utf-8')
    print(f'Saved -> {OUT}')
    print(f'Size: {OUT.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()

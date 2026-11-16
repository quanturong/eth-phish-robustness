"""
Gộp toàn bộ số liệu Baseline (Stage 5) + Stage Attack (Stage 6) từ folder
json_stage5_6_final/ ra file markdown BaoCao_SoLieu.md.
"""
import json
from pathlib import Path
import numpy as np

BASE = Path(r'E:\EthereumPhishingDetection\json_stage5_6_final\json_stage5_6_final')
STAGE5 = BASE / 'stage5'
STAGE6 = BASE / 'stage6'
OUT = Path(r'E:\EthereumPhishingDetection\BaoCao_SoLieu_Stage5_6.md')

MODELS = ['graphsage', 'gatv2', 'peaegnn', 'peaegnnv2']
MODEL_LABEL = {
    'graphsage': 'GraphSAGE',
    'gatv2': 'GATv2',
    'peaegnn': 'PEAE-style (cũ)',
    'peaegnnv2': 'peaegnnv2 (mô hình chính)',
}
SEEDS = [42, 43, 44]
BASE_ATTACKS = ['TOH', 'TIH', 'BPH-T2P', 'BPH-P2T', 'STC', 'MWR']


# ======================================================================
# STAGE 5 — Baseline
# ======================================================================
def load_stage5():
    """Return dict[model] -> list of 3 seeds with test metrics."""
    old = json.load(open(STAGE5 / 'stage5_k2' / 'results_all.json', encoding='utf-8'))
    v2 = json.load(open(STAGE5 / 'stage5_k2_7_10' / 'results_peaegnnv2.json', encoding='utf-8'))
    out = {}
    for m in ['graphsage', 'gatv2', 'peaegnn']:
        out[m] = [s['test'] for s in old[m]['per_seed']]
    out['peaegnnv2'] = [s['test'] for s in v2['peaegnnv2']['per_seed']]
    return out


def mean_std(vals):
    v = np.array(vals, dtype=float)
    return float(v.mean()), float(v.std(ddof=0))


def fmt_pct(mean, std=None, digits=2):
    if std is None:
        return f'{mean*100:.{digits}f}'
    return f'{mean*100:.{digits}f} ± {std*100:.{digits}f}'


def fmt_val(mean, std=None, digits=4):
    if std is None:
        return f'{mean:.{digits}f}'
    return f'{mean:.{digits}f} ± {std:.{digits}f}'


# ======================================================================
# STAGE 6 — attacks
# ======================================================================
def load_stage6_small(model, seed):
    """7-attack small-budget file (6 originals × budgets 1,3,5,10,20)."""
    f = STAGE6 / f'results_{model}_seed{seed}.json'
    if not f.exists():
        return None
    return json.load(open(f, encoding='utf-8'))


def load_stage6_adaptive_big(model, seed):
    f = STAGE6 / f'results_{model}_seed{seed}_adaptive_lv_big.json'
    if not f.exists():
        return None
    return json.load(open(f, encoding='utf-8'))


def load_stage6_mincost(model, seed, group):
    f = STAGE6 / f'results_{model}_seed{seed}_mincost_{group}_full.json'
    if not f.exists():
        return None
    return json.load(open(f, encoding='utf-8'))


MINCOST_GROUPS = {
    'TOH': 'toh_tih', 'TIH': 'toh_tih',
    'BPH-T2P': 'bph', 'BPH-P2T': 'bph',
    'STC': 'stc', 'MWR': 'mwr',
    'ADAPTIVE-STC-LV': 'adaptive',
}


# ======================================================================
# BUILD MARKDOWN
# ======================================================================
def main():
    md = []
    md.append('# Báo cáo số liệu — Stage 5 (Baseline) & Stage 6 (Attack)\n')
    md.append('> Nguồn: `json_stage5_6_final/` (67 file JSON, chốt 2026-10-18).\n')
    md.append('> Mỗi mô hình chạy 3 seed (42/43/44). Mean ± Std là độ lệch chuẩn qua 3 seed.\n')
    md.append('> **Lưu ý**: ROC-AUC không được lưu trong các file JSON Stage 5, nên bảng chỉ có PR-AUC.\n')
    md.append('')

    # ------------------- BASELINE -------------------
    md.append('## 1. Baseline — dữ liệu sạch (Stage 5)\n')
    md.append('> Mục đích: xác định hiệu năng ban đầu của từng mô hình.\n')
    md.append('> Tập test 2026: **1,408 ví** (594 phishing + 814 normal).\n')
    md.append('')

    s5 = load_stage5()

    # Full table: Model × Seed → metrics
    md.append('### 1.1 Chi tiết từng seed\n')
    cols = ['Mô hình', 'Seed', 'Macro-F1', 'Phishing Precision',
            'Phishing Recall', 'Phishing F1', 'PR-AUC']
    md.append('| ' + ' | '.join(cols) + ' |')
    md.append('|' + '|'.join(['---'] * len(cols)) + '|')
    for m in MODELS:
        for i, seed in enumerate(SEEDS):
            r = s5[m][i]
            md.append('| ' + ' | '.join([
                MODEL_LABEL[m],
                str(seed),
                fmt_val(r['macro_f1']),
                fmt_val(r['prec_phishing']),
                fmt_val(r['rec_phishing']),
                fmt_val(r['f1_phishing']),
                fmt_val(r['pr_auc']),
            ]) + ' |')
    md.append('')

    # Mean ± Std summary
    md.append('### 1.2 Tổng hợp Mean ± Std qua 3 seed\n')
    cols = ['Mô hình', 'Macro-F1', 'Phishing Precision',
            'Phishing Recall', 'Phishing F1', 'PR-AUC']
    md.append('| ' + ' | '.join(cols) + ' |')
    md.append('|' + '|'.join(['---'] * len(cols)) + '|')
    for m in MODELS:
        agg = {}
        for key in ['macro_f1', 'prec_phishing', 'rec_phishing', 'f1_phishing', 'pr_auc']:
            agg[key] = mean_std([s[key] for s in s5[m]])
        md.append('| ' + ' | '.join([
            MODEL_LABEL[m],
            fmt_val(*agg['macro_f1']),
            fmt_val(*agg['prec_phishing']),
            fmt_val(*agg['rec_phishing']),
            fmt_val(*agg['f1_phishing']),
            fmt_val(*agg['pr_auc']),
        ]) + ' |')
    md.append('')

    # Normal class metrics (bonus)
    md.append('### 1.3 Bổ sung: số liệu lớp Normal (tham khảo)\n')
    cols = ['Mô hình', 'Normal Precision', 'Normal Recall', 'Normal F1']
    md.append('| ' + ' | '.join(cols) + ' |')
    md.append('|' + '|'.join(['---'] * len(cols)) + '|')
    for m in MODELS:
        agg = {k: mean_std([s[k] for s in s5[m]]) for k in
               ['prec_normal', 'rec_normal', 'f1_normal']}
        md.append('| ' + ' | '.join([
            MODEL_LABEL[m],
            fmt_val(*agg['prec_normal']),
            fmt_val(*agg['rec_normal']),
            fmt_val(*agg['f1_normal']),
        ]) + ' |')
    md.append('')

    # ------------------- STAGE ATTACK -------------------
    md.append('## 2. Stage Attack — dữ liệu bị tấn công (Stage 6)\n')
    md.append('> Mục đích: đo hiệu quả tấn công và sự suy giảm hiệu năng.\n')
    md.append('> **ASR** = N_flipped / N_correct_clean (ví phishing bắt đúng lúc sạch, bị bỏ sót sau tấn công).\n')
    md.append('> **Robust Phishing Recall** = recall phishing sau tấn công (chỉ phishing bị tấn công, normal giữ nguyên).\n')
    md.append('> **Robust Macro-F1** = Macro-F1 sau tấn công.\n')
    md.append('> **Chi phí** = (số tx thêm) × (giá trị ETH + phí gas ETH), trung bình/ví.\n')
    md.append('')

    # 2.1 ADAPTIVE-STC-LV big budgets — 3 mô hình × 5 budget × 3 seed
    md.append('### 2.1 ADAPTIVE-STC-LV ngân sách lớn (3 mô hình × budget 20/50/100/200/500)\n')

    for m in ['graphsage', 'gatv2', 'peaegnnv2']:
        md.append(f'#### {MODEL_LABEL[m]} — ADAPTIVE-STC-LV\n')
        # collect per-seed per-budget
        per_budget = {}  # budget -> list of dicts (per seed)
        for seed in SEEDS:
            d = load_stage6_adaptive_big(m, seed)
            if d is None:
                continue
            for b in d['attacks']['ADAPTIVE-STC-LV']['budgets']:
                per_budget.setdefault(b['budget'], []).append(b)
        cols = ['Budget b', 'Số tx (amt)', 'ASR (%)', 'Robust Phish Recall (%)',
                'Robust Macro-F1', 'Mean P phish', 'Value ETH', 'Gas ETH']
        md.append('| ' + ' | '.join(cols) + ' |')
        md.append('|' + '|'.join(['---'] * len(cols)) + '|')
        for b in sorted(per_budget):
            rows = per_budget[b]
            if not rows:
                continue
            amt = mean_std([r['amt'] for r in rows])
            asr = mean_std([r['asr'] for r in rows])
            rr = mean_std([r['robust_recall'] for r in rows])
            rf = mean_std([r['robust_macro_f1'] for r in rows])
            mp = mean_std([r['mean_p_phish_attacked'] for r in rows])
            v = mean_std([r['mean_value_eth'] for r in rows])
            g = mean_std([r['mean_gas_eth'] for r in rows])
            md.append('| ' + ' | '.join([
                str(b),
                fmt_val(*amt, digits=1),
                fmt_pct(*asr),
                fmt_pct(*rr),
                fmt_val(*rf),
                fmt_val(*mp),
                fmt_val(*v, digits=3),
                fmt_val(*g, digits=3),
            ]) + ' |')
        md.append('')

    # 2.2 6 originals - PEAEGNNV2 only (budget 1,3,5,10,20) - from small file
    md.append('### 2.2 Sáu tấn công gốc, ngân sách nhỏ (peaegnnv2, budget 1/3/5/10/20)\n')
    md.append('> Chỉ có `peaegnnv2` ở 2 seed (42, 43) được chạy; kết quả tham khảo.\n')
    md.append('')
    small_data = {s: load_stage6_small('peaegnnv2', s) for s in SEEDS}
    for atk in BASE_ATTACKS:
        md.append(f'#### {atk} — peaegnnv2\n')
        per_budget = {}
        for seed in SEEDS:
            d = small_data.get(seed)
            if d is None or atk not in d['attacks']:
                continue
            for b in d['attacks'][atk]['budgets']:
                per_budget.setdefault(b['budget'], []).append(b)
        cols = ['Budget b', 'Số tx (amt)', 'ASR (%)', 'Robust Phish Recall (%)',
                'Robust Macro-F1', 'Mean P phish', 'Value ETH', 'Gas ETH']
        md.append('| ' + ' | '.join(cols) + ' |')
        md.append('|' + '|'.join(['---'] * len(cols)) + '|')
        for b in sorted(per_budget):
            rows = per_budget[b]
            if not rows:
                continue
            amt = mean_std([r['amt'] for r in rows])
            asr = mean_std([r['asr'] for r in rows])
            rr = mean_std([r['robust_recall'] for r in rows])
            rf = mean_std([r['robust_macro_f1'] for r in rows])
            mp = mean_std([r['mean_p_phish_attacked'] for r in rows])
            v = mean_std([r['mean_value_eth'] for r in rows])
            g = mean_std([r['mean_gas_eth'] for r in rows])
            md.append('| ' + ' | '.join([
                str(b),
                fmt_val(*amt, digits=1),
                fmt_pct(*asr),
                fmt_pct(*rr),
                fmt_val(*rf),
                fmt_val(*mp),
                fmt_val(*v, digits=4),
                fmt_val(*g, digits=4),
            ]) + ' |')
        md.append('')

    # 2.3 Min cost — tất cả 7 tấn công × 3 mô hình × 3 seed
    md.append('### 2.3 Chi phí tối thiểu (min_cost) — 7 tấn công × 3 mô hình\n')
    md.append('> Tăng dần budget, dừng ngay lần đầu p_phish < 0.5. Giới hạn tối đa 1,200 giao dịch.\n')
    md.append('> Mỗi ô: giá trị trung bình ± độ lệch chuẩn qua 3 seed (giá trị `null` = chưa đạt mốc trong 1,200 txs → báo "chưa đạt").\n')
    md.append('')

    all_attacks = BASE_ATTACKS + ['ADAPTIVE-STC-LV']
    for metric_key, metric_label in [
        ('txs_to_bypass_10pct', 'Số tx để vượt 10% ví'),
        ('txs_to_bypass_25pct', 'Số tx để vượt 25% ví'),
        ('txs_to_bypass_50pct', 'Số tx để vượt 50% ví'),
        ('frac_bypassed_within_max', 'Tỉ lệ bị vượt trong 1,200 tx (%)'),
    ]:
        md.append(f'#### {metric_label}\n')
        cols = ['Tấn công'] + [MODEL_LABEL[m] for m in ['peaegnnv2', 'graphsage', 'gatv2']]
        md.append('| ' + ' | '.join(cols) + ' |')
        md.append('|' + '|'.join(['---'] * len(cols)) + '|')
        for atk in all_attacks:
            group = MINCOST_GROUPS[atk]
            row = [atk]
            for m in ['peaegnnv2', 'graphsage', 'gatv2']:
                vals = []
                for seed in SEEDS:
                    d = load_stage6_mincost(m, seed, group)
                    if d is None or atk not in d['attacks']:
                        continue
                    v = d['attacks'][atk].get(metric_key)
                    if v is None:
                        continue
                    vals.append(v)
                if not vals:
                    row.append('– (chưa đạt)')
                else:
                    if metric_key.endswith('pct'):
                        v = mean_std(vals)
                        hit = len(vals)
                        row.append(f'{v[0]:.0f} ± {v[1]:.0f} ({hit}/3 seed)')
                    else:
                        v = mean_std(vals)
                        row.append(fmt_pct(*v))
            md.append('| ' + ' | '.join(row) + ' |')
        md.append('')

    # 2.4 ASR tại 1200 giao dịch - full table 7 attacks × 3 models
    md.append('### 2.4 Tỉ lệ bị vượt (ASR) tối đa trong 1,200 giao dịch — bảng tổng kết\n')
    md.append('> Trung bình ± độ lệch chuẩn qua 3 seed. **In đậm** = tấn công mạnh nhất của mô hình.\n')
    md.append('')
    cols = ['Tấn công', MODEL_LABEL['peaegnnv2'], MODEL_LABEL['graphsage'], MODEL_LABEL['gatv2']]
    md.append('| ' + ' | '.join(cols) + ' |')
    md.append('|' + '|'.join(['---'] * len(cols)) + '|')
    # First collect best per model
    model_best = {}
    model_data = {}
    for m in ['peaegnnv2', 'graphsage', 'gatv2']:
        best, best_atk = -1, None
        rows = {}
        for atk in all_attacks:
            group = MINCOST_GROUPS[atk]
            vals = []
            for seed in SEEDS:
                d = load_stage6_mincost(m, seed, group)
                if d is None or atk not in d['attacks']:
                    continue
                vals.append(d['attacks'][atk]['frac_bypassed_within_max'])
            if not vals:
                rows[atk] = None
                continue
            v = mean_std(vals)
            rows[atk] = v
            if v[0] > best:
                best, best_atk = v[0], atk
        model_best[m] = best_atk
        model_data[m] = rows
    for atk in all_attacks:
        row = [atk]
        for m in ['peaegnnv2', 'graphsage', 'gatv2']:
            v = model_data[m].get(atk)
            if v is None:
                row.append('–')
            else:
                s = fmt_pct(*v)
                if atk == model_best[m]:
                    s = f'**{s}**'
                row.append(s)
        md.append('| ' + ' | '.join(row) + ' |')
    md.append('')

    # Số ví phishing đủ điều kiện
    md.append('### 2.5 Số ví phishing đủ điều kiện (bắt đúng lúc sạch) — mẫu số của ASR\n')
    md.append('')
    cols = ['Mô hình', 'Seed 42', 'Seed 43', 'Seed 44', 'Mean']
    md.append('| ' + ' | '.join(cols) + ' |')
    md.append('|' + '|'.join(['---'] * len(cols)) + '|')
    for m in ['peaegnnv2', 'graphsage', 'gatv2']:
        vals = []
        for seed in SEEDS:
            d = load_stage6_mincost(m, seed, 'adaptive')
            if d is None:
                vals.append(None)
            else:
                vals.append(d['n_eligible'])
        clean = [v for v in vals if v is not None]
        mean = f'{np.mean(clean):.1f}' if clean else '–'
        row = [MODEL_LABEL[m]] + [str(v) if v is not None else '–' for v in vals] + [mean]
        md.append('| ' + ' | '.join(row) + ' |')
    md.append('')
    md.append('> **Tổng số ví phishing trong test**: 594 (của 1,408 ví).\n')
    md.append('')

    # Note on ROC-AUC
    md.append('## 3. Ghi chú\n')
    md.append('1. **ROC-AUC**: file JSON Stage 5 không lưu metric này; chỉ có PR-AUC. Nếu cần, phải chạy lại Stage 5 với lưu bổ sung.\n')
    md.append('2. **Mô hình `peaegnn` (cũ) vs `peaegnnv2` (mới)**: Nhật ký đổi mô hình chính sang v2 (gần bài báo gốc hơn). PEAE-style (cũ) chỉ có kết quả Stage 5 trong folder này, các kết quả Stage 6 (6 originals, ADAPTIVE big, min_cost) chỉ cho `peaegnnv2 / graphsage / gatv2`.\n')
    md.append('3. **Số liệu robust_recall sau tấn công** đã có sẵn trong trường `robust_recall` của mỗi budget entry; tương tự `robust_macro_f1`.\n')
    md.append('4. **Chi phí**: giá trị ETH là tổng cộng dồn qua các giao dịch (không phải vốn tối thiểu). Gas được lấy mẫu từ lịch sử ví target.\n')
    md.append('')

    OUT.write_text('\n'.join(md), encoding='utf-8')
    print(f'Saved -> {OUT}')
    print(f'Size: {OUT.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()

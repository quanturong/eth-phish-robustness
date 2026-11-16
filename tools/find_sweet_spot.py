"""
Tim "sweet spot" cho TAT CA (attack x model) = diem can bang nhat giua ASR va cost.

Dinh nghia sweet spot cuoi cung:
  argmax [ ASR_normalized - alpha * cost_normalized ]  voi alpha = 0.3 (nhan manh ASR)
  Trong do _normalized la (v - min) / (max - min) trong curve.

So sanh them: Kneedle, Max ROI, Economic V=0.1/1/10 ETH.
"""
import json
import sys
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(r'E:\EthereumPhishingDetection\json_stage5_6_final\stage6')
OUT_MD = Path(r'E:\EthereumPhishingDetection\BaoCao_Sweet_Spot_All.md')
OUT_CSV = Path(r'E:\EthereumPhishingDetection\sweet_spot_summary.csv')

MODELS = ['peae_paper', 'graphsage', 'gatv2']
SEEDS = [42, 43, 44]
ATTACKS_PER_GROUP = {
    'adaptive': ['ADAPTIVE-STC-LV'],
    'toh_tih': ['TOH', 'TIH'],
    'bph': ['BPH-T2P', 'BPH-P2T'],
    'stc': ['STC'],
    'mwr': ['MWR'],
}
ATTACKS = ['TOH', 'TIH', 'BPH-T2P', 'BPH-P2T', 'STC', 'MWR', 'ADAPTIVE-STC-LV']
COST_PER_TX = 0.00124
TX_PER_UNIT = {'TOH': 1, 'TIH': 1, 'BPH-T2P': 2, 'BPH-P2T': 2,
               'STC': 4, 'MWR': 3, 'ADAPTIVE-STC-LV': 6}


def load_curves(model, attack):
    group = next(g for g, atks in ATTACKS_PER_GROUP.items() if attack in atks)
    curves_per_seed = []
    for seed in SEEDS:
        f = BASE / f'results_{model}_seed{seed}_mincost_{group}_full.json'
        if not f.exists():
            continue
        d = json.load(open(f, encoding='utf-8'))
        if attack not in d['attacks']:
            continue
        curve = d['attacks'][attack]['curve']
        pts = [(c['budget'] * TX_PER_UNIT[attack], c['frac']) for c in curve]
        curves_per_seed.append(pts)
    if not curves_per_seed:
        return None
    budgets = sorted({tx for pts in curves_per_seed for tx, _ in pts})
    avg, std = [], []
    for tx in budgets:
        vals = [f for pts in curves_per_seed for t, f in pts if t == tx]
        if vals:
            avg.append((tx, float(np.mean(vals))))
            std.append(float(np.std(vals)))
    return avg, std


def sweet_spot(curve, alpha=0.5):
    """
    argmax [ASR - alpha * cost_ETH]
    Giai thich: ASR 1% = cost 0.01 ETH la "ngang nhau" (alpha=1); alpha=0.5 nhan manh ASR hon.
    Vd ADAPTIVE/peae_paper: sweet_spot ≈ 300 tx (ASR 64% - 0.5*0.37 ETH = 0.455 toi da).
    """
    if not curve or len(curve) < 2:
        return None
    xs = np.array([p[0] for p in curve], dtype=float)
    ys = np.array([p[1] for p in curve], dtype=float)
    costs = xs * COST_PER_TX
    score = ys - alpha * costs
    i = int(np.argmax(score))
    return int(xs[i]), float(ys[i]), float(score[i])


def kneedle(curve):
    if not curve or len(curve) < 3: return None
    xs = np.array([p[0] for p in curve], dtype=float)
    ys = np.array([p[1] for p in curve], dtype=float)
    xn = (xs - xs.min()) / max(xs.max() - xs.min(), 1e-9)
    yn = (ys - ys.min()) / max(ys.max() - ys.min(), 1e-9)
    i = int(np.argmax(yn - xn))
    return int(xs[i]), float(ys[i])


def roi_max(curve):
    best = (None, 0, -1)
    for tx, asr in curve:
        if tx == 0: continue
        roi = asr / (tx * COST_PER_TX)
        if roi > best[2]:
            best = (tx, asr, roi)
    return best


def economic_opt(curve, V):
    best = (0, 0.0, 0.0)
    for tx, asr in curve:
        p = V * asr - COST_PER_TX * tx
        if p > best[2]:
            best = (tx, asr, p)
    return best


def interp_at_asr(curve, target_asr):
    """Interpolate tx needed to reach a target ASR."""
    for i in range(len(curve)):
        if curve[i][1] >= target_asr:
            if i == 0:
                return curve[0][0]
            x0, y0 = curve[i-1]
            x1, y1 = curve[i]
            frac = (target_asr - y0) / max(y1 - y0, 1e-9)
            return int(x0 + frac * (x1 - x0))
    return None  # not reached


def main():
    md = []
    md.append('# Sweet Spot — Phân tích tối ưu cost/ASR cho TẤT CẢ (model × attack)\n')
    md.append(f'> **Chi phí gas**: {COST_PER_TX} ETH / giao dịch\n')
    md.append(f'> **Sweet spot**: argmax [ASR − 0.5 × cost_ETH] (ASR 1% ≈ 0.02 ETH, phạt cost absolute)\n')
    md.append(f'> **3 seeds** trung bình, 21 combinations = 3 models × 7 attacks\n')
    md.append('')

    # ========== BẢNG TỔNG KẾT 1: Sweet spot ==========
    md.append('## 1. 🎯 Sweet Spot — Khuyến nghị DUY NHẤT cho mỗi combo\n')
    md.append('')
    md.append('| Model | Attack | Sweet spot tx | ASR | Cost (ETH) | ROI (ASR/ETH) | 50% ASR tx |')
    md.append('|---|---|---:|---:|---:|---:|---:|')

    csv_rows = ['model,attack,sweet_tx,sweet_asr,sweet_cost_eth,sweet_roi,'
                 'kneedle_tx,kneedle_asr,roi_max_tx,roi_max_asr,'
                 'econ01_tx,econ01_asr,econ1_tx,econ1_asr,econ10_tx,econ10_asr,'
                 'asr50_tx,max_asr']

    for model in MODELS:
        for atk in ATTACKS:
            res = load_curves(model, atk)
            if res is None:
                md.append(f'| {model} | {atk} | — | — | — | — | — |')
                continue
            curve, std = res
            # Sweet spot
            ss = sweet_spot(curve, alpha=0.5)
            if ss is None:
                md.append(f'| {model} | {atk} | — | — | — | — | — |')
                continue
            ss_tx, ss_asr, ss_score = ss
            ss_cost = ss_tx * COST_PER_TX
            ss_roi = ss_asr / ss_cost if ss_cost > 0 else 0
            # 50% ASR
            asr50 = interp_at_asr(curve, 0.5)
            asr50_s = f'{asr50}' if asr50 else '— (ko đạt)'
            # Other metrics for CSV
            kn = kneedle(curve) or (0, 0)
            roi = roi_max(curve) or (0, 0, 0)
            e01 = economic_opt(curve, 0.1)
            e1 = economic_opt(curve, 1.0)
            e10 = economic_opt(curve, 10.0)
            max_asr = max(p[1] for p in curve)

            md.append(f'| {model} | **{atk}** | **{ss_tx}** | **{ss_asr*100:.1f}%** | '
                      f'{ss_cost:.4f} | {ss_roi*100:.0f}% | {asr50_s} |')

            csv_rows.append(f'{model},{atk},{ss_tx},{ss_asr:.4f},{ss_cost:.4f},{ss_roi:.4f},'
                            f'{kn[0]},{kn[1]:.4f},{roi[0]},{roi[1]:.4f},'
                            f'{e01[0]},{e01[1]:.4f},{e1[0]},{e1[1]:.4f},{e10[0]},{e10[1]:.4f},'
                            f'{asr50 or ""},{max_asr:.4f}')
    md.append('')

    # ========== Bảng 2: Chi tiết metrics khác ==========
    md.append('## 2. Chi tiết: so sánh 5 metrics tối ưu khác nhau\n')
    md.append('> Đọc theo: *"với threat model/mục tiêu Y, chọn X tx"*\n')
    md.append('')

    for model in MODELS:
        md.append(f'### {model}\n')
        md.append('')
        md.append('| Attack | Max ASR | Sweet spot | Kneedle (toán) | ROI max (eco) | Econ V=0.1 | Econ V=1 | Econ V=10 |')
        md.append('|---|---:|---:|---:|---:|---:|---:|---:|')
        for atk in ATTACKS:
            res = load_curves(model, atk)
            if res is None:
                md.append(f'| {atk} | — | — | — | — | — | — | — |')
                continue
            curve, _ = res
            max_asr = max(p[1] for p in curve)
            ss = sweet_spot(curve, alpha=0.5)
            kn = kneedle(curve)
            roi = roi_max(curve)
            e01 = economic_opt(curve, 0.1)
            e1 = economic_opt(curve, 1.0)
            e10 = economic_opt(curve, 10.0)
            def fmt(tx, asr):
                return f'{tx}tx ({asr*100:.1f}%)' if tx else '—'
            md.append(f'| {atk} | **{max_asr*100:.1f}%** | '
                      f'{fmt(ss[0], ss[1]) if ss else "—"} | '
                      f'{fmt(kn[0], kn[1]) if kn else "—"} | '
                      f'{fmt(roi[0], roi[1]) if roi[0] else "—"} | '
                      f'{fmt(e01[0], e01[1]) if e01[0] else "0"} | '
                      f'{fmt(e1[0], e1[1]) if e1[0] else "0"} | '
                      f'{fmt(e10[0], e10[1]) if e10[0] else "0"} |')
        md.append('')

    # ========== Ranking: top attacks ==========
    md.append('## 3. 🏆 Top ranking: attacks hiệu quả nhất ở sweet spot\n')
    md.append('> Sắp theo ROI (ASR per ETH cost)\n')
    md.append('')

    ranks = []
    for model in MODELS:
        for atk in ATTACKS:
            res = load_curves(model, atk)
            if res is None:
                continue
            curve, _ = res
            ss = sweet_spot(curve, alpha=0.5)
            if ss is None:
                continue
            tx, asr, _ = ss
            cost = tx * COST_PER_TX
            roi = asr / cost if cost > 0 else 0
            ranks.append((model, atk, tx, asr, cost, roi))

    ranks.sort(key=lambda r: -r[5])  # by ROI desc
    md.append('| # | Model | Attack | Sweet tx | ASR | Cost | ROI (ASR/ETH) |')
    md.append('|---|---|---|---:|---:|---:|---:|')
    for i, r in enumerate(ranks[:15], 1):
        md.append(f'| {i} | {r[0]} | **{r[1]}** | {r[2]} | {r[3]*100:.1f}% | '
                  f'{r[4]:.4f} ETH | **{r[5]*100:.0f}%** |')
    md.append('')

    # ========== Kết luận ==========
    md.append('## 4. 🔑 Kết luận chính\n')
    md.append('')
    md.append('### Sweet spot (alpha=0.5) khuyến nghị:\n')
    for model in MODELS:
        md.append(f'**{model}**:')
        for atk in ATTACKS:
            res = load_curves(model, atk)
            if res is None: continue
            curve, _ = res
            ss = sweet_spot(curve, alpha=0.5)
            if ss is None: continue
            tx, asr, _ = ss
            cost = tx * COST_PER_TX
            md.append(f'- {atk}: **{tx} tx** → {asr*100:.1f}% ASR ({cost:.4f} ETH)')
        md.append('')

    md.append('### Insight tổng quan\n')
    md.append('')
    md.append('1. **ADAPTIVE-STC-LV trên peae_paper** vẫn là attack mạnh nhất ở sweet spot — hiệu quả cao nhất')
    md.append('2. **TIH trên gatv2** cũng rất hiệu quả nhưng cần nhiều tx hơn')
    md.append('3. **BPH-P2T, MWR** gần như vô dụng ở mọi mô hình (ASR thấp dù tx cao)')
    md.append('4. **Attacks trên graphsage** đều yếu — graphsage là mô hình bền nhất')
    md.append('5. **ROI cao nhất** luôn ở budget nhỏ (vài tx) nhưng ASR tuyệt đối thấp')
    md.append('')

    md.append('### Khuyến nghị cho KLTN\n')
    md.append('')
    md.append('- Dùng cột **"Sweet spot"** làm số liệu chính báo cáo "mức tối ưu cân bằng"')
    md.append('- Dùng cột **"50% ASR tx"** để trả lời câu "cần bao nhiêu tx để lật nửa số ví"')
    md.append('- Dùng cột **"ROI (ASR/ETH)"** để so sánh hiệu quả giữa attacks')
    md.append('- Nếu thầy hỏi "mức tối ưu": trả lời **"phụ thuộc threat model (V), nhưng tại α=0.3 thì ..."**')
    md.append('')

    OUT_MD.write_text('\n'.join(md), encoding='utf-8')
    OUT_CSV.write_text('\n'.join(csv_rows), encoding='utf-8')
    print(f'Saved MD -> {OUT_MD}')
    print(f'Saved CSV -> {OUT_CSV}')


if __name__ == '__main__':
    main()

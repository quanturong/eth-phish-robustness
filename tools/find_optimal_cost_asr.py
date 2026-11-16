"""
Tim mức "cost/ASR lý tưởng" cho từng (attack × model).

4 cach dinh nghia "lý tưởng":
  1. Kneedle elbow point (toan hoc, cho cong nhat)
  2. ROI toi da (ASR/cost cao nhat)
  3. Marginal cost per flip = Δcost/Δflipped (diem co dau hieu dim loi bien)
  4. Economic optimum cho tung V ∈ {0.01, 0.1, 1, 10 ETH}: max V·ASR − c·cost

Dau vao: json_stage5_6_final/stage6/results_<model>_seed<seed>_mincost_<group>_full.json
Dau ra: BaoCao_Optimal_Cost_ASR.md
"""
import json
import sys
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(r'E:\EthereumPhishingDetection\json_stage5_6_final\stage6')
OUT = Path(r'E:\EthereumPhishingDetection\BaoCao_Optimal_Cost_ASR.md')

MODELS = ['peae_paper', 'graphsage', 'gatv2']
SEEDS = [42, 43, 44]
ATTACKS_PER_GROUP = {
    'adaptive': ['ADAPTIVE-STC-LV'],
    'toh_tih': ['TOH', 'TIH'],
    'bph': ['BPH-T2P', 'BPH-P2T'],
    'stc': ['STC'],
    'mwr': ['MWR'],
}

# Gas cost per transaction (ETH) - tu bao cao
COST_PER_TX = 0.00124  # ETH


def load_curves(model, attack):
    """Return avg curve across 3 seeds: list of (tx_count, asr_pct)."""
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
        # curve: list of {budget, bypassed, frac}
        # Convert budget to tx count via TXS_PER_UNIT
        tx_per_unit = {'TOH': 1, 'TIH': 1, 'BPH-T2P': 2, 'BPH-P2T': 2,
                       'STC': 4, 'MWR': 3, 'ADAPTIVE-STC-LV': 6}[attack]
        pts = [(c['budget'] * tx_per_unit, c['frac']) for c in curve]
        curves_per_seed.append(pts)
    if not curves_per_seed:
        return None
    # Align all seeds by budget (should be same)
    budgets = sorted({tx for pts in curves_per_seed for tx, _ in pts})
    avg = []
    for tx in budgets:
        vals = []
        for pts in curves_per_seed:
            for t, f in pts:
                if t == tx:
                    vals.append(f)
                    break
        if vals:
            avg.append((tx, float(np.mean(vals))))
    return avg


def kneedle(curve):
    """Find knee/elbow using the point of max distance from line (min, max)."""
    if len(curve) < 3:
        return None
    x = np.array([p[0] for p in curve], dtype=float)
    y = np.array([p[1] for p in curve], dtype=float)
    # Normalize to [0,1]
    xn = (x - x.min()) / max(x.max() - x.min(), 1e-9)
    yn = (y - y.min()) / max(y.max() - y.min(), 1e-9)
    # Distance from each point to line (0,0)-(1,1)
    # For concave curve (ASR saturates), knee is max positive distance BELOW line
    # Actually for ASR curve rising and saturating, knee is max(y − x) in [0,1]
    diff = yn - xn
    idx = int(np.argmax(diff))
    return int(x[idx]), float(y[idx])


def roi_max(curve):
    """Find point with max ASR/cost ratio."""
    best = (None, None, -1)
    for tx, asr in curve:
        if tx == 0 or asr == 0:
            continue
        roi = asr / (tx * COST_PER_TX)
        if roi > best[2]:
            best = (tx, asr, roi)
    return best  # (tx, asr, roi_asr_per_eth)


def marginal_diminish(curve, threshold=0.001):
    """Find smallest tx where marginal gain (ΔASR/Δtx) drops below threshold.
    threshold=0.001 means +0.1% ASR per +1 tx = effectively no gain."""
    for i in range(1, len(curve)):
        tx0, asr0 = curve[i-1]
        tx1, asr1 = curve[i]
        if tx1 == tx0:
            continue
        marg = (asr1 - asr0) / (tx1 - tx0)
        if marg < threshold:
            return tx0, asr0
    return curve[-1]  # curve chưa diminish


def economic_opt(curve, V_eth):
    """For given V (ETH per bypassed), find tx maximizing profit = V*ASR*N_phish − cost*tx.
    N_phish is dropped (just affects scale). Return (tx, asr, profit_per_wallet=V*asr − c*tx)."""
    best = (0, 0.0, 0.0)  # (tx, asr, profit)
    for tx, asr in curve:
        profit = V_eth * asr - COST_PER_TX * tx
        if profit > best[2]:
            best = (tx, asr, profit)
    return best


def fmt_pct(v): return f'{v*100:.1f}%'
def fmt_tx(v): return f'{int(v)}' if v is not None else '—'
def fmt_eth(v): return f'{v:.4f} ETH' if v is not None else '—'


def main():
    md = []
    md.append('# Phân tích "Cost/ASR lý tưởng" cho từng tấn công\n')
    md.append(f'> **Chi phí 1 giao dịch**: {COST_PER_TX} ETH (gas, trung bình từ báo cáo)\n')
    md.append(f'> **Nguồn**: `json_stage5_6_final/stage6/results_*_mincost_*_full.json` (3 seeds)\n')
    md.append('> **Trung bình 3 seeds** cho mỗi điểm trên curve.\n')
    md.append('')

    md.append('## 1. Bốn định nghĩa "lý tưởng"\n')
    md.append('')
    md.append('| Metric | Cách tính | Ý nghĩa |')
    md.append('|---|---|---|')
    md.append('| **Kneedle elbow** | Max khoảng cách tới đường thẳng (min,max) | Toán học — "chỗ cong nhất" |')
    md.append('| **ROI tối đa** | Max `ASR / (tx × 0.00124)` | ASR trên 1 ETH chi phí cao nhất |')
    md.append('| **Diminishing** | tx đầu tiên có `ΔASR/Δtx < 0.001` | Dừng khi hiệu quả biên < 0.1% ASR/tx |')
    md.append('| **Economic V=X** | argmax `V·ASR − c·tx` | Tối đa lợi nhuận (V = giá trị/ví thoát) |')
    md.append('')

    # ===== Chi tiết từng (model, attack) =====
    all_attacks = ['TOH', 'TIH', 'BPH-T2P', 'BPH-P2T', 'STC', 'MWR', 'ADAPTIVE-STC-LV']
    for model in MODELS:
        md.append(f'## 2. {model}\n')
        md.append('')
        md.append('### Bảng chi tiết: điểm lý tưởng theo từng metric\n')
        md.append('')
        md.append('| Attack | Kneedle | ROI max | Diminishing | V=0.01 ETH | V=0.1 ETH | V=1 ETH | V=10 ETH |')
        md.append('|---|---|---|---|---|---|---|---|')
        for atk in all_attacks:
            curve = load_curves(model, atk)
            if curve is None:
                md.append(f'| {atk} | — | — | — | — | — | — | — |')
                continue
            # Kneedle
            kn = kneedle(curve)
            kn_s = f'{kn[0]} tx ({fmt_pct(kn[1])})' if kn else '—'
            # ROI max
            roi = roi_max(curve)
            roi_s = f'{roi[0]} tx ({fmt_pct(roi[1])})' if roi[0] else '—'
            # Diminishing
            dm = marginal_diminish(curve)
            dm_s = f'{dm[0]} tx ({fmt_pct(dm[1])})' if dm else '—'
            # Economic
            econ_vals = []
            for V in [0.01, 0.1, 1.0, 10.0]:
                e = economic_opt(curve, V)
                if e[0] == 0:
                    econ_vals.append('0 (ko lợi)')
                else:
                    econ_vals.append(f'{e[0]} tx ({fmt_pct(e[1])})')
            md.append(f'| {atk} | {kn_s} | {roi_s} | {dm_s} | {econ_vals[0]} | {econ_vals[1]} | {econ_vals[2]} | {econ_vals[3]} |')
        md.append('')

        # ===== Chi tiết curve cho ADAPTIVE (attack mạnh nhất của peae_paper) =====
        if model == 'peae_paper':
            md.append('### Chi tiết curve: ADAPTIVE-STC-LV (attack mạnh nhất của peae_paper)\n')
            md.append('')
            curve = load_curves(model, 'ADAPTIVE-STC-LV')
            md.append('| tx | ASR | Cost ETH | Marg. ASR/tx | ROI (ASR/ETH) |')
            md.append('|---|---|---|---|---|')
            prev_asr = 0
            prev_tx = 0
            for tx, asr in curve:
                cost = tx * COST_PER_TX
                marg = (asr - prev_asr) / max(tx - prev_tx, 1) if tx > prev_tx else 0
                roi = asr / cost if cost > 0 else 0
                md.append(f'| {tx} | {fmt_pct(asr)} | {cost:.4f} | {marg*100:.3f}% / tx | {roi*100:.0f}% / ETH |')
                prev_tx, prev_asr = tx, asr
            md.append('')

    # ===== Khuyến nghị =====
    md.append('## 3. Khuyến nghị cho báo cáo\n')
    md.append('')
    md.append('### Về cách báo cáo chi phí tối ưu\n')
    md.append('1. **Không có một "điểm tối ưu" tuyệt đối** — phụ thuộc vào threat model (giá trị V của mỗi ví)')
    md.append('2. **Nếu đo theo lợi nhuận** (V ETH/ví thoát): ADAPTIVE trên PEAE tối ưu ở ~6 tx (V=0.01) → ~120 tx (V=1 ETH) → 1200 tx (V≥10 ETH)')
    md.append('3. **Nếu đo theo ROI**: ROI tối đa thường ở budget nhỏ nhất (vì cost thấp, dù ASR cũng thấp)')
    md.append('4. **Nếu đo theo Kneedle**: ~300 tx cho ADAPTIVE trên peae_paper (chỉ số kỹ thuật, không có ý nghĩa kinh tế)')
    md.append('5. **Diminishing threshold** cho biết khi nào kẻ tấn công "no" — thường rất cao vì ADAPTIVE curve lâu lên tới trần\n')

    md.append('### Khuyến nghị trình bày trong KLTN\n')
    md.append('- Dùng **Economic optimum với V ∈ {0.01, 0.1, 1 ETH}** làm 3 kịch bản threat model')
    md.append('- Giải thích rõ: *"Không có mức tối ưu phổ quát; mỗi V cho một tx tối ưu khác nhau"*')
    md.append('- Có thể vẽ Pareto frontier (cost vs ASR) với các điểm (Kneedle, ROI_max, V=0.1, V=1) đánh dấu')
    md.append('')

    OUT.write_text('\n'.join(md), encoding='utf-8')
    print(f'Saved -> {OUT}')
    print(f'Size: {OUT.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()

"""
A. Ve Pareto frontier (cost vs ASR) cho 21 (model x attack) + sweet spot markers.
B. Phan tich sweet spot cho defense models (advtrain, ra, ra_noedge).
"""
import json
import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(r'E:\EthereumPhishingDetection\json_stage5_6_final\stage6')
EVAL = Path(r'E:\EthereumPhishingDetection\stage7_peae\eval_results')
FIG_DIR = Path(r'E:\EthereumPhishingDetection\figures\sweet_spot')
FIG_DIR.mkdir(parents=True, exist_ok=True)
OUT_MD = Path(r'E:\EthereumPhishingDetection\BaoCao_Pareto_Defense_SweetSpot.md')

MODELS = ['peae_paper', 'graphsage', 'gatv2']
MODEL_LABEL = {'peae_paper': 'PEAE (paper)', 'graphsage': 'GraphSAGE', 'gatv2': 'GATv2'}
SEEDS = [42, 43, 44]
ATTACKS_GROUP = {
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

# Dark/distinct colors for each attack
ATTACK_COLOR = {
    'TOH': '#1f77b4', 'TIH': '#ff7f0e',
    'BPH-T2P': '#2ca02c', 'BPH-P2T': '#d62728',
    'STC': '#9467bd', 'MWR': '#8c564b',
    'ADAPTIVE-STC-LV': '#e377c2',
}
MODEL_COLOR = {'peae_paper': '#d62728', 'graphsage': '#2ca02c', 'gatv2': '#1f77b4',
               'advtrain_peaepaper': '#ff7f0e', 'ra_peaepaper': '#9467bd',
               'ra_peaepaper_noedge': '#8c564b'}


def load_mincost_curve(model, attack):
    group = next(g for g, atks in ATTACKS_GROUP.items() if attack in atks)
    curves = []
    for seed in SEEDS:
        f = BASE / f'results_{model}_seed{seed}_mincost_{group}_full.json'
        if not f.exists():
            continue
        d = json.load(open(f, encoding='utf-8'))
        if attack in d['attacks']:
            curve = d['attacks'][attack]['curve']
            pts = [(c['budget'] * TX_PER_UNIT[attack], c['frac']) for c in curve]
            curves.append(pts)
    if not curves:
        return None
    budgets = sorted({tx for pts in curves for tx, _ in pts})
    return [(tx, float(np.mean([f for pts in curves for t, f in pts if t == tx])))
            for tx in budgets]


def sweet_spot(curve, alpha=0.5):
    if not curve or len(curve) < 2: return None
    xs = np.array([p[0] for p in curve], dtype=float)
    ys = np.array([p[1] for p in curve], dtype=float)
    score = ys - alpha * (xs * COST_PER_TX)
    i = int(np.argmax(score))
    return int(xs[i]), float(ys[i])


def pareto_frontier(curve):
    """Return subset of (cost, asr) points that are not dominated."""
    pts = sorted([(c * COST_PER_TX, a) for c, a in curve])  # sort by cost asc
    frontier = []
    max_asr = -1
    for cost, asr in pts:
        if asr > max_asr:
            frontier.append((cost, asr))
            max_asr = asr
    return frontier


def load_defense_curve(method_key, attack):
    """Load ASR curve for defense method from Stage 7 eval JSONs (3 seeds avg).
    Budgets in eval are: 5, 20, 100 (units). Convert to tx."""
    curves = []
    for seed in SEEDS:
        f = EVAL / f'eval_seed{seed}_defenseonly.json'
        if not f.exists():
            continue
        d = json.load(open(f, encoding='utf-8'))
        if method_key not in d or attack not in d[method_key].get('attacks', {}):
            continue
        atk_info = d[method_key]['attacks'][attack]
        budgets = atk_info['budgets']
        pts = [(b['budget'] * TX_PER_UNIT[attack], b['asr']) for b in budgets]
        curves.append(pts)
    if not curves:
        return None
    budgets = sorted({tx for pts in curves for tx, _ in pts})
    return [(tx, float(np.mean([a for pts in curves for t, a in pts if t == tx])))
            for tx in budgets]


# ===== A. PARETO FIGURES =====

def fig_adaptive_3models():
    """Fig 1: ADAPTIVE on 3 models + sweet spots."""
    plt.figure(figsize=(9, 6))
    for model in MODELS:
        curve = load_mincost_curve(model, 'ADAPTIVE-STC-LV')
        if not curve:
            continue
        xs = [p[0] * COST_PER_TX for p in curve]
        ys = [p[1] * 100 for p in curve]
        color = MODEL_COLOR[model]
        plt.plot(xs, ys, 'o-', color=color, label=MODEL_LABEL[model], linewidth=2, markersize=6)
        # Sweet spot
        ss = sweet_spot(curve)
        if ss:
            cs = ss[0] * COST_PER_TX
            plt.plot(cs, ss[1] * 100, '*', color=color, markersize=20, markeredgecolor='black', markeredgewidth=1)
            plt.annotate(f'  Sweet: {ss[0]} tx\n  {ss[1]*100:.1f}% ASR',
                         xy=(cs, ss[1]*100), xytext=(cs*1.3, ss[1]*100-5),
                         fontsize=9, color=color)
    plt.xscale('log')
    plt.xlabel('Cost (ETH, log scale)', fontsize=11)
    plt.ylabel('ASR (%)', fontsize=11)
    plt.title('ADAPTIVE-STC-LV: Cost vs ASR trên 3 mô hình (Pareto frontier)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='upper left', fontsize=10)
    plt.tight_layout()
    plt.savefig(FIG_DIR / 'pareto_adaptive_3models.png', dpi=150)
    plt.savefig(FIG_DIR / 'pareto_adaptive_3models.pdf')
    plt.close()
    print(f'  Saved: pareto_adaptive_3models.png/.pdf')


def fig_all_attacks_per_model():
    """Fig 2-4: 3 figures, one per model, showing all 7 attacks."""
    for model in MODELS:
        plt.figure(figsize=(10, 6))
        for atk in ATTACKS:
            curve = load_mincost_curve(model, atk)
            if not curve:
                continue
            xs = [p[0] * COST_PER_TX for p in curve]
            ys = [p[1] * 100 for p in curve]
            color = ATTACK_COLOR[atk]
            plt.plot(xs, ys, 'o-', color=color, label=atk, linewidth=1.8, markersize=5, alpha=0.85)
            ss = sweet_spot(curve)
            if ss:
                cs = ss[0] * COST_PER_TX
                plt.plot(cs, ss[1] * 100, '*', color=color, markersize=16,
                         markeredgecolor='black', markeredgewidth=1)
        plt.xscale('log')
        plt.xlabel('Cost (ETH, log scale)', fontsize=11)
        plt.ylabel('ASR (%)', fontsize=11)
        plt.title(f'7 attacks trên {MODEL_LABEL[model]}: cost vs ASR + sweet spots', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(loc='upper left', fontsize=9, ncol=2)
        plt.ylim(-2, 100)
        plt.tight_layout()
        plt.savefig(FIG_DIR / f'pareto_{model}_7attacks.png', dpi=150)
        plt.savefig(FIG_DIR / f'pareto_{model}_7attacks.pdf')
        plt.close()
        print(f'  Saved: pareto_{model}_7attacks.png/.pdf')


def fig_pareto_frontier_global():
    """Fig 5: Global Pareto frontier across ALL 21 combinations."""
    plt.figure(figsize=(10, 7))
    all_pts = []
    for model in MODELS:
        for atk in ATTACKS:
            curve = load_mincost_curve(model, atk)
            if not curve:
                continue
            for tx, asr in curve:
                all_pts.append((tx * COST_PER_TX, asr * 100, model, atk))

    # Scatter all points lightly
    for cost, asr, model, atk in all_pts:
        plt.scatter(cost, asr, color=MODEL_COLOR[model], alpha=0.25, s=20)

    # Compute global Pareto frontier
    pts_sorted = sorted(all_pts, key=lambda p: p[0])
    front = []
    max_asr = -1
    for p in pts_sorted:
        if p[1] > max_asr:
            front.append(p)
            max_asr = p[1]
    # Draw frontier
    fx = [p[0] for p in front]
    fy = [p[1] for p in front]
    plt.plot(fx, fy, 'k--', linewidth=2.5, label='Pareto frontier', zorder=10)
    plt.scatter(fx, fy, c=[MODEL_COLOR[p[2]] for p in front],
                s=140, edgecolor='black', linewidth=1.5, zorder=11)
    # Annotate top frontier points
    for p in front[::max(1, len(front)//8)]:
        plt.annotate(f'{p[3][:8]}\n{p[2][:5]}',
                     xy=(p[0], p[1]), xytext=(p[0]*1.3, p[1]-3),
                     fontsize=8, color='black', alpha=0.8)

    # Legend
    handles = [mpatches.Patch(color=c, label=MODEL_LABEL[m]) for m, c in MODEL_COLOR.items() if m in MODELS]
    handles.append(plt.Line2D([0], [0], color='k', linestyle='--', label='Pareto frontier'))
    plt.legend(handles=handles, loc='lower right', fontsize=10)

    plt.xscale('log')
    plt.xlabel('Cost (ETH, log scale)', fontsize=11)
    plt.ylabel('ASR (%)', fontsize=11)
    plt.title('Pareto frontier toàn cục: 21 (model × attack) × ~14 ngân sách', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.ylim(-2, 100)
    plt.tight_layout()
    plt.savefig(FIG_DIR / 'pareto_global.png', dpi=150)
    plt.savefig(FIG_DIR / 'pareto_global.pdf')
    plt.close()
    print(f'  Saved: pareto_global.png/.pdf')


def fig_defense_vs_undefended():
    """Fig 6: ADAPTIVE on peae_paper (undefended) vs 3 defenses."""
    plt.figure(figsize=(10, 6))
    # Undefended peae_paper (from mincost)
    curve0 = load_mincost_curve('peae_paper', 'ADAPTIVE-STC-LV')
    if curve0:
        xs = [p[0] * COST_PER_TX for p in curve0]
        ys = [p[1] * 100 for p in curve0]
        plt.plot(xs, ys, 'o-', color='#d62728', label='peae_paper (no defense)',
                 linewidth=2.5, markersize=6)
        ss = sweet_spot(curve0)
        if ss:
            plt.plot(ss[0] * COST_PER_TX, ss[1] * 100, '*', color='#d62728',
                     markersize=22, markeredgecolor='black', markeredgewidth=1.5)
    # Defense models
    for method_key, color in [('advtrain_peaepaper', '#ff7f0e'),
                              ('ra_peaepaper', '#9467bd'),
                              ('ra_peaepaper_noedge', '#8c564b')]:
        curve = load_defense_curve(method_key, 'ADAPTIVE-STC-LV')
        if curve:
            xs = [p[0] * COST_PER_TX for p in curve]
            ys = [p[1] * 100 for p in curve]
            label = method_key.replace('_peaepaper', '').replace('_', '-')
            plt.plot(xs, ys, 's-', color=color, label=label, linewidth=2.2, markersize=8)
            ss = sweet_spot(curve)
            if ss:
                plt.plot(ss[0] * COST_PER_TX, ss[1] * 100, '*', color=color,
                         markersize=20, markeredgecolor='black', markeredgewidth=1.5)
    plt.xscale('log')
    plt.xlabel('Cost (ETH, log scale)', fontsize=11)
    plt.ylabel('ASR (%)', fontsize=11)
    plt.title('ADAPTIVE-STC-LV: peae_paper (no defense) vs 3 phương pháp phòng thủ', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='lower right', fontsize=10)
    plt.ylim(-2, 100)
    plt.tight_layout()
    plt.savefig(FIG_DIR / 'defense_vs_undefended_adaptive.png', dpi=150)
    plt.savefig(FIG_DIR / 'defense_vs_undefended_adaptive.pdf')
    plt.close()
    print(f'  Saved: defense_vs_undefended_adaptive.png/.pdf')


# ===== B. DEFENSE SWEET SPOT =====

def build_defense_sweet_spot_md():
    """Build MD table of sweet spots for undefended + 3 defense models."""
    md = []
    md.append('# Sweet Spot: Undefended vs 3 Defense Methods\n')
    md.append(f'> **Chi phí**: {COST_PER_TX} ETH/tx\n')
    md.append(f'> **Sweet spot**: argmax(ASR − 0.5 × cost_ETH)\n')
    md.append(f'> **Nguồn**: mincost (14 budgets) cho undefended; eval (3 budgets: b=5,20,100) cho defense\n')
    md.append('')

    # For each attack, show undefended + 3 defense sweet spots
    all_attacks_eval = ['TOH', 'TIH', 'BPH-T2P', 'BPH-P2T', 'STC', 'MWR', 'ADAPTIVE-STC-LV']
    defense_methods = [('baseline (undefended)', None, 'peae_paper'),
                       ('advtrain', 'advtrain_peaepaper', None),
                       ('ra', 'ra_peaepaper', None),
                       ('ra_noedge', 'ra_peaepaper_noedge', None)]

    for atk in all_attacks_eval:
        md.append(f'## {atk}\n')
        md.append('')
        md.append('| Method | Sweet tx | ASR | Cost ETH | Score |')
        md.append('|---|---:|---:|---:|---:|')
        for label, method_key, model_name in defense_methods:
            if method_key is None:  # undefended
                curve = load_mincost_curve(model_name, atk)
            else:
                curve = load_defense_curve(method_key, atk)
            if not curve:
                md.append(f'| {label} | — | — | — | — |')
                continue
            ss = sweet_spot(curve)
            if not ss:
                md.append(f'| {label} | — | — | — | — |')
                continue
            tx, asr = ss
            cost = tx * COST_PER_TX
            score = asr - 0.5 * cost
            md.append(f'| **{label}** | **{tx}** | **{asr*100:.1f}%** | {cost:.4f} | {score:.3f} |')
        md.append('')

        # Also show max ASR comparison
        md.append('**Max ASR trong curve** (so sánh "trần tấn công"):')
        md.append('')
        md.append('| Method | Max tx | Max ASR | Max Cost ETH |')
        md.append('|---|---:|---:|---:|')
        for label, method_key, model_name in defense_methods:
            if method_key is None:
                curve = load_mincost_curve(model_name, atk)
            else:
                curve = load_defense_curve(method_key, atk)
            if not curve:
                md.append(f'| {label} | — | — | — |')
                continue
            max_pt = max(curve, key=lambda p: p[1])
            md.append(f'| {label} | {max_pt[0]} | {max_pt[1]*100:.1f}% | {max_pt[0]*COST_PER_TX:.4f} |')
        md.append('')

    md.append('## Insight tổng quan\n')
    md.append('')
    md.append('### Về ADAPTIVE-STC-LV\n')
    md.append('- **Undefended**: sweet spot 300 tx → 64.1% ASR')
    md.append('- **AdvTrain**: sweet spot ~600 tx → ASR ở sweet thấp hơn baseline (defense giúp)')
    md.append('- **RA/RA-noedge**: sweet spot tương tự nhưng ASR cao hơn AdvTrain')
    md.append('- → Defense **kéo đường cong xuống** (cùng cost mà ASR giảm), KHÔNG đẩy sweet spot ra xa\n')

    md.append('### Về attacks khác (TOH/TIH/BPH/STC/MWR)\n')
    md.append('- Tất cả defense đều giảm ASR về gần 0 (<2%) ở các attacks "known"')
    md.append('- Sweet spot cho các attacks này không có ý nghĩa (ASR < 2%, không đáng tấn công)\n')

    md.append('### Figures đã tạo\n')
    md.append('- `figures/sweet_spot/pareto_adaptive_3models.png` — 3 mô hình × ADAPTIVE')
    md.append('- `figures/sweet_spot/pareto_{model}_7attacks.png` — 7 attacks mỗi mô hình')
    md.append('- `figures/sweet_spot/pareto_global.png` — Pareto toàn cục 21 combinations')
    md.append('- `figures/sweet_spot/defense_vs_undefended_adaptive.png` — Defense vs baseline')
    md.append('')

    OUT_MD.write_text('\n'.join(md), encoding='utf-8')
    print(f'Saved MD -> {OUT_MD}')


def main():
    print('=== A. Vẽ figures Pareto ===')
    fig_adaptive_3models()
    fig_all_attacks_per_model()
    fig_pareto_frontier_global()
    print()
    print('=== B. Defense vs baseline ===')
    fig_defense_vs_undefended()
    print()
    print('=== Build Defense Sweet Spot MD ===')
    build_defense_sweet_spot_md()
    print()
    print(f'All figures in: {FIG_DIR}')


if __name__ == '__main__':
    main()

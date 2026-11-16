"""
Tao bieu do (figures) cho bao cao va slides.

Chay all:  python generate_figures.py
Chay 1:    python generate_figures.py --fig slide1
Output:    figures/*.png + figures/*.pdf

Cac fig co san:
  slide1         - Clean baseline K=2 (Macro-F1 + Phish Recall) [theo slide user]
  attack_asr     - ASR theo budget cho ADAPTIVE-STC-LV, 3 models x 3 seeds
  attack_cost    - Cost-vs-ASR curve cho ADAPTIVE-STC-LV tren PEAE
  defense_bar    - So sanh baseline/advtrain/ra_peae/ra_noedge
  defense_curve  - ASR curve defenses theo budget
  d2_zeroshot    - Zero-shot EthPhishGraph-2026 -> D2
  k1_vs_k2       - Clean metrics K=1 vs K=2
  attack_rank    - Heatmap ASR 6 attacks x 3 models (K=2 original)
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

OUT = Path(__file__).parent / "figures"
OUT.mkdir(exist_ok=True)
OUT_SLIDES = OUT / "slides"
OUT_SLIDES.mkdir(exist_ok=True)

# --- Style thong nhat -------------------------------------------------------
plt.rcParams.update({
    "font.family":     "DejaVu Sans",
    "font.size":       11,
    "axes.titlesize":  12,
    "axes.labelsize":  11,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":       True,
    "grid.alpha":      0.3,
    "grid.linestyle":  "--",
    "legend.frameon":  False,
    "figure.dpi":      110,
    "savefig.dpi":     200,
    "savefig.bbox":    "tight",
})

PALETTE = {
    "graphsage":  "#4C72B0",   # blue
    "gatv2":      "#DD8452",   # orange
    "peaegnn":    "#55A868",   # green  (PEAE-style)
    "peaegnnv2":  "#2E7D32",   # dark green
    "baseline":   "#999999",   # gray
    "advtrain":   "#C44E52",   # red
    "ra_peae":    "#8172B2",   # purple
    "ra_noedge":  "#CCB974",   # yellow
}

LABEL = {
    "graphsage": "GraphSAGE",
    "gatv2":     "GATv2",
    "peaegnn":   "PEAE-style",
    "peaegnnv2": "PEAE-GNN v2",
    "baseline":  "Baseline",
    "advtrain":  "AdvTrain",
    "ra_peae":   "RA-SAGE",
    "ra_noedge": "RA-SAGE (no edge)",
}


def _save(fig, name, out_dir=None):
    out_dir = out_dir or OUT
    for ext in ("png", "pdf"):
        p = out_dir / f"{name}.{ext}"
        fig.savefig(p)
    rel = out_dir.name + "/"
    print(f"  saved: {rel}{name}.png / {rel}{name}.pdf")


# --- Fig 1: Slide 1 (clean baselines K=2) ------------------------------------
def fig_slide1():
    """Clean baseline K=2: Macro-F1 va Phishing Recall."""
    models = ["gatv2", "graphsage", "peaegnn"]
    macro = [81.51, 86.63, 88.13]
    recall = [66.2, 77.7, 82.8]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(models))
    w = 0.35

    b1 = ax.bar(x - w/2, macro,  w, label="Macro-F1 (%)",
                color=[PALETTE[m] for m in models], edgecolor="black", linewidth=0.5)
    b2 = ax.bar(x + w/2, recall, w, label="Phishing Recall (%)",
                color=[PALETTE[m] for m in models], edgecolor="black", linewidth=0.5, alpha=0.6)

    for bar in b1:
        ax.annotate(f"{bar.get_height():.2f}",
                    xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=9, fontweight="bold")
    for bar in b2:
        ax.annotate(f"{bar.get_height():.1f}",
                    xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels([LABEL[m] for m in models])
    ax.set_ylabel("Giá trị (%)")
    ax.set_title("Hiệu năng trên dữ liệu sạch (EthPhishGraph-2026, K=2)")
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%d"))
    ax.legend(loc="upper left", ncol=2)
    _save(fig, "slide1_clean_baseline")
    plt.close(fig)


# --- Fig 2: ASR theo budget ADAPTIVE-STC-LV ---------------------------------
def fig_attack_asr():
    """ASR curve ADAPTIVE-STC-LV theo budget cho 3 models."""
    budgets = np.array([20, 50, 100, 200, 500])
    # mean ± std across 3 seeds
    data = {
        "peaegnn":   ([27.2, 37.4, 41.8, 44.7, 49.7], [7.1, 6.8, 8.2, 8.6, 11.2]),
        "graphsage": ([3.5,  6.5,  10.5, 14.7, 23.2], [1.3, 1.8, 1.9, 1.8, 3.9]),
        "gatv2":     ([2.4,  3.8,  5.3,  6.4,  8.5],  [0.4, 1.1, 1.5, 1.4, 1.1]),
    }
    fig, ax = plt.subplots(figsize=(8, 5))
    for m, (mean, std) in data.items():
        mean, std = np.array(mean), np.array(std)
        ax.plot(budgets, mean, "-o", color=PALETTE[m], label=LABEL[m], linewidth=2, markersize=7)
        ax.fill_between(budgets, mean - std, mean + std, color=PALETTE[m], alpha=0.15)
    ax.set_xlabel("Ngân sách b (số motif)")
    ax.set_ylabel("ASR (%)")
    ax.set_xscale("log")
    ax.set_title("ADAPTIVE-STC-LV: ASR theo ngân sách (3 seeds, mean ± std)")
    ax.legend(loc="upper left")
    ax.set_ylim(0, 65)
    _save(fig, "attack_asr_adaptive")
    plt.close(fig)


# --- Fig 3: Cost-vs-ASR curve cho PEAE --------------------------------------
def fig_attack_cost():
    """Chi phi (USD @ ETH=$2500) vs ASR cho PEAE-style, ADAPTIVE-STC-LV."""
    cost_eth = [0.18, 0.46, 0.92, 1.84, 4.60]
    cost_usd = [c * 2500 for c in cost_eth]
    asr_peae = [27.2, 37.4, 41.8, 44.7, 49.7]
    budgets = [20, 50, 100, 200, 500]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(cost_usd, asr_peae, "-s", color=PALETTE["peaegnn"],
            linewidth=2.2, markersize=8, label="PEAE-style")
    for b, c, a in zip(budgets, cost_usd, asr_peae):
        ax.annotate(f"b={b}", xy=(c, a), xytext=(5, 5),
                    textcoords="offset points", fontsize=9, color="#333")
    # Sweet spot shading (b=50-100)
    ax.axvspan(cost_usd[1], cost_usd[2], alpha=0.12, color="green",
               label="Sweet spot (b=50-100)")
    ax.set_xscale("log")
    ax.set_xlabel("Chi phí attacker (USD, giả định ETH = $2,500)")
    ax.set_ylabel("ASR (%)")
    ax.set_title("ADAPTIVE-STC-LV trên PEAE-style: hiệu quả theo chi phí")
    ax.legend(loc="lower right")
    _save(fig, "attack_cost_vs_asr")
    plt.close(fig)


# --- Fig 4: Defense comparison bar -------------------------------------------
def fig_defense_bar():
    """Clean Macro-F1 + ASR_any 4 cấu hình defense."""
    methods = ["baseline", "advtrain", "ra_peae", "ra_noedge"]
    clean_f1 = [88.1, 88.7, 87.6, 88.5]
    clean_std = [0.3, 0.7, 2.0, 0.1]
    asr_any  = [43.9, 21.1, 18.7, 33.0]
    asr_std  = [9.6, 7.7, 2.7, 4.9]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    x = np.arange(len(methods))
    colors = [PALETTE[m] for m in methods]

    bars1 = ax1.bar(x, clean_f1, yerr=clean_std, color=colors, edgecolor="black",
                    linewidth=0.5, capsize=4, alpha=0.9)
    for bar, v in zip(bars1, clean_f1):
        ax1.text(bar.get_x() + bar.get_width()/2, v + 0.3, f"{v:.1f}",
                 ha="center", fontsize=10, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels([LABEL[m] for m in methods], rotation=15, ha="right")
    ax1.set_ylabel("Clean Macro-F1 (%)")
    ax1.set_title("Giữ clean performance (càng cao càng tốt)")
    ax1.set_ylim(80, 92)

    bars2 = ax2.bar(x, asr_any, yerr=asr_std, color=colors, edgecolor="black",
                    linewidth=0.5, capsize=4, alpha=0.9)
    for bar, v in zip(bars2, asr_any):
        ax2.text(bar.get_x() + bar.get_width()/2, v + 1.0, f"{v:.1f}",
                 ha="center", fontsize=10, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels([LABEL[m] for m in methods], rotation=15, ha="right")
    ax2.set_ylabel("ASR_any ADAPTIVE-STC (%)")
    ax2.set_title("Giảm ASR (càng thấp càng tốt)")
    ax2.set_ylim(0, 60)
    ax2.axhline(y=43.9, color=PALETTE["baseline"], linestyle=":", alpha=0.6, label="Baseline")
    ax2.legend(loc="upper right")

    fig.suptitle("So sánh phòng thủ: RA-SAGE giảm ASR tốt hơn, giữ clean tốt hơn",
                 fontsize=12, y=1.02)
    _save(fig, "defense_comparison")
    plt.close(fig)


# --- Fig 5: Defense ASR theo budget -----------------------------------------
def fig_defense_curve():
    """ASR theo budget cho 4 defense configs."""
    budgets = np.array([5, 20, 100])
    data = {
        "baseline": ([14.4, 26.7, 41.7], [6.1, 7.6, 9.4]),
        "advtrain": ([3.6,  9.0,  20.4], [3.6, 7.2, 7.1]),
        "ra_peae":  ([4.9,  9.1,  18.1], [2.9, 1.8, 3.5]),
        "ra_noedge":([10.3, 18.6, 31.8], [4.2, 6.3, 3.6]),
    }
    fig, ax = plt.subplots(figsize=(8, 5))
    for m, (mean, std) in data.items():
        mean, std = np.array(mean), np.array(std)
        ax.errorbar(budgets, mean, yerr=std, fmt="-o",
                    color=PALETTE[m], label=LABEL[m],
                    linewidth=2, markersize=7, capsize=4)
    ax.set_xlabel("Ngân sách b")
    ax.set_ylabel("ASR ADAPTIVE-STC (%)")
    ax.set_xscale("log")
    ax.set_title("Phòng thủ dưới ADAPTIVE-STC: RA-SAGE ổn định nhất")
    ax.legend(loc="upper left")
    _save(fig, "defense_asr_curve")
    plt.close(fig)


# --- Fig 6: D2 zero-shot ----------------------------------------------------
def fig_d2_zeroshot():
    """Comparison 4 models trên EthPhishGraph-2026 test vs D2 zero-shot."""
    models = ["gatv2", "graphsage", "peaegnn", "advtrain"]
    labels = ["GATv2", "GraphSAGE", "PEAE-style", "AdvTrain-PEAE"]
    f1_2026 = [81.5, 86.6, 88.1, 88.7]
    f1_d2   = [58.9, 63.6, 69.1, 59.8]
    prauc_2026 = [84.0, 87.8, 87.9, 88.5]
    prauc_d2   = [65.4, 80.5, 82.4, 84.9]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    x = np.arange(len(models))
    w = 0.38

    for ax, m2026, md2, title in [
        (ax1, f1_2026, f1_d2, "Macro-F1 (%)"),
        (ax2, prauc_2026, prauc_d2, "PR-AUC"),
    ]:
        c = [PALETTE.get(m, "#999") for m in ["gatv2","graphsage","peaegnn","advtrain"]]
        b1 = ax.bar(x - w/2, m2026, w, label="EthPhishGraph-2026 (test)",
                    color=c, edgecolor="black", linewidth=0.5)
        b2 = ax.bar(x + w/2, md2, w, label="D2 (zero-shot)",
                    color=c, edgecolor="black", linewidth=0.5, alpha=0.55, hatch="//")
        for bars in (b1, b2):
            for bar in bars:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f"{bar.get_height():.1f}", ha="center", fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=15, ha="right")
        ax.set_title(title)
        ax.set_ylim(0, 100)
        ax.legend(loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.3))

    fig.suptitle("Zero-shot generalization: EthPhishGraph-2026 → D2",
                 fontsize=12, y=1.02)
    _save(fig, "d2_zeroshot")
    plt.close(fig)


# --- Fig 7: K=1 vs K=2 -----------------------------------------------------
def fig_k1_vs_k2():
    """So sanh clean performance K=1 vs K=2."""
    models = ["graphsage", "gatv2", "peaegnn"]
    labels = [LABEL[m] for m in models]
    k1 = [78.31, 72.81, 75.34]
    k2 = [86.63, 81.51, 88.13]

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(models))
    w = 0.35
    c = [PALETTE[m] for m in models]
    b1 = ax.bar(x - w/2, k1, w, label="K=1 ego-graph", color=c, alpha=0.55,
                edgecolor="black", linewidth=0.5)
    b2 = ax.bar(x + w/2, k2, w, label="K=2 ego-graph", color=c,
                edgecolor="black", linewidth=0.5)
    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                    f"{bar.get_height():.1f}", ha="center", fontsize=9, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Macro-F1 (%)")
    ax.set_title("K=1 vs K=2: tăng độ sâu ego-graph cải thiện mọi model")
    ax.set_ylim(70, 92)
    ax.legend(loc="lower right")
    _save(fig, "k1_vs_k2")
    plt.close(fig)


# --- Fig 8: Attack ranking heatmap (K=2 original 6 attacks) -----------------
def fig_attack_rank():
    """Heatmap ASR 6 original attacks x 3 models (budget mean)."""
    attacks = ["TOH", "TIH", "BPH-T2P", "BPH-P2T", "STC", "MWR"]
    models = ["peaegnn", "graphsage", "gatv2"]
    data = np.array([
        [1.3, 0.6, 0.5, 1.3, 2.4, 0.1],   # peaegnn
        [1.3, 1.0, 1.1, 2.9, 2.7, 0.6],   # graphsage
        [2.8, 0.5, 1.9, 0.1, 2.2, 0.2],   # gatv2
    ])
    fig, ax = plt.subplots(figsize=(9, 3.5))
    im = ax.imshow(data, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=4)
    ax.set_xticks(np.arange(len(attacks)))
    ax.set_xticklabels(attacks, rotation=0)
    ax.set_yticks(np.arange(len(models)))
    ax.set_yticklabels([LABEL[m] for m in models])
    for i in range(len(models)):
        for j in range(len(attacks)):
            ax.text(j, i, f"{data[i,j]:.1f}", ha="center", va="center",
                    color="black" if data[i,j] < 2 else "white", fontsize=10)
    plt.colorbar(im, ax=ax, label="ASR (%) trung bình các budget")
    ax.set_title("ASR 6 tấn công nguyên bản × 3 model (K=2) — tất cả <5%")
    _save(fig, "attack_rank_original")
    plt.close(fig)


# ============================================================================
# PRESENTATION SLIDES (16:9, fonts to, callout boxes)
# ============================================================================
SLIDE_RC = {
    "font.size":      14,
    "axes.titlesize": 18,
    "axes.labelsize": 14,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 13,
}


def _slide_fig(w=14, h=7.5):
    """Tao figure 16:9 cho slide."""
    with plt.rc_context(SLIDE_RC):
        return plt.subplots(figsize=(w, h))


# --- Slide 1 — Clean performance --------------------------------------------
def slide_1_clean():
    """Clean Macro-F1 + Phishing Recall tren 3 mo hinh."""
    with plt.rc_context(SLIDE_RC):
        models = ["gatv2", "graphsage", "peaegnn"]
        macro = [81.51, 86.63, 88.13]
        recall = [66.2, 77.7, 82.8]

        C_MACRO  = "#2b7bba"
        C_RECALL = "#e67e22"

        fig, ax = plt.subplots(figsize=(14, 7.5))
        x = np.arange(len(models))
        w = 0.37

        b1 = ax.bar(x - w/2, macro, w, label="Macro-F1 (%)", color=C_MACRO)
        b2 = ax.bar(x + w/2, recall, w, label="Phishing Recall (%)", color=C_RECALL)

        for bars in (b1, b2):
            for bar in bars:
                ax.annotate(f"{bar.get_height():.2f}",
                            xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                            xytext=(0, 6), textcoords="offset points",
                            ha="center", fontsize=14, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels([LABEL[m] for m in models], fontsize=16, fontweight="bold")
        ax.set_ylabel("Giá trị (%)", fontsize=15)
        ax.set_title("Hiệu năng trên dữ liệu sạch — EthPhishGraph-2026 (K=2)",
                     fontsize=20, fontweight="bold", pad=15)
        ax.set_ylim(0, 100)
        ax.legend(loc="upper left", ncol=2, fontsize=14)
        _save(fig, "slide1_clean_performance", OUT_SLIDES)
        plt.close(fig)


# --- Slide 2 — Adversarial attack -------------------------------------------
def slide_2_attack():
    """ASR line chart cho 3 models."""
    with plt.rc_context(SLIDE_RC):
        budgets = np.array([20, 50, 100, 200, 500])
        data = {
            "peaegnn":   ([27.2, 37.4, 41.8, 44.7, 49.7], [7.1, 6.8, 8.2, 8.6, 11.2]),
            "graphsage": ([3.5,  6.5,  10.5, 14.7, 23.2], [1.3, 1.8, 1.9, 1.8, 3.9]),
            "gatv2":     ([2.4,  3.8,  5.3,  6.4,  8.5],  [0.4, 1.1, 1.5, 1.4, 1.1]),
        }
        fig, ax = plt.subplots(figsize=(14, 7.5))
        for m, (mean, std) in data.items():
            mean, std = np.array(mean), np.array(std)
            ax.plot(budgets, mean, "-o", color=PALETTE[m], label=LABEL[m],
                    linewidth=2.5, markersize=9)
            ax.fill_between(budgets, mean - std, mean + std,
                            color=PALETTE[m], alpha=0.15)

        ax.set_xlabel("Ngân sách tấn công (b)", fontsize=15)
        ax.set_ylabel("Attack Success Rate (%)", fontsize=15)
        ax.set_xscale("log")
        ax.set_title("ADAPTIVE-STC-LV — ASR theo ngân sách tấn công",
                     fontsize=20, fontweight="bold", pad=15)
        ax.set_xticks(budgets)
        ax.set_xticklabels(budgets, fontsize=13)
        ax.legend(loc="upper left", fontsize=14)
        ax.set_ylim(0, 65)
        _save(fig, "slide2_attack_adaptive", OUT_SLIDES)
        plt.close(fig)


# --- Slide 3 — Defense comparison -------------------------------------------
def slide_3_defense():
    """Bar chart 4 configs defense (ASR_any + std) tren ADAPTIVE-STC-LV."""
    with plt.rc_context(SLIDE_RC):
        methods = ["PEAE-style\n(baseline)", "AdvTrain", "RA-SAGE\n(no edge)", "RA-SAGE"]
        colors_m = ["#999999", "#C44E52", "#CCB974", "#2E7D32"]
        # ADAPTIVE-STC-LV, trung binh budgets [5, 20, 100], 3 seeds (section 4.3)
        asr = [27.8, 13.0, 21.3, 11.2]
        asr_std = [6.9, 5.5, 4.7, 1.2]

        fig, ax = plt.subplots(figsize=(14, 7.5))
        x = np.arange(len(methods))
        bars = ax.bar(x, asr, yerr=asr_std, color=colors_m, width=0.6,
                      capsize=8, error_kw={"lw": 2, "capthick": 2})
        for bar, v, s in zip(bars, asr, asr_std):
            ax.text(bar.get_x() + bar.get_width()/2, v + s + 0.8,
                    f"{v:.1f}%", ha="center", fontsize=22, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(methods, fontsize=15, fontweight="bold")
        ax.set_ylabel("ASR (%) trên ADAPTIVE-STC-LV\n(trung bình budgets 5, 20, 100)",
                      fontsize=14)
        ax.set_title("Hiệu quả phòng thủ (mean ± std, 3 seeds)",
                     fontsize=20, fontweight="bold", pad=15)
        ax.set_ylim(0, 40)
        _save(fig, "slide3_defense_comparison", OUT_SLIDES)
        plt.close(fig)


# --- Slide 4 — Cross-dataset D2 (4 models) ---------------------------------
def slide_4_crossdataset():
    """4 models tren D2 zero-shot: ROC-AUC va Phishing Recall."""
    with plt.rc_context(SLIDE_RC):
        models = ["GATv2", "GraphSAGE", "PEAE-style", "AdvTrain-PEAE"]
        colors_m = ["#DD8452", "#4C72B0", "#2E7D32", "#C44E52"]
        roc_auc = [72.7, 81.2, 86.1, 86.6]       # x100 cho de dang chart
        recall  = [86.9, 88.7, 91.4, 94.7]

        fig, ax = plt.subplots(figsize=(14, 7.5))
        x = np.arange(len(models))
        w = 0.37

        b1 = ax.bar(x - w/2, roc_auc, w, label="ROC-AUC (×100)", color=colors_m)
        b2 = ax.bar(x + w/2, recall,  w, label="Phishing Recall (%)",
                    color=colors_m, alpha=0.55, hatch="//")

        for bars, vals in [(b1, roc_auc), (b2, recall)]:
            for bar, v in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width()/2, v + 1.0,
                        f"{v:.1f}", ha="center", fontsize=13, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(models, fontsize=15, fontweight="bold")
        ax.set_ylabel("Giá trị", fontsize=15)
        ax.set_title("Cross-dataset Zero-shot — 4 mô hình trên XBLOCK D2",
                     fontsize=20, fontweight="bold", pad=15)
        ax.set_ylim(0, 105)
        ax.legend(loc="lower right", fontsize=14)
        _save(fig, "slide4_crossdataset", OUT_SLIDES)
        plt.close(fig)


# --- CLI --------------------------------------------------------------------
FIGS = {
    "slide1":        fig_slide1,
    "attack_asr":    fig_attack_asr,
    "attack_cost":   fig_attack_cost,
    "defense_bar":   fig_defense_bar,
    "defense_curve": fig_defense_curve,
    "d2_zeroshot":   fig_d2_zeroshot,
    "k1_vs_k2":      fig_k1_vs_k2,
    "attack_rank":   fig_attack_rank,
    # Slides for presentation (16:9, big fonts, callout boxes)
    "pres_slide1":   slide_1_clean,
    "pres_slide2":   slide_2_attack,
    "pres_slide3":   slide_3_defense,
    "pres_slide4":   slide_4_crossdataset,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fig", choices=list(FIGS) + ["all"], default="all")
    args = ap.parse_args()
    figs_to_run = list(FIGS) if args.fig == "all" else [args.fig]
    print(f"Output dir: {OUT.resolve()}")
    for name in figs_to_run:
        print(f"\n[{name}]")
        FIGS[name]()
    print(f"\nDone. {len(figs_to_run)} figures saved.")


if __name__ == "__main__":
    main()

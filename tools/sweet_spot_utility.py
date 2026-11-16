"""Sweet spot theo utility nhat quan voi threat model (mo rong y tuong gain - cost cua Kireev et al., NDSS 2023).

Hai ke tan cong, moi loai dung ASR va chi phi cung mot gia dinh:

  A. Oracle-stop (can tren cho ke tan cong): biet khi nao vi da lat va dung lai.
     Dung min_txs tung vi tu Stage 6 mincost.
       U_A(b) = sum_i [ 1(m_i <= b) * G_i  -  min(m_i, b) * c ]      (vi khong lat: m_i = inf)

  B. Black-box ngan sach co dinh (khop threat model: khong truy van mo hinh):
     chi du b tx cho moi vi, khong biet vi da lat hay chua.
     Dung xac suat tung vi tu Stage 7 per-budget.
       U_B(b) = sum_{i in E} [ 1(p_i(b) < 0.5) * G_i  -  b * c ]

G_i = tong ETH vi phishing i nhan vao (can tren cua loi ich nho ne phat hien).
Moi cong thuc chay hai bien the: G_i rieng tung vi, va G = median chung.
argmax_b khong phu thuoc N vi N chi nhan ca hai ve.
"""
import argparse
import csv
import json
import statistics
from pathlib import Path

import numpy as np

ATTACK = "ADAPTIVE-STC-LV"
SEEDS = (42, 43, 44)
STAGE7_BUDGETS = {5: 30, 20: 120, 100: 600}
METHODS = ("baseline_peaepaper", "advtrain_peaepaper", "ra_peaepaper", "ra_peaepaper_noedge")
WEI = 10 ** 18


def incoming_eth(bundle: Path, addresses):
    out = {}
    for a in addresses:
        txs = json.load(open(bundle / "phishing_hop1_txs" / f"{a}.json", encoding="utf-8"))
        out[a] = sum(int(t.get("value", "0") or 0) for t in txs
                     if t.get("isError", "0") == "0" and t.get("to", "").lower() == a) / WEI
    return out


def oracle_stop(mincost_dir: Path, gains, g_med, c):
    per_seed = []
    for s in SEEDS:
        d = json.load(open(mincost_dir / f"results_peae_paper_seed{s}_mincost_adaptive_full.json", encoding="utf-8"))
        targets = [t.lower() for t in d["targets"]]
        m = d["attacks"][ATTACK]["min_txs"]
        grid = [b * 6 for b in d["budgets"]]
        rows = []
        for b in grid:
            flipped = [mi is not None and mi <= b for mi in m]
            cost = sum((min(mi, b) if mi is not None else b) for mi in m) * c
            u_i = sum(gains[t] for t, f in zip(targets, flipped) if f) - cost
            u_med = sum(flipped) * g_med - cost
            rows.append({"b": b, "asr": sum(flipped) / len(m), "u_gi": u_i, "u_med": u_med})
        profitable = sum(1 for t, mi in zip(targets, m) if mi is not None and gains[t] > mi * c)
        per_seed.append({"seed": s, "n": len(m), "rows": rows, "profitable_frac": profitable / len(m)})
    return per_seed


def blackbox(stage7_dir: Path, test_phish, gains, g_med, c):
    out = {m: [] for m in METHODS}
    for s in SEEDS:
        z = np.load(stage7_dir / f"eval_probs_seed{s}_withbaseline.npz")
        for m in METHODS:
            elig = z[f"{m}__clean"][np.asarray(z["labels"]) == 1] >= 0.5
            rows = []
            for unit, b in STAGE7_BUDGETS.items():
                flipped = (z[f"{m}__{ATTACK}__{unit}"] < 0.5) & elig
                n = int(elig.sum())
                cost = n * b * c
                u_i = sum(gains[a] for a, f in zip(test_phish, flipped) if f) - cost
                u_med = int(flipped.sum()) * g_med - cost
                rows.append({"b": b, "asr": float(flipped.sum() / n), "u_gi": u_i, "u_med": u_med})
            out[m].append({"seed": s, "n": int(elig.sum()), "rows": rows})
    return out


def summarize(per_seed, key):
    budgets = [r["b"] for r in per_seed[0]["rows"]]
    mean_u = [statistics.mean(ps["rows"][i][key] for ps in per_seed) for i in range(len(budgets))]
    mean_asr = [statistics.mean(ps["rows"][i]["asr"] for ps in per_seed) for i in range(len(budgets))]
    best = max(range(len(budgets)), key=lambda i: mean_u[i])
    seed_best = [max(ps["rows"], key=lambda r: r[key])["b"] for ps in per_seed]
    return budgets, mean_asr, mean_u, budgets[best], seed_best


def main():
    ap = argparse.ArgumentParser()
    root = Path(r"E:/EthereumPhishingDetection")
    ap.add_argument("--bundle", type=Path, default=root / "dataset_bundle")
    ap.add_argument("--mincost_dir", type=Path, default=root / "json_stage5_6_final/stage6")
    ap.add_argument("--stage7_dir", type=Path, default=root / "stage7_peae/eval_results")
    ap.add_argument("--gas", type=float, default=0.00125)
    ap.add_argument("--out", type=Path, default=root / "BaoCao_Sweet_Spot_NhatQuan.md")
    args = ap.parse_args()

    split = list(csv.DictReader(open(args.bundle / "temporal_split.csv", encoding="utf-8")))
    test_phish = [r["address"].lower() for r in split if r["partition"] == "test" and r["label"] == "1"]
    gains = incoming_eth(args.bundle, test_phish)
    g_med = statistics.median(gains.values())
    c = args.gas

    A = oracle_stop(args.mincost_dir, gains, g_med, c)
    B = blackbox(args.stage7_dir, test_phish, gains, g_med, c)

    md = ["# Sweet spot nhat quan voi threat model (PEAE-GNN x ADAPTIVE-STC-LV)", "",
          f"c = {c} ETH/tx | G median = {g_med:.2f} ETH | 3 seeds | U tinh bang ETH", "",
          "## A. Oracle-stop (can tren): ASR va chi phi tu min_txs tung vi (Stage 6)", "",
          "| b (tx) | ASR | U (G_i rieng) | U (G median) |", "|---:|---:|---:|---:|"]
    b_, asr_, ugi, best_gi, seeds_gi = summarize(A, "u_gi")
    _, _, umed, best_med, seeds_med = summarize(A, "u_med")
    for b, a, u1, u2 in zip(b_, asr_, ugi, umed):
        md.append(f"| {b} | {a*100:.1f}% | {u1:,.0f} | {u2:,.0f} |")
    pf = statistics.mean(ps["profitable_frac"] for ps in A)
    md += ["", f"Sweet spot (G_i rieng): **{best_gi} tx** (tung seed: {seeds_gi})",
           f"Sweet spot (G median): **{best_med} tx** (tung seed: {seeds_med})",
           f"Ti le vi ma tan cong co loi (G_i > min_txs_i * c): **{pf*100:.1f}%** so vi eligible", "",
           "## B. Black-box ngan sach co dinh (khop threat model): Stage 7 per-budget", "",
           "| Phuong phap | n eligible | ASR 30/120/600 tx | U (G_i) 30/120/600 | Sweet (G_i) | Sweet (G median) |",
           "|---|---:|---|---|---:|---:|"]
    result = {"A": A, "B": {}}
    for m in METHODS:
        b_, asr_, ugi, best_gi, seeds_gi = summarize(B[m], "u_gi")
        _, _, _, best_med, seeds_med = summarize(B[m], "u_med")
        n = statistics.mean(ps["n"] for ps in B[m])
        md.append(f"| {m} | {n:.0f} | {' / '.join(f'{a*100:.1f}%' for a in asr_)} | "
                  f"{' / '.join(f'{u:,.0f}' for u in ugi)} | {best_gi} {seeds_gi} | {best_med} {seeds_med} |")
        result["B"][m] = B[m]
    md += ["", "Ghi chu: B chi co 3 muc ngan sach (30/120/600 tx) nen sweet spot la tren luoi tho nay.",
           "Ghi chu: baseline_peaepaper trong eval_*_withbaseline la checkpoint train lai o may "
           "(stage5_peae_local), khong phai Stage 5 chinh thuc; cac dong phong thu khong bi anh huong."]
    args.out.write_text("\n".join(md), encoding="utf-8")
    args.out.with_suffix(".json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()

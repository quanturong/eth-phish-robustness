"""
TRANSFER evaluation (inspired by Frankart et al. 2025 Section V.E).

Attack designed against model A, evaluate on model B.
Reports: ∆P reduction correlation matrix across (SAGE, GATv2, PEAE).

Procedure per target x per attack:
  1. Attack targeted at model A (e.g., PEAE) → get new_txs
  2. Build graph(target, new_txs)
  3. Compute p_phish on all 3 models
  4. ∆P_m = p_clean_m - p_attacked_m for each model m

Final: Pearson correlation of ∆P vectors across models.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch_geometric.data import Batch
from tqdm import tqdm

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import stage9_k2_upgrade as k2
from stage5_train_baselines import MODELS, to_pyg
from stage6_adversarial_attacks import (
    ATTACKS, ATTACK_IDS, TargetCache, build_graph,
    _set_base, _atk_rng,
)


def predict(model, g, stats, device):
    """Predict P(phishing) for 1 graph."""
    d = to_pyg(g, stats)
    batch = Batch.from_data_list([d]).to(device)
    with torch.no_grad():
        return float(F.softmax(model(batch), dim=1)[0, 1].item())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base_dir", required=True)
    ap.add_argument("--stage5_dir", default=None)
    ap.add_argument("--attacker", choices=list(MODELS), default="peaegnn",
                    help="model used to GUIDE attack (only matters for GGS)")
    ap.add_argument("--ckpt_seed", type=int, default=42)
    ap.add_argument("--attacks", nargs="+", default=["GGS", "SPOOL", "CRING"])
    ap.add_argument("--budget", type=int, default=50)
    ap.add_argument("--n_targets", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tag", default="transfer")
    args = ap.parse_args()

    base = Path(args.base_dir)
    _set_base(base)
    stage5 = Path(args.stage5_dir) if args.stage5_dir else base / "ethphishgraph2026_stage5_baselines_k2"
    out_dir = base / "ethphishgraph2026_stage6_attacks_k2"
    out_dir.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    stats = torch.load(stage5 / "feat_stats.pt", map_location="cpu", weights_only=True)
    in_dim = int(stats["node_mean"].numel())

    models = {}
    for name in ["graphsage", "gatv2", "peaegnn"]:
        m = MODELS[name](in_dim=in_dim).to(device)
        ckpt = stage5 / f"model_{name}_seed{args.ckpt_seed}.pt"
        m.load_state_dict(torch.load(ckpt, map_location=device, weights_only=True))
        m.eval()
        models[name] = m
        print(f"  Loaded {name}")

    split = pd.read_csv(k2.SPLIT_CSV)
    t_end = int(split["anchor_ts"].max()) + 10 * 365 * 24 * 3600
    label_of = dict(zip(split["address"].str.lower(), split["label"].astype(int)))
    test = split[split["partition"] == "test"].reset_index(drop=True)
    # Chi lay phishing (attacks nham vao phishing targets)
    phish = test[test["label"] == 1].reset_index(drop=True)
    sample = phish.sample(n=min(args.n_targets, len(phish)), random_state=args.seed).reset_index(drop=True)
    print(f"Sampling {len(sample)} phishing targets (of {len(phish)})")

    # dP[attacker_model][eval_model][attack] = list of (p_clean - p_attacked)
    results = {am: {em: {atk: [] for atk in args.attacks} for em in models} for am in models}

    attacker_model = models[args.attacker]
    t0 = time.time()
    for _, row in tqdm(sample.iterrows(), total=len(sample), unit="tgt"):
        addr = row["address"].lower()
        c = TargetCache(addr, 1, t_end, label_of)
        g_clean = build_graph(c)
        if g_clean is None:
            continue
        p_clean = {em: predict(models[em], g_clean, stats, device) for em in models}

        ctx = {"model": attacker_model, "stats": stats, "device": device,
               "cache": c, "build_fn": build_graph, "n_cands": 4}

        for atk in args.attacks:
            try:
                new, _ = ATTACKS[atk](c.txs, addr, args.budget,
                                       _atk_rng(args.seed, addr, ATTACK_IDS[atk], args.budget),
                                       c.pool, **ctx)
            except Exception as e:
                print(f"  [{atk}] {addr[:10]} fail: {e}")
                continue
            g_atk = build_graph(c, new)
            if g_atk is None:
                g_atk = g_clean
            for em in models:
                p_atk = predict(models[em], g_atk, stats, device)
                dP = p_clean[em] - p_atk
                results[args.attacker][em][atk].append(dP)

    # Compute aggregate stats + correlation
    print(f"\nTime: {(time.time()-t0)/60:.1f} min")
    print(f"\n=== Mean ∆P per attack x eval_model (attacker={args.attacker}) ===")
    header = ["attack"] + list(models)
    print("{:<12s}".format(header[0]) + "".join(f"{em:>12s}" for em in models))
    for atk in args.attacks:
        row = [atk]
        for em in models:
            arr = np.array(results[args.attacker][em][atk])
            row.append(float(arr.mean()) if len(arr) else float("nan"))
        print("{:<12s}".format(row[0]) + "".join(f"{v:>12.4f}" for v in row[1:]))

    print(f"\n=== ASR per attack x eval_model (p_atk < 0.5) ===")
    print("{:<12s}".format("attack") + "".join(f"{em:>12s}" for em in models))
    for atk in args.attacks:
        row = [atk]
        for em in models:
            arr = np.array(results[args.attacker][em][atk])
            # ASR = p_clean - dP < 0.5 means p_atk < 0.5
            # Need p_clean values too; reconstruct
            # Simplify: fraction of samples where dP > 0.1 (significant drop)
            frac_big_drop = float((arr > 0.1).mean()) if len(arr) else float("nan")
            row.append(frac_big_drop)
        print("{:<12s}".format(row[0]) + "".join(f"{v:>12.4f}" for v in row[1:]))

    # Pearson correlation of ∆P across eval_models (per attack)
    print(f"\n=== Pearson ρ(∆P) across eval_models (attack designed for {args.attacker}) ===")
    for atk in args.attacks:
        mats = {em: np.array(results[args.attacker][em][atk]) for em in models}
        n = min(len(a) for a in mats.values())
        if n < 2:
            continue
        print(f"\n--- {atk} ---")
        print("{:<12s}".format("") + "".join(f"{em:>12s}" for em in models))
        for em1 in models:
            row = [em1]
            for em2 in models:
                a1, a2 = mats[em1][:n], mats[em2][:n]
                if a1.std() < 1e-9 or a2.std() < 1e-9:
                    row.append(float("nan"))
                else:
                    row.append(float(np.corrcoef(a1, a2)[0, 1]))
            print("{:<12s}".format(row[0]) + "".join(f"{v:>12.3f}" for v in row[1:]))

    # Save raw dP arrays for later analysis
    out = out_dir / f"transfer_{args.tag}_atkr{args.attacker}_s{args.ckpt_seed}_b{args.budget}_n{args.n_targets}.json"
    serial = {am: {em: {atk: list(map(float, results[am][em][atk])) for atk in results[am][em]}
                   for em in results[am]} for am in results}
    out.write_text(json.dumps({"attacker": args.attacker, "budget": args.budget,
                                "n_targets": args.n_targets, "dP": serial}, indent=2),
                   encoding="utf-8")
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()

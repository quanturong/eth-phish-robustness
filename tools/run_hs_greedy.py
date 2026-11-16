"""
HS-greedy baseline comparison (Hide-and-Seek paper style).

Thay vì chon ngẫu nhiên vi trung gian (PN), chon THAM LAM:
- Moi buoc, thu N candidate PN (vi normal co san tu train)
- Tinh P(phishing) sau khi them transaction tu moi candidate
- Chon candidate lam P giam nhieu nhat
- Lap lai cho den khi het budget

So sanh voi tan cong random cua KLTN (TOH, TIH, BPH-T2P, BPH-P2T) o ngan sach b=20.
Noi den: Wen et al. 2023 IEEE TCSS, Bang III-IV (random 7-14%, greedy 48-82%).

Usage:
    python tools/run_hs_greedy.py --model graphsage --ckpt_seed 42 --n_candidates 10 --budget 20
"""
import argparse
import hashlib
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

sys.stdout.reconfigure(encoding='utf-8')

# Import pipeline modules
sys.path.insert(0, str(Path(__file__).parent.parent))
import stage9_k2_upgrade as k2
from stage5_train_baselines import MODELS, to_pyg
import stage6_adversarial_attacks as s6


def load_candidate_pns(normal_hop1_dir: Path, split_df, n: int = 50, seed: int = 42):
    """Load n normal addresses tu TRAIN de dung lam candidate PN."""
    rng = np.random.default_rng(seed)
    normal_train = split_df[(split_df['label'] == 0) &
                            (split_df['partition'] == 'train')]['address'].str.lower().tolist()
    rng.shuffle(normal_train)
    pns = []
    for addr in normal_train:
        f = Path(normal_hop1_dir) / f"{addr}.json"
        if not f.exists() or f.stat().st_size <= 2:
            continue
        pns.append(addr)
        if len(pns) >= n:
            break
    return pns


def hs_greedy_attack(raw_target_txs, target, attack_type, budget, model, stats, device,
                     cache, build_fn, candidate_pns, n_candidates=10, rng=None):
    """
    HS-greedy attack: moi buoc thu n_candidates PN, chon PN lam P giam nhieu nhat.
    attack_type: TOH (target -> PN) | TIH (PN -> target) | BPH-T2P (target -> W -> PN) | BPH-P2T (PN -> W -> target)
    """
    rng = rng or np.random.default_rng(42)
    t0 = s6._last_ts(raw_target_txs) + 3600
    pool = s6._gas_pool(raw_target_txs)
    acc_txs = []
    used_pns = set()
    wal = set()

    def prob(all_txs):
        g = build_fn(cache, all_txs if all_txs else None)
        if g is None: return None
        batch = Batch.from_data_list([to_pyg(g, stats)]).to(device)
        with torch.no_grad():
            return float(F.softmax(model(batch), dim=1)[0, 1].item())

    cur_p = prob([])
    if cur_p is None:
        return [], set()

    for step in range(budget):
        # Shuffle candidates, pick n_candidates not-yet-used
        available = [p for p in candidate_pns if p not in used_pns]
        if not available:
            break
        cands = rng.choice(available, size=min(n_candidates, len(available)), replace=False).tolist()

        best = None
        for pn in cands:
            # Generate 1 unit attack with this specific PN
            val = int(rng.uniform(1e15, 1e16))
            ts = t0 + step * 600 + int(rng.integers(0, 300))
            if attack_type == 'TOH':
                tx = s6._mk_tx(target, pn, val, ts, s6._gp(rng, pool))
                new_txs = [tx]
            elif attack_type == 'TIH':
                tx = s6._mk_tx(pn, target, val, ts, s6._gp(rng, pool))
                new_txs = [tx]
            elif attack_type == 'BPH-T2P':
                w1 = s6._fake_wallet(target, 20000 + step)
                ts2 = ts + 300 + int(rng.integers(0, 200))
                new_txs = [s6._mk_tx(target, w1, val, ts, s6._gp(rng, pool)),
                           s6._mk_tx(w1, pn, int(val * 0.98), ts2, s6._gp(rng, pool))]
            elif attack_type == 'BPH-P2T':
                w1 = s6._fake_wallet(target, 50000 + step)
                ts2 = ts + 300 + int(rng.integers(0, 200))
                new_txs = [s6._mk_tx(pn, w1, val, ts, s6._gp(rng, pool)),
                           s6._mk_tx(w1, target, int(val * 0.98), ts2, s6._gp(rng, pool))]
            else:
                raise ValueError(f"Unknown attack: {attack_type}")

            pv = prob(acc_txs + new_txs)
            if pv is None: continue
            if best is None or pv < best[0]:
                best = (pv, new_txs, pn, w1 if attack_type.startswith('BPH') else None)

        if best is None:
            break
        acc_txs += best[1]
        used_pns.add(best[2])
        wal.add(best[2])
        if best[3]:
            wal.add(best[3])
        if best[0] < cur_p:
            cur_p = best[0]
        if cur_p < 0.3:
            break  # already flipped significantly

    return acc_txs, wal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="graphsage", choices=['graphsage', 'gatv2', 'peaegnn', 'peae_paper'])
    ap.add_argument("--ckpt_seed", type=int, default=42)
    ap.add_argument("--stage5_dir", required=True)
    ap.add_argument("--base_dir", required=True)
    ap.add_argument("--attacks", nargs='+', default=['TOH', 'TIH', 'BPH-T2P', 'BPH-P2T'])
    ap.add_argument("--budget", type=int, default=20)
    ap.add_argument("--n_candidates", type=int, default=10)
    ap.add_argument("--max_targets", type=int, default=0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--tag", default="hsgreedy")
    args = ap.parse_args()

    s6._set_base(Path(args.base_dir))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device} | Model: {args.model} | seed: {args.ckpt_seed}")

    stage5_dir = Path(args.stage5_dir)
    out_dir = Path(args.out or (Path(args.base_dir) / "ethphishgraph2026_stage6_attacks_k2"))
    out_dir.mkdir(parents=True, exist_ok=True)

    stats = torch.load(stage5_dir / "feat_stats.pt", map_location="cpu", weights_only=True)
    in_dim = int(stats["node_mean"].numel())
    model = MODELS[args.model](in_dim=in_dim).to(device)
    model.load_state_dict(torch.load(stage5_dir / f"model_{args.model}_seed{args.ckpt_seed}.pt",
                                     map_location=device, weights_only=True))
    model.eval()

    split = pd.read_csv(k2.SPLIT_CSV)
    t_end = int(split["anchor_ts"].max()) + 10 * 365 * 24 * 3600
    label_of = dict(zip(split["address"].str.lower(), split["label"].astype(int)))
    test = split[split["partition"] == "test"].reset_index(drop=True)
    if args.max_targets:
        test = test.sample(n=min(args.max_targets, len(test)), random_state=0).reset_index(drop=True)
    print(f"Test targets: {len(test)}")

    print(f"Loading {args.n_candidates * 3} candidate PNs...")
    candidate_pns = load_candidate_pns(k2.NORMAL_HOP1_DIR, split, n=args.n_candidates * 3,
                                        seed=args.ckpt_seed)
    print(f"  loaded {len(candidate_pns)} PNs")

    results = {atk: {'n_correct': 0, 'n_flipped': 0, 'details': []} for atk in args.attacks}
    t0 = time.time()
    for _, row in tqdm(test.iterrows(), total=len(test), unit="tgt"):
        addr, label = row["address"].lower(), int(row["label"])
        if label != 1:  # only phishing targets
            continue
        c = s6.TargetCache(addr, label, t_end, label_of)
        g0 = s6.build_graph(c)
        if g0 is None: continue

        batch = Batch.from_data_list([to_pyg(g0, stats)]).to(device)
        with torch.no_grad():
            p_clean = float(F.softmax(model(batch), dim=1)[0, 1].item())
        if p_clean < 0.5:  # not caught cleanly, skip
            continue

        for atk in args.attacks:
            results[atk]['n_correct'] += 1
            rng = np.random.default_rng([args.ckpt_seed,
                                          int(hashlib.md5(addr.encode()).hexdigest()[:8], 16),
                                          hash(atk) & 0xFFFF])
            new_txs, wal = hs_greedy_attack(
                c.txs, addr, atk, args.budget, model, stats, device, c, s6.build_graph,
                candidate_pns, n_candidates=args.n_candidates, rng=rng)
            g_atk = s6.build_graph(c, new_txs)
            if g_atk is None:
                continue
            batch_atk = Batch.from_data_list([to_pyg(g_atk, stats)]).to(device)
            with torch.no_grad():
                p_atk = float(F.softmax(model(batch_atk), dim=1)[0, 1].item())
            flipped = p_atk < 0.5
            if flipped:
                results[atk]['n_flipped'] += 1
            results[atk]['details'].append({
                'target': addr, 'p_clean': p_clean, 'p_atk': p_atk,
                'n_txs': len(new_txs), 'flipped': flipped,
            })
    dt = (time.time() - t0) / 60

    # Summary
    print(f"\n{'='*70}")
    print(f" HS-greedy ASR ({args.model} seed {args.ckpt_seed}, b={args.budget}, {args.n_candidates} cands)")
    print(f"{'='*70}")
    print(f"{'Attack':<12s} {'n_correct':>10s} {'n_flipped':>10s} {'ASR':>8s}")
    for atk in args.attacks:
        r = results[atk]
        asr = r['n_flipped'] / max(r['n_correct'], 1)
        print(f"{atk:<12s} {r['n_correct']:>10d} {r['n_flipped']:>10d} {asr*100:>7.1f}%")
    print(f"\nTime: {dt:.1f} min")

    # Save
    out_file = out_dir / f"results_{args.model}_seed{args.ckpt_seed}_{args.tag}_b{args.budget}.json"
    out_file.write_text(json.dumps({
        'model': args.model, 'ckpt_seed': args.ckpt_seed,
        'budget': args.budget, 'n_candidates': args.n_candidates,
        'attacks': {atk: {'n_correct': r['n_correct'], 'n_flipped': r['n_flipped'],
                          'asr': r['n_flipped'] / max(r['n_correct'], 1)}
                    for atk, r in results.items()},
        'details_sample': {atk: results[atk]['details'][:20] for atk in args.attacks},
        'time_min': dt,
    }, indent=2), encoding='utf-8')
    print(f"Saved -> {out_file}")


if __name__ == '__main__':
    main()

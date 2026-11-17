"""
Stage 8 D2 cross-check cho peae_paper (3 seeds).

Zero-shot: dung model train tren EthPhishGraph-2026, danh gia tren D2 (XBLOCK).
D2 ego graphs da duoc chuyen qua format pipeline tai:
  dataset/EthPhishGraph-2026/ethphishgraph2026_stage8_crosscheck_D2/d2_ego_graphs.pkl

Usage:
    python tools/eval_d2_peae_paper.py --stage5_dir <stage5_peae_local>
"""
import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import (roc_auc_score, average_precision_score, f1_score,
                             precision_recall_fscore_support, roc_curve)
from torch_geometric.data import Batch
from torch_geometric.loader import DataLoader

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent.parent))

from stage5_train_baselines import MODELS, to_pyg

D2_PKL = Path(r'E:\EthereumPhishingDetection\dataset\EthPhishGraph-2026\ethphishgraph2026_stage8_crosscheck_D2\d2_ego_graphs.pkl')


def eval_model(model, graphs, stats, device):
    model.eval()
    pyg = [to_pyg(g, stats) for g in graphs]
    loader = DataLoader(pyg, batch_size=32, shuffle=False)
    probs, labels = [], []
    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            p = F.softmax(model(batch), dim=1)[:, 1].cpu().numpy()
            probs.append(p)
            labels.append(batch.y.cpu().numpy())
    p = np.concatenate(probs)
    y = np.concatenate(labels)
    preds = (p >= 0.5).astype(int)
    roc_auc = float(roc_auc_score(y, p))
    pr_auc = float(average_precision_score(y, p))
    macro_f1 = float(f1_score(y, preds, average='macro'))
    pprec, prec, pf1, _ = precision_recall_fscore_support(
        y, preds, pos_label=1, average='binary', zero_division=0)
    fpr, tpr, _ = roc_curve(y, p)
    idx = np.searchsorted(fpr, 0.10)
    rec_at_fpr10 = float(tpr[min(idx, len(tpr) - 1)])
    return {
        'roc_auc': roc_auc, 'pr_auc': pr_auc, 'macro_f1': macro_f1,
        'prec_phishing': float(pprec), 'rec_phishing': float(prec), 'f1_phishing': float(pf1),
        'recall_at_fpr10': rec_at_fpr10,
        'pred_phishing_rate': float(preds.mean()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage5_dir", required=True)
    ap.add_argument("--model", default="peae_paper")
    ap.add_argument("--seeds", nargs='+', type=int, default=[42, 43, 44])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f'Device: {device}')
    stage5_dir = Path(args.stage5_dir)

    stats = torch.load(stage5_dir / "feat_stats.pt", map_location="cpu", weights_only=True)
    in_dim = int(stats["node_mean"].numel())
    print(f'in_dim: {in_dim}')

    print(f'Loading D2 ego graphs from {D2_PKL}')
    data = pickle.load(open(D2_PKL, 'rb'))
    all_graphs = data['train'] + data['val'] + data['test']
    print(f'D2 total: {len(all_graphs)} graphs')
    print(f'  train={len(data["train"])}, val={len(data["val"])}, test={len(data["test"])}')
    labels_all = [g['label'] for g in all_graphs]
    print(f'  phishing={sum(labels_all)}, normal={len(labels_all) - sum(labels_all)}')

    results = {args.model: {'per_seed': []}}
    for seed in args.seeds:
        ck = stage5_dir / f"model_{args.model}_seed{seed}.pt"
        if not ck.exists():
            print(f'  SKIP seed {seed}: {ck} not found')
            continue
        model = MODELS[args.model](in_dim=in_dim).to(device)
        model.load_state_dict(torch.load(ck, map_location=device, weights_only=True))
        # Eval on ALL D2 graphs (zero-shot)
        m = eval_model(model, all_graphs, stats, device)
        m['seed'] = seed
        results[args.model]['per_seed'].append(m)
        print(f'  seed {seed}: ROC={m["roc_auc"]:.4f} PR={m["pr_auc"]:.4f} '
              f'F1={m["macro_f1"]:.4f} Rec={m["rec_phishing"]:.4f} R@FPR10={m["recall_at_fpr10"]:.4f}')

    # Aggregate
    if results[args.model]['per_seed']:
        agg = {}
        for k in ['roc_auc', 'pr_auc', 'macro_f1', 'prec_phishing', 'rec_phishing',
                  'f1_phishing', 'recall_at_fpr10', 'pred_phishing_rate']:
            vals = [r[k] for r in results[args.model]['per_seed']]
            agg[k] = {'mean': float(np.mean(vals)), 'std': float(np.std(vals, ddof=0))}
        results[args.model]['agg'] = agg
        print(f'\n=== Agg (3 seeds) ===')
        for k, v in agg.items():
            print(f'  {k:<15s} {v["mean"]:.4f} ± {v["std"]:.4f}')

    out = Path(args.out or r'E:\EthereumPhishingDetection\d2_peae_paper_results.json')
    out.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(f'\nSaved -> {out}')


if __name__ == '__main__':
    main()

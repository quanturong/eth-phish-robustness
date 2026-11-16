"""
Tinh ROC-AUC va cac metric bo sung cho 3 mo hinh cu (graphsage, gatv2, peaegnn)
tren tap test K=2. peaegnnv2 chua co checkpoint local nen bo qua.
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import (
    roc_auc_score, average_precision_score, f1_score,
    precision_recall_fscore_support, roc_curve,
)
from torch_geometric.data import Batch
from torch_geometric.loader import DataLoader

sys.stdout.reconfigure(encoding='utf-8')

from stage5_train_baselines import MODELS, to_pyg

STAGE5 = Path(r'E:\EthereumPhishingDetection\dataset\EthPhishGraph-2026\ethphishgraph2026_stage5_baselines_k2')
K2_PKL = Path(r'E:\EthereumPhishingDetection\dataset\EthPhishGraph-2026\ethphishgraph2026_stage9_k2\ego_graph_k2_dataset.pkl')
OUT = Path(r'E:\EthereumPhishingDetection\rocauc_results.json')

MODELS_TO_EVAL = ['graphsage', 'gatv2', 'peaegnn']
SEEDS = [42, 43, 44]


def main():
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f'Device: {device}')

    print(f'Loading {K2_PKL}...')
    with open(K2_PKL, 'rb') as f:
        data = pickle.load(f)
    test_graphs = data['test']
    print(f'  test graphs: {len(test_graphs)}')

    print(f'Loading feat_stats...')
    stats = torch.load(STAGE5 / 'feat_stats.pt', map_location='cpu', weights_only=True)
    in_dim = int(stats['node_mean'].numel())

    # Convert all test graphs to PyG once
    print('Converting to PyG...')
    pyg_graphs = []
    labels = []
    for g in test_graphs:
        pyg_graphs.append(to_pyg(g, stats))
        labels.append(int(g['label']))
    labels = np.array(labels)
    print(f'  phishing: {int((labels == 1).sum())}, normal: {int((labels == 0).sum())}')

    loader = DataLoader(pyg_graphs, batch_size=32, shuffle=False)

    results = {}
    for model_name in MODELS_TO_EVAL:
        results[model_name] = {'per_seed': []}
        for seed in SEEDS:
            ckpt_path = STAGE5 / f'model_{model_name}_seed{seed}.pt'
            if not ckpt_path.exists():
                print(f'  SKIP {model_name} s{seed}: no checkpoint')
                continue
            model = MODELS[model_name](in_dim=in_dim).to(device)
            model.load_state_dict(torch.load(ckpt_path, map_location=device, weights_only=True))
            model.eval()

            all_probs = []
            with torch.no_grad():
                for batch in loader:
                    batch = batch.to(device)
                    logits = model(batch)
                    probs = F.softmax(logits, dim=1)[:, 1].cpu().numpy()
                    all_probs.append(probs)
            probs = np.concatenate(all_probs)
            preds = (probs >= 0.5).astype(int)

            # Compute metrics
            roc_auc = float(roc_auc_score(labels, probs))
            pr_auc = float(average_precision_score(labels, probs))
            macro_f1 = float(f1_score(labels, preds, average='macro'))
            p_phi, r_phi, f_phi, _ = precision_recall_fscore_support(
                labels, preds, pos_label=1, average='binary', zero_division=0)
            p_nor, r_nor, f_nor, _ = precision_recall_fscore_support(
                labels, preds, pos_label=0, average='binary', zero_division=0)

            # Recall at FPR=10%
            fpr, tpr, _ = roc_curve(labels, probs)
            idx = np.searchsorted(fpr, 0.10)
            recall_at_fpr10 = float(tpr[min(idx, len(tpr) - 1)])

            r = {
                'seed': seed,
                'roc_auc': roc_auc,
                'pr_auc': pr_auc,
                'macro_f1': macro_f1,
                'prec_phishing': float(p_phi),
                'rec_phishing': float(r_phi),
                'f1_phishing': float(f_phi),
                'prec_normal': float(p_nor),
                'rec_normal': float(r_nor),
                'f1_normal': float(f_nor),
                'recall_at_fpr10': recall_at_fpr10,
            }
            results[model_name]['per_seed'].append(r)
            print(f'  {model_name} s{seed}: ROC-AUC={roc_auc:.4f} PR-AUC={pr_auc:.4f} '
                  f'MacroF1={macro_f1:.4f} R@FPR10={recall_at_fpr10:.4f}')

        # Aggregate mean ± std
        if results[model_name]['per_seed']:
            agg = {}
            for key in ['roc_auc', 'pr_auc', 'macro_f1', 'prec_phishing',
                        'rec_phishing', 'f1_phishing', 'prec_normal',
                        'rec_normal', 'f1_normal', 'recall_at_fpr10']:
                vals = [r[key] for r in results[model_name]['per_seed']]
                agg[key] = {'mean': float(np.mean(vals)),
                            'std': float(np.std(vals, ddof=0))}
            results[model_name]['agg'] = agg

    OUT.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(f'\nSaved -> {OUT}')


if __name__ == '__main__':
    main()

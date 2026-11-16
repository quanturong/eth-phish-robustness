---
license: cc-by-4.0
task_categories:
- graph-ml
- node-classification
tags:
- ethereum
- blockchain
- phishing-detection
- gnn
- graph-neural-network
- adversarial-robustness
- fraud-detection
- cryptocurrency
size_categories:
- 1K<n<10K
language:
- en
pretty_name: EthPhishGraph-2026
---

# EthPhishGraph-2026

Ego-graph K=2 dataset of Ethereum phishing accounts for Graph Neural Network based phishing detection and adversarial robustness research.

## 📊 Dataset Statistics

| | Count | % Phishing |
|---|---|---|
| **Total targets** | **7,036** | 50.0% |
| Phishing | 3,518 | - |
| Normal | 3,518 | - |

### Temporal split (60/20/20)

| Partition | Count | Phishing ratio | Period |
|---|---|---|---|
| Train | 4,221 | 56.8% | ≤ T1 = 2018-04-23 |
| Val | 1,407 | 37.3% | T1 → T2 = 2018-07-12 |
| Test | 1,408 | 42.2% | > T2 |

### Graph size

| Partition | Avg nodes | Avg edges |
|---|---|---|
| Train | 2,318 | 5,425 |
| Val | 2,482 | 5,376 |
| Test | 3,677 | 7,297 |

> hop-2 chiếm ~99% số node mỗi graph. Số cạnh (edges) tính cả 2 chiều trong hop-1/hop-2.

## 📁 Dataset Structure

```
EthPhishGraph-2026/
├── README.md                          # This file
├── LICENSE                            # CC-BY-4.0
├── ego_graph_k2_dataset.pkl           # 4.5 GB — Main pickle (train/val/test splits)
├── temporal_split.csv                 # 449 KB — Address → (label, partition, anchor_ts)
├── temporal_split_meta.json           # — Split metadata (T1, T2, counts)
├── per_target_neighbors.pkl           # 11 MB — Precomputed hop-1 neighbor lists
├── unique_hop1_neighbors.csv          # — Deduplicated neighbor addresses
├── feat_stats.pt                      # — Normalization stats (mean, std) from TRAIN only
├── bad_files.txt                      # — Known bad hop-2 files to skip
├── raw_txs/                           # Raw transaction JSONs (for Stage 6 attacks)
│   ├── phishing_hop1_txs.tar.gz       # ~50 MB — Phishing accounts' hop-1 txs
│   ├── normal_hop1_txs.tar.gz         # ~100 MB — Normal accounts' hop-1 txs
│   └── hop2_neighbor_txs.tar.gz       # ~5 GB — Hop-2 neighbor txs (compressed from 20 GB)
└── misc/                              # Optional artifacts (not needed for basic use)
    ├── stage1_outputs.tar.gz
    ├── stage4_imbalanced.tar.gz
    └── stage8_crosscheck_D2.tar.gz
```

## 🔬 Data Schema

### `ego_graph_k2_dataset.pkl` (main file)

```python
import pickle
with open("ego_graph_k2_dataset.pkl", "rb") as f:
    data = pickle.load(f)
# data = {"train": [...], "val": [...], "test": [...]}
```

Each entry is a `dict`:

| Key | Type | Shape | Description |
|---|---|---|---|
| `target` | `str` | — | Ethereum address `0x...` |
| `label` | `int` | — | 0 = normal, 1 = phishing |
| `target_idx` | `int` | — | Position of target in node list |
| `n_nodes` | `int` | — | Total nodes in the ego-graph |
| `n_edges` | `int` | — | Total directed edges |
| `n_hop1` | `int` | — | Number of hop-1 neighbors |
| `node_features` | `np.ndarray` | `[N, 11]` | See **Node features** below |
| `edge_index` | `np.ndarray` | `[2, E]` | COO format (source, destination) |
| `edge_attr` | `np.ndarray` | `[E, 4]` | See **Edge features** below |
| `cutoff` | `int` | — | Unix timestamp used as temporal cutoff |

#### Node features (11 columns)

| Col | Name | Description |
|---|---|---|
| 0 | `in_count` | Number of incoming transactions |
| 1 | `out_count` | Number of outgoing transactions |
| 2 | `in_value_sum` | Total incoming value (wei) |
| 3 | `out_value_sum` | Total outgoing value (wei) |
| 4 | `in_value_mean` | Mean incoming value (wei) |
| 5 | `out_value_mean` | Mean outgoing value (wei) |
| 6 | `first_ts` | First tx timestamp (⚠️ absolute — recommend to drop) |
| 7 | `last_ts` | Last tx timestamp (⚠️ absolute — recommend to drop) |
| 8 | `active_span` | `last_ts - first_ts` (relative, safe) |
| 9 | `unique_in_peers` | Number of distinct senders |
| 10 | `unique_out_peers` | Number of distinct recipients |

> **Note**: Columns 6, 7 are *absolute timestamps* which may leak temporal patterns to the model (phishing/normal classes have different time distributions). We recommend using only columns `[0,1,2,3,4,5,8,9,10]` as in `NODE_COLS = [0,1,2,3,4,5,8,9,10]`.

#### Edge features (4 columns)

| Col | Name | Description |
|---|---|---|
| 0 | `value` | Transaction value (wei) |
| 1 | `timestamp` | Transaction timestamp (⚠️ absolute — recommend to drop) |
| 2 | `gas_price` | Gas price (wei) |
| 3 | `gas_used` | Gas used (units) |

> **Note**: We recommend using only `EDGE_COLS = [0, 2, 3]` to avoid temporal leakage.

## 📝 Usage Example

```python
import pickle
import numpy as np
import torch
from torch_geometric.data import Data

# Load
with open("ego_graph_k2_dataset.pkl", "rb") as f:
    data = pickle.load(f)
print(f"Train: {len(data['train'])}, Val: {len(data['val'])}, Test: {len(data['test'])}")

# Convert one graph to PyG format
g = data['train'][0]
NODE_COLS = [0, 1, 2, 3, 4, 5, 8, 9, 10]  # drop absolute timestamps
EDGE_COLS = [0, 2, 3]

d = Data(
    x=torch.from_numpy(g['node_features'][:, NODE_COLS]).float(),
    edge_index=torch.from_numpy(g['edge_index']).long(),
    edge_attr=torch.from_numpy(g['edge_attr'][:, EDGE_COLS]).float(),
    y=torch.tensor([g['label']], dtype=torch.long),
)
print(f"Target: {g['target']}  label={g['label']}  nodes={g['n_nodes']}  edges={g['n_edges']}")
```

## 🛠️ Pipeline Stages (how the dataset was built)

1. **Stage 1 — Collect**: Crawl phishing addresses from Etherscan + known phishing lists
2. **Stage 2 — Normal crawl**: Collect normal (non-phishing) address candidates
3. **Stage 3 — Temporal split**: Split addresses into train/val/test by timestamp (T1, T2)
4. **Stage 9 — K=2 ego-graph construction**: For each target, extract hop-1 neighbors and hop-2 neighbors with full history up to the temporal cutoff. Features aggregated per node.
5. **Stage 5 — GNN baselines**: Train GraphSAGE / GATv2 / PEAE-style on this dataset
6. **Stage 6 — Adversarial attacks**: Evaluate robustness against 7+ transaction-level attacks
7. **Stage 7 — Defenses**: Adversarial training + Reliability-aware GNN

## 📏 Models benchmarked (reference performance)

Macro-F1 on test set (3 seeds mean ± std):

| Model | Macro-F1 | Phishing Recall | Phishing Precision |
|---|---|---|---|
| GraphSAGE | 0.8663 ± 0.0032 | 0.7772 ± 0.0110 | 0.9077 ± 0.0054 |
| GATv2 | 0.8151 ± 0.0108 | 0.6616 ± 0.0159 | 0.9068 ± 0.0106 |
| PEAE-style | **0.8813 ± 0.0028** | **0.8283 ± 0.0060** | 0.8925 ± 0.0072 |
| peaegnnv2 | 0.8564 ± 0.0040 | 0.7581 ± 0.0140 | 0.9035 ± 0.0142 |

## ⚔️ Adversarial Robustness Reference

Attack Success Rate (% target flipped) at max 1,200 injected transactions, 3 seeds mean ± std:

| Attack | peaegnnv2 | GraphSAGE | GATv2 |
|---|---|---|---|
| TOH (target → fake wallet) | 42.4 ± 3.7 | 7.1 ± 3.0 | 18.4 ± 2.5 |
| TIH (fake wallet → target) | 16.7 ± 10.3 | 5.9 ± 1.9 | **33.2 ± 7.5** |
| BPH-T2P | 41.9 ± 5.9 | 6.2 ± 2.2 | 14.7 ± 1.9 |
| STC (split + camouflage) | 23.1 ± 5.3 | 8.2 ± 3.0 | 5.0 ± 1.9 |
| **ADAPTIVE-STC-LV** | **66.6 ± 17.2** | **15.0 ± 2.0** | 6.8 ± 1.7 |

→ Best attack depends on architecture; adaptive-balance mechanism (ADAPTIVE-STC-LV) is strongest on PEAE but weakest on GATv2.

## ⚠️ Known Limitations

1. **Temporal split confound**: Phishing/normal class distribution differs across partitions (57% / 37% / 42%) due to their natural temporal distributions. We recommend dropping absolute `first_ts`, `last_ts`, `timestamp` features.
2. **Gas price is a time proxy**: Gas prices on Ethereum changed over years → models may indirectly use time info even without absolute timestamps.
3. **Max 500 txs per neighbor** was enforced during Stage 9 to limit RAM.
4. **Hop-2 is huge**: ~99% of graph nodes are hop-2 → very memory-intensive. Consider sub-sampling for low-RAM systems.
5. **Phishing labels** derived from publicly reported scam addresses — may contain some noise.

## 📖 Related Scripts

The code accompanying this dataset is in a separate repository (see `src/` folder or thesis repo). Key files:

- `stage9_k2_upgrade.py` — K=2 ego-graph builder
- `stage5_train_baselines.py` — GNN training (GraphSAGE, GATv2, PEAE-style)
- `stage5_train_baselines_paper.py` — Reproduction of Huang et al. 2024 PEAE-GNN
- `stage6_adversarial_attacks.py` — 7+ transaction-level attacks
- `stage7_defense.py` — Adversarial training + Reliability-aware GNN

## 📚 Citation

If you use this dataset, please cite:

```bibtex
@mastersthesis{ethphishgraph2026,
  title = {Evaluating and Enhancing the Robustness of Ethereum Phishing Detection Models
           Against Evasion Attacks on Transaction Graphs},
  author = {[Your Name]},
  school = {[Your University]},
  year = {2026},
  note = {EthPhishGraph-2026 dataset available at https://huggingface.co/datasets/[your-username]/EthPhishGraph-2026}
}
```

## 🔗 Related Papers

- Wen et al. 2022, "Hide and Seek: An Adversarial Hiding Approach Against Phishing Detection on Ethereum", IEEE TCSS — source of TOH, TIH, BPH attacks
- Huang et al. 2024, "PEAE-GNN: Phishing Detection on Ethereum via Augmentation Ego-Graph Based on Graph Neural Network", IEEE TCSS — PEAE architecture
- Frankart et al. 2025, "The Feature-Space Illusion", arXiv — related adversarial robustness work on blockchain GNNs

## 📜 License

**CC-BY-4.0** (Creative Commons Attribution 4.0 International).

Ethereum on-chain data is public and permissionless. Phishing/scam labels aggregated from public threat intelligence sources (Etherscan phishing tags, PhishTank, community-reported lists).

## 🙏 Acknowledgments

Data collected via Etherscan API. Compare dataset D2 from XBlock project ([link](https://xblock.pro)).

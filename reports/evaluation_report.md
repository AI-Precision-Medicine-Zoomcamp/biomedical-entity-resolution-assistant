# Biomedical Entity Resolution Evaluation Report

**Experiment Run ID:** `run_004`  
**Status:** Completed ✅  
**Ground Truth Size:** 31 cases  

## 1. End-to-End Pipeline Performance
| Metric | Score |
| --- | --- |
| **Accuracy** | 0.9677 |
| **Precision** | 0.9677 |
| **Recall** | 0.9677 |
| **F1-Score** | 0.9677 |

## 2. Performance by Ontology Source
| Ontology | Accuracy | Precision | Recall | F1-Score |
| --- | --- | --- | --- | --- |
| **HGNC** | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **MeSH** | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **RxNorm** | 0.9000 | 0.9000 | 0.9000 | 0.9000 |
| **ClinVar** | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

## 3. Retrieval Search Strategy Benchmark
| Strategy | Hit@1 | Hit@5 | Hit@10 | MRR |
| --- | --- | --- | --- | --- |
| **LEXICAL** | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| **VECTOR** | 0.6129 | 0.6452 | 0.6452 | 0.6290 |
| **HYBRID** | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

## 4. Embedding Model Benchmark (Cosine Similarity)
| Model Name | Hit@1 | Hit@5 | Hit@10 | MRR |
| --- | --- | --- | --- | --- |
| **SapBERT-from-PubMedBERT-fulltext** | 0.8710 | 0.9677 | 0.9677 | 0.9140 |
| **all-MiniLM-L6-v2** | 0.8387 | 0.9032 | 0.9032 | 0.8710 |

## 5. Confidence Calibration
| Confidence Bin | Total Samples | Correct | Actual Accuracy |
| --- | --- | --- | --- |
| **0.0-0.60** | 0 | 0 | 0.0000 |
| **0.60-0.80** | 3 | 2 | 0.6667 |
| **0.80-0.90** | 3 | 3 | 1.0000 |
| **0.90-1.0** | 25 | 25 | 1.0000 |

## 6. Visualization Figures
Find figures in `reports/figures/`:
- `retrieval_comparison.png`  
- `ontology_performance.png`  
- `confidence_calibration.png`  
- `embedding_comparison.png`  

import sys
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.evaluation.datasets import load_ground_truth
from src.evaluation.retrieval_eval import evaluate_retrieval_strategies, evaluate_embedding_models
from src.evaluation.entity_eval import evaluate_pipeline
from src.evaluation.reports import save_experiment_report
from src.evaluation.visualization import (
    plot_retrieval_comparison,
    plot_accuracy_by_ontology,
    plot_confidence_calibration,
    plot_embedding_model_comparison
)

def get_next_run_dir(experiments_dir: Path) -> Path:
    experiments_dir.mkdir(parents=True, exist_ok=True)
    existing_runs = [d for d in experiments_dir.iterdir() if d.is_dir() and d.name.startswith("run_")]
    if not existing_runs:
        return experiments_dir / "run_001"
        
    run_numbers = []
    for d in existing_runs:
        try:
            num = int(d.name.split("_")[1])
            run_numbers.append(num)
        except (ValueError, IndexError):
            pass
            
    next_num = max(run_numbers) + 1 if run_numbers else 1
    return experiments_dir / f"run_{next_num:03d}"

def run_benchmark() -> None:
    """
    Main harness to run the full evaluation suite.
    """
    print("=" * 60)
    print("🚀 STARTING BIOMEDICAL ENTITY RESOLUTION BENCHMARK SUITE")
    print("=" * 60)
    
    # 1. Load Ground Truth Dataset
    print("\n[Step 1] Loading ground truth dataset...")
    gt_df = load_ground_truth()
    print(f"Loaded {len(gt_df)} evaluation cases.")
    
    # 2. Evaluate Retrieval Search Strategies
    print("\n[Step 2] Evaluating retrieval search strategies (Lexical vs Vector vs Hybrid)...")
    retrieval_metrics = evaluate_retrieval_strategies(gt_df)
    for strategy, metrics in retrieval_metrics.items():
        print(f"  - {strategy.upper()} -> Hit@5: {metrics['hit_at_5']:.4f} | MRR: {metrics['mrr']:.4f}")
        
    # 3. Compare Embedding Models
    print("\n[Step 3] Comparing embedding models (SapBERT vs MiniLM)...")
    models = ["Xenova/SapBERT-from-PubMedBERT-fulltext", "Xenova/all-MiniLM-L6-v2"]
    embedding_metrics = evaluate_embedding_models(gt_df, models)
    for model_name, metrics in embedding_metrics.items():
        short_name = model_name.split("/")[-1]
        print(f"  - {short_name} -> Hit@5: {metrics['hit_at_5']:.4f} | MRR: {metrics['mrr']:.4f}")
        
    # 4. Evaluate End-to-End Entity Resolution Pipeline
    print("\n[Step 4] Evaluating end-to-end Entity Resolution pipeline...")
    pipeline_results = evaluate_pipeline(gt_df)
    overall = pipeline_results["overall_metrics"]
    print(f"  - Overall Pipeline -> Accuracy: {overall['accuracy']:.4f} | F1: {overall['f1']:.4f}")
    
    # 5. Generate and Save Visualizations
    print("\n[Step 5] Generating visualization charts...")
    figures_dir = PROJECT_ROOT / "reports" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    path_retrieval = plot_retrieval_comparison(retrieval_metrics, figures_dir)
    path_ontology = plot_accuracy_by_ontology(pipeline_results["ontology_metrics"], figures_dir)
    path_calib = plot_confidence_calibration(pipeline_results["calibration"], figures_dir)
    path_embed = plot_embedding_model_comparison(embedding_metrics, figures_dir)
    
    print(f"  Charts saved to {figures_dir}:")
    print(f"    - {path_retrieval.name}")
    print(f"    - {path_ontology.name}")
    print(f"    - {path_calib.name}")
    print(f"    - {path_embed.name}")
    
    # 6. Save Experiment Run and Tracking Data
    print("\n[Step 6] Saving experiment tracking files...")
    experiments_dir = PROJECT_ROOT / "experiments"
    run_dir = get_next_run_dir(experiments_dir)
    
    # Load current configuration settings
    settings_path = PROJECT_ROOT / "configs" / "settings.yaml"
    try:
        with open(settings_path, "r") as f:
            config_settings = yaml.safe_load(f)
    except Exception:
        config_settings = {}
        
    # Build consolidated metrics payload
    full_metrics = {
        "retrieval_strategies": retrieval_metrics,
        "embedding_models": embedding_metrics,
        "pipeline_overall": overall,
        "pipeline_by_ontology": pipeline_results["ontology_metrics"],
        "confidence_calibration": pipeline_results["calibration"]
    }
    
    save_experiment_report(
        metrics=full_metrics,
        errors=pipeline_results["errors"],
        config=config_settings,
        run_dir=run_dir
    )
    
    # 7. Generate a Markdown Summary Report
    print("\n[Step 7] Generating human-readable summary report...")
    summary_report_path = PROJECT_ROOT / "reports" / "evaluation_report.md"
    
    with open(summary_report_path, "w") as f:
        f.write("# Biomedical Entity Resolution Evaluation Report\n\n")
        f.write(f"**Experiment Run ID:** `{run_dir.name}`  \n")
        f.write("**Status:** Completed ✅  \n")
        f.write("**Ground Truth Size:** 31 cases  \n\n")
        
        f.write("## 1. End-to-End Pipeline Performance\n")
        f.write("| Metric | Score |\n")
        f.write("| --- | --- |\n")
        f.write(f"| **Accuracy** | {overall['accuracy']:.4f} |\n")
        f.write(f"| **Precision** | {overall['precision']:.4f} |\n")
        f.write(f"| **Recall** | {overall['recall']:.4f} |\n")
        f.write(f"| **F1-Score** | {overall['f1']:.4f} |\n\n")
        
        f.write("## 2. Performance by Ontology Source\n")
        f.write("| Ontology | Accuracy | Precision | Recall | F1-Score |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for ont, met in pipeline_results["ontology_metrics"].items():
            f.write(f"| **{ont}** | {met['accuracy']:.4f} | {met['precision']:.4f} | {met['recall']:.4f} | {met['f1']:.4f} |\n")
        f.write("\n")
        
        f.write("## 3. Retrieval Search Strategy Benchmark\n")
        f.write("| Strategy | Hit@1 | Hit@5 | Hit@10 | MRR |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for strat, met in retrieval_metrics.items():
            f.write(f"| **{strat.upper()}** | {met['hit_at_1']:.4f} | {met['hit_at_5']:.4f} | {met['hit_at_10']:.4f} | {met['mrr']:.4f} |\n")
        f.write("\n")
        
        f.write("## 4. Embedding Model Benchmark (Cosine Similarity)\n")
        f.write("| Model Name | Hit@1 | Hit@5 | Hit@10 | MRR |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for model_name, met in embedding_metrics.items():
            f.write(f"| **{model_name.split('/')[-1]}** | {met['hit_at_1']:.4f} | {met['hit_at_5']:.4f} | {met['hit_at_10']:.4f} | {met['mrr']:.4f} |\n")
        f.write("\n")
        
        f.write("## 5. Confidence Calibration\n")
        f.write("| Confidence Bin | Total Samples | Correct | Actual Accuracy |\n")
        f.write("| --- | --- | --- | --- |\n")
        for conf_bin, details in pipeline_results["calibration"].items():
            f.write(f"| **{conf_bin}** | {details['total']} | {details['correct']} | {details['accuracy']:.4f} |\n")
        f.write("\n")
        
        f.write("## 6. Visualization Figures\n")
        f.write("Find figures in `reports/figures/`:\n")
        f.write("- `retrieval_comparison.png`  \n")
        f.write("- `ontology_performance.png`  \n")
        f.write("- `confidence_calibration.png`  \n")
        f.write("- `embedding_comparison.png`  \n")
        
    print(f"Summary markdown report written to {summary_report_path}")
    print("=" * 60)
    print("🎉 BENCHMARK RUN COMPLETED SUCCESSFULY!")
    print("=" * 60)

if __name__ == "__main__":
    run_benchmark()

import sys
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"

# Set premium dark/minimalist aesthetic for charts
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 14,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.titlesize": 16,
    "figure.figsize": (8, 5)
})

PRIMARY_COLOR = "#10a37f"  # ChatGPT Emerald
SECONDARY_COLOR = "#fb923c" # Accent Orange
DARK_BG = "#212121"

def plot_retrieval_comparison(retrieval_results: dict, output_dir: Path = FIGURES_DIR) -> Path:
    """
    Plots a comparison of retrieval search strategies (Lexical vs Vector vs Hybrid).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    data = []
    for strategy, metrics in retrieval_results.items():
        for metric_name, val in metrics.items():
            # Format metric name for labels
            lbl = metric_name.replace("_", " ").title()
            data.append({
                "Strategy": strategy.capitalize(),
                "Metric": lbl,
                "Value": val
            })
            
    df = pd.DataFrame(data)
    
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(
        data=df,
        x="Metric",
        y="Value",
        hue="Strategy",
        palette=["#38bdf8", "#fb7185", "#34d399"],
        ax=ax
    )
    
    ax.set_ylim(0, 1.05)
    ax.set_title("Retrieval Strategy Comparison (Hit Rate & MRR)", pad=15)
    ax.set_ylabel("Score")
    ax.set_xlabel("")
    plt.legend(title="Search Strategy", loc="lower right")
    plt.tight_layout()
    
    out_path = output_dir / "retrieval_comparison.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path


def plot_accuracy_by_ontology(ontology_results: dict, output_dir: Path = FIGURES_DIR) -> Path:
    """
    Plots entity resolution accuracy and F1 score by ontology source.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    data = []
    for ont, metrics in ontology_results.items():
        data.append({
            "Ontology": ont,
            "Metric": "Accuracy",
            "Value": metrics["accuracy"]
        })
        data.append({
            "Ontology": ont,
            "Metric": "F1-Score",
            "Value": metrics["f1"]
        })
        
    df = pd.DataFrame(data)
    
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(
        data=df,
        x="Ontology",
        y="Value",
        hue="Metric",
        palette=["#a78bfa", "#4ade80"],
        ax=ax
    )
    
    ax.set_ylim(0, 1.05)
    ax.set_title("Entity Resolution Performance by Ontology", pad=15)
    ax.set_ylabel("Score")
    ax.set_xlabel("Ontology / Knowledge Base")
    plt.legend(loc="lower right")
    plt.tight_layout()
    
    out_path = output_dir / "ontology_performance.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path


def plot_confidence_calibration(calibration_bins: dict, output_dir: Path = FIGURES_DIR) -> Path:
    """
    Plots the confidence calibration curve.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    bin_labels = list(calibration_bins.keys())
    # Find midpoints of bins for x-axis representation
    midpoints = []
    accuracies = []
    
    for lbl, data in calibration_bins.items():
        if "-" in lbl:
            low, high = map(float, lbl.split("-"))
            midpoints.append((low + high) / 2)
        else:
            midpoints.append(0.95)
        accuracies.append(data["accuracy"])
        
    fig, ax = plt.subplots(figsize=(6, 5))
    
    # Plot perfect calibration diagonal line
    ax.plot([0, 1], [0, 1], "--", color="gray", label="Perfect Calibration")
    
    # Plot empirical calibration
    ax.plot(midpoints, accuracies, "o-", color=PRIMARY_COLOR, linewidth=2, markersize=8, label="Empirical")
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Mean Predicted Confidence")
    ax.set_ylabel("Actual Accuracy")
    ax.set_title("Confidence Calibration Curve", pad=15)
    plt.legend(loc="upper left")
    plt.tight_layout()
    
    out_path = output_dir / "confidence_calibration.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path


def plot_embedding_model_comparison(embedding_results: dict, output_dir: Path = FIGURES_DIR) -> Path:
    """
    Plots a comparison of embedding models across Hit Rate and MRR.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    data = []
    for model_name, metrics in embedding_results.items():
        # Shorten HuggingFace model names for neatness
        short_name = model_name.split("/")[-1]
        for metric_name, val in metrics.items():
            lbl = metric_name.replace("_", " ").title()
            data.append({
                "Model": short_name,
                "Metric": lbl,
                "Value": val
            })
            
    df = pd.DataFrame(data)
    
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(
        data=df,
        x="Metric",
        y="Value",
        hue="Model",
        palette=["#f43f5e", "#0ea5e9"],
        ax=ax
    )
    
    ax.set_ylim(0, 1.05)
    ax.set_title("Embedding Model Retrieval Comparison", pad=15)
    ax.set_ylabel("Score")
    ax.set_xlabel("")
    plt.legend(title="Embedding Model", loc="lower right")
    plt.tight_layout()
    
    out_path = output_dir / "embedding_comparison.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path

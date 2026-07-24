import sys
from pathlib import Path

# Add project root to path if not present
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.ingestion.download_hgnc import run_hgnc_ingestion
from src.ingestion.download_mesh import run_mesh_ingestion
from src.ingestion.download_rxnorm import run_rxnorm_ingestion

def main():
    print("=" * 60)
    print("STARTING BIOMEDICAL ENTITY RESOLUTION DATA INGESTION PIPELINE")
    print("=" * 60)
    
    # 1. HGNC Ingestion
    print("\n--- [1/3] Ingesting HGNC (Genes) ---")
    try:
        run_hgnc_ingestion()
    except Exception as e:
        print(f"Error during HGNC ingestion: {e}")
        
    # 2. MeSH Ingestion
    print("\n--- [2/3] Ingesting MeSH (Diseases & Anatomy) ---")
    try:
        run_mesh_ingestion()
    except Exception as e:
        print(f"Error during MeSH ingestion: {e}")
        
    # 3. RxNorm Ingestion
    print("\n--- [3/3] Ingesting RxNorm (Medications) ---")
    try:
        run_rxnorm_ingestion()
    except Exception as e:
        print(f"Error during RxNorm ingestion: {e}")
        
    print("\n" + "=" * 60)
    print("DATA INGESTION PIPELINE COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()

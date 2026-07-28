import sys
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Mock torchvision before other imports
import src.utils.mock_torchvision

from src.entity_resolution.pipeline import BiomedicalEntityResolverPipeline

def main():
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = "Patients diagnosed with MI were given Tylenol. The TP53 mutation was also observed."

    print("=" * 80)
    print("BIOMEDICAL ENTITY RESOLUTION PIPELINE")
    print(f"INPUT TEXT: '{text}'")
    print("=" * 80)
    
    print("\nInitializing Pipeline (loading lookup dictionary)...")
    pipeline = BiomedicalEntityResolverPipeline()
    
    print("\nResolving entities...")
    results = pipeline.resolve_text(text)
    
    print("\nResolved JSON Output:")
    print(json.dumps(results, indent=2))
    print("=" * 80)

if __name__ == "__main__":
    main()

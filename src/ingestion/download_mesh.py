import os
import requests
import zipfile
import pandas as pd
from tqdm import tqdm
from pathlib import Path
import xml.etree.ElementTree as ET

# Constants
MESH_URL = "https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.zip"
PROJECT_DIR = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_DIR / "data" / "processed"
CACHE_DIR = PROJECT_DIR / "data" / "ontology_cache"

def download_mesh(force: bool = False) -> Path:
    """
    Downloads the MeSH descriptor ZIP dataset.
    
    Args:
        force (bool): If True, downloads even if cached.
        
    Returns:
        Path: Path to the downloaded raw zip file.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    zip_path = CACHE_DIR / "desc2026.zip"
    
    if zip_path.exists() and not force:
        print(f"[MeSH] Using cached file: {zip_path}")
        return zip_path
        
    print(f"[MeSH] Downloading MeSH descriptors from {MESH_URL}...")
    response = requests.get(MESH_URL, stream=True)
    
    # Try 2026 first, fallback to 2025 if 404 occurs
    if response.status_code == 404:
        fallback_url = MESH_URL.replace("desc2026", "desc2025")
        print(f"[MeSH] desc2026.zip not found, falling back to: {fallback_url}")
        response = requests.get(fallback_url, stream=True)
        zip_path = CACHE_DIR / "desc2025.zip"
        
    response.raise_for_status()
    
    total_size = int(response.headers.get("content-length", 0))
    block_size = 1024 * 1024  # 1MB
    
    with open(zip_path, "wb") as f, tqdm(
        total=total_size, unit="iB", unit_scale=True, desc="MeSH"
    ) as progress_bar:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            f.write(data)
            
    print(f"[MeSH] Saved raw download to {zip_path}")
    return zip_path

def validate_mesh(zip_path: Path) -> bool:
    """
    Validates that the downloaded file is a valid MeSH zip package containing XML.
    """
    print(f"[MeSH] Validating {zip_path}...")
    if not zip_path.exists():
        print(f"[MeSH] Validation failed: File does not exist.")
        return False
        
    if zip_path.stat().st_size < 5_000_000:  # Expect > 5MB zipped
        print(f"[MeSH] Validation failed: File size too small ({zip_path.stat().st_size} bytes).")
        return False
        
    # Check zip integrity and presence of XML file
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            infolist = zf.infolist()
            has_xml = any(info.filename.endswith('.xml') for info in infolist)
            if not has_xml:
                print(f"[MeSH] Validation failed: No XML file found inside ZIP.")
                return False
    except Exception as e:
        print(f"[MeSH] Validation failed: Invalid zip archive. Error: {e}")
        return False
        
    print("[MeSH] Validation successful!")
    return True

def process_mesh(zip_path: Path) -> Path:
    """
    Parses the XML from the zip archive directly (without fully extracting to disk)
    and saves the relevant Disease and Anatomy concepts to Parquet.
    """
    print(f"[MeSH] Parsing descriptors from ZIP archive...")
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    processed_path = PROCESSED_DATA_DIR / "mesh.parquet"
    
    records = []
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Find the XML filename inside the zip
        xml_filename = next(name for name in zf.namelist() if name.endswith('.xml'))
        
        with zf.open(xml_filename) as xml_file:
            # We use iterparse to save memory and process XML elements incrementally
            context = ET.iterparse(xml_file, events=('start', 'end'))
            event, root = next(context)
            
            descriptor_ui = None
            descriptor_name = None
            synonyms = set()
            tree_numbers = []
            
            # Keep track of path tags to know node context
            path = []
            
            in_descriptor_ui = False
            in_descriptor_name = False
            in_term_name = False
            
            for event, elem in context:
                tag = elem.tag
                
                if event == 'start':
                    path.append(tag)
                    if tag == 'DescriptorRecord':
                        descriptor_ui = None
                        descriptor_name = None
                        synonyms = set()
                        tree_numbers = []
                    elif tag == 'DescriptorUI' and len(path) >= 2 and path[-2] == 'DescriptorRecord':
                        in_descriptor_ui = True
                    elif tag == 'String' and len(path) >= 3:
                        parent_tag = path[-2]
                        grandparent_tag = path[-3]
                        if parent_tag == 'DescriptorName' and grandparent_tag == 'DescriptorRecord':
                            in_descriptor_name = True
                        elif parent_tag == 'Term' and 'Concept' in path:
                            in_term_name = True
                            
                elif event == 'end':
                    if tag == 'DescriptorRecord':
                        # Filter for Diseases ('C') and Anatomy ('A') tree numbers
                        is_biomedical = any(tn.startswith(('A', 'C')) for tn in tree_numbers)
                        
                        # Add record if it matches biomedical categories
                        if descriptor_ui and descriptor_name and is_biomedical:
                            # Classify entity_type
                            if any(tn.startswith('C') for tn in tree_numbers):
                                entity_type = "Disease"
                            else:
                                entity_type = "Anatomy"
                                
                            records.append({
                                "identifier": f"MESH:{descriptor_ui}",
                                "canonical_name": descriptor_name,
                                "description": f"MeSH heading under tree numbers: {', '.join(tree_numbers)}",
                                "synonyms": "|".join(sorted(synonyms - {descriptor_name})),
                                "entity_type": entity_type,
                                "source": "MeSH"
                            })
                            
                        # Clear processed element to free memory
                        root.clear()
                        
                    elif tag == 'DescriptorUI' and in_descriptor_ui:
                        descriptor_ui = elem.text
                        in_descriptor_ui = False
                    elif tag == 'String':
                        if in_descriptor_name:
                            descriptor_name = elem.text
                            in_descriptor_name = False
                        elif in_term_name:
                            if elem.text:
                                synonyms.add(elem.text)
                            in_term_name = False
                    elif tag == 'TreeNumber':
                        if elem.text:
                            tree_numbers.append(elem.text)
                            
                    if path:
                        path.pop()

                    
    # Convert to DataFrame
    df = pd.DataFrame(records)
    print(f"[MeSH] Total parsed biomedical records: {len(df)}")
    
    # Deduplicate and save
    df = df.drop_duplicates(subset=["identifier"])
    df.to_parquet(processed_path, index=False)
    
    print(f"[MeSH] Processed data saved to {processed_path}")
    return processed_path

def run_mesh_ingestion(force: bool = False):
    """
    Runs the full MeSH ingestion pipeline.
    """
    zip_file = download_mesh(force=force)
    if validate_mesh(zip_file):
        process_mesh(zip_file)
        print("[MeSH] Ingestion pipeline completed successfully.")
    else:
        raise ValueError("[MeSH] Downloaded file validation failed.")

if __name__ == "__main__":
    run_mesh_ingestion()

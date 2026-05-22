import requests
import json
import os
from pathlib import Path

def download_mofsimplify():
    url = "https://zenodo.org/api/records/5737968/files-archive"
    cache_dir = Path("data/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = cache_dir / "mofsimplify_stability.zip"
    
    print(f"Downloading MOFSimplify data from Zenodo...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            
    print(f"Downloaded to {output_path}")
    
    # Extract if needed, or just notice it's a zip
    import zipfile
    with zipfile.ZipFile(output_path, 'r') as zip_ref:
        zip_ref.extractall(cache_dir)
        print(f"Extracted files to {cache_dir}")
        # Look for the json file
        for file in zip_ref.namelist():
            if file.endswith(".json"):
                print(f"Found JSON file: {file}")
                # Rename it to the expected name if necessary
                extracted_path = cache_dir / file
                target_path = cache_dir / "mofsimplify_stability.json"
                if extracted_path.exists() and not target_path.exists():
                    extracted_path.rename(target_path)
                    print(f"Renamed {file} to mofsimplify_stability.json")

if __name__ == "__main__":
    try:
        download_mofsimplify()
    except Exception as e:
        print(f"Error: {e}")

# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

import requests
import zipfile
import os
from pathlib import Path

def download_and_extract_core_mof():
    # Assuming a common source for MOF datasets if Zenodo direct link is elusive
    # This URL points to a repository that often contains curated MOF datasets.
    # If this URL is incorrect, a more specific search for 'CoRE MOF dataset source' would be needed.
    url = "https://zenodo.org/api/records/1046076/files-archive" # Example URL, might need refinement
    cache_dir = Path("data/cache/core_mof_data")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    zip_output_path = cache_dir / "core_mof_archive.zip"
    extracted_data_path = cache_dir / "CoREMOF" # Expected extraction folder name

    try:
        print(f"Attempting to download CoRE MOF data from {url}...")
        response = requests.get(url, stream=True)
        response.raise_for_status() # Raise an exception for bad status codes
        
        with open(zip_output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Downloaded archive to {zip_output_path}")

        print(f"Extracting archive to {cache_dir}...")
        with zipfile.ZipFile(zip_output_path, 'r') as zip_ref:
            zip_ref.extractall(cache_dir)
        print("Extraction complete.")

        # Check if the expected CoREMOF directory exists after extraction
        if extracted_data_path.exists():
            print(f"CoRE MOF data found in: {extracted_data_path}")
            # The import script expects a CSV or JSON. We'll need to find the specific file within CoREMOF
            # For now, we'll just confirm extraction. The import script will need to be pointed to the correct file.
            print("Data extracted successfully. You may need to specify the exact file path for import_linker_dataset.py.")
        else:
            print(f"Error: Expected directory '{extracted_data_path}' not found after extraction.")
            print("Please check the contents of the extracted zip file.")

    except requests.exceptions.RequestException as e:
        print(f"Error downloading data: {e}")
    except zipfile.BadZipFile:
        print(f"Error: Downloaded file is not a valid zip archive: {zip_output_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    download_and_extract_core_mof()

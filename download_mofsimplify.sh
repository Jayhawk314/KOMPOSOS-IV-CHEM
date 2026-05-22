#!/bin/bash
# Download MOFSimplify stability data from Zenodo

echo "Downloading MOFSimplify stability data..."
echo "Source: https://zenodo.org/records/5737968"
echo ""

# Create cache directory
mkdir -p data/cache

# Download the JSON file
# Note: The exact filename might vary - check Zenodo page
curl -L -o data/cache/mofsimplify_stability.json \
  "https://zenodo.org/api/records/5737968/files-archive"

echo ""
echo "Download complete!"
echo "File: data/cache/mofsimplify_stability.json"
echo ""
echo "To verify:"
echo "  python -c 'import json; print(len(json.load(open(\"data/cache/mofsimplify_stability.json\"))))'"

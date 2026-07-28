# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""BOM / materials-list ingestion: free-form input in, honest resolution out."""

from ingest.bom_ingest import (  # noqa: F401
    BOMLine,
    IngestResult,
    ResolvedMaterial,
    ingest_bom,
    parse_bom_text,
    resolve_material,
)

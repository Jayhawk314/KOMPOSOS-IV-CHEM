"""
PFAS Compliance Report Generator
==================================

Generates structured compliance reports for enterprise customers.
Wires together existing PFAS screening, replacement scoring, and
compatibility modules into a single auditable deliverable.
"""

from reports.pfas_report import (
    PFASComplianceReport,
    MaterialInput,
    ReportData,
)

__all__ = [
    'PFASComplianceReport',
    'MaterialInput',
    'ReportData',
]

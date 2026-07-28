# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
MITRE ATT&CK Framework Integration

Maps MITRE ATT&CK techniques to category-theoretic objects and morphisms.
Attack chains become composed morphisms that must satisfy compositional constraints.

MITRE ATT&CK v18.1 (2025):
- 14 Tactics (high-level objectives)
- 270+ Techniques (methods to achieve tactics)
- 500+ Sub-techniques (specific implementations)

Key insight: Not all technique compositions are valid.
For example: initial_access ∘ privilege_escalation is valid
But: exfiltration ∘ initial_access violates temporal ordering

This module encodes these compositional constraints as a category.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum


class MITRETactic(Enum):
    """MITRE ATT&CK Tactics (14 total)"""
    RECONNAISSANCE = "TA0043"
    RESOURCE_DEVELOPMENT = "TA0042"
    INITIAL_ACCESS = "TA0001"
    EXECUTION = "TA0002"
    PERSISTENCE = "TA0003"
    PRIVILEGE_ESCALATION = "TA0004"
    DEFENSE_EVASION = "TA0005"
    CREDENTIAL_ACCESS = "TA0006"
    DISCOVERY = "TA0007"
    LATERAL_MOVEMENT = "TA0008"
    COLLECTION = "TA0009"
    COMMAND_AND_CONTROL = "TA0011"
    EXFILTRATION = "TA0010"
    IMPACT = "TA0040"


@dataclass
class ATTACKTechnique:
    """
    A single MITRE ATT&CK technique.

    In category theory: This is an object in the Attack category.
    Morphisms between techniques represent valid transitions in attack chains.
    """
    technique_id: str  # e.g., "T1566" (Phishing)
    name: str
    tactics: List[MITRETactic]  # Which tactics this technique implements
    description: str
    platforms: List[str]  # Windows, Linux, macOS, etc.
    data_sources: List[str]  # Detection data sources

    # Compositional constraints
    requires_privileges: Set[str]  # e.g., {"User", "Administrator"}
    grants_privileges: Set[str]    # What privileges this technique can obtain

    # Detection signatures
    observables: Dict[str, List[str]]  # {"process": ["powershell.exe"], "network": [...]}

    def __hash__(self):
        return hash(self.technique_id)

    def __eq__(self, other):
        return isinstance(other, ATTACKTechnique) and self.technique_id == other.technique_id


class MITREDatabase:
    """
    MITRE ATT&CK knowledge base with compositional constraints.

    This is the "graph database" for cybersecurity, analogous to UniProt for proteins.
    But unlike proteins, we have EXACT compositional rules:
    - Privilege escalation requires initial access first
    - Exfiltration requires collection first
    - etc.
    """

    def __init__(self, environment=None):
        self.techniques: Dict[str, ATTACKTechnique] = {}
        self.valid_compositions: Set[Tuple[str, str]] = set()  # (technique1, technique2) pairs
        self.tactic_ordering: Dict[MITRETactic, int] = {}
        self.environment = environment

        self._initialize_mitre_database()
        self._initialize_composition_rules()

    def _initialize_mitre_database(self):
        """Load MITRE ATT&CK techniques — STIX first, hardcoded fallback."""
        loaded = self._try_load_stix()
        if not loaded:
            self._initialize_hardcoded_database()
        # Always merge custom crypto techniques (not in official MITRE)
        self._initialize_crypto_techniques()

    def _try_load_stix(self) -> bool:
        """Attempt to load techniques from official STIX 2.1 data."""
        try:
            from cyber.mitre_stix_loader import MITRESTIXLoader
            loader = MITRESTIXLoader()
            # Try to fetch if no cache exists (non-blocking if offline)
            loader.fetch_and_cache()
            stix_techniques = loader.load_techniques()
            if len(stix_techniques) < 50:
                return False

            for st in stix_techniques:
                tactic_enums = []
                for tname in st.tactics:
                    try:
                        tactic_enums.append(MITRETactic[tname])
                    except KeyError:
                        pass
                if not tactic_enums:
                    continue

                self.techniques[st.technique_id] = ATTACKTechnique(
                    technique_id=st.technique_id,
                    name=st.name,
                    tactics=tactic_enums,
                    description=st.description,
                    platforms=st.platforms,
                    data_sources=st.data_sources,
                    requires_privileges=self._infer_required_privileges(tactic_enums),
                    grants_privileges=self._infer_granted_privileges(tactic_enums),
                    observables={},
                )
            return True
        except Exception:
            return False

    @staticmethod
    def _infer_required_privileges(tactics: List[MITRETactic]) -> Set[str]:
        """Infer privilege requirements from tactics."""
        if MITRETactic.INITIAL_ACCESS in tactics or MITRETactic.RECONNAISSANCE in tactics:
            return set()
        if MITRETactic.PRIVILEGE_ESCALATION in tactics:
            return {"User"}
        if MITRETactic.CREDENTIAL_ACCESS in tactics:
            return {"User"}
        if MITRETactic.LATERAL_MOVEMENT in tactics:
            return {"Administrator"}
        return {"User"}

    @staticmethod
    def _infer_granted_privileges(tactics: List[MITRETactic]) -> Set[str]:
        """Infer granted privileges from tactics."""
        if MITRETactic.INITIAL_ACCESS in tactics:
            return {"User"}
        if MITRETactic.PRIVILEGE_ESCALATION in tactics:
            return {"Administrator", "SYSTEM", "root"}
        if MITRETactic.CREDENTIAL_ACCESS in tactics:
            return {"Administrator"}
        return {"User"}

    def _initialize_crypto_techniques(self):
        """Load custom TCRYPTO_001-008 techniques (not in official MITRE)."""
        self.techniques["TCRYPTO_001"] = ATTACKTechnique(
            technique_id="TCRYPTO_001",
            name="Weak RSA Key Exploitation",
            tactics=[MITRETactic.CREDENTIAL_ACCESS],
            description="Exploit weak RSA keys (small factors, close primes, smooth p-1) to recover private keys",
            platforms=["Windows", "Linux", "macOS", "Network"],
            data_sources=["Certificate", "Network Traffic"],
            requires_privileges={"User"},
            grants_privileges={"Administrator"},
            observables={"crypto": ["weak_key_detected", "small_factor_found", "fermat_factorization"]}
        )

        self.techniques["TCRYPTO_002"] = ATTACKTechnique(
            technique_id="TCRYPTO_002",
            name="RSA Common Factor Attack",
            tactics=[MITRETactic.CREDENTIAL_ACCESS],
            description="Batch GCD attack on RSA key sets to find shared prime factors",
            platforms=["Windows", "Linux", "macOS", "Network"],
            data_sources=["Certificate", "Key Store"],
            requires_privileges={"User"},
            grants_privileges={"Administrator"},
            observables={"crypto": ["common_factor_found", "batch_gcd_attack", "shared_prime_detected"]}
        )

        self.techniques["TCRYPTO_003"] = ATTACKTechnique(
            technique_id="TCRYPTO_003",
            name="ECDSA Nonce Reuse Exploit",
            tactics=[MITRETactic.CREDENTIAL_ACCESS],
            description="Recover ECDSA private key from signatures with reused or biased nonces",
            platforms=["Windows", "Linux", "macOS", "Network"],
            data_sources=["Network Traffic", "Application Log"],
            requires_privileges={"User"},
            grants_privileges={"Administrator"},
            observables={"crypto": ["nonce_reuse_detected", "signature_r_collision", "nonce_bias_detected"]}
        )

        self.techniques["TCRYPTO_004"] = ATTACKTechnique(
            technique_id="TCRYPTO_004",
            name="Weak Elliptic Curve Attack",
            tactics=[MITRETactic.CREDENTIAL_ACCESS],
            description="Exploit weak or non-standard elliptic curve parameters to recover keys",
            platforms=["Windows", "Linux", "macOS", "Network"],
            data_sources=["Certificate", "Network Traffic"],
            requires_privileges={"User"},
            grants_privileges={"Administrator"},
            observables={"crypto": ["weak_curve_detected", "anomalous_curve", "small_subgroup_attack"]}
        )

        self.techniques["TCRYPTO_005"] = ATTACKTechnique(
            technique_id="TCRYPTO_005",
            name="Certificate Forgery",
            tactics=[MITRETactic.DEFENSE_EVASION, MITRETactic.PERSISTENCE],
            description="Forge X.509 certificates using recovered private keys or CA compromise",
            platforms=["Windows", "Linux", "macOS", "Cloud", "Network"],
            data_sources=["Certificate", "Network Traffic"],
            requires_privileges={"Administrator"},
            grants_privileges={"SYSTEM"},
            observables={"crypto": ["forged_certificate", "unauthorized_cert_issuance", "ct_log_anomaly"]}
        )

        self.techniques["TCRYPTO_006"] = ATTACKTechnique(
            technique_id="TCRYPTO_006",
            name="Quantum Harvest (Store Now, Decrypt Later)",
            tactics=[MITRETactic.COLLECTION, MITRETactic.RECONNAISSANCE],
            description="Capture encrypted traffic for future quantum decryption (SNDL/harvest-now-decrypt-later)",
            platforms=["Network", "Cloud"],
            data_sources=["Network Traffic"],
            requires_privileges=set(),
            grants_privileges=set(),
            observables={"crypto": ["bulk_traffic_capture", "passive_interception", "quantum_vulnerable_cipher"]}
        )

        self.techniques["TCRYPTO_007"] = ATTACKTechnique(
            technique_id="TCRYPTO_007",
            name="CA/PKI Compromise",
            tactics=[MITRETactic.INITIAL_ACCESS, MITRETactic.PERSISTENCE],
            description="Compromise Certificate Authority or PKI infrastructure to issue rogue certificates",
            platforms=["Windows", "Linux", "Cloud", "Network"],
            data_sources=["Certificate", "Application Log"],
            requires_privileges={"Administrator"},
            grants_privileges={"SYSTEM"},
            observables={"crypto": ["ca_compromise", "rogue_root_cert", "pki_infrastructure_breach"]}
        )

        self.techniques["TCRYPTO_008"] = ATTACKTechnique(
            technique_id="TCRYPTO_008",
            name="Cryptographic Downgrade Attack",
            tactics=[MITRETactic.DEFENSE_EVASION],
            description="Force use of weak cryptographic algorithms via protocol downgrade (POODLE, DROWN, etc.)",
            platforms=["Windows", "Linux", "macOS", "Network"],
            data_sources=["Network Traffic"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"crypto": ["protocol_downgrade", "weak_cipher_negotiated", "tls_version_rollback"]}
        )

    def _initialize_hardcoded_database(self):
        """Fallback: Load hardcoded MITRE ATT&CK techniques."""

        # Initial Access techniques
        self.techniques["T1566"] = ATTACKTechnique(
            technique_id="T1566",
            name="Phishing",
            tactics=[MITRETactic.INITIAL_ACCESS],
            description="Adversaries may send phishing messages to gain access",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Email Gateway", "Network Traffic"],
            requires_privileges=set(),  # No privileges needed
            grants_privileges={"User"},
            observables={
                "email": ["suspicious_attachment", "malicious_link"],
                "network": ["connection_to_known_phishing_domain"]
            }
        )

        self.techniques["T1190"] = ATTACKTechnique(
            technique_id="T1190",
            name="Exploit Public-Facing Application",
            tactics=[MITRETactic.INITIAL_ACCESS],
            description="Exploit software vulnerabilities in Internet-facing systems",
            platforms=["Windows", "Linux", "Network"],
            data_sources=["Application Log", "Web Application Firewall"],
            requires_privileges=set(),
            grants_privileges={"User", "System"},
            observables={
                "application": ["sql_injection", "buffer_overflow", "rce_attempt"],
                "network": ["abnormal_http_requests"]
            }
        )

        # Execution techniques
        self.techniques["T1059"] = ATTACKTechnique(
            technique_id="T1059",
            name="Command and Scripting Interpreter",
            tactics=[MITRETactic.EXECUTION],
            description="Execute commands via PowerShell, bash, Python, etc.",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Process", "Command"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={
                "process": ["powershell.exe", "cmd.exe", "bash", "python"],
                "command": ["encoded_command", "web_request"]
            }
        )

        # Privilege Escalation techniques
        self.techniques["T1068"] = ATTACKTechnique(
            technique_id="T1068",
            name="Exploitation for Privilege Escalation",
            tactics=[MITRETactic.PRIVILEGE_ESCALATION],
            description="Exploit software vulnerabilities to elevate privileges",
            platforms=["Windows", "Linux"],
            data_sources=["Process", "Windows Event Logs"],
            requires_privileges={"User"},
            grants_privileges={"Administrator", "SYSTEM", "root"},
            observables={
                "process": ["suspicious_child_process"],
                "kernel": ["privilege_escalation_attempt"]
            }
        )

        self.techniques["T1078"] = ATTACKTechnique(
            technique_id="T1078",
            name="Valid Accounts",
            tactics=[MITRETactic.PRIVILEGE_ESCALATION, MITRETactic.PERSISTENCE,
                     MITRETactic.DEFENSE_EVASION, MITRETactic.INITIAL_ACCESS],
            description="Use legitimate credentials obtained via credential access",
            platforms=["Windows", "Linux", "macOS", "Cloud"],
            data_sources=["Authentication Logs", "Logon Session"],
            requires_privileges=set(),  # Can be used at any privilege level
            grants_privileges={"User", "Administrator", "SYSTEM"},
            observables={
                "authentication": ["anomalous_logon", "unusual_login_time", "impossible_travel"]
            }
        )

        # Credential Access techniques
        self.techniques["T1003"] = ATTACKTechnique(
            technique_id="T1003",
            name="OS Credential Dumping",
            tactics=[MITRETactic.CREDENTIAL_ACCESS],
            description="Dump credentials from operating system (LSASS, SAM, etc.)",
            platforms=["Windows", "Linux"],
            data_sources=["Process", "File", "Windows Registry"],
            requires_privileges={"Administrator", "SYSTEM"},
            grants_privileges={"Administrator"},  # Obtains creds for lateral movement
            observables={
                "process": ["mimikatz", "procdump", "lsass_access"],
                "file": ["ntds.dit", "sam_database"]
            }
        )

        # Lateral Movement techniques
        self.techniques["T1021"] = ATTACKTechnique(
            technique_id="T1021",
            name="Remote Services",
            tactics=[MITRETactic.LATERAL_MOVEMENT],
            description="Use remote services like RDP, SSH, SMB to move laterally",
            platforms=["Windows", "Linux"],
            data_sources=["Network Traffic", "Logon Session"],
            requires_privileges={"Administrator"},  # Need admin creds to move laterally
            grants_privileges={"Administrator"},
            observables={
                "network": ["rdp_connection", "smb_admin_share", "ssh_connection"],
                "authentication": ["network_logon"]
            }
        )

        # Collection techniques
        self.techniques["T1005"] = ATTACKTechnique(
            technique_id="T1005",
            name="Data from Local System",
            tactics=[MITRETactic.COLLECTION],
            description="Search local system for files of interest",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["File", "Process"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={
                "file": ["file_access", "directory_listing"],
                "process": ["suspicious_file_search"]
            }
        )

        # Command and Control techniques
        self.techniques["T1071"] = ATTACKTechnique(
            technique_id="T1071",
            name="Application Layer Protocol",
            tactics=[MITRETactic.COMMAND_AND_CONTROL],
            description="Use application layer protocols (HTTP, DNS) for C2",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Network Traffic"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={
                "network": ["beaconing", "dns_tunneling", "http_c2"]
            }
        )

        # Exfiltration techniques
        self.techniques["T1041"] = ATTACKTechnique(
            technique_id="T1041",
            name="Exfiltration Over C2 Channel",
            tactics=[MITRETactic.EXFILTRATION],
            description="Exfiltrate data over existing C2 channel",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Network Traffic"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={
                "network": ["large_outbound_transfer", "unusual_protocol_usage"]
            }
        )

        # Impact techniques
        self.techniques["T1486"] = ATTACKTechnique(
            technique_id="T1486",
            name="Data Encrypted for Impact",
            tactics=[MITRETactic.IMPACT],
            description="Encrypt data to disrupt availability (ransomware)",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["File", "Process"],
            requires_privileges={"User", "Administrator"},
            grants_privileges=set(),
            observables={
                "file": ["mass_file_encryption", "ransom_note"],
                "process": ["encryption_utility"]
            }
        )

        # =================================================================
        # v18.1 Additions: Cloud/SaaS Techniques (~15)
        # =================================================================

        self.techniques["T1078.004"] = ATTACKTechnique(
            technique_id="T1078.004",
            name="Valid Accounts: Cloud Accounts",
            tactics=[MITRETactic.INITIAL_ACCESS, MITRETactic.PERSISTENCE, MITRETactic.PRIVILEGE_ESCALATION],
            description="Adversaries may obtain and abuse credentials of cloud accounts to gain access",
            platforms=["Azure AD", "Google Workspace", "IaaS", "Office 365", "SaaS"],
            data_sources=["Logon Session", "User Account"],
            requires_privileges=set(),
            grants_privileges={"User", "Administrator"},
            observables={"authentication": ["cloud_logon_anomaly", "impossible_travel_cloud", "unusual_service_principal"]}
        )

        self.techniques["T1580"] = ATTACKTechnique(
            technique_id="T1580",
            name="Cloud Infrastructure Discovery",
            tactics=[MITRETactic.DISCOVERY],
            description="Adversaries may enumerate cloud infrastructure components like VMs, storage, and networks",
            platforms=["IaaS", "Azure AD", "Google Workspace"],
            data_sources=["Cloud Service", "Snapshot"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"cloud": ["api_enumeration", "resource_listing", "describe_instances"]}
        )

        self.techniques["T1530"] = ATTACKTechnique(
            technique_id="T1530",
            name="Data from Cloud Storage",
            tactics=[MITRETactic.COLLECTION],
            description="Adversaries may access data from improperly secured cloud storage",
            platforms=["IaaS", "SaaS"],
            data_sources=["Cloud Storage"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"cloud": ["s3_bucket_access", "blob_download", "storage_enumeration"]}
        )

        self.techniques["T1537"] = ATTACKTechnique(
            technique_id="T1537",
            name="Transfer Data to Cloud Account",
            tactics=[MITRETactic.EXFILTRATION],
            description="Adversaries may exfiltrate data by transferring it to another cloud account they control",
            platforms=["IaaS"],
            data_sources=["Cloud Storage", "Snapshot"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"cloud": ["cross_account_transfer", "snapshot_share", "ami_copy"]}
        )

        self.techniques["T1619"] = ATTACKTechnique(
            technique_id="T1619",
            name="Cloud Storage Object Discovery",
            tactics=[MITRETactic.DISCOVERY],
            description="Adversaries may enumerate objects in cloud storage to find sensitive data",
            platforms=["IaaS", "SaaS"],
            data_sources=["Cloud Storage"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"cloud": ["list_objects", "get_bucket_acl", "storage_enumeration"]}
        )

        self.techniques["T1648"] = ATTACKTechnique(
            technique_id="T1648",
            name="Serverless Execution",
            tactics=[MITRETactic.EXECUTION],
            description="Adversaries may abuse serverless computing for execution",
            platforms=["IaaS", "SaaS"],
            data_sources=["Application Log", "Cloud Service"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"cloud": ["lambda_invoke", "function_creation", "serverless_execution"]}
        )

        self.techniques["T1552.005"] = ATTACKTechnique(
            technique_id="T1552.005",
            name="Unsecured Credentials: Cloud Instance Metadata API",
            tactics=[MITRETactic.CREDENTIAL_ACCESS],
            description="Adversaries may access cloud instance metadata APIs to collect credentials",
            platforms=["IaaS"],
            data_sources=["Cloud Service"],
            requires_privileges={"User"},
            grants_privileges={"User", "Administrator"},
            observables={"cloud": ["metadata_api_access", "imds_request", "169.254.169.254"]}
        )

        self.techniques["T1550.001"] = ATTACKTechnique(
            technique_id="T1550.001",
            name="Use Alternate Authentication Material: Application Access Token",
            tactics=[MITRETactic.DEFENSE_EVASION, MITRETactic.LATERAL_MOVEMENT],
            description="Adversaries may use stolen application access tokens to bypass authentication",
            platforms=["Azure AD", "Office 365", "SaaS", "Google Workspace"],
            data_sources=["Web Credential"],
            requires_privileges=set(),
            grants_privileges={"User"},
            observables={"authentication": ["token_abuse", "oauth_token_reuse", "bearer_token_replay"]}
        )

        self.techniques["T1098.003"] = ATTACKTechnique(
            technique_id="T1098.003",
            name="Account Manipulation: Additional Cloud Roles",
            tactics=[MITRETactic.PERSISTENCE, MITRETactic.PRIVILEGE_ESCALATION],
            description="Adversaries may add additional roles or permissions to a cloud account",
            platforms=["Azure AD", "Google Workspace", "IaaS", "Office 365"],
            data_sources=["User Account"],
            requires_privileges={"Administrator"},
            grants_privileges={"Administrator"},
            observables={"cloud": ["role_assignment", "policy_change", "privilege_grant"]}
        )

        self.techniques["T1136.003"] = ATTACKTechnique(
            technique_id="T1136.003",
            name="Create Account: Cloud Account",
            tactics=[MITRETactic.PERSISTENCE],
            description="Adversaries may create a cloud account to maintain access",
            platforms=["Azure AD", "Google Workspace", "IaaS", "Office 365"],
            data_sources=["User Account"],
            requires_privileges={"Administrator"},
            grants_privileges={"User", "Administrator"},
            observables={"cloud": ["account_creation", "service_principal_created", "iam_user_created"]}
        )

        self.techniques["T1578"] = ATTACKTechnique(
            technique_id="T1578",
            name="Modify Cloud Compute Infrastructure",
            tactics=[MITRETactic.DEFENSE_EVASION],
            description="Adversaries may modify cloud compute infrastructure to evade defenses",
            platforms=["IaaS"],
            data_sources=["Cloud Service", "Instance"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"cloud": ["instance_modification", "security_group_change", "vpc_modification"]}
        )

        self.techniques["T1578.002"] = ATTACKTechnique(
            technique_id="T1578.002",
            name="Modify Cloud Compute Infrastructure: Create Cloud Instance",
            tactics=[MITRETactic.DEFENSE_EVASION],
            description="Adversaries may create a new instance in a region to evade defenses",
            platforms=["IaaS"],
            data_sources=["Instance"],
            requires_privileges={"User"},
            grants_privileges={"User", "Administrator"},
            observables={"cloud": ["instance_creation", "unusual_region", "compute_spin_up"]}
        )

        self.techniques["T1578.003"] = ATTACKTechnique(
            technique_id="T1578.003",
            name="Modify Cloud Compute Infrastructure: Delete Cloud Instance",
            tactics=[MITRETactic.DEFENSE_EVASION],
            description="Adversaries may delete cloud instances to remove forensic evidence",
            platforms=["IaaS"],
            data_sources=["Instance"],
            requires_privileges={"User"},
            grants_privileges=set(),
            observables={"cloud": ["instance_deletion", "resource_cleanup", "evidence_destruction"]}
        )

        self.techniques["T1562.007"] = ATTACKTechnique(
            technique_id="T1562.007",
            name="Impair Defenses: Disable or Modify Cloud Firewall",
            tactics=[MITRETactic.DEFENSE_EVASION],
            description="Adversaries may disable or modify cloud firewalls to allow malicious traffic",
            platforms=["IaaS"],
            data_sources=["Firewall"],
            requires_privileges={"Administrator"},
            grants_privileges=set(),
            observables={"cloud": ["firewall_rule_change", "security_group_modification", "nacl_change"]}
        )

        self.techniques["T1538"] = ATTACKTechnique(
            technique_id="T1538",
            name="Cloud Service Dashboard",
            tactics=[MITRETactic.DISCOVERY],
            description="Adversaries may use cloud service dashboards to discover resources and configurations",
            platforms=["Azure AD", "Google Workspace", "IaaS", "Office 365"],
            data_sources=["Logon Session"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"cloud": ["console_login", "dashboard_access", "portal_activity"]}
        )

        # =================================================================
        # v18.1 Additions: Container/K8s Techniques (~8)
        # =================================================================

        self.techniques["T1610"] = ATTACKTechnique(
            technique_id="T1610",
            name="Deploy Container",
            tactics=[MITRETactic.DEFENSE_EVASION, MITRETactic.EXECUTION],
            description="Adversaries may deploy containers to execute malicious code or evade defenses",
            platforms=["Containers"],
            data_sources=["Container", "Pod"],
            requires_privileges={"User"},
            grants_privileges={"User", "Administrator"},
            observables={"container": ["pod_creation", "container_deploy", "unusual_image"]}
        )

        self.techniques["T1611"] = ATTACKTechnique(
            technique_id="T1611",
            name="Escape to Host",
            tactics=[MITRETactic.PRIVILEGE_ESCALATION],
            description="Adversaries may escape container environments to access the underlying host",
            platforms=["Containers"],
            data_sources=["Container", "Process"],
            requires_privileges={"User"},
            grants_privileges={"Administrator", "root"},
            observables={"container": ["container_escape", "host_mount", "privileged_container"]}
        )

        self.techniques["T1609"] = ATTACKTechnique(
            technique_id="T1609",
            name="Container Administration Command",
            tactics=[MITRETactic.EXECUTION],
            description="Adversaries may abuse container admin tools like kubectl to execute commands",
            platforms=["Containers"],
            data_sources=["Command", "Process"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"container": ["kubectl_exec", "docker_exec", "container_command"]}
        )

        self.techniques["T1613"] = ATTACKTechnique(
            technique_id="T1613",
            name="Container and Resource Discovery",
            tactics=[MITRETactic.DISCOVERY],
            description="Adversaries may enumerate containers and Kubernetes resources",
            platforms=["Containers"],
            data_sources=["Container", "Pod"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"container": ["pod_listing", "service_enumeration", "namespace_discovery"]}
        )

        self.techniques["T1612"] = ATTACKTechnique(
            technique_id="T1612",
            name="Build Image on Host",
            tactics=[MITRETactic.DEFENSE_EVASION],
            description="Adversaries may build a container image on a host to evade image scanning defenses",
            platforms=["Containers"],
            data_sources=["Image", "Process"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"container": ["docker_build", "image_creation", "dockerfile_write"]}
        )

        self.techniques["T1525"] = ATTACKTechnique(
            technique_id="T1525",
            name="Implant Internal Image",
            tactics=[MITRETactic.PERSISTENCE],
            description="Adversaries may implant cloud or container images with malicious code",
            platforms=["Containers", "IaaS"],
            data_sources=["Image"],
            requires_privileges={"Administrator"},
            grants_privileges={"User", "Administrator"},
            observables={"container": ["image_modification", "registry_push", "backdoor_image"]}
        )

        self.techniques["T1552.007"] = ATTACKTechnique(
            technique_id="T1552.007",
            name="Unsecured Credentials: Container API",
            tactics=[MITRETactic.CREDENTIAL_ACCESS],
            description="Adversaries may gather credentials from the container API or service account tokens",
            platforms=["Containers"],
            data_sources=["Container"],
            requires_privileges={"User"},
            grants_privileges={"User", "Administrator"},
            observables={"container": ["service_account_token", "k8s_secret_access", "api_credential_read"]}
        )

        self.techniques["T1053.007"] = ATTACKTechnique(
            technique_id="T1053.007",
            name="Scheduled Task/Job: Container Orchestration Job",
            tactics=[MITRETactic.EXECUTION, MITRETactic.PERSISTENCE, MITRETactic.PRIVILEGE_ESCALATION],
            description="Adversaries may abuse container orchestration jobs (CronJobs) for persistent execution",
            platforms=["Containers"],
            data_sources=["Container", "Scheduled Job"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"container": ["cronjob_creation", "job_schedule", "orchestration_abuse"]}
        )

        # =================================================================
        # v18.1 Additions: CI/CD & Supply Chain Techniques (~10)
        # =================================================================

        self.techniques["T1195"] = ATTACKTechnique(
            technique_id="T1195",
            name="Supply Chain Compromise",
            tactics=[MITRETactic.INITIAL_ACCESS],
            description="Adversaries may manipulate products or delivery mechanisms to compromise targets",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["File"],
            requires_privileges=set(),
            grants_privileges={"User"},
            observables={"file": ["modified_installer", "tampered_package", "supply_chain_indicator"]}
        )

        self.techniques["T1195.001"] = ATTACKTechnique(
            technique_id="T1195.001",
            name="Supply Chain Compromise: Compromise Software Dependencies and Development Tools",
            tactics=[MITRETactic.INITIAL_ACCESS],
            description="Adversaries may compromise software dependencies to gain access to victim systems",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["File"],
            requires_privileges=set(),
            grants_privileges={"User"},
            observables={"file": ["dependency_modification", "build_tool_compromise", "malicious_library"]}
        )

        self.techniques["T1195.002"] = ATTACKTechnique(
            technique_id="T1195.002",
            name="Supply Chain Compromise: Compromise Software Supply Chain",
            tactics=[MITRETactic.INITIAL_ACCESS],
            description="Adversaries may compromise the software supply chain to distribute malicious code",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["File"],
            requires_privileges=set(),
            grants_privileges={"User", "Administrator"},
            observables={"file": ["update_hijack", "signing_compromise", "distribution_tampering"]}
        )

        self.techniques["T1195.003"] = ATTACKTechnique(
            technique_id="T1195.003",
            name="Supply Chain Compromise: Compromise Hardware Supply Chain",
            tactics=[MITRETactic.INITIAL_ACCESS],
            description="Adversaries may compromise hardware components to gain access",
            platforms=["Windows", "Linux"],
            data_sources=["File"],
            requires_privileges=set(),
            grants_privileges={"SYSTEM", "root"},
            observables={"file": ["firmware_modification", "hardware_implant", "uefi_compromise"]}
        )

        self.techniques["T1204.003"] = ATTACKTechnique(
            technique_id="T1204.003",
            name="User Execution: Malicious Image",
            tactics=[MITRETactic.EXECUTION],
            description="Adversaries may rely on users running malicious container images",
            platforms=["Containers"],
            data_sources=["Container", "Image"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"container": ["malicious_image_pull", "untrusted_registry", "image_execution"]}
        )

        self.techniques["T1072"] = ATTACKTechnique(
            technique_id="T1072",
            name="Software Deployment Tools",
            tactics=[MITRETactic.EXECUTION, MITRETactic.LATERAL_MOVEMENT],
            description="Adversaries may abuse software deployment tools to execute code across systems",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Process", "Application Log"],
            requires_privileges={"Administrator"},
            grants_privileges={"Administrator"},
            observables={"process": ["sccm_execution", "puppet_agent", "ansible_playbook", "chef_run"]}
        )

        self.techniques["T1554"] = ATTACKTechnique(
            technique_id="T1554",
            name="Compromise Client Software Binary",
            tactics=[MITRETactic.PERSISTENCE],
            description="Adversaries may modify client software binaries to establish persistence",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["File"],
            requires_privileges={"Administrator"},
            grants_privileges={"User"},
            observables={"file": ["binary_modification", "library_replacement", "client_backdoor"]}
        )

        # === ATT&CK v18 New Techniques (October 2025) ===

        self.techniques["T1059.013"] = ATTACKTechnique(
            technique_id="T1059.013",
            name="Command and Scripting Interpreter: Container CLI/API",
            tactics=[MITRETactic.EXECUTION],
            description="Adversaries may abuse container CLIs like docker and kubectl for execution",
            platforms=["Containers"],
            data_sources=["Command", "Process", "Container"],
            requires_privileges={"User"},
            grants_privileges={"User", "Administrator"},
            observables={"container": ["docker_cli", "kubectl_exec", "crictl_command", "api_server_exec"]}
        )

        self.techniques["T1677"] = ATTACKTechnique(
            technique_id="T1677",
            name="Poisoned Pipeline Execution",
            tactics=[MITRETactic.EXECUTION, MITRETactic.INITIAL_ACCESS],
            description="Adversaries may inject malicious code into CI/CD pipeline configurations to execute",
            platforms=["Windows", "Linux", "macOS", "Containers"],
            data_sources=["Application Log", "Process", "File"],
            requires_privileges={"User"},
            grants_privileges={"User", "Administrator", "SYSTEM"},
            observables={"process": ["pipeline_config_change", "cicd_job_creation", "build_script_modification"]}
        )

        self.techniques["T1676"] = ATTACKTechnique(
            technique_id="T1676",
            name="Linked Devices",
            tactics=[MITRETactic.PERSISTENCE, MITRETactic.LATERAL_MOVEMENT],
            description="Adversaries may abuse linked device features in messaging apps for persistence and lateral movement",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Application Log", "Process", "Network Traffic"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"process": ["device_linking_event", "messaging_app_sync", "cross_device_session"]}
        )

        self.techniques["T1059.004"] = ATTACKTechnique(
            technique_id="T1059.004",
            name="Command and Scripting Interpreter: Unix Shell",
            tactics=[MITRETactic.EXECUTION],
            description="Adversaries may abuse Unix shell commands for execution",
            platforms=["Linux", "macOS"],
            data_sources=["Command", "Process"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"process": ["bash_command", "sh_execution", "unix_shell"]}
        )

        self.techniques["T1059.006"] = ATTACKTechnique(
            technique_id="T1059.006",
            name="Command and Scripting Interpreter: Python",
            tactics=[MITRETactic.EXECUTION],
            description="Adversaries may abuse Python commands and scripts for execution",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Command", "Process"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"process": ["python_execution", "python_script", "python_import"]}
        )

        self.techniques["T1106"] = ATTACKTechnique(
            technique_id="T1106",
            name="Native API",
            tactics=[MITRETactic.EXECUTION],
            description="Adversaries may interact with the native OS API to execute behaviors",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Process", "OS API"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"process": ["api_call", "syscall", "native_function"]}
        )

        # =================================================================
        # v18.1 Additions: Identity/Auth Techniques (~10)
        # =================================================================

        self.techniques["T1556"] = ATTACKTechnique(
            technique_id="T1556",
            name="Modify Authentication Process",
            tactics=[MITRETactic.CREDENTIAL_ACCESS, MITRETactic.DEFENSE_EVASION, MITRETactic.PERSISTENCE],
            description="Adversaries may modify authentication mechanisms to access user credentials or enable access",
            platforms=["Windows", "Linux", "macOS", "Azure AD", "SaaS"],
            data_sources=["File", "Logon Session", "Process"],
            requires_privileges={"Administrator", "SYSTEM"},
            grants_privileges={"Administrator"},
            observables={"authentication": ["auth_module_change", "pam_modification", "ssp_dll_load"]}
        )

        self.techniques["T1556.001"] = ATTACKTechnique(
            technique_id="T1556.001",
            name="Modify Authentication Process: Domain Controller Authentication",
            tactics=[MITRETactic.CREDENTIAL_ACCESS, MITRETactic.DEFENSE_EVASION],
            description="Adversaries may patch domain controller authentication to capture credentials",
            platforms=["Windows"],
            data_sources=["File", "Process"],
            requires_privileges={"Administrator", "SYSTEM"},
            grants_privileges={"Administrator"},
            observables={"authentication": ["skeleton_key", "dc_password_filter", "lsass_patch"]}
        )

        self.techniques["T1556.002"] = ATTACKTechnique(
            technique_id="T1556.002",
            name="Modify Authentication Process: Password Filter DLL",
            tactics=[MITRETactic.CREDENTIAL_ACCESS, MITRETactic.DEFENSE_EVASION],
            description="Adversaries may register malicious password filter DLLs to capture plaintext passwords",
            platforms=["Windows"],
            data_sources=["File", "Windows Registry"],
            requires_privileges={"Administrator"},
            grants_privileges={"Administrator"},
            observables={"authentication": ["password_filter_dll", "registry_modification"]}
        )

        self.techniques["T1556.003"] = ATTACKTechnique(
            technique_id="T1556.003",
            name="Modify Authentication Process: Pluggable Authentication Modules",
            tactics=[MITRETactic.CREDENTIAL_ACCESS, MITRETactic.DEFENSE_EVASION, MITRETactic.PERSISTENCE],
            description="Adversaries may modify PAM to capture credentials or create backdoors",
            platforms=["Linux", "macOS"],
            data_sources=["File", "Logon Session"],
            requires_privileges={"root"},
            grants_privileges={"root"},
            observables={"authentication": ["pam_so_modification", "pam_config_change", "pam_backdoor"]}
        )

        self.techniques["T1556.004"] = ATTACKTechnique(
            technique_id="T1556.004",
            name="Modify Authentication Process: Network Device Authentication",
            tactics=[MITRETactic.CREDENTIAL_ACCESS, MITRETactic.DEFENSE_EVASION, MITRETactic.PERSISTENCE],
            description="Adversaries may use patches to network device OS to modify authentication",
            platforms=["Network"],
            data_sources=["File", "Logon Session"],
            requires_privileges={"Administrator"},
            grants_privileges={"Administrator"},
            observables={"authentication": ["network_device_patch", "ios_modification", "firmware_change"]}
        )

        self.techniques["T1556.005"] = ATTACKTechnique(
            technique_id="T1556.005",
            name="Modify Authentication Process: Reversible Encryption",
            tactics=[MITRETactic.CREDENTIAL_ACCESS, MITRETactic.DEFENSE_EVASION],
            description="Adversaries may enable reversible encryption for password storage to obtain credentials",
            platforms=["Windows"],
            data_sources=["Active Directory"],
            requires_privileges={"Administrator"},
            grants_privileges={"Administrator"},
            observables={"authentication": ["reversible_encryption_enabled", "ad_property_change"]}
        )

        self.techniques["T1556.006"] = ATTACKTechnique(
            technique_id="T1556.006",
            name="Modify Authentication Process: Multi-Factor Authentication",
            tactics=[MITRETactic.CREDENTIAL_ACCESS, MITRETactic.DEFENSE_EVASION],
            description="Adversaries may disable or modify multi-factor authentication to bypass access controls",
            platforms=["Windows", "Azure AD", "SaaS", "Google Workspace", "Office 365"],
            data_sources=["User Account", "Logon Session"],
            requires_privileges={"Administrator"},
            grants_privileges={"Administrator"},
            observables={"authentication": ["mfa_disabled", "mfa_bypass", "conditional_access_change"]}
        )

        self.techniques["T1556.007"] = ATTACKTechnique(
            technique_id="T1556.007",
            name="Modify Authentication Process: Hybrid Identity",
            tactics=[MITRETactic.CREDENTIAL_ACCESS, MITRETactic.DEFENSE_EVASION],
            description="Adversaries may patch on-prem identity systems to manipulate cloud authentication",
            platforms=["Azure AD", "Windows"],
            data_sources=["Application Log", "Logon Session"],
            requires_privileges={"Administrator"},
            grants_privileges={"Administrator"},
            observables={"authentication": ["aad_connect_modification", "hybrid_auth_patch", "pass_through_auth_abuse"]}
        )

        self.techniques["T1621"] = ATTACKTechnique(
            technique_id="T1621",
            name="Multi-Factor Authentication Request Generation",
            tactics=[MITRETactic.CREDENTIAL_ACCESS],
            description="Adversaries may attempt to bypass MFA by generating repeated push requests (MFA fatigue)",
            platforms=["Windows", "Linux", "macOS", "Azure AD", "SaaS"],
            data_sources=["Logon Session", "User Account"],
            requires_privileges=set(),
            grants_privileges={"User"},
            observables={"authentication": ["mfa_bombing", "push_notification_flood", "repeated_mfa_request"]}
        )

        self.techniques["T1558"] = ATTACKTechnique(
            technique_id="T1558",
            name="Steal or Forge Kerberos Tickets",
            tactics=[MITRETactic.CREDENTIAL_ACCESS],
            description="Adversaries may steal or forge Kerberos tickets for lateral movement",
            platforms=["Windows"],
            data_sources=["Active Directory", "Logon Session"],
            requires_privileges={"User"},
            grants_privileges={"User", "Administrator"},
            observables={"authentication": ["ticket_granting_request", "golden_ticket", "silver_ticket"]}
        )

        self.techniques["T1558.003"] = ATTACKTechnique(
            technique_id="T1558.003",
            name="Steal or Forge Kerberos Tickets: Kerberoasting",
            tactics=[MITRETactic.CREDENTIAL_ACCESS],
            description="Adversaries may abuse Kerberos service ticket requests to crack service account passwords offline",
            platforms=["Windows"],
            data_sources=["Active Directory", "Logon Session"],
            requires_privileges={"User"},
            grants_privileges={"Administrator"},
            observables={"authentication": ["tgs_request", "service_ticket_request", "kerberoast"]}
        )

        # =================================================================
        # v18.1 Additions: Defense Evasion (~10)
        # =================================================================

        self.techniques["T1027"] = ATTACKTechnique(
            technique_id="T1027",
            name="Obfuscated Files or Information",
            tactics=[MITRETactic.DEFENSE_EVASION],
            description="Adversaries may encrypt, encode, or obfuscate payload contents",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["File", "Process"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"file": ["encoded_payload", "base64_content", "encrypted_dropper"]}
        )

        self.techniques["T1140"] = ATTACKTechnique(
            technique_id="T1140",
            name="Deobfuscate/Decode Files or Information",
            tactics=[MITRETactic.DEFENSE_EVASION],
            description="Adversaries may use obfuscated files that require deobfuscation on the endpoint",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["File", "Process"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"process": ["certutil_decode", "base64_decode", "xor_decode"]}
        )

        self.techniques["T1070"] = ATTACKTechnique(
            technique_id="T1070",
            name="Indicator Removal",
            tactics=[MITRETactic.DEFENSE_EVASION],
            description="Adversaries may delete or modify artifacts to hinder forensics",
            platforms=["Windows", "Linux", "macOS", "Containers"],
            data_sources=["File", "Process", "Windows Event Logs"],
            requires_privileges={"User", "Administrator"},
            grants_privileges=set(),
            observables={"file": ["log_deletion", "timestamp_modification", "event_log_clear"]}
        )

        self.techniques["T1036"] = ATTACKTechnique(
            technique_id="T1036",
            name="Masquerading",
            tactics=[MITRETactic.DEFENSE_EVASION],
            description="Adversaries may manipulate features of artifacts to make them appear legitimate",
            platforms=["Windows", "Linux", "macOS", "Containers"],
            data_sources=["File", "Process"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"process": ["renamed_binary", "spoofed_extension", "masquerade_process"]}
        )

        self.techniques["T1055"] = ATTACKTechnique(
            technique_id="T1055",
            name="Process Injection",
            tactics=[MITRETactic.DEFENSE_EVASION, MITRETactic.PRIVILEGE_ESCALATION],
            description="Adversaries may inject code into processes to evade defenses and elevate privileges",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Process"],
            requires_privileges={"User"},
            grants_privileges={"User", "Administrator"},
            observables={"process": ["dll_injection", "process_hollowing", "thread_injection", "ptrace_attach"]}
        )

        self.techniques["T1218"] = ATTACKTechnique(
            technique_id="T1218",
            name="System Binary Proxy Execution",
            tactics=[MITRETactic.DEFENSE_EVASION],
            description="Adversaries may bypass process or signature-based defenses by proxying execution through signed binaries",
            platforms=["Windows"],
            data_sources=["Process", "Command"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"process": ["mshta", "rundll32", "regsvr32", "certutil", "msiexec"]}
        )

        self.techniques["T1562"] = ATTACKTechnique(
            technique_id="T1562",
            name="Impair Defenses",
            tactics=[MITRETactic.DEFENSE_EVASION],
            description="Adversaries may maliciously modify defenses to allow malicious activity",
            platforms=["Windows", "Linux", "macOS", "Containers", "IaaS"],
            data_sources=["Process", "Command", "Windows Registry"],
            requires_privileges={"Administrator"},
            grants_privileges=set(),
            observables={"process": ["disable_av", "stop_service", "tamper_protection_off", "etw_bypass"]}
        )

        # =================================================================
        # v18.1 Additions: Discovery (~8)
        # =================================================================

        self.techniques["T1046"] = ATTACKTechnique(
            technique_id="T1046",
            name="Network Service Discovery",
            tactics=[MITRETactic.DISCOVERY],
            description="Adversaries may scan for services running on remote hosts",
            platforms=["Windows", "Linux", "macOS", "Containers"],
            data_sources=["Network Traffic", "Process"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"network": ["port_scan", "service_scan", "nmap_execution"]}
        )

        self.techniques["T1049"] = ATTACKTechnique(
            technique_id="T1049",
            name="System Network Connections Discovery",
            tactics=[MITRETactic.DISCOVERY],
            description="Adversaries may attempt to get a listing of network connections",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Process", "Command"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"process": ["netstat", "ss_command", "network_connection_list"]}
        )

        self.techniques["T1057"] = ATTACKTechnique(
            technique_id="T1057",
            name="Process Discovery",
            tactics=[MITRETactic.DISCOVERY],
            description="Adversaries may attempt to get information about running processes",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Process", "Command"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"process": ["tasklist", "ps_command", "process_enumeration"]}
        )

        self.techniques["T1082"] = ATTACKTechnique(
            technique_id="T1082",
            name="System Information Discovery",
            tactics=[MITRETactic.DISCOVERY],
            description="Adversaries may attempt to get detailed information about the OS and hardware",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Process", "Command"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"process": ["systeminfo", "uname", "hostname_query"]}
        )

        self.techniques["T1083"] = ATTACKTechnique(
            technique_id="T1083",
            name="File and Directory Discovery",
            tactics=[MITRETactic.DISCOVERY],
            description="Adversaries may enumerate files and directories to find sensitive data",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Process", "Command"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"process": ["dir_command", "find_command", "ls_command", "tree_command"]}
        )

        self.techniques["T1087"] = ATTACKTechnique(
            technique_id="T1087",
            name="Account Discovery",
            tactics=[MITRETactic.DISCOVERY],
            description="Adversaries may attempt to get a listing of accounts on a system or within the environment",
            platforms=["Windows", "Linux", "macOS", "Azure AD", "Google Workspace", "Office 365"],
            data_sources=["Process", "Command"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"process": ["net_user", "ldap_query", "whoami", "id_command"]}
        )

        self.techniques["T1201"] = ATTACKTechnique(
            technique_id="T1201",
            name="Password Policy Discovery",
            tactics=[MITRETactic.DISCOVERY],
            description="Adversaries may attempt to access password policy information",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Process", "Command"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"process": ["net_accounts", "chage_command", "password_policy_query"]}
        )

        self.techniques["T1018"] = ATTACKTechnique(
            technique_id="T1018",
            name="Remote System Discovery",
            tactics=[MITRETactic.DISCOVERY],
            description="Adversaries may attempt to get a listing of other systems by IP or hostname",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Network Traffic", "Process"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"network": ["arp_scan", "dns_lookup", "net_view", "ping_sweep"]}
        )

        # =================================================================
        # v18.1 Additions: Persistence (~8)
        # =================================================================

        self.techniques["T1053"] = ATTACKTechnique(
            technique_id="T1053",
            name="Scheduled Task/Job",
            tactics=[MITRETactic.EXECUTION, MITRETactic.PERSISTENCE, MITRETactic.PRIVILEGE_ESCALATION],
            description="Adversaries may abuse task scheduling to execute malicious code at regular intervals",
            platforms=["Windows", "Linux", "macOS", "Containers"],
            data_sources=["Scheduled Job", "Process", "Command"],
            requires_privileges={"User"},
            grants_privileges={"User", "SYSTEM"},
            observables={"process": ["schtasks", "crontab", "at_command", "systemd_timer"]}
        )

        self.techniques["T1098"] = ATTACKTechnique(
            technique_id="T1098",
            name="Account Manipulation",
            tactics=[MITRETactic.PERSISTENCE, MITRETactic.PRIVILEGE_ESCALATION],
            description="Adversaries may manipulate accounts to maintain access",
            platforms=["Windows", "Linux", "macOS", "Azure AD", "Office 365", "Google Workspace"],
            data_sources=["User Account", "Active Directory"],
            requires_privileges={"Administrator"},
            grants_privileges={"Administrator"},
            observables={"authentication": ["account_modification", "group_membership_change", "credential_reset"]}
        )

        self.techniques["T1133"] = ATTACKTechnique(
            technique_id="T1133",
            name="External Remote Services",
            tactics=[MITRETactic.PERSISTENCE, MITRETactic.INITIAL_ACCESS],
            description="Adversaries may use external remote services (VPN, RDP, Citrix) for persistence",
            platforms=["Windows", "Linux"],
            data_sources=["Logon Session", "Network Traffic"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"network": ["vpn_connection", "rdp_external", "citrix_logon"]}
        )

        self.techniques["T1136"] = ATTACKTechnique(
            technique_id="T1136",
            name="Create Account",
            tactics=[MITRETactic.PERSISTENCE],
            description="Adversaries may create accounts to maintain access",
            platforms=["Windows", "Linux", "macOS", "Azure AD"],
            data_sources=["User Account", "Process"],
            requires_privileges={"Administrator"},
            grants_privileges={"User", "Administrator"},
            observables={"process": ["net_user_add", "useradd", "account_creation_event"]}
        )

        self.techniques["T1197"] = ATTACKTechnique(
            technique_id="T1197",
            name="BITS Jobs",
            tactics=[MITRETactic.DEFENSE_EVASION, MITRETactic.PERSISTENCE],
            description="Adversaries may abuse BITS jobs for persistent file transfer and execution",
            platforms=["Windows"],
            data_sources=["Network Traffic", "Process"],
            requires_privileges={"User"},
            grants_privileges={"User"},
            observables={"process": ["bitsadmin", "bits_transfer", "background_transfer"]}
        )

        self.techniques["T1505"] = ATTACKTechnique(
            technique_id="T1505",
            name="Server Software Component",
            tactics=[MITRETactic.PERSISTENCE],
            description="Adversaries may abuse server software components like web shells, transport agents",
            platforms=["Windows", "Linux"],
            data_sources=["File", "Process", "Network Traffic"],
            requires_privileges={"Administrator"},
            grants_privileges={"User", "Administrator"},
            observables={"file": ["web_shell", "iis_module", "sql_stored_procedure"]}
        )

        self.techniques["T1547"] = ATTACKTechnique(
            technique_id="T1547",
            name="Boot or Logon Autostart Execution",
            tactics=[MITRETactic.PERSISTENCE, MITRETactic.PRIVILEGE_ESCALATION],
            description="Adversaries may configure system settings to automatically execute malware on startup",
            platforms=["Windows", "Linux", "macOS"],
            data_sources=["Windows Registry", "File", "Process"],
            requires_privileges={"User"},
            grants_privileges={"User", "SYSTEM"},
            observables={"process": ["registry_run_key", "startup_folder", "init_script", "systemd_service"]}
        )

    def _initialize_composition_rules(self):
        """
        Define valid technique compositions.

        This is the category structure: not all morphisms compose.
        Key constraint: Tactic ordering must be respected.
        """
        # Define tactic precedence (partial order)
        self.tactic_ordering = {
            MITRETactic.RECONNAISSANCE: 0,
            MITRETactic.RESOURCE_DEVELOPMENT: 1,
            MITRETactic.INITIAL_ACCESS: 2,
            MITRETactic.EXECUTION: 3,
            MITRETactic.PERSISTENCE: 3,  # Can happen concurrently with execution
            MITRETactic.PRIVILEGE_ESCALATION: 4,
            MITRETactic.DEFENSE_EVASION: 4,  # Can happen at any stage
            MITRETactic.CREDENTIAL_ACCESS: 5,
            MITRETactic.DISCOVERY: 5,
            MITRETactic.LATERAL_MOVEMENT: 6,
            MITRETactic.COLLECTION: 7,
            MITRETactic.COMMAND_AND_CONTROL: 3,  # Established early, used throughout
            MITRETactic.EXFILTRATION: 8,
            MITRETactic.IMPACT: 9
        }

        # Generate valid compositions based on:
        # 1. Tactic ordering
        # 2. Privilege requirements
        for t1_id, t1 in self.techniques.items():
            for t2_id, t2 in self.techniques.items():
                if self._is_valid_composition(t1, t2):
                    self.valid_compositions.add((t1_id, t2_id))

    def _is_valid_composition(self, tech1: ATTACKTechnique, tech2: ATTACKTechnique) -> bool:
        """
        Check if tech1 ∘ tech2 is a valid composition.

        Valid if:
        1. Tactic ordering is respected (or concurrent tactics)
        2. tech2 requires privileges that tech1 grants (or tech2 requires no privileges)
        """
        # Check tactic ordering
        max_order_t1 = max(self.tactic_ordering.get(tactic, 0) for tactic in tech1.tactics)
        min_order_t2 = min(self.tactic_ordering.get(tactic, 99) for tactic in tech2.tactics)

        # tech2 must come after or concurrent with tech1
        if min_order_t2 < max_order_t1 - 1:  # Allow 1 level of slack for concurrent tactics
            return False

        # Check privilege requirements
        if tech2.requires_privileges:
            # tech2 needs privileges - check if tech1 grants them
            if not (tech2.requires_privileges & tech1.grants_privileges):
                # tech1 doesn't grant what tech2 needs
                # BUT: if tech2 only requires "User" and that's commonly available, allow it
                if tech2.requires_privileges == {"User"}:
                    return True
                return False

        return True

    def can_compose(self, tech1_id: str, tech2_id: str) -> bool:
        """Check if two techniques can compose in an attack chain."""
        return (tech1_id, tech2_id) in self.valid_compositions

    def get_technique(self, tech_id: str) -> Optional[ATTACKTechnique]:
        """Get technique by ID."""
        return self.techniques.get(tech_id)

    def get_techniques_by_tactic(self, tactic: MITRETactic) -> List[ATTACKTechnique]:
        """Get all techniques that implement a specific tactic."""
        return [t for t in self.techniques.values() if tactic in t.tactics]

    def find_attack_paths(self, start_tech: str, end_tech: str, max_length: int = 5) -> List[List[str]]:
        """
        Find all valid attack paths from start to end technique.

        This is path finding in the attack category.
        Returns list of paths, where each path is a list of technique IDs.
        """
        if start_tech not in self.techniques or end_tech not in self.techniques:
            return []

        paths = []

        def dfs(current: str, target: str, path: List[str], visited: Set[str]):
            if len(path) > max_length:
                return

            if current == target:
                paths.append(path.copy())
                return

            # Try composing with all valid next techniques
            for next_tech in self.techniques:
                if next_tech not in visited and self.can_compose(current, next_tech):
                    path.append(next_tech)
                    visited.add(next_tech)
                    dfs(next_tech, target, path, visited)
                    path.pop()
                    visited.remove(next_tech)

        dfs(start_tech, end_tech, [start_tech], {start_tech})
        return paths

    def get_detection_signatures(self, tech_id: str) -> Dict[str, List[str]]:
        """Get detection signatures for a technique."""
        technique = self.get_technique(tech_id)
        return technique.observables if technique else {}

    def get_composable_successors(self, technique_id: str) -> List[Tuple[str, float]]:
        """
        Get all techniques that can validly follow technique_id.

        Returns: List of (successor_id, stealth_weight) tuples.
        Used by streaming Kan extensions for real-time prediction.

        Results are cached on first call — the composition table is static.
        """
        if (not hasattr(self, '_successor_cache')
                or getattr(self, '_successor_cache_env', None) is not self.environment):
            self._build_successor_cache()
        return self._successor_cache.get(technique_id, [])

    def _build_successor_cache(self):
        """Pre-compute the full successor table once (85x85 = 7225 checks)."""
        from cyber.stealth_scoring import StealthScorer
        scorer = StealthScorer(environment=self.environment)

        self._successor_cache = {}
        self._successor_cache_env = self.environment
        for src in self.techniques:
            successors = []
            for tgt in self.techniques:
                if self.can_compose(src, tgt):
                    stealth = scorer.composition_stealth(src, tgt)
                    successors.append((tgt, stealth))
            self._successor_cache[src] = successors

    def build_enriched_category(self):
        """
        Build enriched attack category with stealth weights.

        Returns an EnrichedCategory over the stealth quantale ([0,1], ×, 1)
        where hom-objects are stealth scores for technique transitions.
        """
        from categorical.enriched_category import EnrichedCategory, STEALTH_QUANTALE
        from cyber.stealth_scoring import StealthScorer

        scorer = StealthScorer(environment=self.environment)
        cat = EnrichedCategory(STEALTH_QUANTALE)

        # Add all techniques as objects
        for tech_id, tech in self.techniques.items():
            cat.add_object(tech_id, {
                "name": tech.name,
                "tactics": [t.name for t in tech.tactics],
                "platforms": tech.platforms
            })

        # Add stealth-weighted hom-objects for valid compositions
        for (t1, t2) in self.valid_compositions:
            stealth = scorer.composition_stealth(t1, t2)
            cat.set_hom(t1, t2, stealth)

        return cat

    def explain_composition(self, tech_chain: List[str]) -> str:
        """
        Generate human-readable explanation of an attack chain.

        This is the "categorical proof" that makes detection explainable.
        """
        if not tech_chain:
            return "Empty attack chain"

        explanation = "Attack Chain Analysis:\n"
        explanation += "=" * 60 + "\n\n"

        for i, tech_id in enumerate(tech_chain, 1):
            tech = self.get_technique(tech_id)
            if not tech:
                explanation += f"{i}. Unknown technique: {tech_id}\n"
                continue

            explanation += f"{i}. {tech.name} ({tech_id})\n"
            explanation += f"   Tactics: {', '.join(t.name for t in tech.tactics)}\n"
            explanation += f"   Requires: {tech.requires_privileges or 'None'}\n"
            explanation += f"   Grants: {tech.grants_privileges or 'None'}\n"

            # Check composition validity
            if i > 1:
                prev_tech_id = tech_chain[i-2]
                if self.can_compose(prev_tech_id, tech_id):
                    explanation += f"   [OK] Valid composition with previous step\n"
                else:
                    explanation += f"   [WARNING] Invalid composition - check attack chain\n"

            explanation += "\n"

        # Overall assessment
        valid = all(
            self.can_compose(tech_chain[i], tech_chain[i+1])
            for i in range(len(tech_chain) - 1)
        )

        explanation += "=" * 60 + "\n"
        if valid:
            explanation += "Result: VALID ATTACK CHAIN\n"
            explanation += "All technique compositions satisfy MITRE ATT&CK constraints.\n"
        else:
            explanation += "Result: INVALID ATTACK CHAIN\n"
            explanation += "Contains composition violations - may be false positive.\n"

        return explanation

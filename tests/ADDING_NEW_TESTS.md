# Adding New Mythos Attack Tests

## Quick Reference

When Mythos discovers a new vulnerability class, add tests following this guide.

## Test Template

```python
class TestNewVulnerabilityClass:
    """
    CWE-XXXX: Vulnerability Name
    MITRE TXXXX: Attack Technique

    Maps to: [gray_coherence_gap_type]
    """

    def test_specific_vulnerability(self, gray_layer):
        """Description of the vulnerability pattern"""

        # Step 1: Create context for vulnerable operation
        vuln_ctx = TwoCellProxy(
            source="source_component",
            target="target_component",
            name="operation_name",
            # Add relevant attributes (see Attribute Reference below)
            attribute_name=value,
            confidence=0.X,  # Lower for untrusted input
        )

        # Step 2: Create context for exploited operation
        exploit_ctx = TwoCellProxy(
            source="target_component",
            target="exploited_component",
            name="exploitation",
            attribute_name=expected_value,  # What SHOULD be true
            confidence=0.Y,  # Higher for expected safe behavior
        )

        # Step 3: Check for coherence gap
        gap = gray_layer.check_[appropriate_method](vuln_ctx, exploit_ctx)

        # Step 4: Assert gap was detected
        assert gap is not None
        assert gap.gap_type == CoherenceGapType.EXPECTED_TYPE
        assert gap.severity in ["CRITICAL", "HIGH", "MEDIUM"]
```

## Attribute Reference

### Common TwoCellProxy Attributes

| Attribute | Type | Used For | Gap Types |
|-----------|------|----------|-----------|
| `privilege_level` | int (0-2) | Privilege escalation | privilege_non_commute |
| `sandbox_level` | int (0-3) | Sandbox/container escape | functor_escape |
| `auth_required` | bool | Authentication bypass | sieve_collapse |
| `buffer_size` | int | Buffer overflow | composition_boundary |
| `lifetime_end` | int | Use-after-free | lifetime_violation |
| `type_signature` | str | Type confusion | interchange_failure |
| `timestamp` | int | Race conditions | modification_missing |
| `sanitized` | bool | Input validation | sieve_collapse |
| `path_validated` | bool | Path traversal | sieve_collapse |
| `shell_escaped` | bool | Command injection | sieve_collapse |
| `constant_time` | bool | Timing attacks | interchange_failure |
| `nonce_value` | int | Crypto nonce reuse | interchange_failure |
| `entropy_bits` | int | Weak randomness | composition_boundary |
| `trusted_source` | bool | Deserialization | sieve_collapse |

### Custom Attributes

You can add domain-specific attributes:

```python
TwoCellProxy(
    source="network",
    target="firewall",
    name="packet",
    # Custom attributes
    ip_address="192.168.1.1",
    port=443,
    protocol="tcp",
    encrypted=True,
    confidence=0.8,
)
```

## Gray Layer Check Methods

### 1. check_privilege_commutation()

**For:** Privilege escalation, setuid bugs, capability leaks

**Pattern:** Checks if privilege changes commute properly

```python
gap = gray_layer.check_privilege_commutation(low_priv_ctx, high_priv_ctx)
```

**Example:**
```python
user_ctx = TwoCellProxy(
    source="user_process",
    target="setuid_helper",
    name="invoke",
    privilege_level=0,  # User
    confidence=0.5,
)

root_ctx = TwoCellProxy(
    source="setuid_helper",
    target="kernel_op",
    name="execute",
    privilege_level=2,  # Root
    confidence=0.7,
)

gap = gray_layer.check_privilege_commutation(user_ctx, root_ctx)
# Detects if privilege escalation is unvalidated
```

### 2. check_functor_preservation()

**For:** Sandbox escape, container breakout, VM escape

**Pattern:** Checks if isolation boundaries are preserved

```python
gap = gray_layer.check_functor_preservation(sandboxed_ctx, host_ctx)
```

**Example:**
```python
container_ctx = TwoCellProxy(
    source="container",
    target="mount",
    name="access",
    sandbox_level=3,  # Highly isolated
    confidence=0.6,
)

host_ctx = TwoCellProxy(
    source="mount",
    target="host_kernel",
    name="write",
    sandbox_level=0,  # No isolation
    confidence=0.7,
)

gap = gray_layer.check_functor_preservation(container_ctx, host_ctx)
# Detects sandbox escape
```

### 3. check_sieve_coherence()

**For:** Auth bypass, input validation, XSS, SQLi, path traversal

**Pattern:** Checks if filtering/validation properties hold

```python
gap = gray_layer.check_sieve_coherence(untrusted_ctx, trusted_ctx)
```

**Example:**
```python
input_ctx = TwoCellProxy(
    source="user_input",
    target="html_output",
    name="echo",
    sanitized=False,  # Untrusted input
    confidence=0.3,
)

output_ctx = TwoCellProxy(
    source="html_output",
    target="browser",
    name="render",
    sanitized=True,  # Should be sanitized!
    confidence=0.8,
)

gap = gray_layer.check_sieve_coherence(input_ctx, output_ctx)
# Detects XSS vulnerability
```

### 4. check_composition_boundary()

**For:** Buffer overflow, integer overflow, bounds checking

**Pattern:** Checks if size/boundary constraints are preserved

```python
gap = gray_layer.check_composition_boundary(alloc_ctx, write_ctx)
```

**Example:**
```python
alloc_ctx = TwoCellProxy(
    source="malloc",
    target="buffer",
    name="allocate",
    buffer_size=256,
    confidence=0.6,
)

write_ctx = TwoCellProxy(
    source="buffer",
    target="write",
    name="strcpy",
    buffer_size=512,  # Exceeds allocation!
    confidence=0.7,
)

gap = gray_layer.check_composition_boundary(alloc_ctx, write_ctx)
# Detects buffer overflow
```

### 5. check_lifetime_coherence()

**For:** Use-after-free, double free, dangling pointers

**Pattern:** Checks if object lifetime is respected

```python
gap = gray_layer.check_lifetime_coherence(free_ctx, use_ctx)
```

**Example:**
```python
free_ctx = TwoCellProxy(
    source="object",
    target="free",
    name="deallocate",
    lifetime_end=100,
    confidence=0.7,
)

use_ctx = TwoCellProxy(
    source="object",
    target="method",
    name="call",
    lifetime_end=200,  # Used after free!
    confidence=0.6,
)

gap = gray_layer.check_lifetime_coherence(free_ctx, use_ctx)
# Detects use-after-free
```

### 6. check_interchange_law()

**For:** Type confusion, vtable corruption, prototype pollution

**Pattern:** Checks if type properties are preserved

```python
gap = gray_layer.check_interchange_law(write_type_ctx, read_type_ctx)
```

**Example:**
```python
write_ctx = TwoCellProxy(
    source="union",
    target="int_field",
    name="write_int",
    type_signature="int32",
    confidence=0.6,
)

read_ctx = TwoCellProxy(
    source="union",
    target="ptr_field",
    name="read_ptr",
    type_signature="void*",  # Different type!
    confidence=0.7,
)

gap = gray_layer.check_interchange_law(write_ctx, read_ctx)
# Detects type confusion
```

### 7. detect_race_window()

**For:** Race conditions, TOCTOU, signal handler bugs

**Pattern:** Checks for timing gaps allowing races

```python
gap = gray_layer.detect_race_window(check_ctx, use_ctx)
```

**Example:**
```python
check_ctx = TwoCellProxy(
    source="access_check",
    target="file",
    name="verify",
    timestamp=100,
    confidence=0.5,
)

use_ctx = TwoCellProxy(
    source="file",
    target="open",
    name="use",
    timestamp=200,  # Time gap allows race
    confidence=0.7,
)

gap = gray_layer.detect_race_window(check_ctx, use_ctx)
# Detects TOCTOU race
```

## Step-by-Step: Adding a New CVE

### Example: CVE-2026-XXXX (Hypothetical kernel bug)

**Step 1: Research the vulnerability**
- What component is vulnerable?
- What operation triggers it?
- What gap type does it map to?
- What are the CWE/MITRE IDs?

**Step 2: Create test class**

```python
class TestKernelVulnerabilities:
    """
    CWE-123: Kernel Memory Corruption
    MITRE T1068: Exploitation for Privilege Escalation

    Maps to: composition_boundary + privilege_non_commute
    """

    def test_cve_2026_xxxx_kernel_overflow(self, gray_layer):
        """
        CVE-2026-XXXX: Kernel buffer overflow in ioctl handler

        User-supplied size parameter not validated, allows
        heap overflow leading to privilege escalation.
        """
        # User supplies size parameter
        ioctl_ctx = TwoCellProxy(
            source="user_space",
            target="ioctl_handler",
            name="device_ioctl",
            buffer_size=1024,  # User-controlled
            privilege_level=0,
            confidence=0.3,  # Untrusted
        )

        # Kernel allocates based on user size
        alloc_ctx = TwoCellProxy(
            source="ioctl_handler",
            target="kmalloc",
            name="allocate_kernel_buffer",
            buffer_size=512,  # Actually allocated (integer overflow)
            privilege_level=2,
            confidence=0.6,
        )

        # Kernel copies user data (overflow!)
        copy_ctx = TwoCellProxy(
            source="kmalloc",
            target="copy_from_user",
            name="copy_data",
            buffer_size=1024,  # Copies full user size
            privilege_level=2,
            confidence=0.7,
        )

        # Check for buffer overflow
        boundary_gap = gray_layer.check_composition_boundary(alloc_ctx, copy_ctx)
        assert boundary_gap is not None
        assert boundary_gap.gap_type == CoherenceGapType.COMPOSITION_BOUNDARY

        # Check for privilege escalation (user controls kernel memory)
        priv_gap = gray_layer.check_privilege_commutation(ioctl_ctx, copy_ctx)
        assert priv_gap is not None
        assert priv_gap.gap_type == CoherenceGapType.PRIVILEGE_NON_COMMUTE

        # Combined severity should be CRITICAL
        assert boundary_gap.severity == "CRITICAL" or priv_gap.severity == "CRITICAL"
```

**Step 3: Add to test file**

Add the class to `tests/test_mythos_comprehensive.py`

**Step 4: Update documentation**

Add to `tests/MYTHOS_TEST_COVERAGE.md`:
```markdown
| **CVE-2026-XXXX** | Kernel ioctl buffer overflow | test_cve_2026_xxxx_kernel_overflow | composition_boundary + privilege_non_commute |
```

**Step 5: Run tests**

```bash
pytest tests/test_mythos_comprehensive.py::TestKernelVulnerabilities -v
```

## Testing Exploit Chains

For multi-step attacks:

```python
def test_exploit_chain_example(self, mythos_shield):
    """Chain: InfoLeak → ASLR Bypass → ROP → Privilege Escalation"""

    builder = SoftwareCategoryBuilder()

    # Step 1: Information leak
    builder.add_function("printf_vuln", "leaked_address")

    # Step 2: Calculate ROP chain with known address
    builder.add_function("leaked_address", "calculate_rop")

    # Step 3: Buffer overflow with ROP
    builder.add_function("calculate_rop", "buffer_overflow")

    # Step 4: Execute ROP chain
    builder.add_function("buffer_overflow", "rop_gadget")

    # Step 5: Privilege escalation
    builder.add_function("rop_gadget", "setuid_root")
    builder.add_function("setuid_root", "root_shell")

    # Scan for attack chain
    report = mythos_shield.scan(top_k=100, min_confidence=0.2)

    # Should detect multi-step chain
    assert len(report.findings) >= 1

    # Look for chain-aware finding
    chain_finding = [f for f in report.findings if "chain" in f.explanation.lower()]
    assert len(chain_finding) > 0
```

## Confidence Tuning

**General guidelines:**

| Confidence | Meaning | Use For |
|------------|---------|---------|
| 0.1 - 0.3 | Highly untrusted | User input, network data, attacker-controlled |
| 0.4 - 0.6 | Moderate trust | Parsed input, semi-validated data |
| 0.7 - 0.8 | High trust | Authenticated data, internally generated |
| 0.9 - 1.0 | Complete trust | Constants, verified invariants |

**Gap detection threshold:** Typically `confidence_diff >= 0.3`

```python
# This WILL trigger (0.3 vs 0.9 = 0.6 diff)
untrusted = TwoCellProxy(..., confidence=0.3)
trusted = TwoCellProxy(..., confidence=0.9)

# This might NOT trigger (0.6 vs 0.8 = 0.2 diff)
semi_trusted = TwoCellProxy(..., confidence=0.6)
trusted = TwoCellProxy(..., confidence=0.8)
```

## Negative Tests (Preventing False Positives)

Always add negative tests to ensure safe code doesn't trigger:

```python
def test_safe_pattern_no_false_positive(self, gray_layer):
    """Properly validated code should NOT trigger"""

    validated_ctx = TwoCellProxy(
        source="input",
        target="validator",
        name="check",
        sanitized=True,
        confidence=0.9,  # High confidence in validation
    )

    use_ctx = TwoCellProxy(
        source="validator",
        target="safe_use",
        name="process",
        sanitized=True,
        confidence=0.9,
    )

    gap = gray_layer.check_sieve_coherence(validated_ctx, use_ctx)

    # Should NOT detect gap (both sanitized, high confidence)
    assert gap is None or gap.confidence < 0.5
```

## Performance Considerations

For large-scale tests:

```python
def test_large_scale_detection(self, mythos_shield):
    """Test performance on realistic codebase size"""

    builder = SoftwareCategoryBuilder()

    # Simulate large codebase
    for i in range(10000):
        builder.add_function(f"func_{i}", f"func_{i+1}")

    # Add vulnerabilities
    builder.add_function("func_5000", "vulnerable_operation")
    builder.add_function("vulnerable_operation", "exploit")

    import time
    start = time.time()

    report = mythos_shield.scan(top_k=500, min_confidence=0.2)

    duration = time.time() - start

    # Should complete in reasonable time
    assert duration < 60  # 1 minute for 10K functions

    # Should still find vulnerabilities
    assert len(report.findings) > 0
```

## Common Patterns

### Pattern 1: Privilege Escalation via Confused Deputy

```python
# Step 1: User invokes high-privilege helper
user_ctx = TwoCellProxy(source="user", target="helper", name="invoke",
                        privilege_level=0, confidence=0.4)

# Step 2: Helper performs privileged op without re-validating
priv_ctx = TwoCellProxy(source="helper", target="kernel", name="execute",
                        privilege_level=2, confidence=0.8)

gap = gray_layer.check_privilege_commutation(user_ctx, priv_ctx)
```

### Pattern 2: Injection via Insufficient Sanitization

```python
# Step 1: Receive untrusted input
input_ctx = TwoCellProxy(source="request", target="param", name="parse",
                         sanitized=False, confidence=0.2)

# Step 2: Use in dangerous context
use_ctx = TwoCellProxy(source="param", target="sql_query", name="execute",
                       sanitized=True, confidence=0.8)

gap = gray_layer.check_sieve_coherence(input_ctx, use_ctx)
```

### Pattern 3: Memory Corruption via Bounds Violation

```python
# Step 1: Allocate buffer
alloc_ctx = TwoCellProxy(source="malloc", target="buffer", name="alloc",
                         buffer_size=256, confidence=0.7)

# Step 2: Write beyond bounds
write_ctx = TwoCellProxy(source="buffer", target="write", name="copy",
                         buffer_size=512, confidence=0.6)

gap = gray_layer.check_composition_boundary(alloc_ctx, write_ctx)
```

## Questions?

Check existing tests in `test_mythos_comprehensive.py` for more examples.

Key files:
- `tests/test_mythos_comprehensive.py` - Full test suite
- `tests/test_mythos_attack_simulation.py` - Basic 6-attack validation
- `core/gray_coherence.py` - Gray layer implementation
- `core/gray_coherence_bridge.py` - MythosShield scanner

For Mythos findings, refer to:
- https://red.anthropic.com/2026/mythos-preview/
- https://www.anthropic.com/glasswing
- https://cwe.mitre.org/top25/

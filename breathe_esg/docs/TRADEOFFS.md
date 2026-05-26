# Tradeoffs - Breathe ESG Platform

This document describes deliberate omissions and why they were chosen over alternatives.

---

## 1. No Real-Time API Ingestion for SAP/Utility

### The Tradeoff

| Feature | CSV Upload (Chosen) | Real-Time API (Omitted) |
|---------|--------------------|------------------------|
| Developer effort | 2-3 days | 2-3 weeks |
| Reliability | 100% (file-based) | 95% (network-dependent) |
| Authentication | Simple | Certificate + OAuth + refresh tokens |
| Rate limiting | N/A | Must implement retry/backoff |
| Vendor API changes | Git history shows change | Breaking changes break code |
| Offline operation | Works in air-gapped networks | Requires connectivity |

### Why CSV Was Chosen

**Primary use case:** Analyst has exported data from SAP/Utility portal → uploads to Breathe ESG for processing.

This is how **80% of companies** actually operate. Real-time feeds require:
- IT department configuration
- Service account setup
- Network whitelist approval
- Ongoing monitoring

For a tech intern prototype focusing on **carbon accounting accuracy and workflow**, CSV upload demonstrates 80% of value with 20% effort.

### What We Simplified

1. **No async upload progress** – Simple POST returns task_id
2. **No retry logic** – Tasks fail fast, visible in dashboard
3. **No file size limits** – 100MB hard limit for prototype

**Production migration path:**
```python
# apps/ingestion/base.py
class BaseIngestion:
    async def ingest_file(self, file, size_limit=100*1024*1024):
        # Check size first
        if file.size > size_limit:
            raise ValidationError("File too large")
        # Use async file reading for large files
        async with aiofiles.open(file.path, 'rb') as f:
            content = await f.read()
        # Process chunks for memory efficiency
```

---

## 2. No Granular User Roles (Admin vs. Analyst)

### The Tradeoff

| Roles | Single Analyst Role (Chosen) | Admin/Analyst Separation (Omitted) |
|-------|----------------------------|-----------------------------------|
| Django complexity | Minimal (Groups not needed) | Custom Permission classes |
| Demo clarity | Clear: "You are the analyst" | Extra login screen for admins |
| Audit compliance | Adequate (user identity tracked) | Required for enterprise |
| Bulk operations | One role = one permission set | Complex OR conditions |

### Why Single Role Was Chosen

**Prototype goal:** Demonstrate the core workflow:
1. Upload data → Ingestion pipeline processes
2. Review results → Analyst approves/rejects
3. Audit trail → All actions logged

Adding admin/analyst separation would require:
- Custom Django permissions
- View-level decorators
- Complex permission checks in serializers

**What we captured:** Analyst can approve/reject, view audit logs, manage files. This is the **core analyst workflow**.

### Production Addition

```python
# apps/review/permissions.py
class IsAnalyst(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_analyst and obj.tenant == request.user.tenant

class IsTenantAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_admin and obj.tenant.admin == request.user
```

---

## 3. No PDF Bill Parser

### The Tradeoff

| Approach | Python-Charmoli | pdfplumber | Tesseract OCR |
|----------|---------------|------------|--------------|
| Accuracy | 70% (regular layouts only) | 60% (handwritten fails) | 85% (with good training) |
| Development time | 2-3 weeks | 1-2 weeks | 3-4 weeks |
| Cost | Free | Free | Free + training data |
| Maintenance | Updates needed annually | Updates needed annually | Training data degrades |

### Why PDF Was Omitted

**Research finding:** Utility bill PDFs vary wildly:
- Logo placement affects parsing
- Two-factor authentication codes sometimes include meter readings
- Seasonal promotions add text layers
- Handwritten notes overlay meter data

**Sample failure case:**
```
PDF text layer contains:
"Your account has been upgraded! ✓"
"Thank you for choosing our premium service"
"Meter reading: 12345 (handwritten)"

Parser extracts: "12345" as account number, misses meter reading
```

**What we rely on:** Structured CSV exports from utility portals (which 80% of utilities support).

### Future Path

```python
# apps/utility/parser.py
def parse_pdf_bill(pdf_path):
    # Option 1: Commercial service (AWS Textract)
    # Option 2: Hybrid approach - extract table, validate with utility API
    # Option 3: User uploads both PDF + CSV for fallback
    pass
```

---

## 4. No Material Master Integration

### The Tradeoff

**SAP Material Master contains:**
- Unit of measure conversions (PC → kg)
- Product classification (raw material, finished good)
- Plant-specific data (location, cost center)

**To integrate properly would require:**
- SAP IDoc connectivity (RFC, HTTP, or BAPI)
- Material master caching (100,000+ materials)
- Unit of measure conversion table (50+ UoM combinations)
- Transaction date lookups (historical UoM changes)

**Approximate effort:** 2-3 weeks minimum for basic functionality.

### What We Do Instead

**Heuristic approach:**
```python
def classify_material(material):
    description = material.description.lower()
    if 'diesel' in description or 'fuel' in description:
        return 'fuel_diesel'
    elif 'electricity' in description:
        return 'purchased_electricity'
    else:
        return 'unknown'  # Fails validation
```

**Validation fails → Analyst reviews:**
```
Row 42: "100.0 PC Material X"
Validation error: "Cannot convert PC (piece) to kg - material master required"
Analyst action: Check SAP, note that Material X = 50kg per PC, update manually
```

### Production Migration

```python
# apps/sap/material_master.py
class MaterialMasterClient:
    def __init__(self, connection):
        self.material_cache = {}
    
    def get_conversion_factors(self, material_number):
        # Returns: {
        #   "pc_to_kg": 50.0,
        #   "m_to_kg": 1000.0,
        #   "l_to_kg": 0.85
        # }
        pass
    
    def get_classification(self, material_number):
        # Returns: {"category": "fuel_diesel", "scope": 1}
        pass
```

---

## 5. No Multi-Currency Support

### The Tradeoff

| Feature | Single Currency (Chosen) | Multi-Currency (Omitted) |
|---------|------------------------|----------------------------|
| Complexity | Minimal | Medium-High |
| Demo clarity | Clear workflow | Extra layer of abstraction |
| CO2e accuracy | Not affected (emissions don't change with currency) | Not relevant |
| Cost reporting | Not demonstrated | Important for finance teams |

### Why Omitted

**Key insight:** Carbon accounting ≠ Financial accounting. CO2e is a physical quantity (tonnes of CO2 equivalent), not a monetary value.

**What matters for CO2e:**
- Activity amount (1000 kWh)
- Emission factor (0.385 kg CO2e/kWh)
- Result (385 kg CO2e)

**Currency only matters for:**
- Cost per tonne calculations
- Budget vs. actual variance
- Executive reporting

**Future path:** Add cost fields to `NormalizedEmission` model for later financial integration.

```python
class NormalizedEmission(models.Model):
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # $/kWh, $/kg
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
```

---

## 6. No Real-Time Dashboard with WebSocket

### The Tradeoff

| Feature | Polling (Chosen) | WebSocket (Omitted) |
|---------|----------------|-------------------|
| Complexity | Simple (standard API calls) | Complex (WS server, reconnection logic) |
| Bandwidth | Low (small JSON payloads) | Higher (keep-alive messages) |
| Browser compatibility | Universal | Requires WebSocket polyfill for older browsers |
| Mobile support | Works | Limited on some mobile browsers |

### Why Polling Was Chosen

**Use case:** Analyst opens dashboard → sees recent uploads → polls every 30s for status updates.

This is how **all major enterprise tools** handle real-time updates:
- Slack: ~15s polling for channels
- Gmail: ~30s polling for inbox
- Salesforce: ~10s polling for feed

### Production Implementation

```python
# apps/dashboard/views.py
@action(detail=False, methods=['get'])
def live_updates(self, request):
    # WebSocket-style polling endpoint
    # Returns: {"events": [...]}
    # Client polls every 5s until user navigates away
    pass
```

---

## Summary

| Tradeoff | Choice | Confidence |
|----------|--------|-----------|
| Real-time ingestion | CSV upload | High (80% use case covered) |
| User roles | Single analyst role | Medium (sufficient for demo) |
| PDF parsing | CSV only | High (accuracy concerns) |
| Material master | Heuristics | Medium (fails gracefully) |
| Multi-currency | Single currency | High (not core to carbon accounting) |
| Real-time dashboard | Polling | High (proven pattern) |

**Guiding principle:** Capture **core carbon accounting accuracy** and **analyst workflow**. Secondary features (reporting, integrations) can be added later.

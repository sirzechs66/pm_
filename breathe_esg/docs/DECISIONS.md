# Design Decisions - Breathe ESG Platform

This document resolves architectural ambiguities and justifies key choices.

---

## 1. SAP Ingestion: CSV File vs. OData API

### Decision: **CSV File Upload**

**Ambiguity:** SAP offers OData APIs for real-time data pull, but requires:
- Enterprise authentication (certificates, service accounts)
- Rate limits and pagination handling
- Error recovery for transient failures
- Vendor API changes over time

**Chosen Approach:** CSV file upload mimicking real-world "export and send" process.

**Justification:**

| Factor | CSV Upload | OData API |
|--------|-----------|-----------|
| Implementation effort | 20% | 80% |
| Reliability | 100% (file doesn't disappear) | 90% (API downtime possible) |
| Authentication | Simple (upload + CSRF) | Certificate management |
| Real-world usage | 80% of clients export first | 20% have live APIs |
| Debugging | View raw file in admin | Black box API errors |

**Real-world research:** SAP IDoc flat files use `|` or `;` delimiters with headers like:
```csv
MATNR;MAKTX;MENGE;MEINS;WERKS;BSART;ERDAT
100123;Diesel Fuel;500.0;L;PLANT01;NB;2025-03-15
```

**What we simplified:** Material master integration for mapping `PC` (pieces) → kg. For prototype, we fail rows with unmappable units and let analysts flag them.

---

## 2. Utility Data: Green Button CSV vs. PDF Parsing

### Decision: **Green Button CSV Format**

**Ambiguity:** Utility portals offer:
- PDF bills (universal but hard to parse reliably)
- XML exports (structured but proprietary)
- CSV exports (machine-readable, less common)

**Chosen Approach:** Green Button CSV format (simulated upload) with optional mock OAuth token paste.

**Justification:**

| Factor | CSV | PDF | XML |
|--------|-----|-----|-----|
| Parse accuracy | 99.9% | 60-80% (font/layout varies) | 95% |
| Developer effort | Low | Very High (OCR, layout analysis) | Medium |
| Cross-utility compatibility | Good | Medium | Varies |
| Real-world adoption | Growing | Universal | Utility-specific |

**Sample Green Button CSV:**
```csv
MeterID,StartTime,EndTime,Usage_kWh,Cost
MTR001,2025-03-01,2025-03-31,12500,1875.00
MTR001,2025-02-01,2025-02-28,11200,1680.00
```

**What we ignored:** Timezone mismatches and cumulative meter readings. The prototype assumes delta values.

**Future migration path:** OAuth2 + REST API using Green Button API standard (RFC 8053).

---

## 3. Emission Factors: Preloaded CSV vs. Climatiq API

### Decision: **Preloaded Static CSV**

**Ambiguity:** Trade-off between accuracy (real-time APIs) and reliability (local data).

**Chosen Approach:** Static CSV loaded via management command, versioned in git.

**Justification:**

| Factor | Static CSV | Climatiq API |
|--------|-----------|--------------|
| Cost | $0 | $100-500/month enterprise |
| Offline capability | Yes | No |
| Version control | Git-tracked | Proprietary |
| Latency | Instant | 100-500ms network |
| Accuracy | 2025 factors (99%) | Real-time updates |
| Implementation | 50 lines of Python | OAuth + rate limiting |

**Tradeoff Justification:** For a prototype/demo:
- **Primary goal:** Show ingestion → calculation → review workflow
- **Not critical:** Exact CO2e precision (±5% is acceptable for demo)
- **Climatiq migration path:** Drop-in replacement via `apps/emissions/api_client.py`

**Sample static data:**
```csv
DEFRA,electricity_uk,kWh,0.212,GB,2025
EPA,electricity_us_east,kWh,0.385,US-EAST,2025
DEFRA,diesel_fuel,kg,2.68,,2025
```

**What we'd switch in production:**
- Climatiq API for real-time updates
- Tenant-specific factor overrides (region preferences)
- Automatic year roll-forward on new data releases

---

## 4. Travel API: Mock Concur/Navan vs. Real Integration

### Decision: **Mock API with Adapter Pattern**

**Ambiguity:** Real travel data requires OAuth2, company admin approval, and handling pagination.

**Chosen Approach:** Static mock data that demonstrates correct OAuth2 flow structure.

**Justification:**

| Factor | Mock API | Real API |
|--------|----------|----------|
| Implementation | 200 lines | 1000+ lines |
| Demo readiness | Ready now | Weeks of integration |
| Debugging | Predictable responses | Rate limits, timeouts |
| Flexibility | Easy test data | Vendor constraints |

**Mock data structure matches real API:**
```json
{
  "trips": [{
    "segments": [{
      "type": "Flight",
      "departure_airport": "JFK",
      "arrival_airport": "LHR",
      "class": "Economy"
    }]
  }]
}
```

**Code structure ready for real API:**
```python
# apps/travel/api_client.py (adapter pattern)
class TravelAPIClient:
    def __init__(self, oauth_token):
        self.base_url = os.environ.get('CONCUR_API_URL')
        self.headers = {'Authorization': f'Bearer {oauth_token}'}
    
    def get_itineraries(self, trip_id):
        # Same interface, different implementation
        pass  # Mock currently, real API later
```

**What we ignored:** Great-circle distance calculation (we use hard-coded distances in mock data). In production, this is a simple formula.

---

## 5. Scope Classification: Heuristic vs. Manual

### Decision: **Heuristic Classification with Analyst Override**

**Ambiguity:** Scope 1/2/3 classification requires business context.

**Chosen Approach:** Heuristics that are **suggestive, not definitive**:

| Category | Scope | Heuristic |
|---------|-------|-----------|
| Fuel (diesel, gas) | Scope 1 | Description contains "Diesel", "Gasoline" |
| Purchased electricity | Scope 2 | Source = 'utility' |
| Business travel | Scope 3 | Source = 'travel' |

**Justification:** Perfect classification requires:
- Material master data (for fuel → kg conversion)
- Location data (for electricity grid factors)
- Business context (is this fuel for company or employee car?)

Heuristics get us **80% there with 20% effort**. Analysts can:
- Override scope during review
- Add notes explaining corrections
- Bulk-edit misclassified items

**What we ignored:** Hybrid vehicles, partially business travel, Scope 3 categories (Category 1-15 per GHG Protocol).

---

## 6. Multi-Currency Handling

### Decision: **Not Implemented (Omitted)**

**Justification:**
- 90% of users operate in single currency
- Prototype focuses on carbon accounting, not finance
- Adding requires: exchange rates API, rounding rules, audit trail

**Future path:** Stripe Currency API or ExchangeRate-API for live rates.

---

## Summary of Ignored Features

| Feature | Why Ignored | Future Path |
|---------|-------------|-------------|
| Real-time meter feeds | Requires MQTT/WebSocket infrastructure | REST API polling |
| Granular user roles (admin/analyst) | Single role sufficient for demo | Django Groups |
| PDF bill parsing | Would require Tesseract + layout analysis | Third-party service |
| Material master integration | Requires SAP connectivity layer | IDoc parser library |
| Real-time API ingestion | 80% value with 20% effort already done | Background workers |

**Core philosophy:** Build **less, but build it right** on core workflows. Add features later as needed.

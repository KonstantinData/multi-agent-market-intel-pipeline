# Cross-Reference System Guide for Agent Developers

## Overview

This guide explains how agents should work with the Cross-Reference System to maintain referential integrity and contribute to comprehensive relationship mapping in the market intelligence pipeline.

## Why Cross-References Matter for Agents

When your agent discovers relationships between entities (companies, customers, competitors), the Cross-Reference System ensures:

- **Data Quality**: No broken references or orphaned entities
- **Audit Compliance**: Traceable relationship chains with evidence
- **Business Intelligence**: Comprehensive market relationship mapping
- **System Reliability**: Consistent data for downstream consumers

## Agent Output Requirements

### Relations Delta Format

When your agent discovers relationships, include them in the `relations_delta` section of your output:

```json
{
  "step_id": "AG-40",
  "run_id": "run_20241201_123456",
  "timestamp_utc": "2024-12-01T12:34:56Z",
  "findings": [
    "Discovered 3 customer relationships for target company"
  ],
  "sources": [
    {
      "publisher": "company-website.com",
      "url": "https://company-website.com/customers",
      "title": "Our Customers",
      "accessed_at_utc": "2024-12-01T12:34:56Z"
    }
  ],
  "relations_delta": [
    {
      "from_entity_id": "TGT-001",
      "to_entity_id": "CUS-001", 
      "relation_type": "customer_of",
      "confidence": 0.9,
      "evidence_count": 2,
      "discovered_by_step": "AG-40"
    }
  ]
}
```

### Required Fields for Relations

Each relation in `relations_delta` must include:

- **from_entity_id**: Source entity ID (use entity keys from registry)
- **to_entity_id**: Target entity ID (use entity keys from registry)  
- **relation_type**: One of the supported types (see below)
- **confidence**: Confidence score (0.0 to 1.0)
- **evidence_count**: Number of evidence sources supporting this relation
- **discovered_by_step**: Your agent's step ID (e.g., "AG-40")

### Supported Relation Types

| Relation Type | Description | Example |
|---------------|-------------|---------|
| `customer_of` | A is a customer of B | "Acme Corp is customer of Target Company" |
| `supplier_of` | A is a supplier to B | "Target Company is supplier of Big Customer" |
| `peer_of` | A and B are in same market segment | "Target Company and Competitor Inc are peers" |
| `partner_of` | A and B have strategic partnership | "Target Company partners with Tech Partner" |
| `competitor_of` | A and B compete directly | "Target Company competes with Rival Corp" |

## Entity Reference Guidelines

### Using Entity Keys

**DO NOT** create new entity IDs in your relations. Instead:

1. **Use entity keys from the registry** for existing entities
2. **Reference entities by domain-based keys** for new entities
3. **Let the registry assign final IDs** during merge operations

```json
// ✅ CORRECT: Use entity key from registry
{
  "from_entity_id": "target-company.com",  // Entity key, not final ID
  "to_entity_id": "customer-corp.com",     // Entity key, not final ID
  "relation_type": "customer_of"
}

// ❌ WRONG: Don't create final IDs
{
  "from_entity_id": "TGT-001",  // Final ID - only registry creates these
  "to_entity_id": "CUS-001",    // Final ID - only registry creates these
  "relation_type": "customer_of"
}
```

### Entity Discovery and Relations

When you discover a new entity that's part of a relationship:

1. **Add the entity to `entities_delta`**
2. **Add the relationship to `relations_delta`**
3. **Use consistent entity keys** in both sections

```json
{
  "entities_delta": [
    {
      "entity_key": "new-customer.com",
      "entity_type": "customer",
      "entity_name": "New Customer Corp",
      "domain": "new-customer.com"
    }
  ],
  "relations_delta": [
    {
      "from_entity_id": "target-company.com",
      "to_entity_id": "new-customer.com",  // Same key as in entities_delta
      "relation_type": "customer_of",
      "confidence": 0.8,
      "evidence_count": 1,
      "discovered_by_step": "AG-40"
    }
  ]
}
```

## Confidence Scoring Guidelines

### Confidence Levels

- **0.9-1.0**: Explicit confirmation (official customer list, press release)
- **0.7-0.8**: Strong evidence (case studies, testimonials, partnerships)
- **0.5-0.6**: Moderate evidence (industry reports, indirect mentions)
- **0.3-0.4**: Weak evidence (social media, unverified sources)
- **0.1-0.2**: Speculation (industry analysis, assumptions)

### Evidence Count

Count distinct evidence sources that support the relationship:

- **1**: Single source (website mention, one article)
- **2**: Two independent sources (website + news article)
- **3+**: Multiple independent confirmations

## Common Patterns by Agent Type

### Customer Discovery Agents (AG-40, AG-42)

```json
{
  "relations_delta": [
    {
      "from_entity_id": "target-company.com",
      "to_entity_id": "customer-a.com",
      "relation_type": "customer_of",
      "confidence": 0.9,
      "evidence_count": 2,
      "discovered_by_step": "AG-40"
    }
  ]
}
```

### Competitor Analysis Agents (AG-41)

```json
{
  "relations_delta": [
    {
      "from_entity_id": "target-company.com", 
      "to_entity_id": "competitor-inc.com",
      "relation_type": "peer_of",
      "confidence": 0.8,
      "evidence_count": 1,
      "discovered_by_step": "AG-41"
    }
  ]
}
```

### Supply Chain Agents (AG-70, AG-71)

```json
{
  "relations_delta": [
    {
      "from_entity_id": "supplier-corp.com",
      "to_entity_id": "target-company.com", 
      "relation_type": "supplier_of",
      "confidence": 0.7,
      "evidence_count": 1,
      "discovered_by_step": "AG-70"
    }
  ]
}
```

## Validation and Error Handling

### What Gets Validated

The Cross-Reference Validator checks:

1. **Entity ID Format**: Proper entity key format
2. **Relation Type**: Valid relation type from supported list
3. **Confidence Range**: Between 0.0 and 1.0
4. **Required Fields**: All mandatory fields present
5. **Referential Integrity**: Referenced entities exist or are being created

### Common Validation Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid relation type" | Used unsupported relation type | Use one of: customer_of, supplier_of, peer_of, partner_of, competitor_of |
| "Confidence must be between 0.0 and 1.0" | Invalid confidence score | Use decimal between 0.0 and 1.0 |
| "Missing required field" | Missing from_entity_id, to_entity_id, or relation_type | Include all required fields |
| "Entity not found in registry" | Referenced entity doesn't exist | Add entity to entities_delta or verify entity key |

### Handling Validation Failures

If your agent's relations_delta fails validation:

1. **Check the validation error message** in the pipeline logs
2. **Fix the specific issue** (format, missing fields, etc.)
3. **Test with a minimal example** before full implementation
4. **Ensure entity keys match** between entities_delta and relations_delta

## Best Practices

### 1. Be Conservative with Confidence

- Start with lower confidence scores and increase based on evidence quality
- Multiple weak sources don't necessarily equal high confidence
- Explicit confirmations deserve high confidence (0.9+)

### 2. Document Your Evidence

- Count distinct, independent sources
- Prefer official sources over third-party mentions
- Include source quality in confidence assessment

### 3. Use Consistent Entity Keys

- Always use domain-based entity keys for consistency
- Don't create final entity IDs (TGT-001, MFR-001, CUS-001)
- Ensure entity keys match between entities_delta and relations_delta

### 4. Handle Edge Cases

```json
// When evidence is unclear, use lower confidence
{
  "relation_type": "customer_of",
  "confidence": 0.3,
  "evidence_count": 1
}

// When relationship is uncertain, document in findings
{
  "findings": [
    "Possible customer relationship with Acme Corp, but evidence is indirect"
  ],
  "relations_delta": [
    {
      "relation_type": "customer_of", 
      "confidence": 0.4,
      "evidence_count": 1
    }
  ]
}
```

### 5. Test Your Relations

Before implementing relationship discovery:

1. **Create test cases** with known relationships
2. **Validate output format** against the schema
3. **Check entity key consistency** 
4. **Verify confidence scoring** makes sense

## Debugging Cross-Reference Issues

### Common Issues and Solutions

**Issue**: "Dangling reference" error
**Solution**: Ensure all referenced entities exist in entities_delta or registry

**Issue**: Relations not appearing in final matrix
**Solution**: Check that validation passed and entities were properly merged

**Issue**: Confidence scores seem wrong in output
**Solution**: Verify confidence calculation logic and evidence counting

### Debugging Tools

1. **Check validation logs** for specific error messages
2. **Review registry merge results** to see if entities were created
3. **Examine cross-reference matrix** in exports to verify relationships
4. **Use unit tests** to validate relation format before integration

## Integration with Pipeline

### Validation Timing

Your relations_delta is validated:

1. **Immediately after agent execution** (format and basic checks)
2. **During registry merge** (entity existence checks)  
3. **Before final export** (comprehensive integrity validation)

### Error Propagation

- **Hard validation failures** stop the pipeline
- **Warnings** are logged but don't stop execution
- **Validation results** are included in run artifacts for debugging

### Export Integration

Your relationships appear in:

- **crossref_matrix.json**: Complete relationship matrix
- **relationships_list.json**: Flat list of all relationships
- **adjacency_matrix.json**: Graph representation for analysis
- **report.md**: Business-readable relationship summaries

## Examples and Templates

### Minimal Relation Example

```json
{
  "relations_delta": [
    {
      "from_entity_id": "target-company.com",
      "to_entity_id": "customer.com",
      "relation_type": "customer_of",
      "confidence": 0.8,
      "evidence_count": 1,
      "discovered_by_step": "AG-40"
    }
  ]
}
```

### Complete Agent Output Template

```json
{
  "step_id": "AG-XX",
  "run_id": "{{ run_id }}",
  "timestamp_utc": "{{ timestamp }}",
  "findings": [
    "Discovered {{ count }} relationships for target company"
  ],
  "sources": [
    {
      "publisher": "{{ source_domain }}",
      "url": "{{ source_url }}",
      "title": "{{ source_title }}",
      "accessed_at_utc": "{{ timestamp }}"
    }
  ],
  "entities_delta": [
    {
      "entity_key": "{{ entity_domain }}",
      "entity_type": "{{ entity_type }}",
      "entity_name": "{{ entity_name }}",
      "domain": "{{ entity_domain }}"
    }
  ],
  "relations_delta": [
    {
      "from_entity_id": "{{ from_entity_key }}",
      "to_entity_id": "{{ to_entity_key }}",
      "relation_type": "{{ relation_type }}",
      "confidence": {{ confidence_score }},
      "evidence_count": {{ evidence_count }},
      "discovered_by_step": "AG-XX"
    }
  ]
}
```

## Getting Help

### Documentation References

- **Architecture**: `docs/architecture/07_cross_reference_system.md`
- **ADR**: `docs/adr/ADR-005-cross-reference-system.md`
- **Schema**: `configs/contracts/crossref_schema.json`
- **Tests**: `tests/unit/test_crossref_integrity.py`

### Common Questions

**Q**: Can I create relationships between entities my agent didn't discover?
**A**: Yes, as long as the entities exist in the registry or are being created by another agent.

**Q**: What if I'm not sure about the relationship type?
**A**: Use the most specific type that fits, or use `peer_of` for general associations.

**Q**: How do I handle bidirectional relationships?
**A**: Create separate relations for each direction if both are meaningful.

**Q**: Can I update relationships discovered by other agents?
**A**: No, each agent should only create new relationships. The system handles deduplication.

For additional questions or issues, refer to the architecture documentation or create an issue in the project repository.
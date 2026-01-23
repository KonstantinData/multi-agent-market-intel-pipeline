# Regional Legal Identity Agents Overview

## Introduction
The Regional Legal Identity Agents (AG-10.0 through AG-10.4) provide specialized legal entity extraction capabilities for different geographical regions. Each agent is optimized for region-specific legal forms, address formats, and regulatory requirements.

## Agent Architecture

### Independent Execution
- Each agent runs independently based on UI checkbox selection
- No dependencies between regional agents
- Parallel execution supported for performance
- Results merged automatically in entity registry

### Conditional Activation
- **UI Control**: 5 checkboxes in Streamlit interface
- **Pipeline Integration**: DAG loader filters agents based on case_input
- **Default Behavior**: Only Germany (AG-10.0) enabled by default
- **Flexible Selection**: Users can enable any combination of regions

## Regional Agents Summary

| Agent | Region | Countries | Default | Legal Forms | Postal Format |
|-------|--------|-----------|---------|-------------|---------------|
| **AG-10.0** | Germany | DE | ✅ Enabled | GmbH, AG, SE, UG | 5-digit (70173) |
| **AG-10.1** | DACH | AT, CH | ❌ Disabled | e.U., OG, Einzelfirma | 4-digit (1010, 8001) |
| **AG-10.2** | Europe | EU-27 | ❌ Disabled | SAS, SpA, BV, AB | Country-specific |
| **AG-10.3** | UK | GB | ❌ Disabled | Ltd, PLC, LLP | UK format (SW1A 1AA) |
| **AG-10.4** | USA | US | ❌ Disabled | Inc, Corp, LLC | ZIP (12345-6789) |

## Common Functionality

### Input Processing
All agents receive:
- `company_name_canonical`: Normalized company name from AG-00
- `web_domain_normalized`: Normalized domain from AG-00  
- `meta_target_entity_stub`: Target entity information from AG-00
- `registry_snapshot`: Current entity registry state (optional)

### Output Structure
All agents produce:
```json
{
  "entities_delta": [
    {
      "entity_key": "domain:company.com",
      "entity_type": "target_company",
      "entity_name": "Complete Legal Name",
      "legal_form": "Extracted Legal Form",
      "street_name": "Street Name",
      "house_number": "House Number",
      "postal_code": "Postal Code",
      "city": "City",
      "state": "State/Region",
      "country": "Country Name",
      "country_code": "ISO Code"
    }
  ],
  "findings": [
    {
      "legal_name": "Complete Legal Name",
      "legal_form": "Extracted Legal Form",
      "country_detected": "ISO Code"
    }
  ],
  "sources": [
    {
      "publisher": "Source Name",
      "url": "Source URL",
      "title": "Source Title",
      "accessed_at_utc": "ISO Timestamp"
    }
  ]
}
```

### Entity Registry Integration
- **Entity Updates**: Complete legal names override intake names
- **Merge Logic**: More complete information takes precedence
- **Key Preservation**: Domain-based entity keys maintained
- **Deduplication**: Automatic handling of duplicate entities

## Regional Specializations

### AG-10.0 Germany
- **Focus**: German Impressum extraction
- **Legal Forms**: 9 German legal forms (GmbH, AG, SE, etc.)
- **Address**: German street/PLZ format validation
- **Sources**: Impressum pages, legal notices

### AG-10.1 DACH Extension  
- **Focus**: Austria & Switzerland
- **Legal Forms**: Country-specific (e.U. for AT, Einzelfirma for CH)
- **Address**: 4-digit postal codes, Top/Tür notation
- **Sources**: Multi-language legal documents

### AG-10.2 Europe
- **Focus**: EU member states (excluding DE, AT, CH)
- **Legal Forms**: Country-specific (SAS, SpA, BV, etc.)
- **Address**: Diverse European postal formats
- **Sources**: European legal notices

### AG-10.3 UK
- **Focus**: United Kingdom post-Brexit
- **Legal Forms**: British forms (Ltd, PLC, LLP, etc.)
- **Address**: UK postcode validation
- **Sources**: Companies House compatible data

### AG-10.4 USA
- **Focus**: United States
- **Legal Forms**: American forms (Inc, Corp, LLC, etc.)
- **Address**: ZIP code validation, state codes
- **Sources**: Corporate headquarters information

## Data Quality & Validation

### Format Validation
- **Postal Codes**: Region-specific pattern matching
- **Legal Forms**: Recognized forms per jurisdiction
- **Address Components**: Country-appropriate formats
- **Entity IDs**: Consistent domain-based keys

### Error Handling
- **Missing Data**: Returns "n/v" for unavailable information
- **Invalid Regions**: Returns null if country doesn't match
- **API Failures**: Provides fallback data
- **Format Errors**: Validates and corrects common issues

### Evidence Requirements
- **Source Attribution**: All data linked to sources
- **Timestamp Tracking**: Access times recorded
- **URL References**: Source URLs provided
- **Publisher Information**: Source publishers identified

## Business Applications

### Use Cases
- **Legal Due Diligence**: Accurate legal entity information
- **Address Verification**: Validated business addresses
- **Compliance Checking**: Region-specific legal requirements
- **Market Research**: Comprehensive company profiles

### Benefits
- **Regional Expertise**: Specialized knowledge per region
- **Flexible Coverage**: Select only needed regions
- **Performance Optimization**: Avoid unnecessary searches
- **Cost Efficiency**: Targeted API usage

## Integration Guidelines

### UI Configuration
```typescript
// Checkbox configuration
region_germany: boolean = true    // Default enabled
region_dach: boolean = false     // User selectable
region_europe: boolean = false   // User selectable  
region_uk: boolean = false       // User selectable
region_usa: boolean = false      // User selectable
```

### Pipeline Execution
```python
# Conditional execution based on checkboxes
if case_input.get("region_germany", False):
    execute_agent("AG-10.0")
if case_input.get("region_dach", False):
    execute_agent("AG-10.1")
# ... etc for other regions
```

### Registry Merging
```python
# Automatic entity merging
if new_legal_name_more_complete(existing, new):
    entity.update(new_legal_data)
    entity.legal_form = extract_legal_form(entity.entity_name)
```

## Future Enhancements

### Planned Features
- **Additional Regions**: Asia-Pacific, Latin America
- **Legal Form Expansion**: More specialized legal entities
- **Regulatory Integration**: Direct API connections to registries
- **Multi-Language Support**: Enhanced language processing

### Scalability Considerations
- **Performance Optimization**: Parallel execution capabilities
- **Cache Integration**: Reduce redundant API calls
- **Rate Limiting**: Respect API usage limits
- **Error Recovery**: Robust failure handling

## Conclusion
The Regional Legal Identity Agents provide comprehensive, flexible, and accurate legal entity extraction capabilities tailored to specific geographical regions and regulatory environments. The modular design enables efficient, targeted research while maintaining data quality and compliance standards.
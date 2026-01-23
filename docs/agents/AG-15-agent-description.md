# AG-15 – Network Mapper

## Purpose

Expands the lead universe by identifying related companies (competitors, customers, suppliers) using GPT-4o-powered research and structured relationship mapping.

## Key Features
- **GPT-4o Integration**: Uses OpenAI's most capable model for accurate network research
- **Structured Outputs**: JSON schema validation for reliable entity and relationship parsing
- **Multi-Industry Support**: Medical Technology, Mechanical Engineering, Electrical Engineering
- **Scalable Discovery**: Up to 10 peers and 10 customers per run
- **Evidence-Based Relations**: All relationships backed by AI reasoning and sources

## Research Methodology
- **AI-Powered Analysis**: GPT-4o analyzes company context to identify realistic business relationships
- **Industry-Focused**: Searches within core B2B manufacturing sectors
- **Relationship Validation**: Each discovered entity includes rationale for the business connection
- **Fallback Support**: Graceful degradation when OpenAI API is unavailable

## Discovered Entities
- **Peers/Competitors**: Companies in same industry with similar products/services
- **Customers**: Downstream buyers who purchase from or could purchase from target company
- **Relationship Types**: "peer" (same sector) and "customer" (buyer relationship)

### Responsibilities

* **Network Discovery:** Identify peer companies (same sector) and downstream customers using AI research
* **Relationship Mapping:** Establish explicit connections via `relations_delta` with business rationale
* **Strategic Sourcing:** Verify business sectors and supply chain connections through AI analysis
* **Structured Emission:** Use `n/v` where relationships cannot be verified through research

### Outputs

* **entities_delta:** New companies with relationship_type (peer/customer) and rationale
* **relations_delta:** Specific business relationships ("Same Business Sector", "Supplier to")
* **findings:** Network expansion summary with entity counts
* **sources:** OpenAI API attribution for AI-generated research

### Example Output

```json
{
  "entities_delta": [
    {
      "entity_id": "PEER-001",
      "entity_key": "peer-001", 
      "entity_name": "Festo AG & Co. KG",
      "industry": "Mechanical Engineering",
      "relationship_type": "peer",
      "rationale": "Leading automation technology provider with similar mechanical engineering solutions"
    },
    {
      "entity_id": "CUSTOMER-001",
      "entity_key": "customer-001",
      "entity_name": "Siemens Healthineers", 
      "industry": "Medical Technology",
      "relationship_type": "customer",
      "rationale": "Medical technology company utilizing precision components in their devices"
    }
  ],
  "findings": [{
    "network_expansion_summary": "AI research identified 6 related companies for IMS Gear SE & Co. KGaA",
    "peer_count": 3,
    "customer_count": 3
  }]
}
```

### Gatekeeper Expectations

* **Core Industries Only**: Medical Technology, Mechanical Engineering, Electrical Engineering
* **Required Relations**: All new entities must have corresponding relations_delta entries
* **Source Attribution**: OpenAI API calls properly documented as sources
* **Evidence-Based**: Rationale required for each discovered relationship

### Failure Conditions

* **Missing OpenAI API Key**: Agent requires OPEN-AI-KEY environment variable
* **Entities Without Relations**: New entities added without corresponding relations_delta
* **Invalid Industry Scope**: Companies outside defined core industries
* **Missing Required Fields**: network_expansion_summary field required in findings

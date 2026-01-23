# AG-10 – Regional Legal Identity Agents

## Overview
The AG-10 series consists of 5 independent regional agents that extract verifiable legal identity and contact information for target companies. Each agent specializes in specific geographical regions and their legal requirements.

## Regional Agents

### AG-10.0 – Germany
- **Focus**: German legal forms and Impressum extraction
- **Legal Forms**: GmbH, AG, SE, KG, OHG, GbR, eK, eG, SE & Co. KGaA
- **Address Format**: 5-digit postal codes (PLZ)
- **Specialization**: German Impressum pages, DUNS numbers

### AG-10.1 – DACH (Austria & Switzerland)
- **Focus**: Austrian and Swiss legal entities
- **Legal Forms**: GmbH (AT/CH), AG (AT/CH), KG, OG
- **Address Format**: 4-digit postal codes, Top/Tür notation
- **Specialization**: DACH-specific corporate structures

### AG-10.2 – Europe (EU)
- **Focus**: European Union member states
- **Legal Forms**: SAS, SpA, BV, SA, SL, AS, ApS, Oy, AB
- **Address Format**: Country-specific postal systems
- **Specialization**: EU corporate law compliance

### AG-10.3 – United Kingdom
- **Focus**: British legal entities
- **Legal Forms**: Ltd, PLC, LLP, CIC, CIO
- **Address Format**: UK postcode validation (SW1A 1AA format)
- **Specialization**: Companies House integration

### AG-10.4 – United States
- **Focus**: US corporate entities
- **Legal Forms**: Inc, Corp, LLC, LP, LLP
- **Address Format**: ZIP code processing (5-digit + 4-digit)
- **Specialization**: State-specific incorporation rules

## Conditional Activation
Agents are activated based on UI checkbox selections:
- Users select which regions to search
- Pipeline filters agents based on case_input regional flags
- Multiple agents can run in parallel for comprehensive coverage

## Common Features
- **GPT-4o Integration**: All agents use OpenAI's most capable model
- **Multi-Host Support**: Try both `domain.com` and `www.domain.com`
- **Evidence-Based Validation**: Only verified data accepted
- **Fallback Integration**: Use case_input when web extraction fails
- **Legal Form Extraction**: Automatic extraction from complete company names

## Data Sources
- Primary: Company websites (impressum, legal, contact, about pages)
- Extended: Regional corporate registries and legal databases
- Fallback: UI input data for address, phone, industry

## Extracted Fields
- **Legal Identity**: Legal name, legal form, founding year, registration signals
- **Contact Data**: Street address, city, postal code, phone number
- **Corporate Info**: Industry, social media links
- **Regional Specifics**: Country-specific legal identifiers

## Entity Registry Integration
- All agents update the same target entity (TGT-001)
- More complete legal names override intake names
- Regional data merged with conflict resolution
- Provenance tracking for all updates

## Outputs (Per Agent)
- entities_delta: Target company entity with regional legal data
- relations_delta: (empty for AG-10 series)
- findings: Regional extraction results
- sources: Consulted web pages
- field_sources: Per-field source attribution

## Gatekeeper Expectations
- Schema-compliant output with regional legal fields
- Evidence-based validation (no invented facts)
- Proper source attribution for all claims
- ASCII-only output (regional characters transliterated)
- Regional address format validation

## Failure Conditions
- Missing OPEN-AI-KEY environment variable
- Invalid domain format in case input
- OpenAI API failures
- Regional checkbox validation failures
- Contract validation failures

# AG-10 – Identity and Legal

## Purpose
Extracts verifiable legal identity signals and basic contact information for the target company using GPT-4o and evidence-based validation.

## Key Features
- **GPT-4o Integration**: Uses OpenAI's most capable model for accurate company data extraction
- **Multi-Host Support**: Tries both `domain.com` and `www.domain.com` for robust content discovery
- **Evidence-Based Validation**: Only accepts data that can be verified in the source material
- **UI Fallback Integration**: Uses case_input data when web extraction fails
- **Structured Outputs**: JSON schema validation for reliable parsing

## Data Sources
- Primary: Company websites (impressum, legal, contact, about pages)
- Extended: Company history and corporate pages for founding year research
- Fallback: UI input data for address, phone, industry

## Extracted Fields
- **Legal Identity**: Legal name, legal form, founding year, registration signals
- **Contact Data**: Street address, city, postal code, phone number
- **Corporate Info**: Industry, social media links (LinkedIn, Facebook, Twitter)

## Responsibilities
- Extract legal identity from official company pages
- Validate all extracted data against source evidence
- Use case_input as fallback for missing contact information
- Emit structured outputs with proper source attribution
- Use 'n/v' where information is not verifiable

## Outputs
- entities_delta: Target company entity with enriched legal and contact data
- relations_delta: (empty for AG-10)
- findings: Summary of extraction results
- sources: All consulted web pages
- field_sources: Per-field source attribution

## Gatekeeper Expectations
- Schema-compliant output with required legal identity fields
- Evidence-based validation (no invented facts)
- Proper source attribution for all claims
- ASCII-only output (German characters transliterated)

## Failure Conditions
- Missing OPEN-AI-KEY environment variable
- Invalid domain format in case input
- OpenAI API failures
- Contract validation failures

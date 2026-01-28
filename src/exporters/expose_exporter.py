"""
    DESCRIPTION
    -----------
    expose_exporter builds the final Exposé artifacts from the aggregated registry snapshot.

Outputs:
- exports/entities.json: deterministic entity + relation list
- exports/report.md: human-readable markdown report

    """

from __future__ import annotations

from typing import Any, Dict, List
import re


#note: Generate likely domain from company name for follow-up research
def _generate_domain_from_name(company_name: str) -> str:
    """
    Generate a likely web domain from company name for research purposes.
    """
    if not company_name or company_name == 'n/a':
        return 'n/a'
    
    # Clean company name: remove legal forms and special characters
    name = re.sub(r'\b(GmbH|AG|SE|Co\.?|KG|KGaA|Inc\.?|Corp\.?|Ltd\.?|LLC|&)\b', '', company_name, flags=re.IGNORECASE)
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name).strip()
    
    # Take first significant word, convert to lowercase
    words = [w for w in name.split() if len(w) > 2]
    if not words:
        return 'n/a'
    
    domain_name = words[0].lower()
    return f"{domain_name}.com"


#note: Convert the registry snapshot into a stable JSON export payload.
def build_entities_export(registry_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    #note: The export payload is intentionally stable and schema-friendly for CRM ingestion.
    """
    entities = registry_snapshot.get("entities") or []
    relations = registry_snapshot.get("relations") or []

    #note: Sort entities with target_company first, then alphabetically by entity_id.
    def _sort_key(e: Dict[str, Any]) -> tuple:
        entity_type = str(e.get("entity_type", ""))
        entity_id = str(e.get("entity_id", ""))
        # Target company comes first (0), all others after (1)
        priority = 0 if entity_type == "target_company" else 1
        return (priority, entity_id)
    
    entities = sorted([e for e in entities if isinstance(e, dict)], key=_sort_key)
    relations = sorted([r for r in relations if isinstance(r, dict)], key=lambda x: str(x))

    return {
        "entities": entities,
        "relations": relations,
        "meta": {
            "namespace": registry_snapshot.get("namespace"),
        },
    }


#note: Render a comprehensive professional business report from the registry snapshot.
def build_report_markdown(registry_snapshot: Dict[str, Any]) -> str:
    """
    Professional business intelligence report including all entity_registry.json data.
    """
    entities = registry_snapshot.get("entities") or []
    findings = registry_snapshot.get("findings") or []

    # Find target company
    target = None
    for e in entities:
        if isinstance(e, dict) and (str(e.get("entity_id")) == "TGT-001" or e.get("entity_type") == "target_company"):
            target = e
            break

    company_name = (target or {}).get("legal_name") or (target or {}).get("entity_name") or "Unknown Company"
    # Use domain from target entity (preserved from intake)
    domain = (target or {}).get("domain") or "n/a"

    lines: List[str] = []
    lines.append("# Business Intelligence Report")
    lines.append("")
    lines.append(f"## {company_name}")
    lines.append(f"**Domain:** {domain}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. Company Profile
    lines.append("## 1. Company Profile")
    lines.append("")
    if target:
        lines.append(f"**Legal Name:** {target.get('legal_name', 'n/a')}")
        lines.append(f"**Legal Form:** {target.get('legal_form', 'n/a')}")
        lines.append(f"**Founded:** {target.get('founding_year', 'n/a')}")
        lines.append("")
        
    # 2. Contact Information
    lines.append("## 2. Contact Information")
    lines.append("")
    if target:
        street = target.get('street_name', target.get('street_address', 'n/a'))
        house_num = target.get('house_number', '')
        if street != 'n/a' and house_num and house_num != 'n/a':
            street_display = f"{street} {house_num}"
        else:
            street_display = street
            
        lines.append(f"{street_display}")
        lines.append(f"{target.get('postal_code', 'n/a')} {target.get('city', 'n/a')}")
        lines.append(f"{target.get('country', 'n/a')}")
        lines.append("")
        lines.append(f"**Phone:** {target.get('phone_number', 'n/a')}")
        lines.append(f"**Email:** {target.get('email', 'n/a')}")
        lines.append("")
    
    # 3. Industry Classification
    if target and target.get('liquisto_class') and target.get('liquisto_class') != 'n/v':
        lines.append("## 3. Industry Classification")
        lines.append("")
        lines.append(f"**{target.get('liquisto_class_label', 'n/a')}**")
        lines.append("")
        
        # WZ/NACE Codes
        wz_codes = target.get('wz_codes', [])
        if wz_codes:
            lines.append("**WZ/NACE Codes:**")
            for code in wz_codes:
                lines.append(f"- {code.get('code', 'n/a')}: {code.get('label', 'n/a')}")
            lines.append("")
        
    # 4. Firmographics
    if target:
        has_firmographics = any([
            target.get('firmographics_headcount'),
            target.get('firmographics_financial'),
            target.get('firmographics_market'),
            target.get('firmographics_operational')
        ])
        
        if has_firmographics:
            lines.append("## 4. Firmographics")
            lines.append("")
            
            # Headcount
            if target.get('firmographics_headcount'):
                hc = target['firmographics_headcount']
                if hc.get('total_employees') and hc['total_employees'] != 'n/v':
                    lines.append(f"**Employees:** {hc['total_employees']}")
            
            # Financial
            if target.get('firmographics_financial'):
                fin = target['firmographics_financial']
                if fin.get('revenue_last_fy') and fin['revenue_last_fy'] != 'n/v':
                    lines.append(f"**Revenue:** {fin['revenue_last_fy']}")
                if fin.get('revenue_trend_yoy') and fin['revenue_trend_yoy'] != 'n/v':
                    lines.append(f"**Revenue Trend:** {fin['revenue_trend_yoy']}")
            
            # Market
            if target.get('firmographics_market'):
                mkt = target['firmographics_market']
                if mkt.get('regional_coverage') and mkt['regional_coverage'] != 'n/v':
                    lines.append(f"**Regional Coverage:** {mkt['regional_coverage']}")
            
            # Operational
            if target.get('firmographics_operational'):
                ops = target['firmographics_operational']
                if ops.get('legal_entities') and ops['legal_entities'] != 'n/v':
                    entities = ops['legal_entities']
                    if isinstance(entities, list):
                        lines.append(f"**Legal Entities:** {len(entities)}")
            
            lines.append("")
    

    # 5. Official Registration
    if target and target.get('register_number') and target.get('register_number') != 'n/a':
        lines.append("## 5. Official Registration")
        lines.append("")
        lines.append(f"**Register Court:** {target.get('register_court', 'n/a')}")
        lines.append(f"**Register Number:** {target.get('register_number', 'n/a')}")
        lines.append(f"**Register Type:** {target.get('register_type', 'n/a')}")
        lines.append("")
        
        publications = target.get('northdata_publications', [])
        if publications:
            lines.append("**Recent Publications:**")
            lines.append("")
            for pub in publications[:5]:
                lines.append(f"- {pub.get('date', 'n/a')}: {pub.get('text', 'n/a')}")
            lines.append("")
    
    # 6. Financial Analysis
    financial_data = None
    for f in findings:
        if isinstance(f, dict) and f.get('time_series'):
            financial_data = f
            break
    
    if financial_data:
        lines.append("## 6. Financial Analysis")
        lines.append("")
        
        lines.append("| Year | Revenue | EBITDA | Net Debt | CAPEX |")
        lines.append("|------|---------|--------|----------|-------|")
        for year_data in financial_data.get('time_series', []):
            lines.append(f"| {year_data.get('year', 'n/a')} | {year_data.get('revenue', 'n/a')} | {year_data.get('ebitda', 'n/a')} | {year_data.get('net_debt', 'n/a')} | {year_data.get('capex', 'n/a')} |")
        lines.append("")
        
        lines.append(f"**Trend:** {financial_data.get('trend_summary', 'n/a')}")
        lines.append("")

    # 7. Business Network
    customers = [e for e in entities if isinstance(e, dict) and e.get('relationship_type') == 'customer']
    peers = [e for e in entities if isinstance(e, dict) and e.get('relationship_type') == 'peer']
    
    if customers or peers:
        lines.append("## 7. Business Network")
        lines.append("")

    
    if customers:
        lines.append("### Customers")
        lines.append("")
        for customer in sorted(customers[:10], key=lambda x: x.get('entity_name', '')):
            name = customer.get('entity_name', 'n/a')
            domain = _generate_domain_from_name(name)
            lines.append(f"- **{name}** ({domain})")
        lines.append("")
    
    if peers:
        lines.append("### Competitors")
        lines.append("")
        for peer in sorted(peers[:10], key=lambda x: x.get('entity_name', '')):
            name = peer.get('entity_name', 'n/a')
            domain = _generate_domain_from_name(name)
            lines.append(f"- **{name}** ({domain})")
        lines.append("")



    return "\n".join(lines)

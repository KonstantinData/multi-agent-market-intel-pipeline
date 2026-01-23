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

    #note: Ensure deterministic sorting by entity_id if present.
    entities = sorted([e for e in entities if isinstance(e, dict)], key=lambda x: str(x.get("entity_id") or ""))
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
    sources = registry_snapshot.get("sources") or []

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
    lines.append(f"## {company_name}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"This report provides comprehensive market intelligence for **{company_name}** ({domain}), ")
    lines.append("including company profile, financial analysis, competitive landscape, and customer relationships.")
    lines.append("")

    # Company Profile
    lines.append("## Company Profile")
    lines.append("")
    if target:
        lines.append(f"**Legal Name:** {target.get('legal_name', 'n/a')}")
        lines.append(f"**Domain:** {domain}")
        lines.append(f"**Legal Form:** {target.get('legal_form', 'n/a')}")
        lines.append(f"**Industry:** {target.get('industry', 'n/a')}")
        lines.append("")
        
    # Contact Information
    lines.append("## Contact Information")
    lines.append("")
    if target:
        lines.append(f"**Street:** {target.get('street_name', 'n/a')} {target.get('house_number', 'n/a')}")
        lines.append(f"**Post Code:** {target.get('postal_code', 'n/a')}")
        lines.append(f"**City:** {target.get('city', 'n/a')}")
        lines.append(f"**Country:** {target.get('country', 'n/a')}")
        lines.append(f"**Phone:** {target.get('phone_number', 'n/a')}")
        lines.append("")
        
    # Company History
    lines.append("## Company History")
    lines.append("")
    if target:
        lines.append(f"**Founding Year:** {target.get('founding_year', 'n/a')}")
        lines.append("")
        
        # Company size profile
        if target.get('attributes', {}).get('company_size_profile'):
            profile = target['attributes']['company_size_profile']['target_company']
            lines.append("### Company Size & Operations")
            lines.append("")
            metrics = profile.get('quantitative_metrics', {})
            lines.append(f"**Annual Revenue:** {metrics.get('annual_revenue_eur', 'n/a')}")
            lines.append(f"**Production Sites:** {metrics.get('number_of_production_sites', 'n/a')}")
            lines.append(f"**PPE Value:** {metrics.get('ppe_value_eur', 'n/a')}")
            lines.append(f"**MRO Inventory Value:** {metrics.get('mro_inventory_value_eur', 'n/a')}")
            lines.append("")
    
    # Data sources for company profile
    profile_sources = [s for s in sources if isinstance(s, dict) and s.get('url', '').find('imsgear.com') != -1]
    if profile_sources:
        lines.append("**Data Sources:**")
        for s in profile_sources[:5]:  # Limit to 5 sources
            title = s.get('title') or s.get('source_name') or s.get('url', 'n/a')
            lines.append(f"- {title}")
        lines.append("")
    
    # Financial Analysis
    financial_data = None
    for f in findings:
        if isinstance(f, dict) and f.get('time_series'):
            financial_data = f
            break
    
    if financial_data:
        lines.append("## Financial Analysis")
        lines.append("")
        lines.append(f"**Currency:** {financial_data.get('currency', 'n/a')}")
        lines.append(f"**Equity Ratio 2024:** {financial_data.get('equity_ratio_2024', 'n/a')}")
        lines.append("")
        lines.append(f"**Trend Summary:** {financial_data.get('trend_summary', 'n/a')}")
        lines.append("")
        
        lines.append("### Financial Performance (3-Year Overview)")
        lines.append("")
        lines.append("| Year | Revenue | EBITDA | Net Debt | CAPEX |")
        lines.append("|------|---------|--------|----------|-------|")
        for year_data in financial_data.get('time_series', []):
            lines.append(f"| {year_data.get('year', 'n/a')} | {year_data.get('revenue', 'n/a')} | {year_data.get('ebitda', 'n/a')} | {year_data.get('net_debt', 'n/a')} | {year_data.get('capex', 'n/a')} |")
        lines.append("")
        
        # Financial profile from entities
        for e in entities:
            if isinstance(e, dict) and e.get('financial_profile'):
                fp = e['financial_profile']
                lines.append("### Financial Profile Analysis")
                lines.append("")
                lines.append(f"**Revenue Trend:** {fp.get('revenue_trend', 'n/a')}")
                lines.append(f"**Profitability Trend:** {fp.get('profitability_trend', 'n/a')}")
                lines.append(f"**Leverage Trend:** {fp.get('leverage_trend', 'n/a')}")
                lines.append(f"**Investment Pattern:** {fp.get('investment_pattern', 'n/a')}")
                lines.append(f"**Working Capital Pressure:** {fp.get('working_capital_pressure', 'n/a')}")
                lines.append("")
                break
    
    # Data sources for financial analysis
    financial_sources = [s for s in sources if isinstance(s, dict) and 'financial' in s.get('title', '').lower()]
    if financial_sources:
        lines.append("**Data Sources:**")
        for s in financial_sources[:3]:  # Limit to 3 sources
            title = s.get('title') or s.get('source_name') or s.get('url', 'n/a')
            lines.append(f"- {title}")
        lines.append("")

    # Market Position & Network
    customers = [e for e in entities if isinstance(e, dict) and e.get('relationship_type') == 'customer']
    peers = [e for e in entities if isinstance(e, dict) and e.get('relationship_type') == 'peer']
    
    if customers or peers:
        lines.append("## Market Position & Business Network")
        lines.append("")
        
        network_summary = None
        for f in findings:
            if isinstance(f, dict) and f.get('network_expansion_summary'):
                network_summary = f
                break
        
        if network_summary:
            lines.append(f"**Network Analysis:** {network_summary.get('network_expansion_summary', 'n/a')}")
            lines.append(f"**Total Customers Identified:** {network_summary.get('customer_count', 0)}")
            lines.append(f"**Total Peers/Competitors:** {network_summary.get('peer_count', 0)}")
            lines.append("")
    
    if customers:
        lines.append("### Key Customers")
        lines.append("")
        for customer in sorted(customers[:10], key=lambda x: x.get('entity_name', '')):  # Limit to 10
            name = customer.get('entity_name', 'n/a')
            # Generate domain from company name
            domain = _generate_domain_from_name(name)
            lines.append(f"**{name}**")
            lines.append(f"- Industry: {customer.get('industry', 'n/a')}")
            lines.append(f"- Domain: {domain}")
            lines.append(f"- Relationship: {customer.get('rationale', 'n/a')}")
            lines.append("")
        
        # Data sources for customers
        network_sources = [s for s in sources if isinstance(s, dict) and 'network' in s.get('title', '').lower()]
        if network_sources:
            lines.append("**Data Sources:**")
            for s in network_sources[:3]:
                title = s.get('title') or s.get('source_name') or s.get('url', 'n/a')
                lines.append(f"- {title}")
            lines.append("")
    
    if peers:
        lines.append("### Competitors & Peers")
        lines.append("")
        for peer in sorted(peers[:10], key=lambda x: x.get('entity_name', '')):  # Limit to 10
            name = peer.get('entity_name', 'n/a')
            # Generate domain from company name
            domain = _generate_domain_from_name(name)
            lines.append(f"**{name}**")
            lines.append(f"- Industry: {peer.get('industry', 'n/a')}")
            lines.append(f"- Domain: {domain}")
            lines.append(f"- Competitive Position: {peer.get('rationale', 'n/a')}")
            lines.append("")
        
        # Data sources for competitors
        if network_sources:
            lines.append("**Data Sources:**")
            for s in network_sources[:3]:
                title = s.get('title') or s.get('source_name') or s.get('url', 'n/a')
                lines.append(f"- {title}")
            lines.append("")

    # Research Methodology & Data Sources
    lines.append("## Research Methodology")
    lines.append("")
    lines.append("This report was generated using an automated multi-agent market intelligence pipeline that:")
    lines.append("")
    lines.append("- Analyzes public company information and financial data")
    lines.append("- Maps business relationships and competitive landscape")
    lines.append("- Validates findings through multiple data sources")
    lines.append("- Provides evidence-based insights with source attribution")
    lines.append("")
    
    if sources:
        lines.append("### All Data Sources")
        lines.append("")
        unique_sources = set()
        for s in sources:
            if isinstance(s, dict):
                url = s.get('url', 'n/a')
                title = s.get('title') or s.get('source_name') or url
                if url != 'n/a' and url not in unique_sources:
                    unique_sources.add(url)
                    lines.append(f"- {title}")
        lines.append("")

    # Report Metadata
    lines.append("---")
    lines.append("")
    lines.append("### Report Statistics")
    lines.append("")
    lines.append(f"- **Total Entities Analyzed:** {len([e for e in entities if isinstance(e, dict)])}")
    lines.append(f"- **Data Points Collected:** {len([f for f in findings if isinstance(f, dict)])}")
    lines.append(f"- **Sources Consulted:** {len([s for s in sources if isinstance(s, dict)])}")
    lines.append(f"- **Report Generated:** {registry_snapshot.get('namespace', 'n/a')}")
    lines.append("")
    lines.append("*This report contains publicly available information and AI-generated analysis. All financial figures and business relationships should be independently verified.*")
    lines.append("")

    return "\n".join(lines)

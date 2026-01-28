"""
    DESCRIPTION
    -----------
    step_registry maps pipeline step IDs (AG-XX) to their Python Agent entrypoints.
This provides a single, auditable wiring layer between configs/pipeline/dag.yml and code.
    """

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type

from src.agents.common.base_agent import BaseAgent


#note: A structured pointer to a concrete agent class.
@dataclass(frozen=True)
class StepEntrypoint:
    module_path: str
    class_name: str = "Agent"


#note: Canonical mapping between step IDs and agent modules in this repo.
STEP_ENTRYPOINTS: Dict[str, StepEntrypoint] = {
    "AG-00": StepEntrypoint("src.agents.ag00_intake_normalization.agent", "Agent"),
    "AG-01": StepEntrypoint("src.agents.ag01_source_registry.agent", "Agent"),
    # AG-10 deprecated - functionality split into regional sub-agents AG-10.0 through AG-10.4
    
    # Regional Legal Identity Agents
    "AG-10.0": StepEntrypoint("src.agents.ag10_identity_legal.ag10_0_germany.agent", "Agent"),
    "AG-10.1": StepEntrypoint("src.agents.ag10_identity_legal.ag10_1_dach.agent", "Agent"),
    "AG-10.2": StepEntrypoint("src.agents.ag10_identity_legal.ag10_2_europe.agent", "Agent"),
    "AG-10.3": StepEntrypoint("src.agents.ag10_identity_legal.ag10_3_uk.agent", "Agent"),
    "AG-10.4": StepEntrypoint("src.agents.ag10_identity_legal.ag10_4_usa.agent", "Agent"),
    
    # Company Classification Agents
    "AG-11.0": StepEntrypoint("src.agents.ag11_company_classification.ag11_0_liquisto_classifier.agent", "Agent"),
    "AG-11.1": StepEntrypoint("src.agents.ag11_company_classification.ag11_1_northdata.agent", "Agent"),
    
    # Firmographics Agents
    "AG-13.0": StepEntrypoint("src.agents.ag13_Firmographics.ag13_0_headount.agent", "Agent"),
    "AG-13.1": StepEntrypoint("src.agents.ag13_Firmographics.ag13_1_financial_indicators.agent", "Agent"),
    "AG-13.2": StepEntrypoint("src.agents.ag13_Firmographics.ag13_2_market_scaling_indicators.agent", "Agent"),
    "AG-13.3": StepEntrypoint("src.agents.ag13_Firmographics.ag13_3_operational_complexity.agent", "Agent"),
    "AG-13.4": StepEntrypoint("src.agents.ag13_Firmographics.ag13_4_signals_from_external_effects.agent", "Agent"),
    "AG-13.5": StepEntrypoint("src.agents.ag13_Firmographics.ag13_5_buying_power.agent", "Agent"),
    
    "AG-15": StepEntrypoint("src.agents.ag15_network_mapper.agent", "Agent"),
    "AG-20": StepEntrypoint("src.agents.ag20_Size_Evaluator.agent", "Agent"),

    #note: Planned agents - baseline implementations exist or will be provided.
    "AG-21": StepEntrypoint("src.agents.ag21_financial_development.agent", "Agent"),
    "AG-30": StepEntrypoint("src.agents.ag30_portfolio.agent", "Agent"),
    "AG-31": StepEntrypoint("src.agents.ag31_markets_focus.agent", "Agent"),
    "AG-40": StepEntrypoint("src.agents.ag40_target_customers.agent", "Agent"),
    "AG-41": StepEntrypoint("src.agents.ag41_peer_discovery.agent", "Agent"),
    "AG-42": StepEntrypoint("src.agents.ag42_customers_of_intake_company.agent", "Agent"),
    "AG-50": StepEntrypoint("src.agents.ag50_projects_tenders.agent", "Agent"),
    "AG-51": StepEntrypoint("src.agents.ag51_strategic_changes.agent", "Agent"),
    "AG-60": StepEntrypoint("src.agents.ag60_industry_cycles.agent", "Agent"),
    "AG-61": StepEntrypoint("src.agents.ag61_surplus_stock_signals.agent", "Agent"),
    "AG-62": StepEntrypoint("src.agents.ag62_surplus_sales_channels.agent", "Agent"),
    "AG-70": StepEntrypoint("src.agents.ag70_supply_chain_tech.agent", "Agent"),
    "AG-71": StepEntrypoint("src.agents.ag71_supply_chain_risks.agent", "Agent"),
    "AG-72": StepEntrypoint("src.agents.ag72_sustainability_circular.agent", "Agent"),
    "AG-80": StepEntrypoint("src.agents.ag80_market_position.agent", "Agent"),
    "AG-81": StepEntrypoint("src.agents.ag81_industry_trends.agent", "Agent"),
    "AG-82": StepEntrypoint("src.agents.ag82_trade_fairs_events.agent", "Agent"),
    "AG-83": StepEntrypoint("src.agents.ag83_associations_memberships.agent", "Agent"),
    "AG-90": StepEntrypoint("src.agents.ag90_sales_playbook.agent", "Agent"),
}


#note: Load the agent class for a given step_id.
def load_agent_class(step_id: str) -> Type[BaseAgent]:
    if step_id not in STEP_ENTRYPOINTS:
        raise KeyError(f"Unknown step_id in registry: {step_id}")

    ep = STEP_ENTRYPOINTS[step_id]
    mod = importlib.import_module(ep.module_path)
    cls = getattr(mod, ep.class_name, None)
    if cls is None:
        raise ImportError(f"Agent class not found: {ep.module_path}:{ep.class_name}")
    return cls  # type: ignore[return-value]


#note: Instantiate a concrete agent with optional config.
def build_agent(step_id: str, config: Optional[Dict[str, Any]] = None) -> BaseAgent:
    cls = load_agent_class(step_id)
    try:
        return cls(config=config or {})  # type: ignore[call-arg]
    except TypeError:
        #note: Backward compatibility: older agents may not accept config in __init__.
        return cls()  # type: ignore[call-arg]

from __future__ import annotations

from src.agents.ag00_intake_normalization.agent import AgentAG00IntakeNormalization


def test_ag00_normalizes_domain_and_entity_key() -> None:
    agent = AgentAG00IntakeNormalization()

    case_input = {
        "company_name": "  Liquisto   Technologies GmbH ",
        "web_domain": "https://www.liquisto.com/path?q=1",
    }

    res = agent.run(case_input)
    assert res.ok is True

    cn = res.output["case_normalized"]
    assert cn["company_name_canonical"] == "Liquisto Technologies GmbH"
    assert cn["web_domain_normalized"] == "www.liquisto.com"
    assert cn["entity_key"] == "domain:www.liquisto.com"

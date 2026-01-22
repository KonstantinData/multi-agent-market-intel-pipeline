# AG22 – Financial Evaluator

### Purpose

This agent is responsible for the strategic interpretation of financial data provided by AG-21. It assesses the **financial urgency** (Working Capital Pressure) and the **partnership risk** for **Liquisto** by evaluating longitudinal trends in profitability, debt, and investment behaviour.

### Responsibilities

* **Strategic Analysis:** **Convert raw financial time-series data into a "Liquisto Relevance Score".**
* **Risk Assessment:** **Identify "Red Flags" such as insolvency risks or extreme volatility.**
* **Pitch Generation:** **Formulate evidence-based sales hooks derived from margin compression and leverage trends.**
* **Structured Emission:** **Emit final evaluation reports in a schema-compliant format.**

### Evaluation Matrix (Weighted Logic)

| Criterion                          | Weight        | Liquisto High Score Indicator                                   |
| ---------------------------------- | ------------- | --------------------------------------------------------------- |
| **Margin Compression**       | **40%** | Falling EBITDA margins (Increases the need for Cash-Release).   |
| **Debt-to-Equity Trend**     | **30%** | Rising leverage (Liquisto serves as a non-debt financing tool). |
| **Revenue Stability**        | **20%** | Consistent revenue ensures project stability and ROI.           |
| **Investment Level (CAPEX)** | **10%** | High CAPEX suggests facility modernisation/space needs.         |

### Outputs

* **financial_health_score:** **A rating (1–10) of the target's overall stability.**
* **liquisto_relevance_score:** **A rating (1–10) of the strategic need for inventory optimisation.**
* **strategic_pitch:** **A tailored argument based on the identified financial pain points.**
* **risk_assessment:** **Categorisation of potential collaboration risks (e.g. "Stable", "At Risk").**

Example Output (JSON)

json

```
{
  "agent_source": "AG22-Financial-Evaluator",
  "evaluation_delta": {
    "company_id": "MIDTECH-ENG-2024",
    "financial_health_score": 5.0,
    "liquisto_relevance_score": 9.2
  },
  "findings": {
    "pain_point": "EBITDA margin dropped by 35% while net debt increased by 75% over 3 years.",
    "analysis": "The company is facing a liquidity squeeze. Internal cash release through [Liquisto](https://liquisto.com) is the most viable non-debt financing option."
  },
  "strategic_pitch": {
    "target_persona": "CFO",
    "hook": "Unlock €2M-€5M in Working Capital from stagnant MRO stock to offset rising interest burdens."
  }
}
```

Verwende Code mit Vorsicht.

### Gatekeeper Expectations & Failure Conditions

* **Expectations:** **Must reference the** `entities_delta` **from AG-21, provide a clear numeric score, and ensure the pitch aligns with the** **Liquisto Solutions Portfolio**.
* **Failure Conditions:** **Missing relevance scores, pitches that ignore the target's debt levels, or failure to flag "Negative Equity" (Insolvency risk).**

---

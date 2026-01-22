
# Liquisto Lead Evaluation Framework: `ag20_size_evaluator`

## Executive Summary

This framework is designed for **Liquisto** to automate the qualification of industrial leads in the **Medical Technology, Mechanical Engineering, and Electrical Engineering** sectors. It focuses on identifying "trapped" Working Capital within MRO (Maintenance, Repair, and Operations) inventories.

**The Mission:** The `ag20_size_evaluator` analyses inventory and structural data to assess **Working Capital release potential** and assigns a lead priority score.

---

### The Strategic Evaluation Matrix

The evaluator applies a weighted scoring model to determine the "Liquisto Fit":

| Criterion                         | Weight        | High Score Logic (Tier A)                           |
| --------------------------------- | ------------- | --------------------------------------------------- |
| **MRO Inventory Intensity** | **35%** | MRO stock > 4% of revenue (High capital tie-up).    |
| **Asset Intensity (PP&E)**  | **25%** | Heavy machinery focus (High spare part dependency). |
| **Site Fragmentation**      | **20%** | >3 sites (High probability of duplicates/silos).    |
| **Operational Context**     | **10%** | Recent M&A or fragmented ERP (IT-Complexity).       |
| **Industry Core Fit**       | **10%** | MedTech, MechEng, or Electrical Engineering.        |

---

### Tier A Example: High-Priority Lead

**Profile:** A large-scale Mechanical Engineering firm with redundant stocks following an acquisition.

Input JSON (from AgentAG11)

json

```
{
  "agent_source": "AgentAG11CompanySize",
  "target_company": {
    "name": "GlobalHeavyIndustries GmbH",
    "industry": "Mechanical Engineering",
    "quantitative_metrics": {
      "annual_revenue_eur": 850000000,
      "mro_inventory_value_eur": 42000000,
      "inventory_to_revenue_ratio": 0.049,
      "ppe_value_eur": 310000000,
      "number_of_production_sites": 7
    },
    "qualitative_context": {
      "m_and_a_activity": "Acquired regional competitor in 2024; integration ongoing.",
      "erp_system": "Fragmented: Mix of SAP S/4HANA and 2 legacy Navision instances.",
      "maintenance_structure": "Decentralized: Each plant manager controls their own budget."
    }
  }
}
```

Verwende Code mit Vorsicht.

Evaluator Analysis (Output)

* **Priority Score:** **9.2/10 (Tier A)**
* **Strategic Rationale:**
  * **Inventory Intensity:** **€42M in stock (~5% of revenue) indicates massive inefficiency.**
  * **Fragmentation:** **7 sites with decentralized purchasing guarantee duplicate safety stocks.**
  * **M&A Bonus:** **The 2024 acquisition is a "Quick Win" indicator for stock consolidation.**
* **Outreach Hook:** **CFO-level pitch focusing on** **Working Capital release** **to fund post-merger integration.**

---

### Tier C Example: Low-Priority Lead

**Profile:** A highly optimized, asset-light Medical Technology assembly plant.

Input JSON (from AgentAG11)

json

```
{
  "agent_source": "AgentAG11CompanySize",
  "target_company": {
    "name": "PrecisionAssembly Tech",
    "industry": "Medical Technology",
    "quantitative_metrics": {
      "annual_revenue_eur": 1200000000,
      "mro_inventory_value_eur": 2100000,
      "inventory_to_revenue_ratio": 0.0017,
      "ppe_value_eur": 45000000,
      "number_of_production_sites": 2
    },
    "qualitative_context": {
      "m_and_a_activity": "None; organic growth focus.",
      "erp_system": "Fully integrated single-instance Oracle Cloud ERP.",
      "maintenance_structure": "Fully outsourced to external service providers (OEMs)."
    }
  }
}
```

Verwende Code mit Vorsicht.

Evaluator Analysis (Output)

* **Priority Score:** **2.1/10 (Tier C)**
* **Strategic Rationale:**
  * **Red Flag - Outsourcing:** **Maintenance is handled by OEMs; the company does not own the spare part risk.**
  * **Low Intensity:** **Inventory value (0.17% of revenue) is too low for a profitable Liquisto project.**
  * **ERP Maturity:** **High digital transparency leaves little room for "hidden" duplicates.**
* **Outreach Hook:** **Disqualify.** **No significant pain points regarding** **inventory liquidation**.

---

### Implementation Notes

* **Industry Bias:** **The agent is instructed to add a +1.0 score modifier if the company belongs to the core industries (MedTech, MechEng, Electrical Eng).**
* **Automation:** **Results should be pushed directly to the CRM (e.g., Salesforce/HubSpot) to trigger specific email sequences based on the "Pain Point Hypothesis".**

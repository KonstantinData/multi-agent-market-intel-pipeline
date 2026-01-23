# AG-21 – Financial Development

## Purpose

Collects historical financial data to assess target companies for Liquisto using GPT-4o-powered research with structured financial analysis and trend identification.

## Key Features
- **GPT-4o Integration**: Uses OpenAI's most capable model for accurate financial data extraction
- **Structured Outputs**: JSON schema validation for reliable financial data parsing
- **Time Series Analysis**: 3-year financial trends with key metrics
- **Evidence-Based Research**: All financial claims backed by AI analysis
- **Comprehensive Metrics**: Revenue, EBITDA, Net Debt, CAPEX tracking

## Financial Metrics Collected
- **Revenue Growth**: Annual revenue trends over 3-year period
- **Profitability**: EBITDA margins and operational efficiency
- **Capital Structure**: Equity ratios and leverage analysis
- **Investment Patterns**: CAPEX trends indicating expansion or cost-cutting
- **Working Capital**: Pressure indicators and liquidity assessment

## Research Methodology
- **AI-Powered Analysis**: GPT-4o analyzes company financial context and trends
- **Multi-Year Tracking**: Systematic collection of 3-year financial time series
- **Trend Identification**: Automated analysis of financial development patterns
- **Risk Assessment**: Leverage trends and working capital pressure evaluation

### Responsibilities

* **Financial Research:** Systematic extraction of financial KPIs using GPT-4o analysis
* **Trend Analysis:** Identify revenue, profitability, and leverage development patterns
* **Structured Emission:** Emit structured JSON outputs with time series data
* **Evidence-Based:** All financial claims backed by AI research and reasoning
* **Verifiability:** Use 'n/v' where information cannot be determined

### Outputs

* **entities_delta:** Financial profile entity with comprehensive analysis
* **relations_delta:** (empty for AG-21)
* **findings:** Structured financial data with time series and trend analysis
* **sources:** OpenAI API attribution for AI-generated financial research

### Example Output

```json
{
  "findings": [{
    "currency": "EUR",
    "time_series": [
      {"year": 2021, "revenue": "100 million", "ebitda": "15 million", "net_debt": "20 million", "capex": "5 million"},
      {"year": 2022, "revenue": "110 million", "ebitda": "16 million", "net_debt": "22 million", "capex": "6 million"},
      {"year": 2023, "revenue": "120 million", "ebitda": "17 million", "net_debt": "25 million", "capex": "7 million"}
    ],
    "equity_ratio_2024": "n/v",
    "trend_summary": "Steady revenue growth with stable profitability and manageable debt levels"
  }],
  "entities_delta": [{
    "entity_id": "ENT-F1A069DF073D",
    "financial_profile": {
      "revenue_trend": "Steady increase over the last three years",
      "profitability_trend": "EBITDA margins have remained stable",
      "leverage_trend": "Manageable level of debt with slight increase",
      "investment_pattern": "Consistent capital expenditures indicating ongoing investment",
      "working_capital_pressure": "Moderate pressure with increasing current liabilities"
    }
  }]
}
```

### Gatekeeper Expectations

* **Required Fields**: currency, time_series, trend_summary in findings
* **Financial Data Evidence**: All claims backed by AI research attribution
* **Source Attribution**: OpenAI API calls properly documented
* **Schema Compliance**: Structured outputs matching financial data contracts

### Failure Conditions

* **Missing OpenAI API Key**: Agent requires OPEN-AI-KEY environment variable
* **Missing Required Fields**: currency, time_series, trend_summary must be present
* **Claims Without Sources**: Financial data must include source attribution
* **Contract Validation**: Output must pass financial data schema validation

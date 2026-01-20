# Agent Overview and Deliverables (Status 2026-20-01)

## 0) What AG-00 delivers (Foundation)

### AG-00 produces:

**A) case_normalized**

* company_name_canonical (non-empty)
* web_domain_normalized (normalized domain, no protocol, no path)
* entity_key (deterministic from domain)

**B) target_entity_stub (no final ID yet)**

* entity_type = "target_company"
* entity_name
* domain
* entity_key

**C) sources**

* optional (pure normalization, no research)

**Gatekeeper rules (hard PASS/FAIL):**

* company_name_canonical non-empty
* web_domain_normalized matches basic domain pattern
* entity_key equals domain:<web_domain_normalized>

---

## 1) What AG-01 delivers (Source Registry / Research Plan)

### AG-01 produces:

**A) source_registry**

* primary_sources (official website, legal pages)
* secondary_sources (press, registers, associations)
* source_scope_notes

**B) findings**

* explanation of why sources are relevant

**C) sources**

* list of identified source URLs

**Gatekeeper rules:**

* at least one primary source present
* each source has publisher + url
* no claims beyond source identification

---

## 2) What AG-10 delivers (Identity and Legal)

### AG-10 produces:

**A) entities_delta**

* TGT-001 (target_company)
  * legal_name or n/v
  * legal_form or n/v
  * founding_year or n/v
  * registration_signals or n/v

**B) findings**

* summary of legal identity

**C) sources**

* imprint, registers, official pages

**Gatekeeper rules:**

* entity_type = target_company
* no invented registration numbers
* sources required for any legal claim

---

## 3) What AG-11 delivers (Locations and Sites)

### AG-11 produces:

**A) entities_delta**

* site entities (HQ, production, warehouse) or n/v
  * site_type
  * country_region
  * city or n/v

**B) relations_delta**

* target_company -> operates_at -> site

**C) sources**

**Gatekeeper rules:**

* site entities must reference TGT-001
* country_region mandatory or n/v
* no orphan site entities

---

## 4) What AG-20 delivers (Company Size Signals)

### AG-20 produces:

**A) entities_delta**

* TGT-001 updates:
  * employee_range or n/v
  * revenue_band or n/v
  * market_scope_signal or n/v

**B) findings**

* explanation of size signals

**C) sources**

**Gatekeeper rules:**

* no numeric estimates without source
* ranges allowed, guesses forbidden

---

## 5) What AG-21 delivers (Financial Development)

### AG-21 produces:

**A) findings**

* revenue trend 3-5 years or n/v
* profitability signals (EBIT, profit/loss) or n/v
* risk signals (warnings, insolvency notices)

**B) sources**

**Gatekeeper rules:**

* timelines require dated sources
* missing data must be n/v, not inferred

---

## 6) What AG-30 delivers (Portfolio)

### AG-30 produces:

**A) entities_delta**

* product_group entities
  * product_category
  * use_cases
  * buyer_roles

**B) relations_delta**

* target_company -> offers -> product_group

**C) sources**

**Gatekeeper rules:**

* product groups must be named consistently
* no marketing language without source

---

## 7) What AG-31 delivers (Markets and Industry Focus)

### AG-31 produces:

**A) findings**

* industry_verticals
* sales_markets (regions)
* go_to_market_signals

**B) sources**

**Gatekeeper rules:**

* industries must be named explicitly or n/v
* regions must be ISO-country or macro-region

---

## 8) What AG-40 delivers (Target Customers)

### AG-40 produces:

**A) entities_delta**

* CUS-XXX entities (customers)
  * entity_name
  * domain or n/v
  * role = customer

**B) relations_delta**

* TGT-001 -> supplies_to -> CUS-XXX

**C) sources**

* case studies, references, indirect evidence

**Gatekeeper rules:**

* every customer must have evidence
* no inferred customers

---

## 9) What AG-41 delivers (Peers / Manufacturers)

### AG-41 produces:

**A) entities_delta**

* MFR-XXX entities
  * entity_name
  * domain
  * product_match_reason

**B) relations_delta**

* MFR-XXX -> peer_of -> TGT-001

**C) sources**

**Gatekeeper rules:**

* product match must be explained
* domain required or n/v with justification

---

## 10) What AG-42 delivers (Customers of Manufacturers)

### AG-42 produces:

**A) entities_delta**

* CUS-XXX entities (if new)

**B) relations_delta**

* MFR-XXX -> supplies_to -> CUS-XXX

**C) sources**

**Gatekeeper rules:**

* crossrefs must point to existing IDs
* dedupe by domain enforced

---

## 11) What AG-50 delivers (Projects and Tenders)

### AG-50 produces:

**A) findings**

* public projects
* tenders
* investments

**B) sources**

**Gatekeeper rules:**

* dates and amounts require sources
* announcements only, no speculation

---

## 12) What AG-51 delivers (Strategic Changes)

### AG-51 produces:

**A) findings**

* M&A
* relocations
* expansions
* major partnerships

**B) sources**

**Gatekeeper rules:**

* events must be time-bound
* rumors forbidden

---

## 13) What AG-60 delivers (Industry Cycles)

### AG-60 produces:

**A) findings**

* industry production cycles
* inventory cadence signals

**B) sources**

**Gatekeeper rules:**

* must be industry-level, not company guesses

---

## 14) What AG-61 delivers (Surplus Stock Signals)

### AG-61 produces:

**A) findings**

* surplus indicators (discounting, shutdowns, layoffs)
* overproduction hints or n/v

**B) sources**

**Gatekeeper rules:**

* weak signals allowed only with sources
* absence must be n/v

---

## 15) What AG-62 delivers (Surplus Sales Channels)

### AG-62 produces:

**A) findings**

* outlet channels
* liquidation platforms
* distributors

**B) sources**

**Gatekeeper rules:**

* channels must be verifiable
* generic marketplaces only if explicitly used

---

## 16) What AG-70 delivers (Supply Chain Technology)

### AG-70 produces:

**A) findings**

* ERP/WMS hints
* automation signals

**B) sources**

**Gatekeeper rules:**

* tech claims require explicit mention in sources

---

## 17) What AG-71 delivers (Supply Chain Risks)

### AG-71 produces:

**A) findings**

* concentration risks
* geopolitical exposure
* material shortages

**B) sources**

**Gatekeeper rules:**

* risks must be evidence-based

---

## 18) What AG-72 delivers (Sustainability and Circular Economy)

### AG-72 produces:

**A) findings**

* circular initiatives
* ESG programs
* CO2 targets

**B) sources**

**Gatekeeper rules:**

* marketing claims without proof forbidden

---

## 19) What AG-80 delivers (Market Position)

### AG-80 produces:

**A) findings**

* competitor landscape
* relative positioning signals

**B) sources**

**Gatekeeper rules:**

* positioning must reference peers already defined

---

## 20) What AG-81 delivers (Industry Trends)

### AG-81 produces:

**A) findings**

* macro trends impacting demand and inventory

**B) sources**

**Gatekeeper rules:**

* trends must be industry-wide, not anecdotal

---

## 21) What AG-82 delivers (Trade Fairs and Events)

### AG-82 produces:

**A) findings**

* relevant fairs
* attendance or exhibitor signals

**B) sources**

**Gatekeeper rules:**

* event relevance must be explained

---

## 22) What AG-83 delivers (Industry Associations)

### AG-83 produces:

**A) findings**

* association memberships

**B) sources**

**Gatekeeper rules:**

* memberships must be verifiable

---

## 23) What AG-90 delivers (Sales and Negotiation Playbook)

### AG-90 produces:

**A) report_section**

* discovery questions
* expected objections
* negotiation levers
* next actions

**B) sources**

* references to upstream findings

**Gatekeeper rules:**

* must only reference existing entities and findings
* no generic sales fluff

"""
AG-11.0 Liquisto Company Classifier Agent

Classifies companies using Liquisto taxonomy and rules-based matching.
"""

import os
import re
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import yaml
import httpx

from ...common.base_agent import BaseAgent, AgentResult


class AG11_0_LiquistoClassifier(BaseAgent):
    """
    Agent for classifying companies using Liquisto taxonomy.
    
    Uses:
    - classification/taxanomy.yaml for class definitions
    - classification/rules.yaml for term matching rules
    """

    def __init__(self):
        super().__init__()
        self.agent_id = "AG-11.0"
        self.agent_name = "ag11_0_liquisto_classifier"
        self.api_key = os.getenv("OPEN-AI-KEY") or os.getenv("OPENAI_API_KEY")
        
        # Load classification configs
        repo_root = Path(__file__).resolve().parents[4]
        self.taxonomy = self._load_yaml(repo_root / "classification" / "taxanomy.yaml")
        self.rules = self._load_yaml(repo_root / "classification" / "rules.yaml")

    def run(
        self,
        case_input: Dict[str, Any],
        meta_case_normalized: Dict[str, Any],
        meta_target_entity_stub: Dict[str, Any],
        registry_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Execute classification."""
        
        company_name = meta_case_normalized.get("company_name_canonical", "")
        domain = meta_case_normalized.get("web_domain_normalized", "")
        
        output = {
            "step_meta": self._create_step_meta(),
            "entities_delta": [],
            "relations_delta": [],
            "findings": [],
            "sources": []
        }

        # Research company using LLM
        research_data = self._research_company(company_name, domain)
        
        # Build corpus from research + registry
        corpus = self._build_corpus(registry_snapshot, company_name, research_data)
        
        # Classify
        classification_result = self._classify(corpus)
        
        # Build entity update
        entity_update = {
            "entity_key": meta_target_entity_stub.get("entity_key", ""),
            "entity_type": "target_company",
            "liquisto_class": classification_result["class_id"],
            "liquisto_class_label": classification_result["class_label"],
            "liquisto_class_confidence": classification_result["confidence"],
            "liquisto_tags": classification_result["tags"],
            "wz_codes": classification_result["wz_codes"]
        }
        
        output["entities_delta"] = [entity_update]
        output["findings"] = [{
            "class_id": classification_result["class_id"],
            "class_label": classification_result["class_label"],
            "confidence": classification_result["confidence"],
            "score": classification_result["score"],
            "evidence": classification_result["evidence"],
            "tags": classification_result["tags"]
        }]
        output["sources"] = [{
            "publisher": "Liquisto Classification System",
            "url": "n/v",
            "title": "Liquisto Taxonomy v1.0",
            "accessed_at_utc": datetime.now(timezone.utc).isoformat()
        }]

        return AgentResult(ok=True, output=output)

    def _research_company(self, company_name: str, domain: str) -> Dict[str, Any]:
        """Research company using LLM to extract products, services, and industry info."""
        if not self.api_key:
            return {"products": "", "services": "", "industry_description": ""}
        
        # Fetch website content
        website_content = self._fetch_website_content(domain)
        
        # Build taxonomy context for LLM
        taxonomy_context = self._build_taxonomy_context()
        
        prompt = f"""Analyze this company and extract key information for classification.

Company: {company_name}
Website: {domain}

Website Content:
{website_content[:4000]}

Available Classification Categories:
{taxonomy_context}

Extract:
1. Main products (specific technical products, components, systems)
2. Services offered
3. Industry focus and target markets
4. Key technical terms and specializations

Be specific and technical. Focus on manufacturing, automation, electronics, and industrial components."""

        try:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "company_research",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "products": {"type": "string"},
                            "services": {"type": "string"},
                            "industry_description": {"type": "string"},
                            "technical_terms": {"type": "string"}
                        },
                        "required": ["products", "services", "industry_description", "technical_terms"],
                        "additionalProperties": False
                    }
                }
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 1000,
                "response_format": response_format
            }
            
            headers = {"Authorization": f"Bearer {self.api_key}"}
            with httpx.Client(timeout=30.0) as client:
                resp = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                return json.loads(content)
        except Exception:
            pass
        
        return {"products": "", "services": "", "industry_description": "", "technical_terms": ""}

    def _fetch_website_content(self, domain: str) -> str:
        """Fetch website content from main pages."""
        domain_variants = [f"www.{domain}" if not domain.startswith('www.') else domain, domain]
        url_patterns = ['', '/produkte', '/products', '/leistungen', '/services', '/unternehmen', '/about']
        
        content = ""
        for domain_var in domain_variants:
            for pattern in url_patterns:
                url = f"https://{domain_var}{pattern}"
                try:
                    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                        resp = client.get(url)
                        if resp.status_code == 200:
                            html_content = resp.text
                            text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
                            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                            text = re.sub(r'<[^>]+>', ' ', text)
                            text = re.sub(r'\s+', ' ', text)
                            content += f" {text[:2000]}"
                            if len(content) > 6000:
                                return content
                except Exception:
                    continue
        
        return content or "No website content available"

    def _build_taxonomy_context(self) -> str:
        """Build taxonomy context for LLM."""
        lines = []
        for cls in self.taxonomy.get("classes", []):
            lines.append(f"- {cls['label']} ({cls['id']})")
        return "\n".join(lines)

    def _build_corpus(self, registry_snapshot: Optional[Dict[str, Any]], company_name: str, research_data: Dict[str, Any]) -> str:
        """Build text corpus from all available data."""
        texts = [
            company_name,
            research_data.get("products", ""),
            research_data.get("services", ""),
            research_data.get("industry_description", ""),
            research_data.get("technical_terms", "")
        ]
        
        if registry_snapshot:
            entities = registry_snapshot.get("entities", [])
            for entity in entities:
                if isinstance(entity, dict) and entity.get("entity_type") == "target_company":
                    texts.append(entity.get("industry", ""))
                    texts.append(entity.get("industry_description", ""))
                    
                    # Add portfolio/product info if available
                    if entity.get("attributes", {}).get("portfolio"):
                        portfolio = entity["attributes"]["portfolio"]
                        texts.append(str(portfolio.get("products", "")))
                        texts.append(str(portfolio.get("services", "")))
        
        return " ".join(filter(None, texts))

    def _classify(self, corpus: str) -> Dict[str, Any]:
        """Classify text corpus using rules."""
        
        # Normalize corpus
        normalized = self._normalize_text(corpus)
        
        # Generate n-grams
        ngrams = self._generate_ngrams(normalized, self.rules["match"]["ngrams"])
        
        # Score all rules
        scores = []
        for rule in self.rules["rules"]:
            score, evidence = self._score_rule(rule, ngrams)
            scores.append({
                "target_type": rule["target_type"],
                "target_id": rule["target_id"],
                "score": score,
                "evidence": evidence
            })
        
        # Find best class
        class_scores = [s for s in scores if s["target_type"] == "class"]
        class_scores.sort(key=lambda x: x["score"], reverse=True)
        
        best = class_scores[0] if class_scores else None
        runner_up = class_scores[1] if len(class_scores) > 1 else None
        
        # Check confidence thresholds
        conf_config = self.rules["confidence"]
        confidence = "n/v"
        
        if best and best["score"] >= conf_config["min_score"]:
            if len(best["evidence"]) >= conf_config["min_evidence_hits"]:
                margin = best["score"] - (runner_up["score"] if runner_up else 0)
                if margin >= conf_config["margin_to_runner_up"]:
                    confidence = "high"
                else:
                    confidence = "medium"
        
        # Get class info from taxonomy
        class_id = best["target_id"] if best else "n/v"
        class_label = self._get_class_label(class_id)
        wz_codes = self._get_wz_codes(class_id)
        
        # Get matching tags
        tag_scores = [s for s in scores if s["target_type"] == "tag" and s["score"] > 0]
        tags = [{"id": t["target_id"], "label": self._get_tag_label(t["target_id"])} for t in tag_scores]
        
        return {
            "class_id": class_id,
            "class_label": class_label,
            "confidence": confidence,
            "score": best["score"] if best else 0,
            "evidence": best["evidence"] if best else [],
            "tags": tags,
            "wz_codes": wz_codes
        }

    def _normalize_text(self, text: str) -> str:
        """Normalize text according to rules config."""
        norm_config = self.rules["match"]["normalize"]
        
        if norm_config["lowercase"]:
            text = text.lower()
        
        if norm_config["umlauts"]:
            text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
            text = text.replace("ß", "ss")
        
        if norm_config["strip_punctuation"]:
            text = re.sub(r'[^\w\s]', ' ', text)
        
        return text

    def _generate_ngrams(self, text: str, n_values: List[int]) -> List[str]:
        """Generate n-grams from text."""
        words = text.split()
        ngrams = []
        
        for n in n_values:
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i:i+n])
                ngrams.append(ngram)
        
        return ngrams

    def _score_rule(self, rule: Dict[str, Any], ngrams: List[str]) -> Tuple[float, List[str]]:
        """Score a rule against n-grams."""
        score = 0.0
        evidence = []
        
        # Include terms
        for term_weight in rule["include"]:
            term = self._normalize_text(term_weight["term"])
            if term in ngrams:
                score += term_weight["weight"]
                evidence.append(term)
        
        # Exclude terms
        for term_weight in rule.get("exclude", []):
            term = self._normalize_text(term_weight["term"])
            if term in ngrams:
                score += term_weight["weight"]  # Already negative
        
        return score, evidence

    def _get_class_label(self, class_id: str) -> str:
        """Get class label from taxonomy."""
        for cls in self.taxonomy.get("classes", []):
            if cls["id"] == class_id:
                return cls["label"]
        return "n/v"

    def _get_tag_label(self, tag_id: str) -> str:
        """Get tag label from taxonomy."""
        for tag in self.taxonomy.get("tags", []):
            if tag["id"] == tag_id:
                return tag["label"]
        return "n/v"

    def _get_wz_codes(self, class_id: str) -> List[Dict[str, str]]:
        """Get WZ/NACE codes for class."""
        for cls in self.taxonomy.get("classes", []):
            if cls["id"] == class_id:
                return cls.get("codes", [])
        return []

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML file."""
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def _create_step_meta(self) -> Dict[str, Any]:
        """Create step metadata."""
        now = datetime.now(timezone.utc)
        return {
            "step_id": self.agent_id,
            "agent_name": self.agent_name,
            "run_id": getattr(self, 'run_id', 'unknown'),
            "started_at_utc": now.isoformat(),
            "finished_at_utc": now.isoformat(),
            "pipeline_version": "1.0.0"
        }


# Wiring-safe alias
Agent = AG11_0_LiquistoClassifier

'''transfer_validation.py
 
Validates transfer of knowledge/skills across domains.
Compares predictions from a source benchmark to a target benchmark using simple overlap metrics.
''' 

from typing import List, Dict, Any, Set
import hashlib

class TransferValidator:
    def __init__(self):
        # Define transferable concept categories with weights
        self.transferable_concepts = {
            "algorithms": {"weight": 0.3, "keywords": {"sort", "search", "graph", "tree", "sorting", "searching"}},
            "mathematics": {"weight": 0.25, "keywords": {"calculus", "algebra", "geometry", "statistics", "probability", "derivative", "integral", "equation"}},
            "data_structures": {"weight": 0.2, "keywords": {"array", "list", "stack", "queue", "tree", "graph", "hash", "heap", "linked"}},
            "optimization": {"weight": 0.15, "keywords": {"optimization", "optimize", "minimum", "maximum", "efficiency", "performance"}},
            "machine_learning": {"weight": 0.1, "keywords": {"learning", "training", "model", "prediction", "classification", "regression", "clustering"}}
        }
        
        # Domain mapping for contextual transfer validation
        self.domain_mappings = {
            "math_to_cs": {"source_domains": {"mathematics"}, "target_domains": {"algorithms", "data_structures"}, "transfer_factor": 0.7},
            "cs_to_math": {"source_domains": {"algorithms", "data_structures"}, "target_domains": {"mathematics"}, "transfer_factor": 0.6},
            "ml_to_software": {"source_domains": {"machine_learning"}, "target_domains": {"algorithms", "optimization"}, "transfer_factor": 0.5}
        }

    def validate(self, predictions: List[Dict[str, str]]) -> Dict[str, float]:
        """Calculate a transfer score based on concept overlap and semantic similarity.
        
        For each prediction, we analyze the predicted outcome for transferable concepts
        from source to target domains, considering both direct matches and conceptual 
        similarities.
        Returns a dictionary with transfer_score and detailed breakdown.
        """
        if not predictions:
            return {"transfer_score": 0.0, "details": {"reason": "no_predictions_provided"}}
        
        # Analyze each prediction for transferable concepts
        total_transfer_score = 0.0
        category_scores = {category: 0.0 for category in self.transferable_concepts.keys()}
        category_counts = {category: 0 for category in self.transferable_concepts.keys()}
        
        for pred in predictions:
            outcome = pred.get("predicted_outcome", "").lower()
            source_domain = pred.get("source_domain", "unknown").lower()
            target_domain = pred.get("target_domain", "unknown").lower()
            
            # Check for direct keyword matches
            for category, config in self.transferable_concepts.items():
                keyword_matches = sum(1 for keyword in config["keywords"] if keyword in outcome)
                if keyword_matches > 0:
                    # Normalize by number of keywords in category
                    category_score = min(keyword_matches / len(config["keywords"]), 1.0)
                    category_scores[category] += category_score * config["weight"]
                    category_counts[category] += 1
            
            # Check for domain-specific transfer patterns
            transfer_bonus = self._calculate_transfer_bonus(source_domain, target_domain, outcome)
            total_transfer_score += transfer_bonus
        
        # Calculate average scores
        num_predictions = len(predictions)
        avg_category_scores = {
            category: (category_scores[category] / max(category_counts[category], 1)) 
            for category in category_scores.keys()
        }
        
        # Overall transfer score combines category scores and transfer bonus
        base_score = sum(avg_category_scores.values()) if num_predictions > 0 else 0.0
        transfer_bonus_avg = total_transfer_score / num_predictions
        
        # Final score is weighted combination
        final_score = min((base_score * 0.7) + (transfer_bonus_avg * 0.3), 1.0)
        
        # Generate deterministic but prediction-specific details
        details = self._generate_validation_details(predictions, final_score, avg_category_scores)
        
        return {
            "transfer_score": round(final_score, 4),
            "details": details
        }

    def _calculate_transfer_bonus(self, source_domain: str, target_domain: str, outcome: str) -> float:
        """Calculate bonus score for known transfer patterns between domains."""
        bonus = 0.0
        
        # Check for known transfer mappings
        for mapping_key, mapping in self.domain_mappings.items():
            source_match = any(domain in source_domain for domain in mapping["source_domains"])
            target_match = any(domain in target_domain for domain in mapping["target_domains"])
            
            if source_match and target_match:
                # Check if outcome contains relevant terms for this transfer
                outcome_words = set(outcome.split())
                # Simple check: if outcome contains terms from either domain, give bonus
                if any(word in outcome_words for word in 
                       [word for domain in list(mapping["source_domains"]) + list(mapping["target_domains"]) 
                        for word in domain.split("_")]):
                    bonus += mapping["transfer_factor"]
                break  # Only apply one matching transfer bonus per prediction
        
        return bonus

    def _generate_validation_details(self, predictions: List[Dict[str, str]], 
                                   overall_score: float, 
                                   category_scores: dict) -> dict:
        """Generate deterministic details about the validation based on input predictions."""
        # Create a deterministic seed from the predictions
        pred_string = str(sorted([str(sorted(p.items())) for p in predictions]))
        seed = int(hashlib.sha256(pred_string.encode()).hexdigest()[:8], 16)
        
        # Generate consistent but varied details based on the seed
        details = {
            "total_predictions_evaluated": len(predictions),
            "overall_transfer_strength": self._categorize_strength(overall_score),
            "strongest_category": max(category_scores, key=category_scores.get) if any(category_scores.values()) else "none",
            "weakest_category": min(category_scores, key=category_scores.get) if any(category_scores.values()) else "none",
            "evaluation_seed": seed,
            "assessment_summary": self._generate_assessment_summary(overall_score, category_scores)
        }
        
        return details

    def _categorize_strength(self, score: float) -> str:
        """Categorize a score into strength levels."""
        if score >= 0.8:
            return "strong"
        elif score >= 0.6:
            return "moderate"
        elif score >= 0.4:
            return "weak"
        else:
            return "very_weak"

    def _generate_assessment_summary(self, overall_score: float, category_scores: dict) -> str:
        """Generate a textual summary of the transfer validation assessment."""
        strength = self._categorize_strength(overall_score)
        
        if overall_score >= 0.7:
            return f"Strong transfer learning potential detected ({strength} strength). {len([c for c, s in category_scores.items() if s > 0.5])} concept areas show significant transferability."
        elif overall_score >= 0.4:
            return f"Moderate transfer learning potential observed ({strength} strength). Some concept transfer evident but opportunities for improvement exist."
        else:
            return f"Limited transfer learning detected ({strength} strength). Consider enhancing cross-domain connections in training data."

    def __repr__(self):
        return f"TransferValidator(concepts={len(self.transferable_concepts)}, domain_mappings={len(self.domain_mappings)})"

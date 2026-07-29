"""
immutable_core.py
هسته تغییرناپذیر سیستم + حافظه تکاملی
- قوانین بنیادین که هرگز نقض نمی‌شوند
- ثبت تاریخچه تصمیم‌گیری برای یادگیری تکاملی
"""

import time
from typing import Dict, List, Tuple, Optional

class ImmutableCore:
    def __init__(self):
        # قوانین بنیادین (غیرقابل مذاکره)
        self.rules = {
            "min_stability": 0.60,
            "max_energy": 0.90,
            "max_phase_error": 0.50,
            "require_explainability": True
        }

        # حافظه تکاملی: ثبت تصمیمات و نتایج
        self._evolution_memory: List[Dict] = []
        self._decision_stats: Dict[str, Dict] = {}

    def validate(self, proposal_metrics: Dict) -> Dict:
        """
        اعتبارسنجی پیشنهاد بر اساس قوانین هسته
        """
        violations = []

        if proposal_metrics.get("stability", 1) < self.rules["min_stability"]:
            violations.append("stability_below_core_limit")

        if proposal_metrics.get("energy", 0) > self.rules["max_energy"]:
            violations.append("energy_over_limit")

        if proposal_metrics.get("phase_error", 0) > self.rules["max_phase_error"]:
            violations.append("phase_desynchronization")

        if self.rules["require_explainability"] and not proposal_metrics.get("explainability", False):
            violations.append("explainability_removed")

        return {
            "approved": len(violations) == 0,
            "violations": violations
        }

    def record_decision(self, mutation_id: str, proposal: Dict, metrics: Dict, decision: bool, fitness: float = 0.0):
        """
        ثبت تصمیم در حافظه تکاملی
        """
        record = {
            "timestamp": time.time(),
            "mutation_id": mutation_id,
            "proposal": proposal,
            "metrics": metrics,
            "decision": decision,
            "fitness": fitness,
            "version": "v1.1"
        }
        self._evolution_memory.append(record)

        # به‌روزرسانی آمار
        mutation_type = proposal.get("mutation_type", "unknown")
        if mutation_type not in self._decision_stats:
            self._decision_stats[mutation_type] = {"accepted": 0, "rejected": 0, "avg_fitness": 0.0}

        if decision:
            self._decision_stats[mutation_type]["accepted"] += 1
            total = self._decision_stats[mutation_type]["accepted"] + self._decision_stats[mutation_type]["rejected"]
            self._decision_stats[mutation_type]["avg_fitness"] = (
                (self._decision_stats[mutation_type]["avg_fitness"] * (total - 1) + fitness) / total
            )
        else:
            self._decision_stats[mutation_type]["rejected"] += 1

    def get_evolution_memory(self, limit: int = 10) -> List[Dict]:
        """دریافت آخرین تصمیمات ثبت‌شده"""
        return self._evolution_memory[-limit:]

    def get_decision_stats(self) -> Dict:
        """دریافت آمار تصمیمات به تفکیک نوع جهش"""
        return self._decision_stats

    def get_rules(self):
        return self.rules

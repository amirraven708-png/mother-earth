"""
evolution_rules.py
قوانین تکامل — محدودیت‌های عملیاتی برای چرخه تکامل.
"""

class EvolutionRules:
    def __init__(self):
        self.rules = {
            "max_mutations_per_cycle": 1,
            "sandbox_duration_ticks": 100,
            "fitness_threshold": 0.65,
            "min_improvement": 0.05,
            "rollback_on_failure": True
        }

    def get_rules(self):
        return self.rules

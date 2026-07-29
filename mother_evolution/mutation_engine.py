"""
mutation_engine.py
موتور تولید تغییرات در چهارچوب هسته تغییرناپذیر
"""

import random
import math

class MutationEngine:
    def generate_proposal(self, current_state, core_rules):
        # استخراج پارامترهای فعلی
        coupling_k = current_state.get("coupling_k", 0.5)
        buffer_size = current_state.get("buffer_size", 1024)
        decay_rate = current_state.get("decay_rate", 0.015)

        # تولید تغییرات تصادفی اما محدود
        proposal = {
            "id": f"mut_{random.randint(1000, 9999)}",
            "optimized_parameters": {
                "coupling_k": max(0.1, min(0.9, coupling_k * (1 + random.uniform(-0.1, 0.1)))),
                "buffer_size": max(256, min(8192, int(buffer_size * (1 + random.uniform(-0.2, 0.2))))),
                "decay_rate": max(0.001, min(0.05, decay_rate * (1 + random.uniform(-0.15, 0.15))))
            },
            "mutation_type": "adaptive_tuning",
            "violates_core": False
        }
        return proposal

"""
fitness_evaluator.py
ارزیاب تطبیقی مبتنی بر قانون بیضی و حافظه
"""

class FitnessEvaluator:
    def observe(self, state):
        return {
            "stability": state.get("stability", 0.7),
            "energy": state.get("energy", 1.0),
            "phase_error": state.get("phase_error", 0.1),
            "adaptability": state.get("adaptability", 0.5)
        }

    def calculate_fitness(self, metrics):
        energy_factor = 1.0 / (metrics.get("energy_cost", 1.0) + 1e-8)
        stability = metrics.get("stability", 0.5)
        adaptability = metrics.get("adaptability", 0.5)

        # قانون بیضی: تعادل بین کانون (پایداری) و محیط (اکتشاف)
        ellipse_balance = 1.0 - abs(stability - adaptability)

        fitness = (
            energy_factor * 0.30 +
            stability * 0.30 +
            adaptability * 0.20 +
            ellipse_balance * 0.20
        )

        return fitness if fitness > 0.65 else -1.0

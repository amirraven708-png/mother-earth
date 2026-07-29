"""
release_manager.py
مدیریت انتشار تدریجی نسخه‌ها
"""

class ReleaseManager:
    def __init__(self):
        self.active_version = "v1.0.0-Alpha"
        self.history = []

    def promote(self, proposal, fitness_score):
        new_version = f"v1.1.{len(self.history) + 1}"
        self.history.append({
            "version": new_version,
            "proposal": proposal,
            "fitness": fitness_score
        })
        self.active_version = new_version
        print(f"🌟 Promoted to {new_version} (fitness: {fitness_score:.3f})")

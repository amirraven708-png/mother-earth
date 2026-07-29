"""
evolution_runtime.py
نقطه ورود اصلی سیستم تکامل
"""

from .evolution_controller import EvolutionController
from .mutation_engine import MutationEngine
from .sandbox_runner import SandboxRunner
from .fitness_evaluator import FitnessEvaluator
from .release_manager import ReleaseManager
from .core.immutable_core import ImmutableCore

class EvolutionRuntime:
    def __init__(self):
        self.core = ImmutableCore()
        self.controller = EvolutionController(
            immutable_core=self.core,
            mutation_engine=MutationEngine(),
            sandbox=SandboxRunner(),
            evaluator=FitnessEvaluator(),
            release_mgr=ReleaseManager()
        )

    def evolve(self, current_state):
        return self.controller.step_evolution(current_state)

    def get_version(self):
        return self.controller.release_mgr.active_version

    def get_history(self):
        return self.controller.release_mgr.history

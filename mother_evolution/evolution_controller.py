"""
evolution_controller.py
مدیر مرکزی چرخه تکامل با Core Firewall
"""

class EvolutionController:
    def __init__(self, immutable_core, mutation_engine, sandbox, evaluator, release_mgr):
        self.core = immutable_core
        self.mutation = mutation_engine
        self.sandbox = sandbox
        self.evaluator = evaluator
        self.release_mgr = release_mgr
        self._cycle_count = 0

    def step_evolution(self, current_state):
        print("🔍 [1. Observe & Diagnose] Analyzing system stability...")
        metrics = self.evaluator.observe(current_state)
        print(f"   Stability: {metrics.get('stability', 0):.3f}")
        print(f"   Energy: {metrics.get('energy', 0):.3f}")

        print("🧬 [2. Generate Change] Generating mutation proposal...")
        proposal = self.mutation.generate_proposal(current_state, self.core)
        print(f"   Proposal: {proposal}")

        print("🧪 [3. Simulate] Testing in sandbox...")
        simulation_result = self.sandbox.run(current_state, proposal)
        print(f"   Simulated stability: {simulation_result.get('stability', 0):.3f}")
        print(f"   Simulated energy: {simulation_result.get('energy', 0):.3f}")

        # ⭐ Core Firewall: اعتبارسنجی قبل از Fitness
        print("🛡️ [4. Core Firewall] Validating against immutable rules...")
        core_check = self.core.validate(simulation_result)

        if not core_check["approved"]:
            print("❌ Core Firewall REJECTED mutation:")
            for violation in core_check["violations"]:
                print(f"   ❌ {violation}")
            # ثبت رد در حافظه تکاملی
            self.core.record_decision(
                mutation_id=proposal.get("id", "unknown"),
                proposal=proposal,
                metrics=simulation_result,
                decision=False,
                fitness=0.0
            )
            self._cycle_count += 1
            return {
                "cycle": self._cycle_count,
                "accepted": False,
                "fitness": -1.0,
                "version": self.release_mgr.active_version,
                "reason": core_check["violations"]
            }

        print("⚖️ [5. Validate] Elliptic fitness evaluation...")
        fitness_score = self.evaluator.calculate_fitness(simulation_result)
        print(f"   Fitness: {fitness_score:.3f}")

        if fitness_score > 0:
            print("🚀 [6. Deploy] Mutation accepted and promoted.")
            self.release_mgr.promote(proposal, fitness_score)
            # ثبت پذیرش در حافظه تکاملی
            self.core.record_decision(
                mutation_id=proposal.get("id", "unknown"),
                proposal=proposal,
                metrics=simulation_result,
                decision=True,
                fitness=fitness_score
            )
        else:
            print("❌ Proposal rejected: Violates elliptic balance.")
            self.core.record_decision(
                mutation_id=proposal.get("id", "unknown"),
                proposal=proposal,
                metrics=simulation_result,
                decision=False,
                fitness=fitness_score
            )

        self._cycle_count += 1
        return {
            "cycle": self._cycle_count,
            "accepted": fitness_score > 0,
            "fitness": fitness_score,
            "version": self.release_mgr.active_version
        }

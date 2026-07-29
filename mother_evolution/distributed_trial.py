"""
distributed_trial.py
آزمایش توزیع‌شده‌ی جهش‌ها در شبکه‌ی نودها
"""

import time
import random
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

@dataclass
class TrialResult:
    node_id: str
    proposal_id: str
    accepted: bool
    fitness: float
    metrics: Dict[str, float]
    timestamp: float = field(default_factory=time.time)
    version: str = ""
    trial_id: str = ""  # اضافه‌شده برای تطبیق دقیق با کلید آزمایش

@dataclass
class TrialProposal:
    id: str
    proposal: Dict[str, Any]
    origin_node: str
    timestamp: float = field(default_factory=time.time)
    timeout: float = 10.0
    results: List[TrialResult] = field(default_factory=list)
    status: str = "pending"

class DistributedTrialCoordinator:
    def __init__(self, node_id: str, gossip_layer=None, min_consensus: float = 0.6):
        self.node_id = node_id
        self.gossip = gossip_layer
        self.min_consensus = min_consensus
        self._active_trials: Dict[str, TrialProposal] = {}
        self._trial_history: List[Dict] = []

    # ============================================================
    # Gossip Interface
    # ============================================================
    def receive_gossip(self, msg: Dict):
        msg_type = msg.get("type")
        if msg_type == "trial_proposal":
            return self.receive_trial_proposal(msg)
        elif msg_type == "trial_result":
            return self.receive_trial_result(msg)
        else:
            print(f"⚠️ Unknown gossip message type: {msg_type}")

    def receive_trial_proposal(self, msg: Dict) -> bool:
        trial_id = msg.get("trial_id")
        proposal = msg.get("proposal")
        origin = msg.get("origin")
        timestamp = msg.get("timestamp", time.time())

        if trial_id in self._active_trials:
            return False

        trial = TrialProposal(
            id=trial_id,
            proposal=proposal,
            origin_node=origin,
            timestamp=timestamp
        )
        self._active_trials[trial_id] = trial
        return True

    def receive_trial_result(self, result_data: Dict) -> bool:
        trial_id = result_data.get("trial_id", "")
        result = TrialResult(
            node_id=result_data.get("node_id", ""),
            proposal_id=result_data.get("proposal_id", ""),
            accepted=result_data.get("accepted", False),
            fitness=result_data.get("fitness", 0.0),
            metrics=result_data.get("metrics", {}),
            timestamp=result_data.get("timestamp", time.time()),
            version=result_data.get("version", ""),
            trial_id=trial_id
        )
        return self._process_result(result)

    def _process_result(self, result: TrialResult) -> bool:
        """
        پردازش نتیجه با جستجوی دقیق بر اساس trial_id
        """
        trial = self._active_trials.get(result.trial_id)
        if not trial:
            # جستجوی پشتیبان اگر trial_id مستقیماً مچ نشد
            for t_id, t in self._active_trials.items():
                if t.id == result.trial_id or t.proposal.get("id") == result.proposal_id:
                    trial = t
                    break
        if not trial:
            return False

        # جلوگیری از ثبت تکراری از یک نود
        if any(r.node_id == result.node_id for r in trial.results):
            return False

        trial.results.append(result)

        # بررسی اینکه آیا به حد نصاب آراء (مثلاً ۳ نود) رسیده‌ایم یا خیر
        if len(trial.results) >= 3:
            self._evaluate_trial(trial)

        return True

    # ============================================================
    # Core Logic
    # ============================================================
    def propose_mutation(self, proposal: Dict[str, Any], target_nodes: List[str]) -> str:
        trial_id = f"trial_{uuid.uuid4().hex[:8]}"
        trial = TrialProposal(
            id=trial_id,
            proposal=proposal,
            origin_node=self.node_id
        )
        self._active_trials[trial_id] = trial

        if self.gossip:
            msg = {
                "type": "trial_proposal",
                "trial_id": trial_id,
                "proposal": proposal,
                "origin": self.node_id,
                "timestamp": trial.timestamp
            }
            for node in target_nodes:
                self.gossip.send_to_node(node, msg)

        return trial_id

    def _evaluate_trial(self, trial: TrialProposal) -> Dict:
        if trial.status != "pending":
            return {"status": trial.status}

        accepted = [r for r in trial.results if r.accepted]
        acceptance_rate = len(accepted) / max(1, len(trial.results))
        avg_fitness = sum(r.fitness for r in trial.results) / max(1, len(trial.results))

        if acceptance_rate >= self.min_consensus and avg_fitness > 0:
            trial.status = "accepted"
        elif acceptance_rate < 0.3 or avg_fitness <= 0:
            trial.status.status = "rejected" # صیقل‌کاری امنیتی
            trial.status = "rejected"
        else:
            trial.status = "voting"

        self._trial_history.append({
            "trial_id": trial.id,
            "proposal": trial.proposal,
            "acceptance_rate": acceptance_rate,
            "avg_fitness": avg_fitness,
            "status": trial.status,
            "results": [r.__dict__ for r in trial.results]
        })

        if trial.status in ["accepted", "rejected"]:
            if trial.id in self._active_trials:
                del self._active_trials[trial.id]

        return {
            "trial_id": trial.id,
            "status": trial.status,
            "acceptance_rate": acceptance_rate,
            "avg_fitness": avg_fitness
        }

    def get_trial_status(self, trial_id: str) -> Optional[Dict]:
        trial = self._active_trials.get(trial_id)
        if not trial:
            for record in self._trial_history:
                if record["trial_id"] == trial_id:
                    return record
            return None
        return {
            "trial_id": trial.id,
            "status": trial.status,
            "results_count": len(trial.results),
            "results": [r.__dict__ for r in trial.results]
        }

    def get_history(self, limit: int = 10) -> List[Dict]:
        return self._trial_history[-limit:]

    def get_active_trials(self) -> List[str]:
        return list(self._active_trials.keys())

    def run_local_trial(self, proposal: Dict, current_state: Dict, evaluator, sandbox) -> TrialResult:
        simulated = sandbox.run(current_state, proposal)
        fitness = evaluator.calculate_fitness(simulated)
        accepted = fitness > 0

        result = TrialResult(
            node_id=self.node_id,
            proposal_id=proposal.get("id", f"mut_{uuid.uuid4().hex[:4]}"),
            accepted=accepted,
            fitness=fitness if fitness > 0 else 0.0,
            metrics={
                "stability": simulated.get("stability", 0),
                "energy": simulated.get("energy_cost", 0),
                "adaptability": simulated.get("adaptability", 0)
            },
            version="v1.1"
        )
        return result

    def report_trial_result(self, trial_id: str, result: TrialResult) -> bool:
        result.trial_id = trial_id  # تزریق شناسه آزمایش به نتیجه
        if self.gossip:
            msg = {
                "type": "trial_result",
                "trial_id": trial_id,
                "node_id": result.node_id,
                "proposal_id": result.proposal_id,
                "accepted": result.accepted,
                "fitness": result.fitness,
                "metrics": result.metrics,
                "timestamp": result.timestamp,
                "version": result.version
            }
            self.gossip.broadcast(msg)
        return True

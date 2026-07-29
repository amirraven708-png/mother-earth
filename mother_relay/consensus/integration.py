#!/usr/bin/env python3
"""
integration.py – Updated for TemporalStarConsensus (with schedule-aware integration)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .temporal_star import TemporalStarConsensus, TemporalStar, TemporalObservation
from .temporal_schedule import TemporalSchedule
from ..hypergraph.cluster_state import ClusterStateManager, DynamicCluster


@dataclass
class NetworkState:
    collective_phase: float
    max_distance: float
    phase_coherence: float
    geometry_sim: float
    temporal_agreement: float
    block_clock: float
    consensus_score: float
    credibility: float
    node_count: int
    consensus: bool
    reason: str = "ok"


@dataclass
class StarSignature:
    path: List[int]
    phase: float
    credibility: float
    fitness: Optional[float] = None
    result: Optional[str] = None


class StarConsensusIntegration:
    def __init__(self, bubble_db, consensus: TemporalStarConsensus, trial_coordinator=None):
        self.db = bubble_db
        self.consensus = consensus
        self.coordinator = trial_coordinator
        self._signature_history: List[StarSignature] = []
        self.memory = None
        self.cluster_manager = ClusterStateManager(consensus)
        self._clusters: List[DynamicCluster] = []

    def collect_node_state(self, node_id: str) -> Dict:
        stats = self.db.get_stats() if hasattr(self.db, 'get_stats') else {}
        if not stats:
            stats = {"avg_phase": 0.5, "avg_heat": 0.3, "total_records": 100,
                     "migration_stats": {}, "tick_count": 0}
        return {
            "node_id": node_id,
            "phase": stats.get("avg_phase", 0.0),
            "heat": stats.get("avg_heat", 0.0),
            "density": stats.get("total_records", 0) / 1000.0,
            "migration_count": len(stats.get("migration_stats", {})),
            "gossip_round": stats.get("tick_count", 0),
            "phase_index": int(stats.get("avg_phase", 0.5) * 101) % 101,
            "tick": self.consensus.schedule.get_global_tick()
        }

    def generate_star(self, node_id: str) -> Dict:
        state = self.collect_node_state(node_id)
        star = self.consensus.draw_temporal_star(state)
        return {"node_id": node_id, "star": star, "hash": star.path}

    def validate_network_state(self, stars: Dict[str, TemporalStar]) -> NetworkState:
        self.consensus.receive_star_list(stars)
        star_vectors = {node_id: star.path for node_id, star in stars.items()}
        self.cluster_manager.rebuild_clusters(star_vectors, threshold=0.7)
        self._clusters = self.cluster_manager.clusters
        status = self.consensus.get_consensus_status()

        return NetworkState(
            collective_phase=status.get("collective_phase", 0.0),
            max_distance=status.get("max_distance", 1.0),
            phase_coherence=status.get("phase_coherence", 0.0),
            geometry_sim=status.get("geometry_sim", 0.0),
            temporal_agreement=status.get("temporal_agreement", 0.0),
            block_clock=status.get("block_clock", 0.0),
            consensus_score=status.get("score", 0.0),
            credibility=status.get("credibility", 0.0),
            node_count=status.get("node_count", 0),
            consensus=status.get("consensus", False),
            reason=status.get("reason", "ok")
        )

    def authorize_mutation(self, proposal: Dict, network_state: NetworkState) -> Dict:
        if not network_state.consensus:
            return {
                "approved": False,
                "reason": f"no_consensus (score={network_state.consensus_score:.3f}, max_dist={network_state.max_distance:.3f})"
            }

        if network_state.credibility < 0.6:
            return {
                "approved": False,
                "reason": f"low_credibility (cred={network_state.credibility:.2f})"
            }

        if network_state.phase_coherence < 0.6:
            return {
                "approved": False,
                "reason": f"low_phase_coherence (coherence={network_state.phase_coherence:.2f})"
            }

        if network_state.temporal_agreement < 0.6:
            return {
                "approved": False,
                "reason": f"low_temporal_agreement (agreement={network_state.temporal_agreement:.2f})"
            }

        node_id = proposal.get("node_id", "self")
        cluster = self.cluster_manager.get_cluster_for_node(node_id)
        if cluster and cluster.get_credibility() < 0.5:
            return {
                "approved": False,
                "reason": f"unhealthy_cluster (cred={cluster.get_credibility():.2f})"
            }

        proposal = proposal.copy()
        proposal["star_signature"] = {
            "path": self.consensus._star_cache.get("self", TemporalStar([],0,0,0)).path,
            "phase": network_state.collective_phase,
            "credibility": network_state.credibility,
            "max_distance": network_state.max_distance,
            "phase_coherence": network_state.phase_coherence,
            "temporal_agreement": network_state.temporal_agreement,
            "consensus_score": network_state.consensus_score,
            "cluster_id": cluster.id if cluster else "none"
        }

        self._signature_history.append(StarSignature(
            path=proposal["star_signature"]["path"],
            phase=network_state.collective_phase,
            credibility=network_state.credibility
        ))

        return {"approved": True, "proposal": proposal, "reason": "ok", "cluster_id": cluster.id if cluster else "none"}

    def record_mutation_result(self, proposal: Dict, result: str, fitness: float) -> None:
        if "star_signature" not in proposal:
            return
        sig = StarSignature(
            path=proposal["star_signature"].get("path", []),
            phase=proposal["star_signature"].get("phase", 0.0),
            credibility=proposal["star_signature"].get("credibility", 0.0),
            fitness=fitness,
            result=result
        )
        self._signature_history.append(sig)
        if self.memory is not None:
            self.memory.add_from_proposal(proposal, result, fitness)

    def get_clusters(self) -> List[DynamicCluster]:
        return self._clusters

    def get_cluster_for_node(self, node_id: str):
        return self.cluster_manager.get_cluster_for_node(node_id)

    def get_cluster_summary(self) -> Dict:
        return self.cluster_manager.get_summary()

    def health_check(self) -> Dict:
        status = self.consensus.get_consensus_status()
        cluster_summary = self.get_cluster_summary()
        return {
            "healthy": status.get("consensus", False) and status.get("credibility", 0.0) > 0.5,
            "credibility": status.get("credibility", 0.0),
            "max_distance": status.get("max_distance", 1.0),
            "phase_coherence": status.get("phase_coherence", 0.0),
            "temporal_agreement": status.get("temporal_agreement", 0.0),
            "consensus_score": status.get("score", 0.0),
            "node_count": status.get("node_count", 0),
            "history_length": len(self._signature_history),
            "cluster_count": cluster_summary.get("cluster_count", 0),
            "cluster_health": all(c["is_healthy"] for c in cluster_summary.get("clusters", []))
        }

    def reset(self):
        self.consensus.reset_tracker()
        self.consensus.clear_cache()
        self._signature_history.clear()
        self.cluster_manager.clusters = []

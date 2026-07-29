# بخش اصلاح‌شده از run_kuma_002_tests() - خطوط 450 تا 470

    for r in results:
        key_metric = ""
        if r.scenario_name == "node_drop":
            key_metric = f"recovery={r.recovery_time}s"
        elif r.scenario_name == "phase_delay_ramp":
            break_delay = r.metadata.get('break_delay')
            if break_delay is not None:
                key_metric = f"break={break_delay:.2f}s"
            else:
                key_metric = "break=N/A"
        elif r.scenario_name == "causal_replay":
            max_diff = r.metadata.get('max_difference', 0)
            key_metric = f"diff={max_diff:.4f}"
        elif r.scenario_name == "grf_supervisor":
            key_metric = f"R={r.final_order_parameter:.4f}"
        
        status = "✅" if r.success else "❌"
        print(f"{r.scenario_name:<20} | {status:<10} | {r.resilience_score:<12.3f} | {key_metric:<20}")

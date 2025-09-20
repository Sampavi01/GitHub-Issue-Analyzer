# agents/reporter.py
from typing import Dict, Any

def generate_report(issue_types_counts: Dict[str, int], workers_per_task: Dict[str, int]) -> Dict[str, Any]:
    report = {}
    for issue_type, count in issue_types_counts.items():
        workers = int(workers_per_task.get(issue_type, 0))
        if workers <= 0:
            avg_load = None if count > 0 else 0
            recommendation = f"No workers assigned for '{issue_type}'. Consider hiring or reassigning."
        else:
            avg_load = count / workers
            if avg_load > 10:
                recommendation = f"High load (~{avg_load:.1f} issues/worker). Consider hiring."
            elif avg_load > 3:
                recommendation = f"Moderate load (~{avg_load:.1f} issues/worker). Monitor & consider hiring."
            else:
                recommendation = f"Load looks reasonable (~{avg_load:.1f} issues/worker)."

        suggested_hires = 0
        if workers > 0:
            if avg_load is not None and avg_load > 5:
                # crude suggestion: bring avg_load down to ~3
                suggested_hires = int(max(0, (count / 3) - workers))
        else:
            suggested_hires = int(max(0, -workers + (count // 3))) if count > 0 else 0

        report[issue_type] = {
            "issues_count": count,
            "workers_assigned": workers,
            "avg_load": avg_load,
            "suggested_hires": suggested_hires,
            "recommendation": recommendation
        }
    return report


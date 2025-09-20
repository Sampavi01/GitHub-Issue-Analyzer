def generate_report(issue_counts: dict, workers_per_task: dict):
    """
    Generate user-friendly report for task allocation.
    """
    report = []
    for task, count in issue_counts.items():
        workers = workers_per_task.get(task, 0)
        load = count / (workers or 1)
        warning = " ⚠️ More workers needed!" if workers < 1 or load > 10 else ""
        report.append(
            f"Task: {task}, Issues: {count}, Workers: {workers}, Load: {load:.2f}{warning}"
        )
    return report

from servers.shared.constants import METRICS


def build_analytics_tools(mcp):
    for metric_id, description in zip(METRICS, [
        "Calculate conversion rate from funnel events",
        "Calculate customer churn rate over a period",
        "Calculate monthly recurring revenue",
        "Calculate annual recurring revenue",
        "Calculate daily active users",
        "Calculate monthly active users",
        "Calculate user retention cohort metrics",
        "Calculate customer lifetime value",
        "Calculate customer acquisition cost",
        "Calculate net promoter score from survey responses",
        "Calculate average API response time",
        "Calculate error rate across services",
        "Calculate request throughput per second",
        "Calculate p99 latency from trace data",
        "Calculate storage usage across tenants",
        "Calculate active session count",
        "Analyze signup funnel drop-off stages",
        "Calculate shopping cart abandonment rate",
        "Calculate support ticket volume trends",
        "Calculate SLA compliance percentage",
    ]):
        def make_metric(mid, desc):
            def calculate_metric(input_values: str = "") -> str:
                return f"{mid.upper()} computed (input={input_values or 'defaults'})"
            calculate_metric.__name__ = f"calculate_{mid}"
            calculate_metric.__doc__ = desc
            return calculate_metric
        mcp.tool()(make_metric(metric_id, description))

    @mcp.tool()
    def generate_report(report_type: str, start_date: str, end_date: str) -> str:
        return f"Report '{report_type}' generated for {start_date} to {end_date}"

    @mcp.tool()
    def aggregate_data(entity_type: str, group_by: str = "day") -> str:
        return f"Aggregated {entity_type} data grouped by {group_by}"

    @mcp.tool()
    def compare_periods(metric: str, period_a: str, period_b: str) -> str:
        return f"Compared {metric}: {period_a} vs {period_b} -> +12.4%"

    @mcp.tool()
    def forecast_trend(metric: str, horizon_days: int = 30) -> str:
        return f"Forecast {metric} for next {horizon_days} days: upward trend"

    @mcp.tool()
    def detect_anomaly(metric: str, threshold: float = 2.0) -> str:
        return f"Anomaly detection on {metric}: 2 outliers above {threshold} sigma"

    @mcp.tool()
    def rank_entities(entity_type: str, metric: str, limit: int = 10) -> str:
        return f"Top {limit} {entity_type} by {metric}"

    @mcp.tool()
    def export_dashboard(dashboard_id: str, format: str = "pdf") -> str:
        return f"Exported dashboard {dashboard_id} as {format}"

    @mcp.tool()
    def summarize_usage(tenant_id: str) -> str:
        return f"Usage summary for tenant {tenant_id}: 42k API calls, 3.2GB storage"

    @mcp.tool()
    def calculate_growth_rate(metric: str, window: str = "month") -> str:
        return f"Growth rate for {metric} over {window}: 8.7%"

    @mcp.tool()
    def build_funnel(steps: str) -> str:
        return f"Funnel built for steps [{steps}]: 3 stages analyzed"

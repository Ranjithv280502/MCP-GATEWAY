ENTITY_TYPES = [
    "User", "Account", "Order", "Product", "Invoice", "Payment", "Customer",
    "Team", "Project", "Task", "Comment", "File", "Document", "Event",
    "Message", "Notification", "Subscription", "Plan", "Coupon", "Review",
    "Category", "Tag", "Address", "Contact", "Lead", "Deal", "Pipeline",
    "Report", "Dashboard", "Metric", "Alert", "Webhook", "Integration",
    "ApiKey", "Session", "Token", "Role", "Permission", "AuditLog", "Setting",
]

SCHEMA_PROFILES = [
    "strict", "minimal", "public-api", "internal-api", "export",
    "import", "webhook-payload", "mobile-client", "admin-console",
]

METRICS = [
    "conversion_rate", "churn_rate", "mrr", "arr", "dau", "mau",
    "retention", "ltv", "cac", "nps", "response_time", "error_rate",
    "throughput", "latency_p99", "storage_usage", "active_sessions",
    "signup_funnel", "cart_abandonment", "ticket_volume", "sla_compliance",
]

WORKFLOW_ACTIONS = [
    "send_email", "send_sms", "send_push", "schedule_job", "cancel_job",
    "trigger_webhook", "retry_webhook", "assign_task", "escalate_ticket",
    "approve_request", "reject_request", "archive_record", "restore_record",
    "sync_external", "rotate_secret", "flush_cache", "reindex_search",
    "publish_event", "enqueue_message", "run_health_check",
]

from servers.shared.constants import WORKFLOW_ACTIONS


def build_workflow_tools(mcp):
    for action_id in WORKFLOW_ACTIONS:
        def make_action(aid):
            def run_action(target: str = "", params: str = "") -> str:
                return f"Action '{aid}' executed on '{target or 'default'}'"
            run_action.__name__ = aid
            run_action.__doc__ = f"Execute workflow action: {aid.replace('_', ' ')}"
            return run_action
        mcp.tool()(make_action(action_id))

    @mcp.tool()
    def validate_record(payload: str) -> str:
        return "[PASS] Record workflow schema check (workflow server)"

    @mcp.tool()
    def create_workflow(name: str, steps: str) -> str:
        return f"Workflow '{name}' created with steps: {steps}"

    @mcp.tool()
    def run_workflow(workflow_id: str, input_data: str = "") -> str:
        return f"Workflow {workflow_id} started (run-id: wf-001)"

    @mcp.tool()
    def list_workflows(status: str = "active") -> str:
        return f"Workflows ({status}): onboarding, billing-retry, data-sync"

    @mcp.tool()
    def pause_workflow(workflow_id: str) -> str:
        return f"Workflow {workflow_id} paused"

    @mcp.tool()
    def resume_workflow(workflow_id: str) -> str:
        return f"Workflow {workflow_id} resumed"

    @mcp.tool()
    def get_job_status(job_id: str) -> str:
        return f"Job {job_id}: completed"

    @mcp.tool()
    def cancel_job(job_id: str) -> str:
        return f"Job {job_id}: cancelled"

    @mcp.tool()
    def register_webhook(url: str, events: str) -> str:
        return f"Webhook registered at {url} for events: {events}"

    @mcp.tool()
    def test_webhook(webhook_id: str) -> str:
        return f"Webhook {webhook_id}: test delivery 200 OK"

    @mcp.tool()
    def send_notification(channel: str, recipient: str, message: str) -> str:
        return f"Notification sent via {channel} to {recipient}"

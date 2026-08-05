from servers.shared.constants import ENTITY_TYPES


def build_data_tools(mcp):
    for entity_type in ENTITY_TYPES:
        et_lower = entity_type.lower()

        def make_search(et, rtl):
            def search_records(query: str = "", count: int = 10) -> str:
                return f"Search {et}: found {min(count, 3)} result(s) for '{query}'"
            search_records.__name__ = f"search_{rtl}"
            search_records.__doc__ = f"Search {et} records by query parameters"
            return search_records
        mcp.tool()(make_search(entity_type, et_lower))

        def make_get(et, rtl):
            def get_record(record_id: str) -> str:
                return f"Retrieved {et}/{record_id}"
            get_record.__name__ = f"get_{rtl}"
            get_record.__doc__ = f"Read a single {et} record by ID"
            return get_record
        mcp.tool()(make_get(entity_type, et_lower))

        def make_create(et, rtl):
            def create_record(payload: str) -> str:
                return f"Created {et} record (201)"
            create_record.__name__ = f"create_{rtl}"
            create_record.__doc__ = f"Create a new {et} record"
            return create_record
        mcp.tool()(make_create(entity_type, et_lower))

    @mcp.tool()
    def validate_record(payload: str) -> str:
        return "[PASS] Record schema check (data server)"

    @mcp.tool()
    def bulk_export(entity_type: str = "User", since: str = "") -> str:
        return f"Bulk export started for {entity_type} since={since or 'beginning'}"

    @mcp.tool()
    def bulk_import(file_path: str) -> str:
        return f"Bulk import queued from {file_path}"

    @mcp.tool()
    def transaction_batch(payload: str) -> str:
        return "Transaction batch processed: 3 records committed"

    @mcp.tool()
    def history_user(user_id: str) -> str:
        return f"History for User/{user_id}: 5 versions"

    @mcp.tool()
    def patch_task(task_id: str, patch: str) -> str:
        return f"Patched Task/{task_id}"

    @mcp.tool()
    def delete_order(order_id: str) -> str:
        return f"Deleted Order/{order_id}"

    @mcp.tool()
    def list_collections() -> str:
        return "Collections: users, orders, products, tasks, invoices"

    @mcp.tool()
    def count_records(entity_type: str) -> str:
        return f"Count {entity_type}: 1,024 records"

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from gateway.auth import (
    Token,
    TokenData,
    UserInfo,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from gateway.config import ensure_data_dirs, get_settings
from gateway.registry import get_registry

os.environ.setdefault("MCP_GATEWAY_ROOT", str(get_settings().project_root))


class ToolSearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=8, ge=1, le=50)


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolSearchResult(BaseModel):
    name: str
    description: str
    relevance_score: float
    namespace: str | None = None
    server_id: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_data_dirs()
    registry = get_registry()
    try:
        info = await registry.connect_all()
        app.state.boot_info = info
    except Exception as exc:
        app.state.boot_info = {"error": str(exc), "total_tools": 0}
    yield
    await registry.disconnect_all()


app = FastAPI(
    title="MCP Gateway",
    description="Unified MCP gateway with semantic tool search, RBAC, audit, and rate limiting",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    registry = get_registry()
    return {
        "status": "ok" if registry.is_connected else "degraded",
        "connected": registry.is_connected,
        "tool_count": registry.tool_count,
        "boot_info": getattr(app.state, "boot_info", {}),
    }


@app.post("/auth/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    registry = get_registry()
    user = authenticate_user(form_data.username, form_data.password, registry.rbac)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user["email"], "roles": user["roles"]})
    return Token(access_token=token, token_type="bearer", roles=user["roles"])


@app.get("/auth/me", response_model=UserInfo)
async def me(user: TokenData = Depends(get_current_user)):
    return UserInfo(email=user.email, roles=user.roles)


@app.get("/tools")
async def list_all_tools(user: TokenData = Depends(get_current_user)):
    registry = get_registry()
    tools = registry.get_all_tools()
    allowed = []
    for tool in tools:
        ok, _ = registry.rbac.is_allowed(user.email, tool["name"])
        if ok:
            allowed.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "namespace": tool.get("namespace"),
                "server_id": tool.get("server_id"),
            })
    return {"total": len(tools), "allowed_for_user": len(allowed), "tools": allowed}


@app.post("/tools/search")
async def search_tools(req: ToolSearchRequest, user: TokenData = Depends(get_current_user)):
    registry = get_registry()
    results = registry.search_tools(req.query, req.top_k)
    filtered = []
    for tool in results:
        ok, reason = registry.rbac.is_allowed(user.email, tool["name"])
        if ok:
            filtered.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "relevance_score": tool.get("relevance_score", 0),
                "namespace": tool.get("namespace"),
                "server_id": tool.get("server_id"),
            })
    savings = registry.semantic.estimate_token_savings(req.top_k)
    return {
        "query": req.query,
        "top_k": req.top_k,
        "results": filtered,
        "token_savings": savings,
    }


@app.post("/tools/call")
async def call_tool(req: ToolCallRequest, user: TokenData = Depends(get_current_user)):
    registry = get_registry()
    result = await registry.invoke_tool(req.tool_name, req.arguments, user.email)
    if not result.get("success") and result.get("decision") in ("denied", "rate_limited"):
        status_code = 429 if result.get("decision") == "rate_limited" else 403
        raise HTTPException(status_code=status_code, detail=result)
    return result


@app.get("/audit")
async def get_audit_log(
    caller: str | None = None,
    tool_name: str | None = None,
    decision: str | None = None,
    limit: int = Query(default=50, le=500),
    user: TokenData = Depends(get_current_user),
):
    if "admin" not in user.roles and "analyst" not in user.roles:
        caller = user.email
    registry = get_registry()
    entries = await registry.audit.query(caller, tool_name, decision, limit)
    return {"entries": entries, "stats": registry.audit.stats()}


@app.get("/admin/collisions")
async def get_collisions(user: TokenData = Depends(get_current_user)):
    if "admin" not in user.roles:
        raise HTTPException(status_code=403, detail="Admin only")
    registry = get_registry()
    return {"collisions": registry.collision.get_collisions()}


@app.get("/admin/stats")
async def admin_stats(user: TokenData = Depends(get_current_user)):
    if "admin" not in user.roles:
        raise HTTPException(status_code=403, detail="Admin only")
    registry = get_registry()
    return {
        "tool_count": registry.tool_count,
        "audit": registry.audit.stats(),
        "token_savings": registry.semantic.estimate_token_savings(),
        "collisions": len(registry.collision.get_collisions()),
    }


def main():
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "gateway.main:app",
        host=settings.gateway_host,
        port=settings.gateway_port,
        reload=False,
    )


if __name__ == "__main__":
    main()

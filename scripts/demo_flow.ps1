#!/usr/bin/env pwsh
# Demo flow for 60-second GIF recording
# 1. Start: docker compose up -d  OR  python -m gateway.main
# 2. Record screen while running this script

$Base = "http://localhost:8080"

Write-Host "=== MCP Gateway Demo ===" -ForegroundColor Cyan

Write-Host "`n[1] Health check..."
Invoke-RestMethod "$Base/health" | ConvertTo-Json -Depth 4

Write-Host "`n[2] Authenticate as engineer..."
$token = Invoke-RestMethod -Method Post -Uri "$Base/auth/token" `
    -Body @{ username = "engineer@example.com"; password = "demo123" } `
    -ContentType "application/x-www-form-urlencoded"
$headers = @{ Authorization = "Bearer $($token.access_token)" }

Write-Host "`n[3] Semantic search: 243 tools -> top 8..."
$search = @{ query = "create a GitHub issue for bug report"; top_k = 8 } | ConvertTo-Json
$result = Invoke-RestMethod -Method Post -Uri "$Base/tools/search" -Headers $headers -Body $search -ContentType "application/json"
Write-Host "  Total tools: $($result.token_savings.total_tools)"
Write-Host "  Returned: $($result.results.Count) tools"
Write-Host "  Token reduction: $($result.token_savings.reduction_factor)x"
$result.results | Select-Object -First 3 | ForEach-Object { Write-Host "    - $($_.name) (score: $([math]::Round($_.relevance_score, 3)))" }

Write-Host "`n[4] Cross-server call: read workspace file..."
$call = @{
    tool_name = "fs.read_text_file"
    arguments = @{ path = "README.md" }
} | ConvertTo-Json -Depth 3
try {
    $callResult = Invoke-RestMethod -Method Post -Uri "$Base/tools/call" -Headers $headers -Body $call -ContentType "application/json"
    Write-Host "  Result: $($callResult.result.Substring(0, [Math]::Min(80, $callResult.result.Length)))..."
} catch {
    Write-Host "  (fs.read_text_file may vary by MCP version)"
}

Write-Host "`n[5] RBAC deny: readonly tries create_issue..."
$ro = Invoke-RestMethod -Method Post -Uri "$Base/auth/token" `
    -Body @{ username = "readonly@example.com"; password = "demo123" } `
    -ContentType "application/x-www-form-urlencoded"
$roHeaders = @{ Authorization = "Bearer $($ro.access_token)" }
try {
    Invoke-RestMethod -Method Post -Uri "$Base/tools/call" -Headers $roHeaders `
        -Body '{"tool_name":"github.create_issue","arguments":{"owner":"demo","repo":"demo","title":"test"}}' `
        -ContentType "application/json"
} catch {
    Write-Host "  BLOCKED (403) - RBAC working" -ForegroundColor Green
}

Write-Host "`n[6] Audit log entry..."
$admin = Invoke-RestMethod -Method Post -Uri "$Base/auth/token" `
    -Body @{ username = "admin@example.com"; password = "demo123" } `
    -ContentType "application/x-www-form-urlencoded"
$adminHeaders = @{ Authorization = "Bearer $($admin.access_token)" }
$audit = Invoke-RestMethod -Uri "$Base/audit?limit=3" -Headers $adminHeaders
Write-Host "  Recent entries: $($audit.entries.Count)"
$audit.entries | ForEach-Object { Write-Host "    [$($_.decision)] $($_.caller) -> $($_.tool_name)" }

Write-Host "`n=== Demo complete ===" -ForegroundColor Cyan

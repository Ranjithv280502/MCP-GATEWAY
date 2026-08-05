#!/usr/bin/env pwsh
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Env:MCP_GATEWAY_ROOT = $Root
$Env:PYTHONPATH = "$Root;$Env:PYTHONPATH"

Write-Host "Starting MCP Gateway on http://localhost:8080"
python -m gateway.main

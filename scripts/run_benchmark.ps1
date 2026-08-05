#!/usr/bin/env pwsh
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Env:MCP_GATEWAY_ROOT = $Root
$Env:PYTHONPATH = "$Root;$Env:PYTHONPATH"
Set-Location $Root
python benchmarks/run_benchmark.py

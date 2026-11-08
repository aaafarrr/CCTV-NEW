# 1-Click Startup Script for CCTV NEW Enterprise (Windows PowerShell)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  CCTV NEW - Enterprise AI Surveillance & Multi-Cloud NVR " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

Write-Host "[1/2] Starting FastAPI Backend Server on http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; python -m uvicorn app.main:app --reload --port 8000"

Write-Host "[2/2] Starting React + Ant Design Frontend on http://localhost:3000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Write-Host ""
Write-Host "Servers launched in separate windows!" -ForegroundColor Yellow
Write-Host "-> Frontend UI : http://localhost:3000 (Login: admin / admin123)"
Write-Host "-> Backend Docs: http://localhost:8000/docs"


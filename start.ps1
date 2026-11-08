# 1-Click Startup Script for Clospol CCTV & Google Drive NVR
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "     Clospol CCTV - Surveillance & Google Drive Storage   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

Write-Host "[1/2] Menjalankan Backend FastAPI (Port 8000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; python -m uvicorn app.main:app --reload --port 8000"

Write-Host "[2/2] Menjalankan Frontend Vite React (Port 3000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Write-Host ""
Write-Host "Kedua server berhasil dijalankan pada jendela terpisah!" -ForegroundColor Yellow
Write-Host "-> Buka Browser: http://localhost:3000" -ForegroundColor Cyan
Write-Host "-> Dokumentasi API: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "-> Saat pertama kali buka, Anda akan diarahkan ke form Setup Awal untuk membuat akun Administrator."

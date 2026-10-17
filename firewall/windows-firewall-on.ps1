# Kavach - block other computers from reaching the demo's ports (Windows Defender Firewall).
#
# Run ONCE in an Administrator PowerShell:
#     powershell -ExecutionPolicy Bypass -File firewall\windows-firewall-on.ps1
# Undo:
#     powershell -ExecutionPolicy Bypass -File firewall\windows-firewall-off.ps1
#
# Why: `next dev` listens on every network interface, so on shared Wi-Fi (e.g. at the event)
# anyone could open http://<your-ip>:3000 - including /lab. PostgreSQL's installer may also open
# 5432. These rules block INBOUND connections from other machines only. Traffic on this laptop
# (localhost / 127.0.0.1) is never filtered by Windows Firewall, so Kavach keeps working normally.

$ErrorActionPreference = "Stop"

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Please run this from an Administrator PowerShell." -ForegroundColor Red
    exit 1
}

$name  = "Kavach demo - block remote access"
$ports = @(
    3000,  # Kavach UI (Next.js) + /lab
    3001,  # College Portal
    3002,  # spare Kavach UI port used for testing
    4000,  # Attack Lab server
    5000,  # Citizen Portal
    8000,  # Kavach API (FastAPI)
    5432   # PostgreSQL
)

Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue | Remove-NetFirewallRule

New-NetFirewallRule -DisplayName $name `
    -Description "Blocks other machines from Kavach demo ports. Localhost is unaffected." `
    -Direction Inbound -Action Block -Protocol TCP -LocalPort $ports -Profile Any | Out-Null

Write-Host "Done. Other computers can no longer reach ports $($ports -join ', ')." -ForegroundColor Green
Write-Host "Kavach still works on this laptop at http://localhost:3000"

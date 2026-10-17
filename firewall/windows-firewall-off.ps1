# Kavach - remove the rule added by windows-firewall-on.ps1 (run in an Administrator PowerShell).
#     powershell -ExecutionPolicy Bypass -File firewall\windows-firewall-off.ps1

$name = "Kavach demo - block remote access"
$rules = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
if ($rules) {
    $rules | Remove-NetFirewallRule
    Write-Host "Removed '$name'." -ForegroundColor Green
} else {
    Write-Host "No Kavach firewall rule found - nothing to remove."
}

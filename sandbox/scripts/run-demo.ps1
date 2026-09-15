param([string]$BaseUrl = "http://localhost:8080")

Write-Output "SPP REFERENCE SANDBOX — experimental / non-normative"
foreach ($Scenario in @("admitted", "degraded", "denied", "expired", "tampered", "missing-restriction-ack", "changed-subject")) {
    Write-Output "`n== $Scenario =="
    Invoke-RestMethod -Method Post -Uri "$BaseUrl/verify" -ContentType "application/json" -Body (@{ scenario = $Scenario } | ConvertTo-Json -Compress) | ConvertTo-Json -Depth 12
}

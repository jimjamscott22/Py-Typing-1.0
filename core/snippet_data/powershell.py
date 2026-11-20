"""PowerShell snippets. Cmdlets are checked by test_snippets.py's allowlist."""

from core.models import Snippet
from core.snippet_data._helpers import code

_L = "PowerShell"

SNIPPETS: tuple[Snippet, ...] = (
    Snippet(_L, "Junior", "Find the largest files", code(r"""
Get-ChildItem -Path C:\Logs -Recurse -File |
    Where-Object { $_.Length -gt 10MB } |
    Sort-Object Length -Descending |
    Select-Object -First 5 FullName, Length
""")),
    Snippet(_L, "Junior", "Busy processes", code(r"""
$procs = Get-Process | Where-Object CPU -gt 100
foreach ($p in $procs) {
    Write-Host "$($p.Name) used $([math]::Round($p.CPU)) CPU seconds"
}
""")),
    Snippet(_L, "Junior", "Restart a stopped service", code(r"""
$service = Get-Service -Name Spooler
if ($service.Status -ne 'Running') {
    Start-Service -Name Spooler
}
Write-Output "Spooler is $((Get-Service Spooler).Status)"
""")),
    Snippet(_L, "Mid", "Function with validated parameters", code(r"""
function Get-DiskReport {
    param(
        [Parameter(Mandatory)] [string]$ComputerName,
        [ValidateSet('C:', 'D:')] [string]$Drive = 'C:'
    )
    Get-CimInstance Win32_LogicalDisk -ComputerName $ComputerName |
        Where-Object DeviceID -eq $Drive
}
""")),
    Snippet(_L, "Mid", "Splatting into Export-Csv", code(r"""
$params = @{
    Path              = 'C:\Reports\services.csv'
    NoTypeInformation = $true
    Encoding          = 'UTF8'
}
Get-Service | Select-Object Name, Status | Export-Csv @params
""")),
    Snippet(_L, "Mid", "Try and catch a missing file", code(r"""
try {
    $content = Get-Content -Path $path -ErrorAction Stop
    Write-Output "Read $($content.Count) lines"
}
catch [System.IO.FileNotFoundException] {
    Write-Warning "Missing file: $path"
}
""")),
    Snippet(_L, "Senior", "Advanced function with pipeline input", code(r"""
function Test-Port {
    [CmdletBinding()]
    param([Parameter(ValueFromPipeline)] [string]$ComputerName)
    process {
        Test-NetConnection -ComputerName $ComputerName -Port 443
    }
}
""")),
    Snippet(_L, "Senior", "Remoting with Invoke-Command", code(r"""
$servers = 'web01', 'web02', 'web03'
Invoke-Command -ComputerName $servers -ScriptBlock {
    Get-Service -Name W3SVC | Select-Object Name, Status
} | Sort-Object PSComputerName |
    Format-Table PSComputerName, Name, Status
""")),
    Snippet(_L, "Senior", "Regex captures into objects", code(r"""
Get-Content .\access.log | ForEach-Object {
    if ($_ -match '(?<ip>\d+\.\d+\.\d+\.\d+) .* (?<code>\d{3}) ') {
        [pscustomobject]@{ IP = $Matches.ip; Code = $Matches.code }
    }
}
""")),
)

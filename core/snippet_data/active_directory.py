"""Active Directory snippets (PowerShell ActiveDirectory and GroupPolicy modules)."""

from core.models import Snippet
from core.snippet_data._helpers import code

_L = "Active Directory"

SNIPPETS: tuple[Snippet, ...] = (
    Snippet(_L, "Junior", "Look up a user", code(r"""
$user = Get-ADUser -Identity jsmith -Properties DisplayName, Department
Write-Output $user.DisplayName
$user | Select-Object Name, Department, Enabled
""")),
    Snippet(_L, "Junior", "List a group's user members", code(r"""
Get-ADGroupMember -Identity 'Helpdesk' |
    Where-Object objectClass -eq 'user' |
    Get-ADUser -Properties Title |
    Select-Object Name, Title
""")),
    Snippet(_L, "Junior", "Find lab computers", code(r"""
Get-ADComputer -Filter "Name -like 'LAB-*'" `
    -Properties OperatingSystem |
    Select-Object Name, OperatingSystem |
    Sort-Object Name
""")),
    Snippet(_L, "Mid", "Unlock locked accounts", code(r"""
Search-ADAccount -LockedOut -UsersOnly |
    ForEach-Object {
        Unlock-ADAccount -Identity $_
        Write-Output "Unlocked $($_.SamAccountName)"
    }
""")),
    Snippet(_L, "Mid", "Create a user with splatting", code(r"""
$newUser = @{
    Name              = 'Jane Smith'
    SamAccountName    = 'jsmith'
    UserPrincipalName = 'jsmith@contoso.com'
    Path              = 'OU=Staff,DC=contoso,DC=com'
    Enabled           = $false
}
New-ADUser @newUser
""")),
    Snippet(_L, "Mid", "Export stale accounts", code(r"""
$old = (Get-Date).AddDays(-90)
Get-ADUser -Filter {LastLogonDate -lt $old} -Properties LastLogonDate |
    Select-Object Name, LastLogonDate |
    Export-Csv -Path .\stale-users.csv -NoTypeInformation
""")),
    Snippet(_L, "Senior", "Bulk add members with error handling", code(r"""
Import-Csv .\new-hires.csv | ForEach-Object {
    $sam = $_.SamAccountName
    try {
        Add-ADGroupMember Staff -Members $sam -ErrorAction Stop
    }
    catch { Write-Warning "${sam}: $($_.Exception.Message)" }
}
""")),
    Snippet(_L, "Senior", "Replication failures on every DC", code(r"""
Get-ADDomainController -Filter * |
    ForEach-Object {
        Get-ADReplicationFailure -Target $_.HostName
    } |
    Select-Object Server, FirstFailureTime, FailureCount, LastError
""")),
    Snippet(_L, "Senior", "Password policy and GPO status", code(r"""
Get-ADDefaultDomainPasswordPolicy |
    Select-Object MinPasswordLength, LockoutThreshold, MaxPasswordAge

Get-GPO -All |
    Where-Object GpoStatus -ne 'AllSettingsEnabled' |
    Select-Object DisplayName, GpoStatus
""")),
)

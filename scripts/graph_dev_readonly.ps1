<#!
.SYNOPSIS
  Optional, read-only Microsoft Graph demo in your OWN authorized development tenant.
.DESCRIPTION
  Not exercised in this project. Requires Microsoft.Graph PowerShell SDK, delegated
  tenant permissions and explicit confirmation. Never execute against employer/CERN tenant.
#!>
param(
    [Parameter(Mandatory=$true)][string]$TenantId,
    [switch]$AcknowledgeDevelopmentTenant
)
$ErrorActionPreference = 'Stop'
if (-not $AcknowledgeDevelopmentTenant) {
    throw 'Explicitly pass -AcknowledgeDevelopmentTenant for an authorized development tenant only.'
}
Import-Module Microsoft.Graph.Authentication -ErrorAction Stop
Import-Module Microsoft.Graph.Users -ErrorAction Stop
Connect-MgGraph -TenantId $TenantId -Scopes 'User.ReadBasic.All' -NoWelcome
$context = Get-MgContext
if ($context.TenantId -ne $TenantId) { throw 'Connected to a different tenant. Stopping.' }
Write-Host 'Read-only demonstration; no data will be written to disk.'
Get-MgUser -Top 5 -Property 'id,displayName,userPrincipalName' | Select-Object DisplayName, Id
Disconnect-MgGraph | Out-Null

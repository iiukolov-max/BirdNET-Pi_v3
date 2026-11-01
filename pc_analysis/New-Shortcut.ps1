$ErrorActionPreference='Stop'
$taskShell=New-Object -ComObject WScript.Shell
$taskLink=$taskShell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'BirdNET Analysis.lnk'))
$taskLink.TargetPath=Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
$taskLink.Arguments='-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $PSScriptRoot 'Start-Service.ps1')+'"'
$taskLink.WorkingDirectory=$PSScriptRoot
$taskLink.Description='Start the BirdNET analysis service on this computer'
$taskLink.Save()
Write-Host 'Created BirdNET Analysis on the desktop.'

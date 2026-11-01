param(
 [Parameter(Mandatory=$true)][string]$PiAddress,
 [ValidateSet('cuda','cpu')][string]$Backend='cuda',
 [string]$Python='python'
)
$ErrorActionPreference='Stop'
$address=[IPAddress]::Parse($PiAddress)
if($address.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork){throw 'Use a LAN IPv4 address for the Pi'}
$taskVenv=Join-Path $PSScriptRoot ('.venv-'+$Backend)
& $Python -c "import sys; assert sys.version_info[:2] == (3,10), 'Use Python 3.10 x64'; assert sys.maxsize > 2**32, 'Use 64-bit Python'"
if($LASTEXITCODE -ne 0){throw 'Python version check failed'}
& $Python -m venv $taskVenv
if($LASTEXITCODE -ne 0){throw 'Virtual environment creation failed'}
$taskPython=Join-Path $taskVenv 'Scripts/python.exe'
& $taskPython -m pip install --upgrade pip
if($LASTEXITCODE -ne 0){throw 'pip upgrade failed'}
$taskRequirements=if($Backend -eq 'cuda'){'requirements-gpu.txt'}else{'requirements.txt'}
& $taskPython -m pip install -r (Join-Path $PSScriptRoot $taskRequirements)
if($LASTEXITCODE -ne 0){throw 'Dependency installation failed'}
& $taskPython (Join-Path $PSScriptRoot '../scripts/download_v3.py') --manifest (Join-Path $PSScriptRoot ('models-'+$Backend+'.json')) --directory (Join-Path $PSScriptRoot 'models')
if($LASTEXITCODE -ne 0){throw 'Model download/verification failed'}
@{PiAddress=$address.ToString();Backend=$Backend} | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $PSScriptRoot 'service-settings.json')
Write-Host 'Setup finished. Run New-Shortcut.ps1, then use BirdNET Analysis on the desktop.'

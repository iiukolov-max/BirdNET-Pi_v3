param([string]$PiAddress='', [ValidateSet('','cuda','cpu')][string]$Backend='', [switch]$NoWait, [ValidateRange(1024,65535)][int]$Port=8766)
$ErrorActionPreference='Stop'
try {
 $taskSettings=Join-Path $PSScriptRoot 'service-settings.json'
 if(Test-Path -LiteralPath $taskSettings){
  $taskConfig=Get-Content -Raw -LiteralPath $taskSettings | ConvertFrom-Json
  if(!$PiAddress){$PiAddress=$taskConfig.PiAddress}
  if(!$Backend){$Backend=$taskConfig.Backend}
 }
 if(!$Backend){$Backend='cuda'}
 $taskReady=$null
 try {$taskReady=Invoke-RestMethod -Uri ('http://127.0.0.1:'+$Port+'/health') -TimeoutSec 3} catch {}
 if($taskReady.ready -and $taskReady.model_sha256 -ne 'f4af6290690e0031cd785d4c810167af83467ce1426f4eba249ca994681000db'){throw 'Port 8766 is occupied by a different service'}
 if(!$taskReady.ready){
  $taskAddress=[IPAddress]::Parse($PiAddress)
  if($taskAddress.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork){throw 'Use a LAN IPv4 address for the Pi'}
  $taskIndices=@(Get-NetAdapter -Physical | Where-Object {$_.Status -eq 'Up'} | Select-Object -ExpandProperty ifIndex)
  $taskAddresses=@(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceIndex -in $taskIndices -and $_.IPAddress -notlike '169.254.*' -and $_.IPAddress -ne '127.0.0.1'} | Select-Object -ExpandProperty IPAddress)
  if(!$taskAddresses.Count){throw 'No active physical LAN IPv4 address found'}
  $taskPython=Join-Path $PSScriptRoot ('.venv-'+$Backend+'/Scripts/python.exe')
  if(!(Test-Path -LiteralPath $taskPython)){throw 'Run Setup-Service.ps1 first'}
  $taskModel=if($Backend -eq 'cuda'){'BirdNET+_V3.0-preview3.1_Global_11K_FP16_pruned.onnx'}else{'BirdNET+_V3.0-preview3.1_Global_11K_FP16_pruned.tflite'}
  $taskEntry=if($Backend -eq 'cuda'){'gpu.py'}else{'server.py'}
  $taskData=Join-Path $PSScriptRoot 'data'
  [IO.Directory]::CreateDirectory($taskData) | Out-Null
  $taskArgs=@('-u',(Join-Path $PSScriptRoot $taskEntry),'--model',(Join-Path $PSScriptRoot ('models/'+$taskModel)),'--labels',(Join-Path $PSScriptRoot 'models/BirdNET+_V3.0-preview3.1_Global_11K_Labels.csv'),'--cache',(Join-Path $taskData ('cache-'+$Backend)),'--port',[string]$Port,'--bind','0.0.0.0','--allow-client',$taskAddress.ToString())
  foreach($taskIP in $taskAddresses){$taskArgs+=@('--advertise-ip',$taskIP)}
  $taskQuoted=@($taskArgs | ForEach-Object {'"'+$_+'"'})
  $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
  $taskProcess=Start-Process -FilePath $taskPython -ArgumentList $taskQuoted -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskData ($taskStamp+'.stdout.log')) -RedirectStandardError (Join-Path $taskData ($taskStamp+'.stderr.log')) -PassThru
  $taskProcess.Id | Set-Content (Join-Path $taskData 'server.pid')
  for($taskIndex=0;$taskIndex -lt 60;$taskIndex++){
   Start-Sleep -Seconds 2
   if($taskProcess.HasExited){throw 'Service exited; see pc_analysis/data logs'}
   try {$taskReady=Invoke-RestMethod -Uri ('http://127.0.0.1:'+$Port+'/health') -TimeoutSec 3;if($taskReady.ready){break}} catch {}
  }
 }
 if(!$taskReady.ready){throw 'Service did not become ready; see pc_analysis/data logs'}
 Write-Host ('Ready: '+$taskReady.backend) -ForegroundColor Green
 Write-Host ('Computer IP for Advanced Settings: '+(($taskReady.addresses | Where-Object {$_ -ne '127.0.0.1'}) -join ', '))
 Write-Host 'Runs in the background. Keep the computer awake. You can close this window.'
} catch {
 Write-Host ('Startup failed: '+$_.Exception.Message) -ForegroundColor Red
 if(!$NoWait){Read-Host 'Press Enter to close'}
 exit 1
}
if(!$NoWait){Read-Host 'Press Enter to close'}

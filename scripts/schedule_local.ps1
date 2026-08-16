# 一键注册本地每日任务（Windows 计划任务，每天 08:00 运行 digest.py）
# 用法：右键"使用 PowerShell 运行"，或：
#   powershell -ExecutionPolicy Bypass -File scripts\schedule_local.ps1
param(
  [string]$At = "08:00",
  [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$taskName = 'literature-lab-daily'

if ($Remove) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "已移除计划任务 $taskName"
    exit 0
}

$venvPy = Join-Path $root '.venv\Scripts\python.exe'
$python = if (Test-Path $venvPy) { $venvPy } else { (Get-Command python).Source }
$script = Join-Path $root 'scripts\digest.py'
$arg = '"' + $script + '"'
$action = New-ScheduledTaskAction -Execute $python -Argument $arg -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At $At
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Description 'literature-lab 每日文献推送' -Force | Out-Null
Write-Host "已注册计划任务 $taskName，每天 $At 运行 $script"
Write-Host "立即试跑：python $arg"

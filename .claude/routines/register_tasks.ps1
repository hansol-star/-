<#
  정훈 증권 — 무인 루틴을 윈도우 작업 스케줄러에 등록 (경로 B)

  ★[2026-09-01 정훈 지시 "무인 다 로컬로 빼자"]
  정본 = docs/routines.md 「실제 스케줄 등록」 표. 시각·요일을 바꿀 땐 그 표를 먼저 고친다.

  설계 판단 3가지:
   · StartWhenAvailable = $true  — 절전·종료로 시각을 놓치면 깨어난 직후 따라잡는다.
     웹 Routines는 서버가 늘 깨어 있어 공짜였던 성질이다. 이게 없으면 조용히 건너뛴다.
   · WakeToRun = $true           — 절전 중이면 깨워서 실행. 단 전원이 꺼져 있으면 불가(물리 한계).
   · ExecutionTimeLimit = 2h     — 무한 대기(권한 프롬프트 등)로 좀비가 되는 것 차단.

  사용:  powershell -ExecutionPolicy Bypass -File register_tasks.ps1
         powershell -ExecutionPolicy Bypass -File register_tasks.ps1 -Unregister
#>
param([switch]$Unregister)

$ErrorActionPreference = 'Stop'
$Repo     = 'C:\Users\sd182\portfolio-desk'
$Launcher = Join-Path $Repo '.claude\routines\run_routine.ps1'
$Folder   = '\JeonghunDesk'

$Weekdays = @('Monday','Tuesday','Wednesday','Thursday','Friday')

# 정본 표와 1:1 — docs/routines.md 「실제 스케줄 등록」
$Routines = @(
  @{ Kind='r1';  Name='JD-R1-video-prefetch'; Time='10:00'; Days=$Weekdays;     Desc='영상 리서치 프리페치 (3채널 자막)' },
  @{ Kind='r2';  Name='JD-R2-main-report';    Time='16:00'; Days=$Weekdays;     Desc='메인 풀 보고서' },
  @{ Kind='r3';  Name='JD-R3-calibration';    Time='09:00'; Days=@('Saturday'); Desc='주말 콜 캘리브레이션' },
  @{ Kind='r4a'; Name='JD-R4a-retry-2000';    Time='20:00'; Days=$Weekdays;     Desc='토큰-리셋 재시도 파수꾼 1' },
  @{ Kind='r4b'; Name='JD-R4b-retry-2115';    Time='21:15'; Days=$Weekdays;     Desc='토큰-리셋 재시도 파수꾼 2' }
)

if ($Unregister) {
  foreach ($r in $Routines) {
    if (Get-ScheduledTask -TaskName $r.Name -TaskPath "$Folder\" -ErrorAction SilentlyContinue) {
      Unregister-ScheduledTask -TaskName $r.Name -TaskPath "$Folder\" -Confirm:$false
      Write-Output "removed  $($r.Name)"
    }
  }
  exit 0
}

if (-not (Test-Path $Launcher)) { throw "런처가 없다: $Launcher" }

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew

foreach ($r in $Routines) {
  $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File `"$Launcher`" -Kind $($r.Kind)" -WorkingDirectory $Repo
  $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $r.Days -At $r.Time

  if (Get-ScheduledTask -TaskName $r.Name -TaskPath "$Folder\" -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $r.Name -TaskPath "$Folder\" -Confirm:$false
  }
  Register-ScheduledTask -TaskName $r.Name -TaskPath $Folder -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "$($r.Desc) - 정본 docs/routines.md" | Out-Null
  Write-Output ("registered  {0,-22} {1}  {2}" -f $r.Name, $r.Time, ($r.Days -join ','))
}

Write-Output ""
Write-Output "등록 완료. 확인: Get-ScheduledTask -TaskPath '\JeonghunDesk\' | Format-Table TaskName,State"

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
$Catchup  = Join-Path $Repo '.claude\routines\catchup.ps1'
$Folder   = '\JeonghunDesk'
$CatchupName = 'JD-catchup-on-wake'

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
  if (Get-ScheduledTask -TaskName $CatchupName -TaskPath "$Folder\" -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $CatchupName -TaskPath "$Folder\" -Confirm:$false
    Write-Output "removed  $CatchupName"
  }
  if (Get-ScheduledTask -TaskName 'JD-price-watch' -TaskPath "$Folder\" -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName 'JD-price-watch' -TaskPath "$Folder\" -Confirm:$false
    Write-Output "removed  JD-price-watch"
  }
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

# ── 장중 트리거 감시 [9/3 신설] — 폰 상시 가용 전환에 따른 실시간 대응 ──────
#   정훈 폰창이 하루 3시간20분일 땐 실시간으로 알 이유가 없었다(그 창에서만 집행하니까).
#   9/3 평일 상시 전환으로 "가격이 닿는 순간"이 곧 행동 가능 시점이 됐다.
#   ⚠️ 알림 전용 — 자동 매매 없음. price_watch.py는 notify.py로 텔레그램만 보낸다.
#   ⚠️ 스크립트 자신이 장 시간을 판정해 밖이면 즉시 종료하므로, 트리거가 넉넉해도 무해하다.
$WatchName = 'JD-price-watch'
$Watcher = Join-Path $Repo '.claude\skills\portfolio-desk\scripts\price_watch.py'
if (Test-Path $Watcher) {
  $wAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument (
    "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -Command " +
    "`"& { `$env:Path='$env:LOCALAPPDATA\Programs\Python\Python312;' + `$env:Path; " +
    "python '$Watcher' --once --quiet }`"") -WorkingDirectory $Repo
  # KRX 프리(08:00~) + 정규 + 애프터(~20:00) → **08:00부터 12시간**.
  # ★[9/4] 토스 market-calendar 1차 출처로 확인: integrated(KRX+NXT) 기준
  #   **오늘도 이미 08:00~20:00**이다. 우리가 "9/14부터 확장"이라고 적은 건
  #   NXT(넥스트레이드)를 빼먹은 서술이었다 — 09:00 시작은 프리마켓 1시간을 통째로 놓쳤다.
  # ⚠️ [9/3 정정①] 첫 등록은 6h30m이라 15:30에 끊겼다 — 시간외가 감시 사각이었다.
  # ⚠️ [9/3 정정②] 9h(18:00)도 부족하다 — **9/14부터 애프터마켓이 20:00까지**다
  #    (시간외단일가 폐지 → 시간외접속매매 16:00~20:00, 한국거래소 확정).
  #    스크립트가 장 시간을 스스로 판정해 밖이면 즉시 종료하므로 11시간이어도 헛돌지 않는다.
  #    ⚠️ 프리마켓(07:00~07:50, 9/14~)은 이 트리거 밖이라 **아직 감시 사각**이다 —
  #      9/14 전에 07:00 트리거를 추가할 것(지금 넣으면 11일간 매일 헛돈다).
  $wt1 = New-ScheduledTaskTrigger -Daily -At '08:00'
  $wt1.Repetition = (New-ScheduledTaskTrigger -Once -At '08:00' `
      -RepetitionInterval (New-TimeSpan -Minutes 10) `
      -RepetitionDuration (New-TimeSpan -Hours 12)).Repetition
  $wt2 = New-ScheduledTaskTrigger -Daily -At '22:30'
  $wt2.Repetition = (New-ScheduledTaskTrigger -Once -At '22:30' `
      -RepetitionInterval (New-TimeSpan -Minutes 10) `
      -RepetitionDuration (New-TimeSpan -Hours 6 -Minutes 30)).Repetition
  # 감시는 가볍고 자주 돈다 — 2시간 상한(루틴용)은 과하므로 5분으로 줄인다.
  $wSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
      -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
      -MultipleInstances IgnoreNew
  if (Get-ScheduledTask -TaskName $WatchName -TaskPath "$Folder\" -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $WatchName -TaskPath "$Folder\" -Confirm:$false
  }
  Register-ScheduledTask -TaskName $WatchName -TaskPath $Folder -Action $wAction `
      -Trigger @($wt1, $wt2) -Principal $principal -Settings $wSettings `
      -Description "장중 트리거 감시(10분) - 알림 전용 - 정본 docs/routines.md" | Out-Null
  Write-Output ("registered  {0,-22} {1}" -f $WatchName, '08:00(12h)·22:30(6.5h) +10분')
}

# ── 정기 브리핑 [9/4 신설] — 할 일 중심 카톡 요약 하루 3회 ────────────────
#   정훈 9/4: "내가 할 일, 그리고 했는지도 체크해서 확인 느낌으로".
#   ⚠️ **10분마다 보내지 않는다.** 감시는 10분마다 돌지만(토큰 0) 카톡은
#     ①새 전이 ②하루 3회 정기 뿐이다. 10분 간격이면 하루 60통이고,
#     매일 같은 알림이 오면 알림 자체를 안 보게 된다 — 그러면 만든 의미가 사라진다.
#     (price_watch의 전이 기반 설계와 같은 이유)
#   시각 = 국내 개장 09:05 · 국내 마감 15:40 · 미국 개장 22:35
$BriefName = 'JD-brief'
$Notify = Join-Path $Repo '.claude\skills\portfolio-desk\scripts\notify.py'
if (Test-Path $Notify) {
  $bAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument (
    "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -Command " +
    "`"& { `$env:Path='$env:LOCALAPPDATA\Programs\Python\Python312;' + `$env:Path; " +
    "python '$Notify' --brief }`"") -WorkingDirectory $Repo
  $bTriggers = @(
    (New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Weekdays -At '09:05'),
    (New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Weekdays -At '15:40'),
    (New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Weekdays -At '22:35')
  )
  $bSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
      -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
      -MultipleInstances IgnoreNew
  if (Get-ScheduledTask -TaskName $BriefName -TaskPath "$Folder\" -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $BriefName -TaskPath "$Folder\" -Confirm:$false
  }
  Register-ScheduledTask -TaskName $BriefName -TaskPath $Folder -Action $bAction `
      -Trigger $bTriggers -Principal $principal -Settings $bSettings `
      -Description "정기 브리핑(할 일 중심) 09:05·15:40·22:35 - 정본 docs/routines.md" | Out-Null
  Write-Output ("registered  {0,-22} {1}" -f $BriefName, '09:05·15:40·22:35')
}

# ── 캐치업 [9/2 신설] — 꺼져 있어 놓친 루틴을 켜지자마자 따라잡는다 ──────────
#   StartWhenAvailable은 **절전**은 따라잡지만 **전원 종료**는 못 따라잡는다.
#   9/1 14:34~9/2 15:13 머신이 꺼져 R2·R4a·R4b·R1이 통째로 증발한 것이 그 증거다
#   (경로 B 전환 이후 보고서 0건의 실제 원인). 부팅·로그온 시 한 번 점검한다.
#   ⚠️ 이 태스크 자체는 가볍다 — 놓친 게 없으면 즉시 종료한다(판정만 하고 끝).
if (Test-Path $Catchup) {
  $cAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File `"$Catchup`"" -WorkingDirectory $Repo
  # 로그온 트리거만 쓴다. 3분 지연 = 네트워크·PATH가 준비될 시간(스케줄러 세션은 늦게 붙는다).
  # ⚠️ `-AtStartup`은 **관리자 권한이 필요해 쓸 수 없다**(9/2 실측: Access is denied).
  #    실효 손실은 거의 없다 — 꺼진 머신을 켜면 정훈이 로그온하기 때문이다.
  #    (자동 로그인 없이 잠금화면에 방치되는 경우만 사각으로 남는다.)
  $cTriggers = @( (New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME") )
  foreach ($t in $cTriggers) { $t.Delay = 'PT3M' }
  if (Get-ScheduledTask -TaskName $CatchupName -TaskPath "$Folder\" -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $CatchupName -TaskPath "$Folder\" -Confirm:$false
  }
  Register-ScheduledTask -TaskName $CatchupName -TaskPath $Folder -Action $cAction -Trigger $cTriggers -Principal $principal -Settings $settings -Description "부팅·로그온 시 놓친 루틴 따라잡기 - 정본 docs/routines.md" | Out-Null
  Write-Output ("registered  {0,-22} {1}" -f $CatchupName, '로그온 +3분')
}

Write-Output ""
Write-Output "등록 완료. 확인: Get-ScheduledTask -TaskPath '\JeonghunDesk\' | Format-Table TaskName,State"

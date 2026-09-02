<#
  정훈 증권 — 루틴 캐치업 (머신이 꺼져 있어 놓친 루틴을 켜지자마자 따라잡는다)

  ★[2026-09-02 신설] 왜 필요한가 — 하루 만에 실증됐다.
    경로 B(로컬 작업 스케줄러) 전환 다음 날, 머신이 9/1 14:34에 꺼져 9/2 15:13에 켜졌다.
    그 25시간에 **R2(9/1 16:00)·R4a(20:00)·R4b(21:15)·R1(9/2 10:00)이 통째로 증발**했다.
    경로 B 전환 이후 보고서가 **0건**인 이유가 이것이다(최신 v87 = 8/28).

    `WakeToRun=True`도, wake timer(AC/DC 둘 다 활성)도 소용없다 —
    **꺼진 머신은 깨울 수 없다.** 이건 감지로 못 막는 물리 한계다.
    ⇒ 막을 수 없으면 **따라잡는다.** 이 스크립트가 그 역할이다.

  ⚠️ 이건 R4(토큰-리셋 파수꾼)와 다른 문제를 푼다:
       R4  = "돌았는데 토큰에 막혀 못 끝냈다"
       여기 = "아예 안 돌았다(머신이 없었다)"
     둘 다 필요하다.

  판정 규율:
    · **놓친 것만 돌린다.** 이미 오늘 돈 루틴은 건드리지 않는다(로그 파일·report_guard로 판정).
    · **늦으면 포기한다.** R1은 15:30까지, R2는 23:00까지. 그 뒤엔 다음날 정규 실행이 낫다
      (한밤중에 보고서를 내봐야 정훈 폰창 20:50이 이미 닫혔다 = 읽는 사람이 없다).
    · **주말엔 R3만.** 평일 루틴을 주말에 소급 실행하지 않는다.

  사용:
    powershell -ExecutionPolicy Bypass -File catchup.ps1
    powershell -ExecutionPolicy Bypass -File catchup.ps1 -WhatIf   # 판정만, 실행 안 함
#>
param([switch]$WhatIf)

$ErrorActionPreference = 'Stop'

# 콘솔 UTF-8 고정 — 안 하면 cp949로 디코딩돼 한글 로그가 깨진 채 스케줄러 출력에 남는다
# (run_routine.ps1과 같은 처리. 9/2 실측에서 실제로 깨졌다.)
try {
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  $OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }

$Repo    = 'C:\Users\sd182\portfolio-desk'
$Here    = Join-Path $Repo '.claude\routines'
$Scripts = Join-Path $Repo '.claude\skills\portfolio-desk\scripts'
$LogDir  = Join-Path $Repo 'data\logs\routines'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# KST 고정 (UTC+9) — 로컬 시계 설정에 기대지 않는다(8/31 교훈)
function Get-Kst { (Get-Date).ToUniversalTime().AddHours(9) }
$kst   = Get-Kst
$stamp = $kst.ToString('yyyy-MM-dd')
$mins  = $kst.Hour * 60 + $kst.Minute
$dow   = $kst.DayOfWeek
$Log   = Join-Path $LogDir "catchup_$stamp.log"

function Say([string]$m) {
  $line = "[{0}] {1}" -f (Get-Kst).ToString('yyyy-MM-dd HH:mm:ss'), $m
  Add-Content -Path $Log -Value $line -Encoding utf8
  Write-Output $line
}

Say "=== 캐치업 점검 (KST $($kst.ToString('yyyy-MM-dd HH:mm')) $dow) ==="

# 오늘 그 루틴이 이미 돌았나 = 그날짜 로그 파일의 존재로 본다.
# (run_routine.ps1이 실행 즉시 로그를 만들므로, 중간에 죽어도 '돌긴 했다'로 잡힌다 —
#  중복 실행보다 미실행 오판이 덜 위험하다는 판단. 반쯤 돈 건 R4가 이어받는다.)
function Ran([string]$kind) { Test-Path (Join-Path $LogDir "$kind`_$stamp.log") }

$todo = @()

if ($dow -eq 'Saturday') {
  # 주말은 R3만. 평일 루틴을 소급하지 않는다.
  if ($mins -ge 540 -and $mins -lt 1200 -and -not (Ran 'r3')) { $todo += 'r3' }
  else { Say "주말 — R3 대상 아님(이미 돌았거나 창 밖)" }
}
elseif ($dow -eq 'Sunday') {
  Say "일요일 — 예정 루틴 없음"
}
else {
  # R1 영상 프리페치: 10:00 예정. 15:30 넘으면 포기 — R2가 소비할 캐시를
  # 만드는 게 목적인데 R2(16:00)를 코앞에 두고 시작하면 둘이 같은 토큰 창에서 겹친다
  # (7/11 재설계가 정확히 그걸 피하려고 두 루틴을 6시간 떼어놓은 것).
  if ($mins -ge 600 -and $mins -lt 930 -and -not (Ran 'r1')) { $todo += 'r1' }

  # R2 메인 보고서: 16:00 예정. 23:00 넘으면 포기(폰창 20:50이 닫혀 읽는 사람이 없다).
  # 판정은 로그가 아니라 **산출물**로 한다 — report_guard가 오늘 보고서 유무를 본다.
  if ($mins -ge 960 -and $mins -lt 1380) {
    & python3 (Join-Path $Scripts 'report_guard.py') --check --kind R2 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { $todo += 'r2' }
    else { Say "R2 — 오늘 보고서 이미 있음" }
  }
}

if ($todo.Count -eq 0) { Say "따라잡을 것 없음"; Say "=== 종료 ==="; exit 0 }

Say "따라잡을 루틴: $($todo -join ', ')"
if ($WhatIf) { Say "WhatIf — 실행 생략"; Say "=== 종료 ==="; exit 0 }

foreach ($k in $todo) {
  Say "실행 → $k"
  & powershell -ExecutionPolicy Bypass -File (Join-Path $Here 'run_routine.ps1') -Kind $k
  Say "$k 종료 exit=$LASTEXITCODE"
}
Say "=== 종료 ==="
exit 0

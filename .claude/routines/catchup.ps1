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
    · **늦으면 포기한다.** R1은 20:00까지(9/28 15:30→20:00), R2는 23:00까지. 그 뒤엔 다음날 정규 실행이 낫다
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

# ★[2026-09-10 분업 전환] 로컬 스케줄은 R1만 남았다 — R2 보고서는 정훈 "보고서 작성" 시 대화형,
#   재료는 클라우드 C2(평일 16:00), R3는 클라우드(토 09:00). 여기서 R2·R3를 소급하면 클라우드와 중복된다.
if ($dow -eq 'Saturday' -or $dow -eq 'Sunday') {
  Say "주말 — 로컬 소급 대상 없음(R3는 클라우드)"
}
else {
  # R1 영상 프리페치: 10:00 예정. 15:30 넘으면 포기 — 클라우드 C2(16:00)가 소비할 캐시를
  # 만드는 게 목적이라, 그 뒤에 만들면 C2가 못 본다.
  # ★[2026-09-28] 15:30 → 20:00. C2가 못 봐도 C3(17:00)·대화형 보고서·다음날 C2는 본다.
  #   PC가 오후에 켜지는 날(9/16·9/23·9/28) 영상이 통째로 빠지는 쪽이 더 나쁘다(9/28 누적 34편).
  #   run_routine.ps1 $MaxLateMap r1=600과 짝.
  if ($mins -ge 600 -and $mins -lt 1200 -and -not (Ran 'r1')) { $todo += 'r1' }
  elseif ($mins -ge 600 -and $mins -lt 1200 -and (Ran 'r1')) {
    # ★[2026-10-20] 돌았지만 아무것도 못 낸 날을 다시 민다. 舊 판정은 '로그 파일 존재 = 돌았다'라
    #   10/15 R1(10:00 세션 한도 → TOKEN_LIMIT · 13:10 리셋)을 '이미 돌았다'로 넘겨 그날 영상이 통째로 빠졌다.
    #   재시도 대상 = 마지막 판정이 TOKEN_LIMIT·NO_OUTPUT·BG_KILLED · 하루 시작 3회 미만 · 한도면 리셋 시각이 지났을 때.
    #   주간 한도("resets Oct 19, 10pm")는 날짜가 오늘이 아니면 기다리지 않는다(내일 정규 R1이 --catchup으로 메운다).
    $r1Log = Join-Path $LogDir "r1_$stamp.log"
    $body  = Get-Content -Path $r1Log -Raw -Encoding utf8
    $starts = ([regex]::Matches($body, '=== 루틴 r1 시작')).Count
    $last = [regex]::Matches($body, 'verdict=(\w+)') | Select-Object -Last 1
    $lastV = if ($last) { $last.Groups[1].Value } else { '' }
    if ($lastV -in 'TOKEN_LIMIT','NO_OUTPUT','BG_KILLED' -and $starts -lt 3) {
      $ready = $true
      if ($lastV -eq 'TOKEN_LIMIT') {
        $m = [regex]::Matches($body, 'resets (?:([A-Z][a-z]{2}) (\d{1,2}), )?(\d{1,2})(?::(\d{2}))?\s*(am|pm)') | Select-Object -Last 1
        if ($m) {
          $h = [int]$m.Groups[3].Value % 12; if ($m.Groups[5].Value -eq 'pm') { $h += 12 }
          $mm = if ($m.Groups[4].Success) { [int]$m.Groups[4].Value } else { 0 }
          if ($m.Groups[1].Success) {
            $d = [datetime]::ParseExact("$($m.Groups[1].Value) $($m.Groups[2].Value) $($kst.Year)", 'MMM d yyyy', [Globalization.CultureInfo]::InvariantCulture)
            if ($d.Date -ne $kst.Date) { $ready = $false }
          }
          if ($mins -lt ($h * 60 + $mm + 5)) { $ready = $false }
          Say "R1 직전 판정 TOKEN_LIMIT — 리셋 $($m.Value) · $(if ($ready) { '지났다 → 재시도' } else { '아직 → 대기' })"
        }
      }
      if ($ready) { $todo += 'r1'; Say "R1 재시도 대상 — 직전 verdict=$lastV · 오늘 시작 ${starts}회" }
    }
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

<#
  정훈 증권 — 무인 루틴 런처 (경로 B · 로컬 작업 스케줄러)

  ★[2026-09-01 정훈 지시 "무인 다 로컬로 빼자"] 舊 웹 Claude Code Routines를 대체한다.
  왜 옮겼나: 8/31 로컬 이전으로 yt-dlp 스트림·자막(429 우회)이 열렸는데, 정작 그 이득이
  가장 큰 R1(영상 프리페치)이 웹에서 돌아 **열린 경로에 닿지 못했다.**

  이 런처가 지는 책임 4가지 — 웹 Routines가 공짜로 주던 것들이라 직접 만들어야 한다:
    ① 프롬프트 정본화  : docs/routines.md에서 매 실행 직접 읽는다(사본 없음 = 문서=실행물).
    ② 자격증명 격리    : 토스 키를 환경에서 **지우고** 자식 프로세스를 띄운다(아래 §토스).
    ③ 실패 가시화     : 웹은 실패가 기록에 남았다. 로컬은 조용하다 → 로그 + 상태파일 + 토스트.
    ④ 시각 정합       : KST 고정(kst_now.py와 같은 UTC+9) — 로컬 시계 오독 방지.

  §토스 — 이 스크립트에서 가장 중요한 줄:
    CLAUDE.md 운영제약 = "무인 루틴(경로 B)에는 토스 키를 노출하지 않는다 —
    사람이 안 보는 세션에 매매 권한을 주지 않는다." 8/31에 키를 사용자 환경변수로
    저장했으므로 **작업 스케줄러 자식 프로세스는 기본적으로 그 키를 상속한다.**
    ⇒ 여기서 명시적으로 제거한다. 이게 빠지면 룰 위반이다.

  사용:
    powershell -ExecutionPolicy Bypass -File run_routine.ps1 -Kind r2
    powershell -ExecutionPolicy Bypass -File run_routine.ps1 -Kind r2 -DryRun
#>
param(
  [Parameter(Mandatory=$true)]
  [ValidateSet('r1','r2','r3','r4a','r4b')]
  [string]$Kind,

  # 무인 기본값 = acceptEdits. 권한에 막히면 **조용히 넘어가지 말고** settings.json
  # allow 목록에 추가하는 것이 정답이다(bypassPermissions는 최후수단·정훈 판단).
  [string]$PermissionMode = 'acceptEdits',

  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$Repo = 'C:\Users\sd182\portfolio-desk'
$Scripts = Join-Path $Repo '.claude\skills\portfolio-desk\scripts'
$LogDir = Join-Path $Repo 'data\logs\routines'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# ── KST (UTC+9 고정 — 한국은 서머타임 없음. 로컬 시계 설정에 기대지 않는다) ──
function Get-Kst { (Get-Date).ToUniversalTime().AddHours(9) }
$kst = Get-Kst
$stamp = $kst.ToString('yyyy-MM-dd')
$LogFile = Join-Path $LogDir "$Kind`_$stamp.log"
$StatusFile = Join-Path $LogDir 'last_status.json'

function Write-Log([string]$msg) {
  $line = "[{0}] {1}" -f (Get-Kst).ToString('yyyy-MM-dd HH:mm:ss'), $msg
  Add-Content -Path $LogFile -Value $line -Encoding utf8
  Write-Output $line
}

# ── PATH — 스케줄러 세션은 로그인 셸의 PATH를 다 못 받는다 ────────────────
$env:Path = "$env:APPDATA\npm;$env:LOCALAPPDATA\Programs\Python\Python312;" +
            "$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;$env:USERPROFILE\bin;" +
            "C:\Program Files\Git\bin;C:\Program Files\nodejs;$env:Path"
$env:PYTHONUTF8 = '1'          # 콘솔 cp949에서 한글 출력이 깨지는 것 방지
$env:PYTHONIOENCODING = 'utf-8'
# 자식 프로세스와 주고받는 텍스트를 UTF-8로 고정(한글 프롬프트·로그 깨짐 방지)
try {
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  [Console]::InputEncoding  = [System.Text.Encoding]::UTF8
  $OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }

# ── §토스: 매매 가능한 자격증명을 자식에게 물려주지 않는다 ────────────────
$scrubbed = @()
foreach ($k in 'TOSS_CLIENT_ID','TOSS_CLIENT_SECRET') {
  if (Test-Path "env:$k") { Remove-Item "env:$k"; $scrubbed += $k }
}

Write-Log "=== 루틴 $Kind 시작 (KST $($kst.ToString('yyyy-MM-dd HH:mm')) · $PermissionMode) ==="
if ($scrubbed.Count -gt 0) { Write-Log "토스 키 제거: $($scrubbed -join ',') (무인 세션 매매권한 차단)" }
else { Write-Log "토스 키 없음 — 제거 불요" }

Set-Location $Repo

# ── 지각 감지 — 절전이 루틴을 먹는다 [9/1 신설] ──────────────────────────
#   9/1 실측: R1은 10:00 예약인데 **12:00에 돌았다**. 이벤트로그상 04:27 절전 → 11:57 복귀 →
#   StartWhenAvailable로 뒤늦게 기동. WakeToRun=True·wake timer도 켜져 있는데 안 깼다.
#   물리 한계라 못 막지만 **조용히 넘어가면 안 된다** — 2시간 늦은 R1은 '오늘 오전 영상'을
#   놓치고, 그 공백은 다음날 R1이 메운다는 전제가 깨진다. 기록해서 보이게 만든다.
$SchedMap = @{ r1='10:00'; r2='16:00'; r3='09:00'; r4a='20:00'; r4b='21:15' }
$Scheduled = $SchedMap[$Kind]
$LateMin = 0
try {
  $due = [datetime]::ParseExact("$($kst.ToString('yyyy-MM-dd')) $Scheduled", 'yyyy-MM-dd HH:mm', $null)
  $LateMin = [int]([math]::Round(($kst - $due).TotalMinutes))
  if ($LateMin -ge 45) { Write-Log "지각 실행 ${LateMin}분 (예정 $Scheduled) — 절전/전원 확인" }
} catch { $LateMin = 0 }

# ── 프롬프트 = docs/routines.md 정본에서 직접 ───────────────────────────
# ⚠️ 파일 경유로 읽는다. 네이티브 stdout을 PowerShell 5.1이 콘솔 코드페이지(cp949)로
# 디코딩해 **한글 프롬프트가 통째로 깨진 채 모델에 전달**된다(첫 구현에서 실측).
$PromptFile = Join-Path $env:TEMP "routine_$Kind.prompt.txt"
& python3 (Join-Path $Scripts 'routine_prompts.py') --kind $Kind --out $PromptFile | Out-Null
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $PromptFile)) {
  Write-Log "프롬프트 추출 실패 — docs/routines.md 구조 확인 (routine_prompts.py --check)"
  exit 2
}
$prompt = Get-Content -Path $PromptFile -Raw -Encoding UTF8
if ([string]::IsNullOrWhiteSpace($prompt)) { Write-Log "프롬프트가 비었다"; exit 2 }
Write-Log "프롬프트 $($prompt.Length)자 추출 (정본 = docs/routines.md)"

if ($DryRun) {
  Write-Log "DryRun — claude 호출 생략. 프롬프트 첫 200자:"
  Write-Log ($prompt.Substring(0, [Math]::Min(200, $prompt.Length)))
  exit 0
}

# ── 실행 ────────────────────────────────────────────────────────────────
# ⚠️ claude 실행 파일이 없으면 여기서 끝낸다. 없는 채로 아래로 내려가면
# CommandNotFoundException이 나고 $LASTEXITCODE는 **직전 python3 호출의 0이 그대로 남아**
# verdict=OK로 기록된다 — 아무것도 안 하고 성공했다고 보고하는 최악의 실패 모드다.
# (9/1 실측: npm 전역 설치가 사용자 셸에 안 보이는 상태가 실제로 있었다.)
$claudeCmd = (Get-Command claude -ErrorAction SilentlyContinue)
if (-not $claudeCmd) {
  Write-Log "claude 실행 파일을 찾을 수 없다 (PATH: %APPDATA%
pm 확인 · npm install -g @anthropic-ai/claude-code)"
  $status = [ordered]@{ kind=$Kind; verdict='CLAUDE_NOT_FOUND'; exit_code=127
                        kst=(Get-Kst).ToString('yyyy-MM-dd HH:mm:ss'); minutes=0
                        log=$LogFile; toss_scrubbed=$scrubbed }
  [IO.File]::WriteAllText($StatusFile, ($status | ConvertTo-Json -Depth 3),
                          (New-Object System.Text.UTF8Encoding($false)))
  exit 127
}
Write-Log "claude = $($claudeCmd.Source)"

# ⚠️ PowerShell 5.1은 네이티브 exe의 stderr를 ErrorRecord로 감싸고, $ErrorActionPreference='Stop'
# 이면 **거기서 스크립트를 끝낸다.** 첫 구현이 실제로 그렇게 죽어 상태파일도 못 남겼다 —
# 실패를 보이게 하려고 만든 런처가 실패를 숨긴 꼴(8/22 "가드 없는 폴백은 침묵보다 나쁘다").
# ⇒ 자식 호출 구간에서만 Continue로 낮춘다.
$prevEAP = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$sw = [Diagnostics.Stopwatch]::StartNew()
$out = $prompt | & claude -p --permission-mode $PermissionMode --output-format text 2>&1
$code = $LASTEXITCODE
$sw.Stop()
$ErrorActionPreference = $prevEAP

$outText = ($out | Out-String)
Add-Content -Path $LogFile -Value $outText -Encoding utf8

# ── 판정 — "돌았다"가 아니라 "쓸 것을 냈나"로 본다(8/22 교훈) ───────────
$hitLimit = $outText -match 'session limit|usage limit|rate limit'
$permBlock = $outText -match 'permission denied|requires approval|not allowed'
$notLogged = $outText -match 'Not logged in|/login'

# ★[9/1 신설] 산출물 검사 — 문자열 매칭이 아니라 **워킹트리**로 판정한다.
#   왜: 9/1 R1이 영상 6편을 분석해놓고 git add/commit/push가 allow에 없어 커밋을 못 했는데
#   verdict=OK로 기록됐다. 위 $permBlock 정규식이 못 잡은 이유 = 모델이 그 사실을
#   **한국어 산문**("승인 대기로 실패")으로 설명해서다. 영어 패턴을 더 늘리는 건 같은 실패의 반복이다
#   ⇒ 말이 아니라 결과를 본다. 루틴의 결과물은 '커밋된 변경'이지 '설명'이 아니다.
#   (8/23 "초록불은 위반이 없다는 뜻이 아니라 탐지기가 그 형태를 안 본다는 뜻일 수 있다")
#   ⚠️ data/logs/ 는 .gitignore에 있으므로 루틴 자신의 로그는 여기 안 잡힌다(오탐 없음).
$dirty = @()
try {
  $prevEAP2 = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  $dirty = @(& git -C $Repo status --porcelain 2>$null | Where-Object { $_ -ne '' })
  $ErrorActionPreference = $prevEAP2
} catch { Write-Log "git status 확인 실패(무시): $($_.Exception.Message)" }
$uncommitted = $dirty.Count
if ($uncommitted -gt 0) {
  Write-Log "미커밋 $uncommitted건 — 연속성 규약 미이행(다음 세션이 이 작업을 못 본다):"
  foreach ($d in ($dirty | Select-Object -First 12)) { Write-Log "    $d" }
}

$verdict = if ($notLogged) { 'NOT_LOGGED_IN' }
           elseif ($hitLimit) { 'TOKEN_LIMIT' }
           elseif ($code -ne 0) { 'FAILED' }
           elseif ($permBlock) { 'PERMISSION_BLOCKED' }
           elseif ($uncommitted -gt 0) { 'UNCOMMITTED' }
           else { 'OK' }

Write-Log "=== 종료 verdict=$verdict exit=$code 소요=$([int]$sw.Elapsed.TotalMinutes)분 ==="

$status = [ordered]@{
  kind = $Kind; verdict = $verdict; exit_code = $code
  kst = (Get-Kst).ToString('yyyy-MM-dd HH:mm:ss')
  minutes = [int]$sw.Elapsed.TotalMinutes
  log = $LogFile
  toss_scrubbed = $scrubbed
  uncommitted = $uncommitted
  scheduled = $Scheduled
  late_min = $LateMin
}
# BOM 없는 UTF-8 — Out-File -Encoding utf8은 5.1에서 BOM을 붙여 python json.load가 깨진다.
[IO.File]::WriteAllText($StatusFile, ($status | ConvertTo-Json -Depth 3),
                        (New-Object System.Text.UTF8Encoding($false)))

# ── 알림 ①폰(텔레그램) — 웹 Routines push의 실제 대체재 [9/1 신설] ──────
#   토스트는 PC 앞에 있을 때만 보인다. 정훈 폰창(평일 17:30~20:50)이 열리기 전에
#   R2의 오더북이 폰에 닿아야 국내 시간외단일가(~18:00)를 쓸 수 있다.
#   ⚠️ 미설정이면 notify.py가 exit 3으로 **미발송을 분명히 말한다** — 성공한 척하지 않는다.
try {
  $nOut = & python3 (Join-Path $Scripts 'notify.py') --routine $Kind --verdict $verdict --status $StatusFile 2>&1
  $nCode = $LASTEXITCODE
  Write-Log "폰 알림: exit=$nCode $(($nOut | Out-String).Trim() -replace '\s+', ' ')"
} catch { Write-Log "폰 알림 호출 실패(무시): $($_.Exception.Message)" }

# ── 알림 ②윈도우 토스트 — PC 앞에 있을 때의 즉시 경보 ────────────────────
if ($verdict -ne 'OK') {
  try {
    Add-Type -AssemblyName System.Windows.Forms
    $n = New-Object System.Windows.Forms.NotifyIcon
    $n.Icon = [System.Drawing.SystemIcons]::Warning
    $n.Visible = $true
    $n.ShowBalloonTip(10000, "루틴 $Kind 실패", "verdict=$verdict — $LogFile", 'Warning')
    Start-Sleep -Seconds 2
    $n.Dispose()
  } catch { Write-Log "알림 실패(무시): $($_.Exception.Message)" }
}

exit $code

#!/usr/bin/env python3
"""KST 실측 시각 — 날짜 앵커링(7/6 사고)의 이식 가능한 정본 커맨드.

★[8/31 로컬 이전] 舊 지시문은 전부 `TZ=Asia/Seoul date`였는데 **윈도우 Git Bash에서 틀린다.**
실측: MSYS에 `/usr/share/zoneinfo`가 없어 알 수 없는 TZ 이름이 **UTC로 폴백**한다 —
  date                 -> Mon Aug 31 16:50 (맞음, 시스템 시계가 KST라서)
  TZ=Asia/Seoul date   -> Mon Aug 31 07:50 GMT  ← **9시간 뒤로 밀린다**
즉 **날짜를 지키라고 만든 그 명령이 날짜를 틀리게 한다.** 00~09시 KST엔 어제가 나온다.
(같은 날 `local_doctor`의 KST 항목도 같은 원인으로 07:49를 KST라며 ✅로 찍고 있었다.)

⇒ 한국은 서머타임이 없으므로 **UTC+9 고정 오프셋**이 어떤 OS에서도 정답이다.
   tzdata·zoneinfo·TZ 환경변수 어디에도 기대지 않는다.
"""
import sys
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9), "KST")
now = datetime.now(KST)
fmt = sys.argv[1] if len(sys.argv) > 1 else "%Y-%m-%d %H:%M %A"
fmt = fmt[1:] if fmt.startswith("+") else fmt   # `date '+%H:%M'` 습관을 그대로 받아준다
print(now.strftime(fmt))

# 시스템 로컬 시계와 어긋나면 알린다(머신 시계 자체가 틀린 경우 — 조용히 지나가면 안 된다).
skew = abs((datetime.now() - now.replace(tzinfo=None)).total_seconds())
if skew > 300:
    print(f"[WARN] 시스템 로컬 시계와 {skew/3600:.1f}시간 차 — 머신 시간대/시계 확인",
          file=sys.stderr)

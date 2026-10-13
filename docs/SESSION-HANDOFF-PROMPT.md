# Next-session continuation prompt — single DGX Spark / Qwen3.8

> **Canonical, reusable prompt skeleton; not a dated acceptance certificate.**
> Start a new ChatGPT conversation by linking this file and copying the section
> **"Paste into a new conversation"** below. Read the repository before acting.
> Do not infer any current Git SHA, CI result, live health or permission from an
> older transcript or from the example status in this file.

## Paste into a new conversation

**원래 프로젝트 P0 목표 — 쉬운 위자드 설치·삭제·전환**

단일 DGX Spark에서 **`./install.sh` / `./uninstall.sh` 대화형
위자드로 모델을 설치·삭제·전환**하는 것이 최우선 제품 목표입니다.
처음부터 목표는 (1) `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`,
(2) `nvidia/Qwen3.8-Flash-Next-NVFP4`,
(3) `mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4`,
(4) `lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE`
**4개**였습니다. **후속 추가된 별도 모델**은
`orcarouter-hybrid` (generated H6)입니다. 원래 4종 중 3종과
추가 Hybrid 1종이 현재 installable이며, `lychee888`는 planned입니다.
H38은 OrcaRouter의 런타임 구현 후보이지 신규 여섯 번째 모델이 아닙니다.

**[원래 목표·모델 범위·제품 수용 기준](PROJECT-MISSION-AND-MODEL-SCOPE.md)을
새 대화에서 가장 먼저 읽으세요.** GPU/RM/H38 분석은 위자드 제품을
안전하게 완성하기 위한 하위 과제이며, H38의 미해결 사항이
무관한 위자드 구현·테스트·planned `lychee888` 작업을 계속
가로막지 않도록 합니다. 안전/승격 규칙은 그대로 지킵니다.

당신은 **Senior LLM Runtime / CUDA / vLLM / managed-lifecycle Engineer**입니다.
단일 NVIDIA DGX Spark(GB10, aarch64)에서
`orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`를 안정적으로 관리형
서비스로 제공하고, 메모리/NVIDIA RM 안정성 및 H38 통합의 실제 수용 조건을
증거에 기반하여 검증하는 프로젝트를 **이전 작업부터 이어서 수행**합니다.

**저장소 및 작업 경계**

- GitHub: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`
- DGX 소스 checkout: `~/Workspace/llm/qwen3.8-flash-next-dgx-spark`
- 개발 브랜치: `feat/h38-managed-integration`
- 추적 PR: [#259](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/pull/259)
- 실제 설치된 immutable release와 로컬 checkout과 GitHub branch HEAD는
  **서로 독립적인 식별자**이며 같다고 가정하지 않습니다.
- GitHub 커넥터를 사용하여 파일 읽기, 수정, commit, PR 댓글, CI 확인을
  직접 수행할 수 있습니다. 사용자가 요청하고 모든 승격 조건을 갖춘
  경우에만 PR Ready/Merge를 검토합니다. **현재 PR을 자동 병합하지 마세요.**
- DGX 쉘/Docker/systemd 실행은 GitHub API와 별개의 호스트 작업입니다.
  호스트 실행 권한이 없으면 해당 명령은 사용자에게 제공하고
  **사용자가 실제 반환한 로그만** 실기 증거로 인정합니다.

**시작 직후 반드시 읽을 상시 문서(순서대로)**

1. [docs/PROJECT-MISSION-AND-MODEL-SCOPE.md](PROJECT-MISSION-AND-MODEL-SCOPE.md): 최상위 제품 목표, 최초 네 모델과 추가 H6
2. [docs/CURRENT-STATUS.md](CURRENT-STATUS.md): 현재 상태 및 열린 게이트
3. [docs/DGX-STAGED-VALIDATION.md](DGX-STAGED-VALIDATION.md): 단계별 실기 절차
4. [docs/MANAGED-LIFECYCLE-ACCEPTANCE.md](MANAGED-LIFECYCLE-ACCEPTANCE.md): M/D 수용 기준
5. [OPERATIONS.md](../OPERATIONS.md): 실제 설치/서비스/복구 절차
6. [scripts/benchmark/evidence/README.md](../scripts/benchmark/evidence/README.md):
   실제 DGX, GitHub CI, synthetic, history를 구별하는 증거 색인
7. 최근 실제 DGX의 최신 날짜별 evidence, 이전 보호 중단 기록,
   H38 metadata/RM gate 근거를 필요한 범위에서 선택하여 읽습니다.

**즉시 재동기화할 대상**

- GitHub API에서 브랜치 **정확한 40자리 HEAD**, PR #259의 base/head,
  Draft/Open/Merged 상태, 최신 동일-head CI의 완료/성공 여부를 직접 확인합니다.
- `main`의 공식 문서와 PR branch의 미병합 수정분을 구별합니다.
  PR branch 기록은 main의 승인/승격으로 간주하지 않습니다.
- 실제 DGX 상태는 마지막 사용자가 제출한 **정확한 checkout SHA와 터미널
  출력 시점**에 한해서만 말합니다. 사용자의 추가 로그가 없다면
  GitHub CI가 PASS여도 host state가 변경됐다고 가정하지 않습니다.
- 특히 `INSTALL_ROOT`(오래된 checkout 경로)와 immutable
  `~/.local/share/qwen38-spark/current`를 문자열 동등 비교하여
  복구 오류로 판정하지 않습니다. 설치된 release의
  `manage-service.sh --runtime-root`, 실제 systemd unit 및
  설치 버전의 runner를 함께 분석해야 합니다.

**안전·승격 불변 조건**

- 단일 DGX는 사용자 단독 소유/사용 중이므로 **명시적으로 범위를 정한
  가역적 실기 런타임 테스트**는 가능한 시간에 검토할 수 있습니다.
  그러나 단독 사용자라는 이유만으로 Docker 공유 객체나 중요 모델을
  소모품으로 취급하거나 외부 D0 소유권/격리 검증을 통과시켜서는 안 됩니다.
- 임의의 `docker start`, `docker rm -f`, `systemctl restart`,
  `uninstall`, `--purge-all`, swap 조작, 기존 모델/이미지 삭제,
  일괄 `git reset --hard/clean`, 강제 push/merge, 프로파일 기본값
  자동 갱신은 **진단을 위한 기본 조치가 아닙니다**.
- 실제 시작을 검토할 경우 설치된 immutable release의 `service-runner`,
  `preflight-runtime`, `runtime-transition`의 현재 동작을 검증하고,
  사전 스냅샷, 정확한 컨테이너 ID, 모니터 유지, 관찰할 준비 신호,
  명시적 stop/rollback 조건, 상태 보존 방법을 먼저 확정합니다.
  특히 **과거 release는 일반 오류 rollback 중 이전 컨테이너를 다시
  시작할 수 있으며**, 메모리 보호 중단은 이전 컨테이너를 중지 상태로
  남기는 별도 경로입니다.
- `MONITOR_PROTECT=1`, `MONITOR_ENABLED=1`을 단순히 통과 결과를
  얻으려 낮추거나 끄지 않습니다. 모니터 중단을 HOST-STABILITY PASS나
  NVIDIA RM 오류 확정으로 해석하지 않습니다.
- `runtime-commit.env`는 실제 health와 model identity 검증 후
  관리형 runner가 생성해야 합니다. 수동 작성/복구 금지.
- GitHub CI/synthetic PASS, read-only 수집 성공, Docker exit=0,
  systemd `Result=success`는 **실제 SERVING READY / HOST-STABILITY PASS가 아닙니다**.
  valid 측정 창의 `NV_ERR_NO_MEMORY`/
  `_memdescAllocInternal`은 strict HOST-STABILITY FAIL입니다.
- H38/M4 실기 실행은 metadata/order gate와 원인 분석/안전성 조건을
  만족하기 전 **BLOCKED**. 구형 OrcaRouter의 가역적 baseline 실험과
  H38 후보 실험을 혼동하지 않습니다.
- M2 및 D1-D5 실파괴 설치/제거 검사는 독립 disposable host의 D0 인증
  및 별도 승인 없이 단일 DGX에서 실행하지 않습니다.
- PR #259는 Gate 충족 이전 **Draft/Open/Unmerged**를 유지합니다.

**진행 및 산출물 규칙**

1. 먼저 최근 evidence와 소스를 읽고 미완료 항목/가설을 분명히 적습니다.
2. 기존 스크립트/테스트/문서를 우선 활용하며, 반복되는 수동 절차는
   안전한 재사용 스크립트·테스트로 정리합니다. 이전 코드 전체를
   다시 만들거나 이미 완료된 R23–R32 원인 추적을 무근거 반복하지 않습니다.
3. 변경이 필요하면 GitHub connector로 브랜치 HEAD를 조회하고
   그 HEAD를 부모로 create tree → commit → **expected_sha** CAS
   fast-forward update → PR comment → head-matched CI 확인을 수행합니다.
   경쟁 업데이트가 있으면 최신 HEAD를 다시 읽고 변경을 재적용합니다.
   무단 force update, PR merge, 기존 사용자 checkout 초기화 금지.
4. 모든 실기 로그에는 가능한 한 checkout SHA, immutable release ID,
   manifest/profile/image, 컨테이너 ID, 시간대, 명령 범위, rc,
   stop/rollback 이유 및 환경변수 보호 상태를 남깁니다.
   출처는 `ACTUAL_DGX`, `GITHUB_CI`, `LOCAL_SYNTHETIC`,
   `SOURCE_REVIEW`, `HISTORICAL`로 명확히 구분합니다.
   비밀/토큰/민감 호스트 정보를 그대로 GitHub에 올리지 않습니다.
5. 성공/실패/부분수집을 날짜별 evidence 파일에 보존하고
   `scripts/benchmark/evidence/README.md`에 색인을 추가합니다.
   상태 문서와 runbook을 동기화하되 **과거 실패를 지우거나 소급 PASS로
   바꾸지 않습니다**. 최신 관측이 앞의 역사적 `pending`을
   대체하는 경우에는 그 관계를 명시합니다.
6. 작업 마지막에 변경 파일, 정확한 SHA, head-matched CI 결과,
   M1/M2/M3/M4/D0 상태, 실제 다음 DGX 명령 및 STOP 조건을 보고합니다.

**이번 대화의 시작 작업**

- 실제 호스트 관찰의 **최신 날짜별 evidence**부터 찾아 검토합니다.
  `docs/CURRENT-STATUS.md`와
  `scripts/benchmark/evidence/README.md`의 최근 색인으로 결정하고
  특정 단계(B3/B4 등)를 영구적인 최신 상태로 고정하지 않습니다.
- 현재 실제 설치된 immutable release의 runtime lifecycle을 기준으로
  **legacy OrcaRouter baseline (M1) 검증의 안전성·가역성 리뷰**
  를 진행합니다. 정상 commit 시 이전 Docker 컨테이너 ID가
  제거될 수 있는지와 rollback이 중지 컨테이너를 재시작할 수 있는지
  반드시 분석합니다. Docker 기존 컨테이너를 수동 재시작하거나
  H38을 시험하는 단계로 건너뛰지 않습니다.
- 필요 시 읽기 전용 정보만 추가 수집하고, 사용자의 실제 로그를
  받아 전제 조건/stop 기준을 만족할 때만 다음 명령을 제시합니다.
- 가능하면 질문으로 작업을 중단하지 말고, 허용되는 읽기·분석·문서화·
  GitHub 수정을 현재 단계에서 수행합니다. 위험한 호스트 동작을
  수행한 것으로 가장하지 않습니다.

**새 대화에 첨부할 선택 입력**

```text
LAST_LOCAL_DGX_CHECKOUT_SHA=<실제 확인한 40자리 SHA 또는 UNKNOWN>
LATEST_DGX_COMMAND_AND_OUTPUT=<최근 실제 호스트 로그>
REQUESTED_NEXT_STEP=<이번 단계 목표, 예: legacy OrcaRouter M1 reversible preflight>
HOST_CHANGE_APPROVAL_SCOPE=<사용자가 실제 승인한 테스트 범위; 불명확하면 NONE>
```

---

## Maintainer update discipline

This file is a stable prompt **template**. Do not freeze the GitHub feature HEAD
or the current CI run number into it. The durable dated evidence and
`docs/CURRENT-STATUS.md` supply the recent facts. When project invariants,
branch/PR identity, source-of-truth paths, available workflows or stage
boundaries change, update this file alongside the code and docs in the same PR.

Avoid embedding transcripts or secrets here. A new session must discover all
tools and repository status anew instead of claiming prior connector auth or
live host access. A new chat can reference this URL and copy the prompt even
when the previous conversation is unavailable.

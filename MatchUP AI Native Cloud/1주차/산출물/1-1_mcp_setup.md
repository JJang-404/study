# 실습 1-1 · Claude Desktop MCP 설정 + 인기 MCP 3종 등록

> 1주차 실습 산출물 · 작성일 2026-10-14

## 1. 실습 목표

Claude Desktop의 MCP 설정 파일을 생성하고, 인기 MCP 서버 3종을 **멱등(idempotent)** 방식으로 등록한다.

멱등 등록이란: 같은 이름(key)의 서버가 이미 있으면 **건드리지 않고 건너뛰고**, 없는 것만 병합해 추가한다. 따라서 여러 번 실행해도 결과가 같고 기존 설정이 손실되지 않는다.

## 2. 설정 파일 경로

| 항목 | 값 |
|---|---|
| OS | Windows 11 |
| 경로 | `%APPDATA%\Claude\claude_desktop_config.json` |
| 실제 경로 | `C:\Users\w00sh\AppData\Roaming\Claude\claude_desktop_config.json` |

PowerShell에서 확인하는 방법:

```powershell
$p = "$env:APPDATA\Claude\claude_desktop_config.json"
Test-Path $p
```

> macOS는 `~/Library/Application Support/Claude/claude_desktop_config.json`, Linux는 `~/.config/Claude/claude_desktop_config.json`.

## 3. 수행 내역

실행 전 상태: **`Claude` 폴더 자체가 존재하지 않음** → 폴더 생성 후 기본 JSON 신규 작성.

```powershell
New-Item -ItemType Directory -Path "$env:APPDATA\Claude" -Force
```

## 4. 등록 결과

| # | 서버 이름 | command | args | 결과 |
|---|---|---|---|---|
| 1 | `context7` | `npx` | `-y`, `@upstash/context7-mcp` | **추가됨** |
| 2 | `sequential-thinking` | `npx` | `-y`, `@modelcontextprotocol/server-sequential-thinking` | **추가됨** |
| 3 | `playwright` | `npx` | `-y`, `@playwright/mcp@latest` | **추가됨** |

파일이 신규 생성되었으므로 기존 항목 충돌 없이 3종 모두 추가되었다. (기존 설정이 있었다면 해당 key는 `이미 존재해서 건너뜀`으로 처리된다.)

## 5. 각 MCP 서버의 역할

| 서버 | 역할 |
|---|---|
| **context7** | 라이브러리·프레임워크의 최신 공식 문서를 실시간 조회. 오래된 API 정보로 인한 환각 방지 |
| **sequential-thinking** | 복잡한 문제를 단계적 사고 체인으로 분해. 추론 과정을 명시적으로 전개 |
| **playwright** | 브라우저 자동화. 실제 웹 페이지 조작·스크래핑·E2E 테스트 수행 |

## 6. 최종 파일 내용

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": [
        "-y",
        "@upstash/context7-mcp"
      ]
    },
    "sequential-thinking": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sequential-thinking"
      ]
    },
    "playwright": {
      "command": "npx",
      "args": [
        "-y",
        "@playwright/mcp@latest"
      ]
    }
  }
}
```

## 7. Windows 주의사항 — `npx` vs `npx.cmd`

Windows에서 `"command": "npx"` 가 동작하지 않을 수 있다. Node의 npx는 `npx.cmd` (배치 파일)로 설치되는데, Claude Desktop이 셸을 거치지 않고 프로세스를 직접 실행하면 확장자 없는 `npx` 를 찾지 못해 서버 기동이 실패한다.

증상: Claude Desktop에서 해당 MCP 서버가 목록에 뜨지 않거나 "failed to start" 로그가 남는다.

해결: `command` 를 `npx.cmd` 로 바꾼다.

```json
"context7": {
  "command": "npx.cmd",
  "args": ["-y", "@upstash/context7-mcp"]
}
```

그래도 안 되면 절대 경로를 지정한다. 경로 확인:

```powershell
(Get-Command npx).Source
```

또는 `cmd /c` 로 감싸는 방법도 있다.

```json
"command": "cmd",
"args": ["/c", "npx", "-y", "@upstash/context7-mcp"]
```

## 8. 다음 단계

1. **Claude Desktop 완전 종료** — 창만 닫으면 트레이에 남는다. 시스템 트레이 아이콘 우클릭 → 종료.
2. Claude Desktop 재시작.
3. 첫 실행 시 각 MCP 서버의 **권한 승인** 요청 → 승인.
4. 입력창의 도구/커넥터 아이콘에서 3개 서버가 보이는지 확인.
5. 동작 확인 프롬프트 예:
   - context7: "React 19의 use hook 공식 문서 찾아줘"
   - sequential-thinking: "이 문제를 단계적으로 분해해서 풀어줘"
   - playwright: "example.com 열어서 제목 알려줘"

> 첫 기동 시 `npx` 가 패키지를 다운로드하므로 수십 초 걸릴 수 있다. 로그는 `%APPDATA%\Claude\logs\` 에서 확인한다.

## 9. MCP 3종 동작 검증 결과 (2026-10-14)

### npx 이슈 여부

| 항목 | 결과 |
|---|---|
| `npx` 경로 | `D:\Program\NodeJS\npx` (npx.cmd도 같은 경로에 존재) |
| npx 버전 | 10.9.3 |
| 설정 파일 command | `"npx"` (현재 상태) |
| **이슈 발생 여부** | **없음 — `npx` 그대로 동작** |

> `npx.cmd`로 바꾸지 않아도 됐다. PATH에 `.cmd`가 포함되어 있어서 `npx` 단독 호출도 성공한 것으로 보인다.

### 3종 서버 동작 확인

| # | 서버 | 테스트 내용 | 결과 |
|---|---|---|---|
| 1 | **context7** | Next.js 라이브러리 ID 조회 (`resolve-library-id`) | ✅ 정상 — `/vercel/next.js` (Code Snippets: 5481, Benchmark: 89.36) 반환 |
| 2 | **sequential-thinking** | 단계적 사고 체인 1-step 실행 | ✅ 정상 — `thoughtNumber:1`, `nextThoughtNeeded:false` 응답 |
| 3 | **playwright** | `https://modelcontextprotocol.io` 접속 및 스냅샷 | ✅ 정상 — 페이지 타이틀 "What is the Model Context Protocol (MCP)?" 수신 |

### context7 파라미터 주의사항

`resolve-library-id` 는 **`libraryName`과 `query` 두 파라미터가 모두 필수**다. 하나만 넘기면 validation error가 발생한다.

```
올바른 호출:
  libraryName: "Next.js"
  query: "App Router Server Actions"

잘못된 호출 (둘 중 하나만):
  libraryName: "Next.js"  ← query 누락 → 오류
  query: "Next.js"        ← libraryName 누락 → 오류
```

## 10. 트러블슈팅 — context7·sequential-thinking 실패 (2026-10-14)

### 증상

Claude Desktop 설정 → 개발자 → MCP 항목에서 context7, sequential-thinking이 **실패** 상태로 표시됨. playwright는 정상.

### 원인

로그 위치: `%LOCALAPPDATA%\Claude\logs\mcp-server-context7.log` / `mcp-server-sequential-thinking.log`

```
npm warn tar TAR_ENTRY_ERROR UNKNOWN: unknown error, open '...\node_modules\...'
→ Error [ERR_MODULE_NOT_FOUND] / ENOENT
```

`npx -y`로 패키지를 처음 다운로드할 때 **tar 압축 해제 중 파일이 손상**되어 `node_modules` 내 일부 파일이 누락된 채로 캐시에 남음. Node.js 실행 시 누락된 JS 파일을 찾지 못해 즉시 종료.

playwright는 로그 파일이 0바이트 → 에러 없이 정상 기동된 것.

### 해결

손상된 캐시 경로를 직접 삭제하고 Claude Desktop을 재시작하면 재다운로드 시 정상 설치됨.

```powershell
# 손상된 캐시 항목 삭제
Remove-Item "$env:LOCALAPPDATA\npm-cache\_npx\eea2bd7412d4593b" -Recurse -Force
Remove-Item "$env:LOCALAPPDATA\npm-cache\_npx\de2bd410102f5eda" -Recurse -Force

# 전체 캐시 무결성 검증 (선택)
npm cache verify
```

이후 Claude Desktop 완전 종료(트레이 아이콘 우클릭 → 종료) 후 재시작.

> 캐시 손상은 antivirus 실시간 검사, 네트워크 불안정, 디스크 I/O 오류 등이 원인이 될 수 있음. 재현 시 `npm cache clean --force` 로 전체 캐시를 초기화한다.

### 복구 확인

```
npx -y @upstash/context7-mcp --version
→ 4.4.1 (exit 0)                                    ✅

npx -y @modelcontextprotocol/server-sequential-thinking
→ Sequential Thinking MCP Server running on stdio    ✅
```

### ⚠️ 주의 — 캐시 삭제는 실행 중인 세션을 끊는다

캐시를 삭제하는 순간, **이미 실행 중이던 MCP 서버 프로세스가 참조하던 파일이 사라져 즉시 연결 해제된다.** 실제로 이번에 캐시 삭제 직후 현재 세션에서 context7·sequential-thinking 도구가 목록에서 사라졌다.

따라서 캐시 수리 작업의 순서는:

1. 손상된 캐시 삭제
2. **Claude Desktop / Claude Code 완전 재시작** ← 생략 불가
3. 재시작 후 동작 확인 프롬프트 실행

재시작 전에는 "패키지는 고쳐졌지만 현재 세션에서는 여전히 사용 불가" 상태다.

### 재시작 후 최종 검증 (2026-10-14)

세션 재연결 후 3종 모두 실제 호출 테스트 완료.

| # | 서버 | 테스트 호출 | 응답 | 상태 |
|---|---|---|---|---|
| 1 | **context7** | `resolve-library-id` (Next.js) | `/vercel/next.js` · Snippets 5481 · Benchmark 89.19 | ✅ 정상 |
| 1-b | **context7** | `query-docs` (Server Actions) | 실제 Next.js 공식 문서 5건 반환 | ✅ 정상 |
| 2 | **sequential-thinking** | 사고 체인 1-step | `thoughtNumber:1`, `thoughtHistoryLength:1` | ✅ 정상 |
| 3 | **playwright** | `modelcontextprotocol.io` 접속 | 타이틀 "What is the Model Context Protocol (MCP)?" | ✅ 정상 |

> context7은 `resolve-library-id`만으로는 ID 검색만 검증된다. **`query-docs`까지 호출해야 실제 문서 조회 경로가 검증**된다. 캐시 손상 시 깨지는 지점이 주로 후자이므로 두 단계 모두 확인할 것.

### 참고 — Context7로 조회한 Next.js Server Actions 핵심

출처: `/vercel/next.js` (Context7 · 공식 레포 `docs/01-app/` 및 `examples/next-forms/`)

1. **서버 함수 정의** — 파일 상단에 `'use server'` 선언 후 `async` 함수를 export. `<form action={fn}>` 에 넘기면 `FormData`를 자동으로 받는다.
2. **상태·검증 처리** — `useActionState`와 함께 쓰면 시그니처가 `(prevState, formData)` 로 바뀌며, 클라이언트에서 `[state, formAction, pending]` 로 메시지와 로딩 상태를 관리한다.
3. **보안** — Server Actions는 POST로 동작해 CSRF 위험이 낮고 렌더 중 부작용을 막으므로, 변경(mutation) 작업은 route handler보다 Server Action이 권장된다.

```tsx
// app/actions.ts
'use server'
export async function createUser(initialState: any, formData: FormData) {
  const validated = schema.safeParse({ email: formData.get('email') })
  // ...
}

// app/signup.tsx
'use client'
import { useActionState } from 'react'
import { createUser } from '@/app/actions'

export function Signup() {
  const [state, formAction, pending] = useActionState(createUser, { message: '' })
  return (
    <form action={formAction}>
      <input type="text" name="email" required />
      <p aria-live="polite">{state?.message}</p>
      <button disabled={pending}>Sign up</button>
    </form>
  )
}
```

## 11. Claude Code MCP 연결 상태 확인 (2026-10-14)

### 확인 명령

```powershell
claude mcp list
```

### 결과

| # | 서버 | 유형 | 엔드포인트 / 실행 경로 | 상태 |
|---|---|---|---|---|
| 1 | claude.ai Claude Docs | 원격 (HTTP) | `https://api.anthropic.com/v1/pages/mcp` | ✅ Connected |
| 2 | claude.ai Notion | 원격 (HTTP) | `https://mcp.notion.com/mcp` | ⚠️ Needs authentication |
| 3 | claude.ai Google Drive | 원격 (HTTP) | `https://drivemcp.googleapis.com/mcp/v1` | ✅ Connected |
| 4 | claude.ai Gmail | 원격 (HTTP) | `https://gmailmcp.googleapis.com/mcp/v1` | ✅ Connected |
| 5 | claude.ai Google Calendar | 원격 (HTTP) | `https://calendarmcp.googleapis.com/mcp/v1` | ✅ Connected |
| 6 | plugin:oh-my-claudecode:t | 로컬 (stdio) | `node .../oh-my-claudecode/4.11.6/bridge/mcp-server.cjs` | ✅ Connected |

**요약: 6개 중 5개 연결 완료, 1개(Notion) 인증 대기**

### Claude Desktop 설정과의 차이

| 구분 | Claude Desktop | Claude Code |
|---|---|---|
| 설정 위치 | `%APPDATA%\Claude\claude_desktop_config.json` | `claude mcp add` / `~/.claude.json` |
| 확인 방법 | 설정 → 개발자 → MCP | `claude mcp list` |
| 이번 실습 등록 | context7, sequential-thinking, playwright | (별도) 원격 커넥터 5종 + 플러그인 1종 |

> 두 호스트는 **MCP 설정을 공유하지 않는다.** 같은 서버를 양쪽에서 쓰려면 각각 등록해야 한다.

### 전송 방식(Transport) 비교 — 실측 확인

| 방식 | 이번 목록의 예 | 특징 |
|---|---|---|
| **stdio** | `plugin:oh-my-claudecode:t` | 로컬 프로세스를 `node` 로 띄워 표준입출력으로 통신. 설정 간단, 인증 불필요 |
| **Streamable HTTP** | Gmail, Drive, Calendar, Notion, Claude Docs | 원격 서버에 HTTP로 접속. **OAuth 인증 필요** → 미인증 시 `Needs authentication` |

이 목록이 MCP의 두 transport를 실제로 보여준다. 로컬 플러그인은 인증 단계가 없고, 원격 SaaS 커넥터는 모두 계정 인증을 거친다.

### Notion 인증 처리

`Needs authentication` 은 서버 등록은 됐지만 OAuth 승인이 안 된 상태다. 인증은 대화형 세션에서 `/mcp` 를 실행해 Notion 항목을 선택하거나, claude.ai 웹의 커넥터 설정에서 직접 승인한다. 승인 후 다시 확인:

```powershell
claude mcp list
```

`✔ Connected` 로 바뀌면 완료.

> OAuth는 브라우저 플로우가 필요하므로 비대화형 세션에서는 처리할 수 없다.

## 12. 플랫폼 호환성 — Windows / macOS 대조

Windows와 macOS를 번갈아 쓰는 환경을 위한 대조표. **MCP 설정은 기기별로 따로** 해야 한다 (클라우드 동기화되지 않음).

### 12-1. 경로 대조표

| 항목 | Windows | macOS |
|---|---|---|
| Desktop 설정 파일 | `%APPDATA%\Claude\claude_desktop_config.json` | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| 로그 디렉터리 | `%LOCALAPPDATA%\Claude\logs\` | `~/Library/Logs/Claude/` |
| npx 캐시 | `%LOCALAPPDATA%\npm-cache\_npx\` | `~/.npm/_npx/` |
| `command` 값 | `npx` (실패 시 `npx.cmd`) | `npx` — `.cmd` 이슈 **없음** |
| 앱 완전 종료 | 트레이 아이콘 우클릭 → 종료 | `Cmd+Q` |
| 설정 파일 열기 | `notepad %APPDATA%\Claude\claude_desktop_config.json` | `open -e ~/Library/Application\ Support/Claude/claude_desktop_config.json` |

### 12-2. 설정 JSON은 양쪽 동일

6절의 JSON을 그대로 쓴다. macOS에서는 `npx.cmd` 대안이 필요 없으므로 `"command": "npx"` 고정이다.

```bash
# macOS — 폴더 생성 후 편집
mkdir -p ~/Library/Application\ Support/Claude
open -e ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

```powershell
# Windows — 폴더 생성 후 편집
New-Item -ItemType Directory -Path "$env:APPDATA\Claude" -Force
notepad "$env:APPDATA\Claude\claude_desktop_config.json"
```

### 12-3. 캐시 손상 복구 (10절의 플랫폼별 버전)

```powershell
# Windows
Get-Content "$env:LOCALAPPDATA\Claude\logs\mcp-server-context7.log" -Tail 50
Remove-Item "$env:LOCALAPPDATA\npm-cache\_npx\<해시>" -Recurse -Force
npm cache verify
```

```bash
# macOS
tail -50 ~/Library/Logs/Claude/mcp-server-context7.log
rm -rf ~/.npm/_npx          # 해시 특정이 어려우면 통째로 삭제
npm cache verify
```

> 10절의 경고는 양쪽 공통 — **캐시를 지우면 실행 중이던 MCP 서버가 즉시 끊기므로 반드시 호스트 앱을 재시작**해야 한다.

### 12-4. ⚠️ 공통 함정 — GUI 앱은 셸 PATH를 모른다

**Windows와 macOS 모두에서 같은 원리로 발생하는 문제**다. GUI 앱(Claude Desktop, VS Code)은 셸 프로필을 읽지 않거나, 앱 실행 시점의 환경 변수를 그대로 물려받는다.

| 플랫폼 | 증상 | 원인 | 해결 |
|---|---|---|---|
| Windows | 설치 후에도 `az`/`npx` 인식 실패 | 설치 전 실행된 프로세스가 옛 PATH 보유 | **앱 자체를 재시작** (터미널 탭만 새로 여는 것으론 부족) |
| macOS | nvm으로 설치한 Node를 못 찾음 | GUI 앱이 `~/.zshrc`를 읽지 않음 | 설정에 **절대 경로** 지정 |

macOS에서 nvm을 쓰는 경우 절대 경로를 넣는다.

```bash
which npx
# 예: /Users/me/.nvm/versions/node/v22.19.0/bin/npx
```

```json
"context7": {
  "command": "/Users/me/.nvm/versions/node/v22.19.0/bin/npx",
  "args": ["-y", "@upstash/context7-mcp"]
}
```

> Homebrew로 설치한 Node(`/opt/homebrew/bin/npx`)는 대체로 문제없다. nvm 사용자만 해당된다.

### 12-5. 기기 간 이동 체크리스트

새 기기에서 환경을 세팅할 때 순서대로 확인한다.

- [ ] Node.js 설치 확인 — `node -v`, `npx -v`
- [ ] 설정 파일 경로에 맞게 JSON 생성 (12-1 표 참조)
- [ ] macOS + nvm 조합이면 `command`에 절대 경로 지정
- [ ] 호스트 앱 **완전 종료 후** 재시작
- [ ] 설정 → 개발자 → MCP에서 3종 상태 확인
- [ ] 실패 시 로그 확인 → 캐시 삭제 → 재시작 (12-3)

## 13. 배운 점 / 개념 정리

- **MCP (Model Context Protocol)**: AI 모델과 외부 도구·데이터를 연결하는 표준 프로토콜. N개 모델 × M개 도구의 조합 폭발(N×M)을 N+M으로 줄인다.
- **MCP 호스트 / 서버**: Claude Desktop은 호스트, 등록된 각 서버는 독립 프로세스로 기동되어 `stdio` 로 통신한다.
- **설정의 멱등성**: 설정 자동화에서 "덮어쓰기"가 아닌 "없는 것만 병합"이 중요하다. 재실행 안전성과 기존 설정 보존을 동시에 달성한다.
- **호스트별 독립 설정**: MCP 서버는 호스트(Desktop / Code)별로 따로 등록·관리된다. 한쪽 설정이 다른 쪽에 자동 반영되지 않는다.
- **"등록됨" ≠ "사용 가능"**: 원격 MCP 서버는 OAuth 승인까지 끝나야 도구가 실제로 노출된다. `claude mcp list` 의 상태 기호(`✔` / `!`)로 연결 문제와 인증 문제를 구분할 수 있다.
- **캐시 손상 가능성**: `npx -y` 방식은 편하지만 첫 다운로드 시 tar 압축 해제가 깨지면 조용히 실패한다. 로그 확인 → 해당 `_npx` 캐시 삭제 → **호스트 재시작**이 복구 절차다.
- **환경 변수 상속**: 프로세스는 시작 시점의 환경 변수를 복사해 가진다. 이후 시스템 PATH가 바뀌어도 이미 떠 있는 프로세스는 영원히 모른다. Windows의 "터미널 재시작으로 안 됨" 문제와 macOS의 "GUI 앱이 nvm Node를 못 찾음" 문제는 **같은 원리의 다른 증상**이다.
- **설정의 기기 종속성**: MCP 설정과 Azure 로그인 자격 증명은 모두 로컬에 저장되어 기기 간 동기화되지 않는다. 반면 클라우드 리소스(구독, 서비스 가용성)는 어느 기기에서 조회하든 동일하다. **"무엇이 로컬이고 무엇이 원격인지"** 구분하면 기기 이동 시 재설정 범위를 정확히 예측할 수 있다.

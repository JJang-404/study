# 실습 1-2 · Azure CLI로 koreacentral 리전 AI/Cognitive Services 조회

> 1주차 실습 산출물 · 작성일 2026-10-14
> **상태: ✅ 완료 — 22개 kind 중 koreacentral 가용 14개 확인**

## 1. 실습 목표

Azure CLI를 사용해 `koreacentral` 리전에서 사용 가능한 AI/Cognitive Services 종류를 조회하고 표로 정리한다.

## 2. 환경 준비 결과

| 항목 | 상태 | 비고 |
|---|---|---|
| Azure CLI 설치 | ✅ 완료 | winget으로 설치, **v2.91.0** |
| 설치 경로 | — | `C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd` |
| 현재 셸 PATH 반영 | ⚠️ 미반영 | 설치 직후라 기존 셸에서는 `az` 인식 불가 → **터미널 재시작 필요** |
| az login | ❌ 미완료 | 브라우저 대화형 인증 — 사용자 본인만 수행 가능 |
| 조회 실행 | ❌ 미실행 | 로그인 선행 필요 |

설치에 사용한 명령:

```powershell
winget install --id Microsoft.AzureCLI --accept-package-agreements --accept-source-agreements
```

### ⚠️ 함정 — 설치 후 `az`를 인식하지 못하는 문제

설치 직후 기존 터미널에서 `az login`을 실행하면 다음 오류가 난다.

```
az : 'az' 용어가 cmdlet, 함수, 스크립트 파일 또는 실행할 수 있는 프로그램 이름으로 인식되지 않습니다.
```

**원인은 PATH 미등록이 아니다.** 확인해보면 Machine PATH에는 정상 등록되어 있다.

```powershell
[Environment]::GetEnvironmentVariable("Path","Machine") -split ';' | Where-Object { $_ -like '*Azure*CLI*' }
# → C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin   (등록됨)

$env:Path -split ';' | Where-Object { $_ -like '*Azure*CLI*' }
# → (출력 없음)                                        (현재 세션엔 없음)
```

환경 변수는 **프로세스 시작 시점에 상속**된다. 설치 전에 열려 있던 셸은 변경된 PATH를 끝까지 알지 못한다.

#### 해결 1 — 현재 세션에서 PATH 새로고침 (즉시)

```powershell
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
```

#### 해결 2 — 전체 경로로 직접 호출

```powershell
& "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd" version
```

#### 해결 3 — VS Code 완전 재시작 (영구)

| 방법 | 효과 |
|---|---|
| PATH 새로고침 한 줄 | 즉시 해결, 단 **현재 탭 한정** |
| 터미널 탭만 새로 열기 | ⚠️ **실패 가능** — 새 탭은 VS Code 프로세스의 환경을 상속하므로, VS Code를 설치 전에 켰다면 여전히 옛 PATH |
| **VS Code 완전 종료 후 재시작** | ✅ 영구 해결 |

> 핵심: "터미널 재시작"으로 충분하다고 흔히 안내되지만, VS Code·Claude Desktop 같은 **호스트 앱을 설치 전에 켜뒀다면 앱 자체를 재시작**해야 한다. 터미널 탭은 앱의 자식 프로세스라 앱의 낡은 환경을 그대로 물려받는다.

## 3. ⚠️ 원래 제안된 명령 조합의 문제점

실습 과제에서 제안된 `az cognitiveservices account list-kinds` + `az group list -o table` 조합은 목표에 맞지 않는다. 이유는 두 가지다.

### 3-1. `list-kinds`는 리전 필터를 지원하지 않는다

```powershell
az cognitiveservices account list-kinds
```

이 명령은 구독에서 **사용 가능한 전체 kind 목록**(OpenAI, ComputerVision, TextAnalytics 등)을 반환할 뿐, `--location` 인자를 받지 않는다. 즉 "koreacentral에서 쓸 수 있는 것"으로 좁혀주지 않는다.

리전별 가용성을 보려면 `list-skus`를 써야 한다. `az cognitiveservices account list-skus --help` 로 확인한 실제 인자:

```
--kind          : The API name of cognitive services account.
                  Values from: az cognitiveservices account list-kinds.
--location -l   : Location. Values from: az account list-locations.
--name -n       : (지정 시 --kind와 --location은 무시됨)
```

### 3-2. `az group list`는 이 작업과 무관하다

`az group list`는 **내 구독 안에 만들어둔 리소스 그룹** 목록을 반환한다. "리전에서 제공되는 AI 서비스 종류"와는 다른 층위의 정보라, 두 결과를 조합해도 의미 있는 표가 나오지 않는다.

## 4. 올바른 실행 절차

### STEP 1 — 로그인

```powershell
az login
```

브라우저가 열리면 Azure 계정으로 로그인한다. 구독이 여러 개면 선택 프롬프트가 뜬다.

> 브라우저가 안 열리는 환경(원격 SSH 등)이면 기기 코드 방식을 쓴다:
> ```powershell
> az login --use-device-code
> ```

### STEP 2 — 로그인 확인

```powershell
az account show -o table
```

구독 이름·ID·테넌트가 출력되면 성공이다.

### STEP 3 — 전체 kind 목록 조회

```powershell
az cognitiveservices account list-kinds -o table
```

### STEP 4 — koreacentral 리전 가용 SKU 조회 (핵심)

특정 kind가 koreacentral에서 제공되는지 확인한다.

```powershell
az cognitiveservices account list-skus --kind OpenAI --location koreacentral -o table
```

결과가 비어 있으면 해당 리전에서 그 kind를 쓸 수 없다는 뜻이다.

### STEP 5 — 전체 kind를 koreacentral 기준으로 일괄 점검

PowerShell 반복문으로 모든 kind를 훑어 가용 여부를 표로 만든다.

```powershell
$kinds = az cognitiveservices account list-kinds -o tsv
$result = foreach ($k in $kinds) {
    $skus = az cognitiveservices account list-skus --kind $k --location koreacentral --query "[].name" -o tsv 2>$null
    [PSCustomObject]@{
        종류   = $k
        이름   = if ($skus) { ($skus -join ', ') } else { '(koreacentral 미제공)' }
        사용가능 = if ($skus) { 'O' } else { 'X' }
    }
}
$result | Format-Table -AutoSize
```

Markdown 표로 바로 저장하려면:

```powershell
$result | ForEach-Object { "| $($_.종류) | $($_.이름) | $($_.사용가능) |" } |
    Out-File -Append -Encoding utf8 ".\1-2_azure_ai_services.md"
```

## 5. 조회 결과 ✅

조회 일시: 2026-10-14 · 구독: `Azure subscription 1` (`d7846858-512a-474b-8447-dca0d075a171`)

**전체 22개 kind 중 koreacentral 가용 14개 / 미제공 8개**

### 5-1. koreacentral 사용 가능 (14종)

| # | 종류 (Kind) | 이름 (SKU) |
|---|---|---|
| 1 | `AIServices` | S0 |
| 2 | `CognitiveServices` | S0 |
| 3 | `ComputerVision` | F0, S1 |
| 4 | `ContentModerator` | F0, S0 |
| 5 | `ContentSafety` | F0, S0 |
| 6 | `Face` | E0, F0, S0 |
| 7 | `FormRecognizer` | F0, S0 |
| 8 | `ImmersiveReader` | S0, S1 |
| 9 | `Internal.AllInOne` | S0 |
| 10 | `OpenAI` | S0 |
| 11 | `QnAMaker.v2` | S0 |
| 12 | `SpeechServices` | F0, S0 |
| 13 | `TextAnalytics` | F0, S |
| 14 | `TextTranslation` | C2, C3, C4, D3, F0, S1 |

### 5-2. koreacentral 미제공 (8종)

| # | 종류 (Kind) | 비고 |
|---|---|---|
| 1 | `ConversationalLanguageUnderstanding` | 다른 리전 사용 필요 |
| 2 | `CustomVision.Prediction` | 다른 리전 사용 필요 |
| 3 | `CustomVision.Training` | 다른 리전 사용 필요 |
| 4 | `HealthInsights` | 다른 리전 사용 필요 |
| 5 | `LUIS.Authoring` | 다른 리전 사용 필요 |
| 6 | `LanguageAuthoring` | 다른 리전 사용 필요 |
| 7 | `MetricsAdvisor` | 다른 리전 사용 필요 |
| 8 | `Personalizer` | 다른 리전 사용 필요 |

### 5-3. 결과 해석

- **Azure OpenAI는 koreacentral에서 사용 가능**(S0)하다. 다만 kind 가용성과 *모델* 가용성은 별개라, 실제 배포 전 `az cognitiveservices account deployment list`로 모델별 제공 여부를 따로 확인해야 한다.
- **F0(무료 티어)를 제공하는 kind가 8종**(ComputerVision, ContentModerator, ContentSafety, Face, FormRecognizer, SpeechServices, TextAnalytics, TextTranslation)이다. 학습·실습 목적이라면 이들을 우선 선택하면 비용이 들지 않는다.
- **CustomVision 계열(Training/Prediction)이 모두 미제공**이다. 이미지 분류 모델을 직접 학습시키는 실습을 하려면 `japaneast`, `eastus` 등 다른 리전을 써야 한다.
- `TextTranslation`이 SKU 6종으로 가장 세분화되어 있다. C2~C4, D3는 대용량 번역용 고정 가격 등급이다.

## 6. 트러블슈팅 기록

실행 과정에서 막힌 지점 3곳과 해결 방법.

### 6-1. `az` 명령 인식 실패

2절의 "함정" 항목 참조. 설치 전에 열려 있던 셸은 바뀐 PATH를 모른다.

### 6-2. MFA 요구로 로그인 실패 (AADSTS50076)

```
Authentication failed against tenant 4e110df0-... '기본 디렉터리':
AADSTS50076: ... you must use multi-factor authentication to access ...
No subscriptions found for <계정>.
```

기본 `az login`은 테넌트 목록을 훑기만 하고 MFA 대화 상자를 띄우지 못한다. **테넌트를 명시**하면 MFA 프롬프트가 정상적으로 뜬다.

```powershell
az account clear
az login --tenant 4e110df0-a60f-4da0-ab9e-7f875d63a511
```

> `No subscriptions found`가 함께 떠도 당황하지 말 것. MFA 실패로 테넌트 조회가 중단된 결과이지, 구독이 없다는 확정 신호가 아니다.

### 6-3. `Invalid selection` — 실제로는 로그인 성공

```
Select a subscription and tenant (Type a number or Enter for no changes): <명령어 붙여넣음>
Invalid selection.
```

`az login`이 **구독 선택 번호를 기다리는 대화형 프롬프트**인데 다음 명령어를 붙여넣어 발생. 단, 구독이 1개뿐이면 선택이 거부돼도 **기본값으로 자동 설정되어 로그인은 완료된다.** 오류 메시지만 보고 재시도하지 말고 먼저 상태를 확인할 것.

```powershell
az account show -o table   # 구독이 나오면 성공
```

> 역으로, 선택 프롬프트가 떴다는 것 자체가 **구독이 존재한다는 증거**다. 구독이 없으면 그 화면이 나오지 않는다.

## 7. macOS에서 동일 실습 수행하기

Windows/macOS를 번갈아 쓰는 경우를 위한 대조표. **구독과 조회 결과는 클라우드 쪽이라 완전히 동일**하고, 기기별로 다른 것은 설치 방법·셸 문법·로그인 상태뿐이다.

### 7-1. 플랫폼 대조표

| 항목 | Windows | macOS |
|---|---|---|
| 설치 | `winget install --id Microsoft.AzureCLI` | `brew install azure-cli` |
| PATH 문제 | ⚠️ 설치 전 열린 셸은 수동 갱신 필요 | 거의 없음 (brew가 처리, 필요 시 `source ~/.zshrc`) |
| 설치 경로 | `C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\` | `/opt/homebrew/bin/az` (Apple Silicon) / `/usr/local/bin/az` (Intel) |
| 로그인 캐시 | `%USERPROFILE%\.azure` | `~/.azure` |
| 셸 | PowerShell | zsh / bash |
| **로그인** | — | **머신별로 저장 → 맥에서 `az login` 재수행 필요** |
| **구독·조회 결과** | — | **동일** |

### 7-2. macOS 실행 절차

```bash
# 1. 설치 (Homebrew 필요)
brew install azure-cli

# 2. 확인
az version

# 3. 로그인 (MFA 테넌트 지정 — Windows와 동일한 이슈 발생)
az account clear
az login --tenant 4e110df0-a60f-4da0-ab9e-7f875d63a511

# 4. 구독 확인
az account list --all -o table
```

### 7-3. 조회 스크립트 — bash 버전

5절의 PowerShell 스크립트는 맥에서 동작하지 않는다. 아래로 대체한다.

```bash
for k in $(az cognitiveservices account list-kinds -o tsv); do
  skus=$(az cognitiveservices account list-skus --kind "$k" --location koreacentral \
         --query "[].name" -o tsv 2>/dev/null | sort -u | paste -sd ', ' -)
  if [ -n "$skus" ]; then
    echo "| $k | $skus | O |"
  else
    echo "| $k | - | X |"
  fi
done
```

Markdown 표로 바로 저장하려면:

```bash
{
  echo "| 종류 | 이름(SKU) | 가용 |"
  echo "|---|---|---|"
  for k in $(az cognitiveservices account list-kinds -o tsv); do
    skus=$(az cognitiveservices account list-skus --kind "$k" --location koreacentral \
           --query "[].name" -o tsv 2>/dev/null | sort -u | paste -sd ', ' -)
    [ -n "$skus" ] && echo "| $k | $skus | O |" || echo "| $k | - | X |"
  done
} > az_koreacentral.md
```

> Homebrew가 없다면 먼저 설치한다:
> `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`

## 8. 배운 점 / 개념 정리

- **Kind vs SKU**: `kind`는 서비스 종류(OpenAI, ComputerVision 등), `sku`는 그 안의 가격·성능 등급(F0 무료, S0 표준 등)이다. 리전 가용성은 kind가 아니라 **kind + location 조합**으로 판정된다.
- **리전별 가용성 차이**: 모든 Azure AI 서비스가 모든 리전에 있지는 않다. 특히 Azure OpenAI는 리전별 제공 모델이 다르므로 배포 전 반드시 확인해야 한다.
- **CLI 명령 검증 습관**: 명령어를 믿고 쓰기 전에 `--help`로 실제 지원 인자를 확인하면, 이번처럼 "리전 필터가 없는 명령에 리전을 기대하는" 설계 오류를 미리 잡을 수 있다.
- **자동화의 경계**: 설치·조회·정리는 자동화 가능하지만, 자격 증명 입력은 사람의 영역이다. 자동화 범위를 설계할 때 이 경계를 명시해두면 혼선이 줄어든다.

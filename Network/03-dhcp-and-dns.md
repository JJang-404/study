# 03. DHCP와 DNS

## 이번 학습 목표

- DHCP가 장치에 어떤 네트워크 설정을 전달하는지 설명합니다.
- 새 장치가 주소를 받는 기본 과정(DORA)을 말할 수 있습니다.
- DNS가 이름을 IP 주소 등으로 조회하는 과정을 설명합니다.
- `ipconfig`와 `nslookup` 결과를 이용해 DHCP 문제와 DNS 문제를 구분하는 출발점을 찾습니다.

## 1. DHCP: 네트워크 설정을 자동으로 받기

DHCP(Dynamic Host Configuration Protocol)는 네트워크에 연결된 클라이언트에 설정을 제공하고, 동적으로 주소를 빌려주는 프로토콜입니다. 일반적으로 다음 항목을 전달할 수 있습니다.

- 클라이언트의 IPv4 주소와 임대 기간
- 서브넷 마스크(또는 프리픽스 정보)
- 기본 게이트웨이
- DNS 서버 주소
- 필요에 따라 검색 도메인 등 추가 설정

관리자는 주소를 나눠 줄 범위(범위, scope)를 설정할 수 있습니다. 특정 주소를 자동 배정에서 제외하거나, 특정 클라이언트가 같은 주소를 받도록 예약할 수도 있습니다. 예약은 DHCP 서버와 클라이언트를 식별하는 정보에 따라 동작하며, 반드시 MAC 주소만을 유일한 식별자로 쓴다고 단정하면 안 됩니다.

DHCP가 자동으로 설정을 나눠주면 장치마다 주소를 수동 입력하는 실수를 줄일 수 있습니다. 다만 잘못된 DHCP 범위나 옵션은 여러 장치에 잘못된 설정을 한꺼번에 전달할 수 있습니다.

## 2. DORA: 주소를 받는 기본 과정

새 클라이언트가 DHCPv4 서버에서 주소를 받는 대표적인 초기 흐름은 DORA 네 단계입니다.

1. **Discover** — 클라이언트가 DHCP 서버를 찾기 위해 요청을 보냅니다.
2. **Offer** — 서버가 사용할 수 있는 주소와 설정을 제안합니다.
3. **Request** — 클라이언트가 제안 중 하나를 선택해 요청합니다.
4. **Acknowledge** — 서버가 할당을 확인하고 임대 정보를 응답합니다.

이 이름의 첫 글자를 이어 DORA라고 부릅니다. 초기 연결에서는 클라이언트가 아직 주소를 모를 수 있으므로 브로드캐스트가 사용됩니다. 클라이언트와 DHCP 서버가 서로 다른 서브넷에 있으면 라우터의 DHCP relay 기능이 요청을 전달하도록 구성할 수 있습니다.

### 임대(lease)와 갱신

DHCP 주소는 임대 기간 동안 사용할 수 있습니다. 클라이언트는 임대가 끝나기 전에 갱신을 시도합니다. 따라서 장치가 오랫동안 연결되어 있어도 DHCP에 의한 주소 재사용·갱신 과정이 진행될 수 있습니다.

`ipconfig /release`와 `ipconfig /renew`는 DHCP 주소를 해제하거나 새로 요청하는 명령입니다. 연결이 잠시 끊기거나 현재 원격 접속이 중단될 수 있으므로 아래 실습에서는 조회 명령만 먼저 사용합니다.

## 3. DNS: 이름으로 대상을 찾기

DNS(Domain Name System)는 도메인 이름과 IP 주소 같은 정보를 계층적으로 저장하고 조회하는 시스템입니다. 사람이 `example.com` 같은 이름을 쓰면, 클라이언트는 설정된 DNS 서버에 필요한 정보를 질의합니다.

일반적인 조회 흐름은 다음과 같이 이해할 수 있습니다.

1. 운영체제 또는 앱이 이미 가진 캐시와 로컬 이름 정보를 확인합니다.
2. 답이 없으면 설정된 DNS 리졸버에 질의합니다.
3. 리졸버는 캐시에 답이 없을 때 다른 DNS 서버에 질의해 답을 찾을 수 있습니다.
4. 결과를 클라이언트에 반환하고, 지정된 TTL 동안 캐시할 수 있습니다.
5. 앱은 응답에 포함된 주소를 이용해 대상 서비스와 통신을 시도합니다.

실제 환경에서는 브라우저 자체 캐시, 운영체제 캐시, 기업 네트워크 리졸버, 암호화된 DNS 등 변수가 더 있을 수 있습니다. 따라서 한 번의 조회 결과가 모든 앱의 접속 결과와 항상 같다고 가정하지 않습니다.

### 자주 접하는 DNS 레코드

| 레코드 | 용도 |
|---|---|
| `A` | 이름을 IPv4 주소로 연결 |
| `AAAA` | 이름을 IPv6 주소로 연결 |
| `CNAME` | 다른 이름을 가리키는 별칭 |
| `MX` | 메일을 받는 서버 정보 |
| `PTR` | IP 주소에서 이름을 찾는 역방향 조회 |
| `TXT` | 도메인에 연결된 텍스트 정보. 이메일 발신 정책 등에 활용되기도 함 |

DNS는 웹사이트 내용이나 네트워크 경로를 전달하는 기능이 아닙니다. 이름 조회가 성공해도 서버가 꺼져 있거나, 경로·포트·방화벽에 문제가 있으면 서비스 접속은 실패할 수 있습니다.

## 4. DHCP와 DNS는 어떻게 연결되나요?

DHCP와 DNS는 서로 다른 일을 하지만 함께 쓰입니다.

- DHCP는 클라이언트에 IP 주소, 게이트웨이, DNS 서버 주소 같은 설정을 제공합니다.
- DNS는 도메인 이름에 대응하는 IP 주소 등 정보를 질의합니다.

클라이언트가 DHCP에서 잘못된 DNS 서버 주소를 받으면 인터넷 연결 자체가 되어도 이름 조회가 실패할 수 있습니다. 반대로 IP 주소를 직접 사용한 연결은 되지만 이름을 사용한 연결만 실패할 수도 있습니다. 일부 네트워크에서는 DHCP 서버나 장치가 동적 DNS 등록을 도와주기도 하지만, 이것은 구성에 따라 다릅니다.

## 5. Windows에서 확인하기

아래 명령은 설정을 살펴보는 용도입니다.

```powershell
ipconfig /all
nslookup example.com
nslookup -type=A example.com
nslookup -type=AAAA example.com
ipconfig /displaydns
```

- `ipconfig /all`: 주소를 자동으로 받는지, DHCP 서버·임대 정보·기본 게이트웨이·DNS 서버가 무엇인지 확인합니다.
- `nslookup example.com`: 설정된 DNS 서버에 이름을 질의해 응답을 확인합니다.
- `nslookup -type=A example.com`: IPv4 주소 레코드를 질의합니다.
- `nslookup -type=AAAA example.com`: IPv6 주소 레코드를 질의합니다.
- `ipconfig /displaydns`: Windows DNS 클라이언트 캐시를 표시합니다.

특정 DNS 서버를 지정해 비교할 수도 있습니다.

```powershell
nslookup example.com 1.1.1.1
```

이 비교 결과가 다르다고 곧바로 한 서버가 고장이라고 단정하지 않습니다. 공용 DNS 서버로의 질의가 네트워크 정책으로 차단될 수 있고, 내부 전용 이름은 공용 DNS 서버에서 조회되지 않는 것이 정상일 수 있습니다. 실제 실습에서는 본인이 사용할 권한이 있는 공개 도메인만 질의합니다.

## 6. 증상별로 생각하기

| 증상 | 먼저 확인할 것 | 아직 단정하지 말 것 |
|---|---|---|
| IP 주소·게이트웨이가 없거나 `169.254.x.x`가 보임 | 어댑터 연결, DHCP 사용 여부, 임대 주소와 DHCP 서버 정보 | DHCP 서버 고장이라고 바로 결론 내리지 않기. 케이블·Wi-Fi·VLAN·relay 등의 경로도 가능성 |
| IP로는 통신되는데 이름 조회가 실패 | `ipconfig /all`의 DNS 서버, `nslookup` 응답과 오류 | 인터넷 전체 장애라고 바로 결론 내리지 않기 |
| `nslookup`은 성공하지만 사이트가 열리지 않음 | 응답 주소, 서버 접근성, 애플리케이션 포트, 프록시·방화벽 | DNS가 서비스 접속 전체를 보장한다고 생각하지 않기 |
| 공용 이름은 조회되지만 내부 이름은 실패 | 연결된 네트워크와 DNS 서버, DNS 접미사·내부 DNS 구성 | 내부 이름을 공용 DNS에 공개해 해결하려 하지 않기 |

`169.254.x.x`는 IPv4 링크 로컬 자동 구성 주소 범위에 속하며, DHCP를 통해 정상 설정을 받지 못한 단서가 될 수 있습니다. 환경과 운영체제에 따라 동작이 다를 수 있으므로 이것 하나만으로 원인을 확정하지 않습니다.

## 7. 안전한 첫 실습

1. `ipconfig /all`에서 현재 어댑터의 DHCP 사용 여부, IPv4 주소, 게이트웨이, DNS 서버를 확인합니다.
2. 실제 IP, MAC 주소, 장치 이름, 내부 DNS 접미사 등 공개하지 않을 정보는 저장소에 그대로 복사하지 않습니다.
3. `nslookup example.com` 결과에서 질의한 DNS 서버와 응답 주소를 찾습니다.
4. `nslookup -type=A example.com`과 `nslookup -type=AAAA example.com`의 차이를 기록합니다.
5. `ipconfig /displaydns`를 실행해 캐시된 항목이 어떤 형태로 보이는지 확인합니다.
6. 결과와 해석을 [실습 기록](lab-notes.md)에 적습니다.

현재 연결에 영향을 주는 `/release`, `/renew`, `/flushdns` 명령은 사용 목적과 영향을 이해한 뒤에만 실행합니다. 특히 원격 접속 중인 컴퓨터에서는 연결을 끊을 수 있습니다.

## 8. 내 말로 설명해 보기

- DHCP에서 주소를 받는 DORA 네 단계를 순서대로 설명해 보세요.
- DHCP가 정상이어도 DNS 문제가 생길 수 있는 이유는 무엇인가요?
- `A`와 `AAAA` 레코드는 무엇이 다른가요?
- `nslookup`에서 IP 응답을 받았는데 웹 서비스가 열리지 않을 수 있는 이유는 무엇인가요?

모르는 문장이나 질문은 [질문과 답변](questions-and-answers.md)에 그대로 추가합니다.

## 참고 자료

- [RFC 2131: Dynamic Host Configuration Protocol](https://www.rfc-editor.org/rfc/rfc2131.html) — DHCP 메시지, 주소 임대와 갱신
- [RFC 1034: Domain Names — Concepts and Facilities](https://www.rfc-editor.org/rfc/rfc1034.html) — DNS 이름 공간과 기본 개념
- [RFC 1035: Domain Names — Implementation and Specification](https://www.rfc-editor.org/rfc/rfc1035.html) — DNS 질의·응답 형식과 구현 기초
- [Microsoft Learn: ipconfig](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/ipconfig) — Windows IP 설정 및 DHCP·DNS 관련 명령
- [Microsoft Learn: nslookup](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/nslookup) — DNS 질의 명령과 옵션
- [Microsoft Learn: DNS 클라이언트 문제 해결](https://learn.microsoft.com/en-us/windows-server/networking/dns/troubleshoot/troubleshoot-dns-client) — DNS 클라이언트 확인 순서

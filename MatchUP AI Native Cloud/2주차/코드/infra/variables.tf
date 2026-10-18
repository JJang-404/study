# 입력 변수 — 지역과 리소스 접두어를 외부화한다 (AC-15)

variable "location" {
  description = "모든 리소스를 배포할 Azure 지역"
  type        = string
  default     = "koreacentral" # AC-6
}

variable "prefix" {
  description = "리소스 이름 접두어. 전역 고유 이름(App Service, SQL Server)에도 사용되므로 짧게 유지한다"
  type        = string
  default     = "evtplat"

  validation {
    # App Service·SQL Server 이름은 전역 고유 + 길이 제한이 있어 접두어를 제한한다
    condition     = can(regex("^[a-z][a-z0-9]{2,11}$", var.prefix))
    error_message = "prefix는 소문자로 시작하는 3~12자의 영소문자/숫자여야 합니다."
  }
}

variable "vnet_cidr" {
  description = "VNet 전체 주소 공간"
  type        = string
  default     = "10.10.0.0/16"
}

variable "subnet_cidrs" {
  description = "계층별 서브넷 CIDR. 서로 겹치지 않아야 한다 (AC-11)"
  type = object({
    web = string
    api = string
    db  = string
  })
  default = {
    web = "10.10.1.0/24"
    api = "10.10.2.0/24"
    db  = "10.10.3.0/24"
  }
}

variable "api_instance_count" {
  description = "api 계층 VM Scale Set 인스턴스 수"
  type        = number
  default     = 2
}

variable "api_vm_size" {
  description = "api 계층 VM 크기"
  type        = string
  default     = "Standard_B2s"
}

variable "admin_username" {
  description = "api VM 관리자 계정명"
  type        = string
  default     = "azureuser"
}

variable "ssh_public_key" {
  description = "api VM에 등록할 SSH 공개키. 암호 인증 대신 키 인증만 허용한다"
  type        = string
  # 기본값 없음 — 반드시 외부에서 주입한다 (terraform.tfvars 또는 -var)
}

variable "sql_admin_username" {
  description = "Azure SQL 관리자 계정명"
  type        = string
  default     = "sqladmin"
}

variable "sql_admin_password" {
  description = "Azure SQL 관리자 비밀번호. 코드에 하드코딩하지 않는다"
  type        = string
  sensitive   = true
  # 기본값 없음 — 환경변수 TF_VAR_sql_admin_password 로 주입 권장
}

variable "tags" {
  description = "모든 리소스에 공통으로 부여할 태그"
  type        = map(string)
  default = {
    project = "customer-event-platform"
    course  = "matchup-ai-native-cloud"
    week    = "2"
  }
}

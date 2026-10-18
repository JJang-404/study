# Terraform 및 프로바이더 버전 고정
# 버전을 고정하지 않으면 같은 코드가 시점에 따라 다른 결과를 낸다.

terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  # 인증은 az login 세션을 사용한다 (별도 자격증명 하드코딩 없음)
}

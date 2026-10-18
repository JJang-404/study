# 출력 — 배포 후 검증과 다음 단계 연결에 쓰인다

output "resource_group_name" {
  description = "생성된 리소스 그룹 이름"
  value       = azurerm_resource_group.main.name
}

output "location" {
  description = "배포 지역 — AC-6 검증용"
  value       = azurerm_resource_group.main.location
}

output "web_url" {
  description = "web 계층 공개 엔드포인트 — 유일한 외부 접근 지점"
  value       = "https://${azurerm_linux_web_app.web.default_hostname}"
}

output "api_private_ip" {
  description = "api 내부 로드밸런서 사설 IP — 공개 IP 없음을 확인하는 용도"
  value       = azurerm_lb.api.private_ip_address
}

output "db_fqdn" {
  description = "Azure SQL 서버 FQDN. 프라이빗 엔드포인트로만 해석된다"
  value       = azurerm_mssql_server.db.fully_qualified_domain_name
}

output "subnet_cidrs" {
  description = "계층별 서브넷 CIDR — AC-11 중첩 검사용"
  value = {
    web = azurerm_subnet.web.address_prefixes
    api = azurerm_subnet.api.address_prefixes
    db  = azurerm_subnet.db.address_prefixes
  }
}

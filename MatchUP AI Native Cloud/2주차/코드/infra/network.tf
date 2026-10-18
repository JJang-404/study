# 네트워크 계층 — VNet, 서브넷 3개, NSG 3개와 그 연결
# 설계 의도: web → api → db 단방향 인접 통신만 허용 (REQ-CMN-2, REQ-CMN-3)

# 모든 리소스를 담는 리소스 그룹
resource "azurerm_resource_group" "main" {
  name     = "${var.prefix}-rg"
  location = var.location
  tags     = var.tags
}

# 플랫폼 전체를 감싸는 단일 VNet (AC-10)
resource "azurerm_virtual_network" "main" {
  name                = "${var.prefix}-vnet"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = [var.vnet_cidr]
  tags                = var.tags
}

# ---------------------------------------------------------------------------
# 서브넷 — 계층마다 하나씩, 주소 범위는 서로 겹치지 않는다 (AC-10, AC-11)
# ---------------------------------------------------------------------------

# web 서브넷: App Service를 VNet에 통합하기 위한 위임(delegation) 필요
resource "azurerm_subnet" "web" {
  name                 = "${var.prefix}-snet-web"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.subnet_cidrs.web]

  # App Service(서버팜)가 이 서브넷을 전용으로 쓰도록 위임한다
  delegation {
    name = "appservice-delegation"
    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

# api 서브넷: VM Scale Set이 배치된다
resource "azurerm_subnet" "api" {
  name                 = "${var.prefix}-snet-api"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.subnet_cidrs.api]
}

# db 서브넷: Azure SQL 프라이빗 엔드포인트가 배치된다
resource "azurerm_subnet" "db" {
  name                 = "${var.prefix}-snet-db"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.subnet_cidrs.db]

  # 프라이빗 엔드포인트가 네트워크 정책에 막히지 않도록 해제한다
  private_endpoint_network_policies = "Disabled"
}

# ---------------------------------------------------------------------------
# NSG — 계층별 인바운드 통제 (AC-12, AC-13, AC-14)
# 규칙 우선순위는 숫자가 작을수록 먼저 평가된다.
# ---------------------------------------------------------------------------

# web NSG: 인터넷에서 오는 HTTP/HTTPS만 허용 (AC-4)
resource "azurerm_network_security_group" "web" {
  name                = "${var.prefix}-nsg-web"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags

  security_rule {
    name                       = "allow-https-from-internet"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = ["80", "443"]
    source_address_prefix      = "Internet"
    destination_address_prefix = var.subnet_cidrs.web
  }

  # 위 규칙에 해당하지 않는 인바운드는 전부 차단한다
  security_rule {
    name                       = "deny-all-inbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# api NSG: web 서브넷에서 오는 트래픽만 허용. 인터넷 직접 접근 차단 (AC-5, AC-13)
resource "azurerm_network_security_group" "api" {
  name                = "${var.prefix}-nsg-api"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags

  security_rule {
    name                       = "allow-http-from-web-subnet"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8080"
    source_address_prefix      = var.subnet_cidrs.web # web 서브넷에서만
    destination_address_prefix = var.subnet_cidrs.api
  }

  # 인터넷 → api 직접 접근을 명시적으로 차단한다 (deny-all보다 먼저 평가)
  security_rule {
    name                       = "deny-internet-inbound"
    priority                   = 200
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "deny-all-inbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# db NSG: api 서브넷에서 오는 1433(SQL) 포트만 허용 (AC-5, AC-14)
resource "azurerm_network_security_group" "db" {
  name                = "${var.prefix}-nsg-db"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags

  security_rule {
    name                       = "allow-sql-from-api-subnet"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "1433" # SQL Server 전용 포트만
    source_address_prefix      = var.subnet_cidrs.api
    destination_address_prefix = var.subnet_cidrs.db
  }

  # web 계층이 db에 직접 접근하는 경로를 명시적으로 차단한다 (REQ-CMN-2 핵심 제약)
  security_rule {
    name                       = "deny-web-subnet-inbound"
    priority                   = 200
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = var.subnet_cidrs.web
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "deny-all-inbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# ---------------------------------------------------------------------------
# NSG ↔ 서브넷 연결 — 선언만으로는 적용되지 않으므로 반드시 연결한다 (AC-12)
# ---------------------------------------------------------------------------

resource "azurerm_subnet_network_security_group_association" "web" {
  subnet_id                 = azurerm_subnet.web.id
  network_security_group_id = azurerm_network_security_group.web.id
}

resource "azurerm_subnet_network_security_group_association" "api" {
  subnet_id                 = azurerm_subnet.api.id
  network_security_group_id = azurerm_network_security_group.api.id
}

resource "azurerm_subnet_network_security_group_association" "db" {
  subnet_id                 = azurerm_subnet.db.id
  network_security_group_id = azurerm_network_security_group.db.id
}

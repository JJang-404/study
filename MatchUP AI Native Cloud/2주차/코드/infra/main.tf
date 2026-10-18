# 3계층 워크로드 — web(App Service) · api(VM Scale Set) · db(Azure SQL)
# 각 계층은 network.tf가 만든 전용 서브넷에 배치된다.

# ---------------------------------------------------------------------------
# web 계층 — App Service (AC-7)
# 유일하게 외부에 노출되는 계층이다.
# ---------------------------------------------------------------------------

# App Service를 올릴 호스팅 플랜. VNet 통합을 위해 Standard 이상이 필요하다.
resource "azurerm_service_plan" "web" {
  name                = "${var.prefix}-plan-web"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = "S1"
  tags                = var.tags
}

resource "azurerm_linux_web_app" "web" {
  name                = "${var.prefix}-app-web"
  location            = azurerm_service_plan.web.location
  resource_group_name = azurerm_resource_group.main.name
  service_plan_id     = azurerm_service_plan.web.id
  tags                = var.tags

  # web 서브넷에 통합해 api 계층과 사설 통신한다
  virtual_network_subnet_id = azurerm_subnet.web.id

  site_config {
    always_on     = true
    http2_enabled = true

    application_stack {
      node_version = "20-lts"
    }
  }

  # 평문 HTTP 접속을 막는다
  https_only = true

  app_settings = {
    # api 계층 내부 주소. web은 이 경로로만 백엔드에 접근한다
    API_BASE_URL = "http://${azurerm_lb.api.private_ip_address}:8080"
  }
}

# ---------------------------------------------------------------------------
# api 계층 — VM Scale Set (AC-8)
# 외부 공개 IP 없이 내부 로드밸런서 뒤에 배치한다 (AC-5).
# ---------------------------------------------------------------------------

# 내부 전용 로드밸런서 — 공개 IP를 붙이지 않는 것이 핵심이다
resource "azurerm_lb" "api" {
  name                = "${var.prefix}-lb-api"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"
  tags                = var.tags

  frontend_ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.api.id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_lb_backend_address_pool" "api" {
  name            = "${var.prefix}-pool-api"
  loadbalancer_id = azurerm_lb.api.id
}

resource "azurerm_lb_probe" "api" {
  name            = "health-8080"
  loadbalancer_id = azurerm_lb.api.id
  protocol        = "Tcp"
  port            = 8080
}

resource "azurerm_lb_rule" "api" {
  name                           = "http-8080"
  loadbalancer_id                = azurerm_lb.api.id
  protocol                       = "Tcp"
  frontend_port                  = 8080
  backend_port                   = 8080
  frontend_ip_configuration_name = "internal"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.api.id]
  probe_id                       = azurerm_lb_probe.api.id
}

resource "azurerm_linux_virtual_machine_scale_set" "api" {
  name                = "${var.prefix}-vmss-api"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.api_vm_size
  instances           = var.api_instance_count
  admin_username      = var.admin_username
  tags                = var.tags

  # 암호 인증을 끄고 SSH 키만 허용한다
  disable_password_authentication = true

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  os_disk {
    storage_account_type = "Standard_LRS"
    caching              = "ReadWrite"
  }

  network_interface {
    name    = "${var.prefix}-nic-api"
    primary = true

    ip_configuration {
      name      = "internal"
      primary   = true
      subnet_id = azurerm_subnet.api.id

      # public_ip_address 블록을 두지 않는다 → 외부 진입 경로 없음 (AC-5)
      load_balancer_backend_address_pool_ids = [azurerm_lb_backend_address_pool.api.id]
    }
  }
}

# ---------------------------------------------------------------------------
# db 계층 — Azure SQL Database (AC-9)
# 공개 엔드포인트를 끄고 프라이빗 엔드포인트로만 접근한다 (AC-5).
# ---------------------------------------------------------------------------

resource "azurerm_mssql_server" "db" {
  name                         = "${var.prefix}-sqlsrv"
  location                     = azurerm_resource_group.main.location
  resource_group_name          = azurerm_resource_group.main.name
  version                      = "12.0"
  administrator_login          = var.sql_admin_username
  administrator_login_password = var.sql_admin_password
  minimum_tls_version          = "1.2"
  tags                         = var.tags

  # 인터넷에서 직접 접근하는 경로를 차단한다
  public_network_access_enabled = false
}

resource "azurerm_mssql_database" "db" {
  name      = "${var.prefix}-sqldb-events"
  server_id = azurerm_mssql_server.db.id
  sku_name  = "S0"
  collation = "SQL_Latin1_General_CP1_CI_AS"
  tags      = var.tags
}

# db 서브넷 안에 사설 IP를 만들어 api 계층에서만 도달하게 한다
resource "azurerm_private_endpoint" "db" {
  name                = "${var.prefix}-pe-db"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = azurerm_subnet.db.id
  tags                = var.tags

  private_service_connection {
    name                           = "${var.prefix}-psc-db"
    private_connection_resource_id = azurerm_mssql_server.db.id
    subresource_names              = ["sqlServer"]
    is_manual_connection           = false
  }
}

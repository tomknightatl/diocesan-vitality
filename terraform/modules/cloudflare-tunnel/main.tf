terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.20"
    }
  }
}

# Use existing Cloudflare tunnel instead of creating a new one
# The tunnel should already exist with name "do-nyc2-${var.cluster_name}"
data "cloudflare_zero_trust_tunnel_cloudflared" "diocesan_vitality" {
  account_id = var.cloudflare_account_id
  name       = "do-nyc2-${var.cluster_name}"
}

# Configure zone SSL/TLS settings for proper tunnel operation
resource "cloudflare_zone_settings_override" "diocesan_vitality_ssl" {
  zone_id = var.cloudflare_zone_id
  settings {
    ssl                      = "flexible"  # Cloudflare handles SSL, backend is HTTP
    always_use_https         = "on"        # Force HTTPS redirect
    automatic_https_rewrites = "on"        # Rewrite HTTP links to HTTPS
    tls_1_3                  = "on"        # Enable TLS 1.3
    min_tls_version          = "1.2"       # Minimum TLS version
  }
}

# DNS records for the tunnel - these will appear as Public Hostnames in Cloudflare dashboard
resource "cloudflare_record" "ui" {
  count   = var.create_ui_record ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = var.ui_subdomain
  content = "${data.cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality.id}.cfargotunnel.com"
  type    = "CNAME"
  proxied = true

  comment = "Managed by Terraform - ${var.environment} UI"
}

resource "cloudflare_record" "api" {
  count   = var.create_api_record ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = var.api_subdomain
  content = "${data.cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality.id}.cfargotunnel.com"
  type    = "CNAME"
  proxied = true

  comment = "Managed by Terraform - ${var.environment} API"
}

resource "cloudflare_record" "argocd" {
  count   = var.create_argocd_record ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = var.argocd_subdomain
  content = "${data.cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality.id}.cfargotunnel.com"
  type    = "CNAME"
  proxied = true

  comment = "Managed by Terraform - ${var.environment} ArgoCD"
}

# Tunnel configuration (commented out since we're using existing tunnel configuration)
# We don't manage the tunnel configuration via Terraform since it's already configured in Kubernetes
# The ingress rules are managed via the Kubernetes configmap in the cloudflare-tunnel namespace

# Note: Tunnel credentials are managed separately via sealed secrets in Kubernetes
# The tunnel tokens are created manually and stored as sealed secrets in the cluster
# This Terraform module only manages the DNS records pointing to existing tunnels

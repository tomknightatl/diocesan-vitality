terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.20"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.4"
    }
  }
}

# Generate a random tunnel secret
resource "random_password" "tunnel_secret" {
  length  = 32
  special = true
}

# Create the Cloudflare tunnel
resource "cloudflare_zero_trust_tunnel_cloudflared" "diocesan_vitality" {
  account_id = var.cloudflare_account_id
  name       = "${var.environment}-${var.cluster_name}"
  secret     = base64encode(random_password.tunnel_secret.result)
}

# DNS records for the tunnel
resource "cloudflare_record" "ui" {
  count   = var.create_ui_record ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = var.ui_subdomain
  value   = "${cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality.id}.cfargotunnel.com"
  type    = "CNAME"
  proxied = true

  comment = "Managed by Terraform - ${var.environment} UI"
}

resource "cloudflare_record" "api" {
  count   = var.create_api_record ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = var.api_subdomain
  value   = "${cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality.id}.cfargotunnel.com"
  type    = "CNAME"
  proxied = true

  comment = "Managed by Terraform - ${var.environment} API"
}

resource "cloudflare_record" "argocd" {
  count   = var.create_argocd_record ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = var.argocd_subdomain
  value   = "${cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality.id}.cfargotunnel.com"
  type    = "CNAME"
  proxied = true

  comment = "Managed by Terraform - ${var.environment} ArgoCD"
}

# Tunnel configuration
resource "cloudflare_tunnel_config" "diocesan_vitality" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality.id

  config {
    dynamic "ingress_rule" {
      for_each = var.create_ui_record ? [1] : []
      content {
        hostname = "${var.ui_subdomain}.${var.domain_name}"
        service  = "http://diocesan-vitality-ui.default.svc.cluster.local:80"
        origin_request {
          http_host_header = "${var.ui_subdomain}.${var.domain_name}"
        }
      }
    }

    dynamic "ingress_rule" {
      for_each = var.create_api_record ? [1] : []
      content {
        hostname = "${var.api_subdomain}.${var.domain_name}"
        service  = "http://diocesan-vitality-api.default.svc.cluster.local:8000"
        origin_request {
          http_host_header = "${var.api_subdomain}.${var.domain_name}"
        }
      }
    }

    dynamic "ingress_rule" {
      for_each = var.create_argocd_record ? [1] : []
      content {
        hostname = "${var.argocd_subdomain}.${var.domain_name}"
        service  = "https://argocd-server.argocd.svc.cluster.local:443"
        origin_request {
          http_host_header = "${var.argocd_subdomain}.${var.domain_name}"
          no_tls_verify    = true
        }
      }
    }

    # Catch-all rule
    ingress_rule {
      service = "http_status:404"
    }
  }
}

# Generate Kubernetes secret manifest for the tunnel credentials
locals {
  tunnel_credentials = jsonencode({
    "AccountTag"   = var.cloudflare_account_id
    "TunnelSecret" = random_password.tunnel_secret.result
    "TunnelID"     = cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality.id
  })

  k8s_secret_manifest = yamlencode({
    apiVersion = "v1"
    kind       = "Secret"
    metadata = {
      name      = "cloudflare-tunnel-credentials"
      namespace = "cloudflare-tunnel"
    }
    type = "Opaque"
    data = {
      "credentials.json" = base64encode(local.tunnel_credentials)
    }
  })
}

# Write the secret manifest to a file for manual application or CI/CD
resource "local_file" "tunnel_secret" {
  count    = var.write_k8s_secret ? 1 : 0
  content  = local.k8s_secret_manifest
  filename = "${path.root}/k8s-secrets/cloudflare-tunnel-${var.environment}.yaml"

  depends_on = [cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality]
}

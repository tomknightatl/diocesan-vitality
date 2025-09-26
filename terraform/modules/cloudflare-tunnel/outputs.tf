output "tunnel_id" {
  description = "ID of the existing Cloudflare tunnel"
  value       = data.cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality.id
}

output "tunnel_name" {
  description = "Name of the existing Cloudflare tunnel"
  value       = data.cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality.name
}

output "tunnel_cname" {
  description = "CNAME target for the tunnel"
  value       = "${data.cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality.id}.cfargotunnel.com"
}

output "ui_hostname" {
  description = "Full hostname for the UI service"
  value       = var.create_ui_record ? "${var.ui_subdomain}.${var.domain_name}" : null
}

output "api_hostname" {
  description = "Full hostname for the API service"
  value       = var.create_api_record ? "${var.api_subdomain}.${var.domain_name}" : null
}

output "argocd_hostname" {
  description = "Full hostname for ArgoCD"
  value       = var.create_argocd_record ? "${var.argocd_subdomain}.${var.domain_name}" : null
}

# Note: Tunnel credentials are managed separately via sealed secrets in Kubernetes
# No longer outputting tunnel credentials since we use existing tunnels

output "dns_records" {
  description = "Information about created DNS records (which appear as Public Hostnames)"
  value = {
    ui = var.create_ui_record ? {
      hostname = cloudflare_record.ui[0].hostname
      content  = cloudflare_record.ui[0].content
      comment  = cloudflare_record.ui[0].comment
    } : null
    api = var.create_api_record ? {
      hostname = cloudflare_record.api[0].hostname
      content  = cloudflare_record.api[0].content
      comment  = cloudflare_record.api[0].comment
    } : null
    argocd = var.create_argocd_record ? {
      hostname = cloudflare_record.argocd[0].hostname
      content  = cloudflare_record.argocd[0].content
      comment  = cloudflare_record.argocd[0].comment
    } : null
  }
}

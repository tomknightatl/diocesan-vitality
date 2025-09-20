output "tunnel_id" {
  description = "ID of the created Cloudflare tunnel"
  value       = cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality.id
}

output "tunnel_name" {
  description = "Name of the created Cloudflare tunnel"
  value       = cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality.name
}

output "tunnel_cname" {
  description = "CNAME target for the tunnel"
  value       = "${cloudflare_zero_trust_tunnel_cloudflared.diocesan_vitality.id}.cfargotunnel.com"
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

output "tunnel_credentials" {
  description = "Tunnel credentials for Kubernetes secret"
  value       = local.tunnel_credentials
  sensitive   = true
}

output "k8s_secret_file" {
  description = "Path to the generated Kubernetes secret file"
  value       = var.write_k8s_secret ? local_file.tunnel_secret[0].filename : null
}

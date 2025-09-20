variable "cloudflare_account_id" {
  description = "Cloudflare account ID"
  type        = string
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID for the domain"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
}

variable "domain_name" {
  description = "Base domain name (e.g., diocesan-vitality.org)"
  type        = string
  default     = "diocesan-vitality.org"
}

variable "ui_subdomain" {
  description = "Subdomain for the UI service"
  type        = string
}

variable "api_subdomain" {
  description = "Subdomain for the API service"
  type        = string
}

variable "argocd_subdomain" {
  description = "Subdomain for ArgoCD"
  type        = string
}

variable "create_ui_record" {
  description = "Whether to create DNS record for UI"
  type        = bool
  default     = true
}

variable "create_api_record" {
  description = "Whether to create DNS record for API"
  type        = bool
  default     = true
}

variable "create_argocd_record" {
  description = "Whether to create DNS record for ArgoCD"
  type        = bool
  default     = true
}

variable "write_k8s_secret" {
  description = "Whether to write Kubernetes secret manifest to file"
  type        = bool
  default     = true
}

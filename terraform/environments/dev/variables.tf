variable "kubernetes_version" {
  description = "Kubernetes version for the development cluster"
  type        = string
  default     = "1.28.2-do.0"
}

variable "cloudflare_account_id" {
  description = "Cloudflare account ID"
  type        = string
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID for diocesan-vitality.org"
  type        = string
}

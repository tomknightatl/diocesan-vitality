variable "kubernetes_version" {
  description = "Kubernetes version for the development cluster"
  type        = string
  default     = "1.31.9-do.3"
}

variable "cloudflare_account_id" {
  description = "Cloudflare account ID"
  type        = string
  default     = null
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID for diocesanvitality.org"
  type        = string
  default     = null
}

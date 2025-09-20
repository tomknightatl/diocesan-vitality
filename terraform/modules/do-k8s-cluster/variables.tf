variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
}

variable "region" {
  description = "DigitalOcean region for the cluster"
  type        = string
  default     = "nyc2"
}

variable "kubernetes_version" {
  description = "Kubernetes version for the cluster"
  type        = string
  default     = "1.28.2-do.0"
}

variable "node_size" {
  description = "Size of the worker nodes"
  type        = string
  default     = "s-2vcpu-2gb"
}

variable "node_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 2
}

variable "auto_scale" {
  description = "Enable auto-scaling for the node pool"
  type        = bool
  default     = true
}

variable "min_nodes" {
  description = "Minimum number of nodes when auto-scaling"
  type        = number
  default     = 1
}

variable "max_nodes" {
  description = "Maximum number of nodes when auto-scaling"
  type        = number
  default     = 5
}

variable "cluster_tags" {
  description = "Tags to apply to the cluster"
  type        = list(string)
  default     = ["diocesan-vitality", "kubernetes"]
}

variable "node_tags" {
  description = "Tags to apply to the worker nodes"
  type        = list(string)
  default     = ["diocesan-vitality", "worker-node"]
}

variable "write_kubeconfig" {
  description = "Whether to write kubeconfig file locally"
  type        = bool
  default     = true
}

variable "add_kubectl_context" {
  description = "Whether to add kubectl context to local machine"
  type        = bool
  default     = true
}

variable "kubectl_context_name" {
  description = "Name for the kubectl context (defaults to cluster_name if empty)"
  type        = string
  default     = ""
}

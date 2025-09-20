output "cluster_id" {
  description = "ID of the created cluster"
  value       = digitalocean_kubernetes_cluster.cluster.id
}

output "cluster_name" {
  description = "Name of the created cluster"
  value       = digitalocean_kubernetes_cluster.cluster.name
}

output "cluster_endpoint" {
  description = "Kubernetes API server endpoint"
  value       = digitalocean_kubernetes_cluster.cluster.endpoint
}

output "cluster_status" {
  description = "Status of the cluster"
  value       = digitalocean_kubernetes_cluster.cluster.status
}

output "cluster_version" {
  description = "Kubernetes version of the cluster"
  value       = digitalocean_kubernetes_cluster.cluster.version
}

output "node_pool_id" {
  description = "ID of the default node pool"
  value       = digitalocean_kubernetes_cluster.cluster.node_pool[0].id
}

output "kubeconfig_raw" {
  description = "Raw kubeconfig for the cluster"
  value       = digitalocean_kubernetes_cluster.cluster.kube_config[0].raw_config
  sensitive   = true
}

output "kubeconfig_file_path" {
  description = "Path to the generated kubeconfig file"
  value       = var.write_kubeconfig ? local_file.kubeconfig[0].filename : null
}

output "cluster_ca_certificate" {
  description = "Base64 encoded cluster CA certificate"
  value       = digitalocean_kubernetes_cluster.cluster.kube_config[0].cluster_ca_certificate
  sensitive   = true
}

output "cluster_token" {
  description = "Kubernetes authentication token"
  value       = digitalocean_kubernetes_cluster.cluster.kube_config[0].token
  sensitive   = true
}

output "kubectl_context_name" {
  description = "Name of the kubectl context"
  value       = var.add_kubectl_context ? (var.kubectl_context_name != "" ? var.kubectl_context_name : var.cluster_name) : null
}

output "kubectl_context_added" {
  description = "Whether kubectl context was added to local machine"
  value       = var.add_kubectl_context
}

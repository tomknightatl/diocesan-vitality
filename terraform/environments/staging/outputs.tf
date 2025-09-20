output "cluster_info" {
  description = "Staging cluster information"
  value = {
    id       = module.k8s_cluster.cluster_id
    name     = module.k8s_cluster.cluster_name
    endpoint = module.k8s_cluster.cluster_endpoint
    status   = module.k8s_cluster.cluster_status
    version  = module.k8s_cluster.cluster_version
  }
}

output "kubeconfig_path" {
  description = "Path to the kubeconfig file"
  value       = module.k8s_cluster.kubeconfig_file_path
}

output "tunnel_info" {
  description = "Cloudflare tunnel information"
  value = {
    id    = module.cloudflare_tunnel.tunnel_id
    name  = module.cloudflare_tunnel.tunnel_name
    cname = module.cloudflare_tunnel.tunnel_cname
  }
}

output "hostnames" {
  description = "Service hostnames"
  value = {
    ui     = module.cloudflare_tunnel.ui_hostname
    api    = module.cloudflare_tunnel.api_hostname
    argocd = module.cloudflare_tunnel.argocd_hostname
  }
}

output "kubectl_context" {
  description = "Kubectl context information"
  value = {
    name       = module.k8s_cluster.kubectl_context_name
    added      = module.k8s_cluster.kubectl_context_added
    switch_cmd = "kubectl config use-context ${module.k8s_cluster.kubectl_context_name}"
  }
}

output "next_steps" {
  description = "Next steps after infrastructure creation"
  value = [
    "1. Switch kubectl context: kubectl config use-context ${module.k8s_cluster.kubectl_context_name}",
    "2. Apply tunnel secret: kubectl apply -f ${module.cloudflare_tunnel.k8s_secret_file}",
    "3. Install ArgoCD: kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml",
    "4. Apply ArgoCD ApplicationSets from k8s/argocd/",
    "5. Access ArgoCD at: https://${module.cloudflare_tunnel.argocd_hostname}"
  ]
}

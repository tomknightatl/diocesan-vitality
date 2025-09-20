terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.34"
    }
  }
}

resource "digitalocean_kubernetes_cluster" "cluster" {
  name    = var.cluster_name
  region  = var.region
  version = var.kubernetes_version

  node_pool {
    name       = "${var.cluster_name}-default-pool"
    size       = var.node_size
    node_count = var.node_count
    auto_scale = var.auto_scale
    min_nodes  = var.min_nodes
    max_nodes  = var.max_nodes
    tags       = var.node_tags
  }

  tags = var.cluster_tags

  # Ensure cluster is fully provisioned before proceeding
  timeouts {
    create = "30m"
  }
}

# Create kubeconfig file
resource "local_file" "kubeconfig" {
  count    = var.write_kubeconfig ? 1 : 0
  content  = digitalocean_kubernetes_cluster.cluster.kube_config[0].raw_config
  filename = "${path.root}/kubeconfig-${var.cluster_name}"

  depends_on = [digitalocean_kubernetes_cluster.cluster]
}

# Output cluster endpoint for ArgoCD configuration
data "digitalocean_kubernetes_cluster" "cluster_data" {
  name       = digitalocean_kubernetes_cluster.cluster.name
  depends_on = [digitalocean_kubernetes_cluster.cluster]
}

terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.34"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
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

# Add kubectl context to local machine
resource "null_resource" "add_kubectl_context" {
  count = var.add_kubectl_context ? 1 : 0

  triggers = {
    cluster_id   = digitalocean_kubernetes_cluster.cluster.id
    cluster_name = digitalocean_kubernetes_cluster.cluster.name
    context_name = var.kubectl_context_name != "" ? var.kubectl_context_name : var.cluster_name
  }

  # Create a temporary kubeconfig for merging
  provisioner "local-exec" {
    command = <<-EOT
      # Create a temporary kubeconfig file with renamed context
      TEMP_KUBECONFIG=$(mktemp)
      cat > "$TEMP_KUBECONFIG" << 'EOF'
${digitalocean_kubernetes_cluster.cluster.kube_config[0].raw_config}
EOF

      # Rename the context in the temporary kubeconfig
      ORIGINAL_CONTEXT=$(kubectl --kubeconfig="$TEMP_KUBECONFIG" config current-context)
      kubectl --kubeconfig="$TEMP_KUBECONFIG" config rename-context "$ORIGINAL_CONTEXT" "${self.triggers.context_name}"

      # Backup existing kubeconfig
      if [[ -f ~/.kube/config ]]; then
        cp ~/.kube/config ~/.kube/config.backup.$(date +%Y%m%d_%H%M%S)
      fi

      # Merge the new context into the default kubeconfig
      KUBECONFIG=~/.kube/config:"$TEMP_KUBECONFIG" kubectl config view --flatten > ~/.kube/config.tmp
      mv ~/.kube/config.tmp ~/.kube/config
      chmod 600 ~/.kube/config

      # Clean up temporary file
      rm "$TEMP_KUBECONFIG"

      echo "✅ Added kubectl context: ${self.triggers.context_name}"
      echo "🔄 Switch to context: kubectl config use-context ${self.triggers.context_name}"
    EOT
  }

  # Remove context when destroying
  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      if kubectl config get-contexts -o name | grep -q "^${self.triggers.context_name}$"; then
        # Switch to a different context if this is the current one
        CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || echo "")
        if [[ "$CURRENT_CONTEXT" == "${self.triggers.context_name}" ]]; then
          # Try to switch to another available context
          OTHER_CONTEXT=$(kubectl config get-contexts -o name | grep -v "^${self.triggers.context_name}$" | head -1)
          if [[ -n "$OTHER_CONTEXT" ]]; then
            kubectl config use-context "$OTHER_CONTEXT"
            echo "🔄 Switched to context: $OTHER_CONTEXT"
          fi
        fi

        # Delete the context
        kubectl config delete-context "${self.triggers.context_name}"
        echo "🗑️ Removed kubectl context: ${self.triggers.context_name}"
      fi
    EOT
  }

  depends_on = [digitalocean_kubernetes_cluster.cluster]
}

# Output cluster endpoint for ArgoCD configuration
data "digitalocean_kubernetes_cluster" "cluster_data" {
  name       = digitalocean_kubernetes_cluster.cluster.name
  depends_on = [digitalocean_kubernetes_cluster.cluster]
}

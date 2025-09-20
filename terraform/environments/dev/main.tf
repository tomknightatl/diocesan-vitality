terraform {
  required_version = ">= 1.0"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.34"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.20"
    }
  }

  backend "local" {
    path = "terraform-dev.tfstate"
  }
}

# Configure providers
provider "digitalocean" {
  # token is set via DIGITALOCEAN_TOKEN environment variable
}

provider "cloudflare" {
  # api_token is set via CLOUDFLARE_API_TOKEN environment variable
}

# Local values for the development environment
locals {
  environment  = "dev"
  cluster_name = "dv-dev"
  region       = "nyc3"

  # Domain configuration
  domain_name      = "diocesan-vitality.org"
  ui_subdomain     = "dev.ui"
  api_subdomain    = "dev.api"
  argocd_subdomain = "dev.argocd"

  # Cluster configuration
  node_size  = "s-2vcpu-2gb"
  node_count = 2
  min_nodes  = 1
  max_nodes  = 3

  # Tags
  common_tags = [
    "diocesan-vitality",
    "development",
    "terraform-managed"
  ]
}

# Create DigitalOcean Kubernetes cluster
module "k8s_cluster" {
  source = "../../modules/do-k8s-cluster"

  cluster_name       = local.cluster_name
  region             = local.region
  kubernetes_version = var.kubernetes_version

  node_size  = local.node_size
  node_count = local.node_count
  auto_scale = true
  min_nodes  = local.min_nodes
  max_nodes  = local.max_nodes

  cluster_tags     = local.common_tags
  node_tags        = concat(local.common_tags, ["worker-node"])
  write_kubeconfig = true
}

# Create Cloudflare tunnel and DNS records
module "cloudflare_tunnel" {
  source = "../../modules/cloudflare-tunnel"

  cloudflare_account_id = var.cloudflare_account_id
  cloudflare_zone_id    = var.cloudflare_zone_id

  environment  = local.environment
  cluster_name = local.cluster_name
  domain_name  = local.domain_name

  ui_subdomain     = local.ui_subdomain
  api_subdomain    = local.api_subdomain
  argocd_subdomain = local.argocd_subdomain

  create_ui_record     = true
  create_api_record    = true
  create_argocd_record = true
  write_k8s_secret     = true
}

# Create directories for generated files
resource "local_file" "create_secrets_dir" {
  content  = "# Directory for Kubernetes secrets\n"
  filename = "${path.root}/k8s-secrets/.gitkeep"
}

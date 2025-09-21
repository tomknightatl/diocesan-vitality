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
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }

  backend "local" {
    path = "terraform-staging.tfstate"
  }
}

# Configure providers
provider "digitalocean" {
  # token is set via DIGITALOCEAN_TOKEN environment variable
}

provider "cloudflare" {
  # api_token is set via CLOUDFLARE_API_TOKEN environment variable
}

provider "null" {
  # No configuration required
}

# Local values for the staging environment
locals {
  environment  = "staging"
  cluster_name = "dv-stg"
  region       = "nyc2"

  # Domain configuration
  domain_name      = "diocesanvitality.org"
  ui_subdomain     = "stg.ui"
  api_subdomain    = "stg.api"
  argocd_subdomain = "stg.argocd"

  # Cluster configuration (slightly larger for staging)
  node_size  = "s-2vcpu-4gb"
  node_count = 2
  min_nodes  = 2
  max_nodes  = 4

  # Tags
  common_tags = [
    "diocesan-vitality",
    "staging",
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

  cluster_tags         = local.common_tags
  node_tags            = concat(local.common_tags, ["worker-node"])
  write_kubeconfig     = true
  add_kubectl_context  = false
  kubectl_context_name = ""
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

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "The project ID for this HydroServer instance."
  type        = string
}

variable "region" {
  description = "The GCP region this HydroServer instance will be deployed in."
  type        = string
}

data "google_project" "current" {
  project_id = var.project_id
}


# ---------------------------------
# GCP Artifact Registry
# ---------------------------------

resource "google_artifact_registry_repository" "hydroserver" {
  repository_id = "hydroserver-demo"
  provider      = google
  project       = var.project_id
  location      = var.region
  format        = "DOCKER"
}

resource "null_resource" "ghcr_to_artifact_registry" {
  depends_on = [google_artifact_registry_repository.hydroserver]

  provisioner "local-exec" {
    command = <<EOT
      set -euo pipefail

      REGION="${var.region}"
      REPO="${var.region}-docker.pkg.dev/${var.project_id}/hydroserver-demo/hydroserver-api-services"
      GHCR_IMAGE="ghcr.io/hydroserver2/hydroserver-api-services:latest"

      # GCP Authentication
      gcloud auth configure-docker $REGION-docker.pkg.dev --quiet

      # Mirror HydroServer GHCR image to Artifact Registry
      docker pull --platform linux/amd64 $GHCR_IMAGE
      docker tag $GHCR_IMAGE $REPO:latest
      docker push $REPO:latest
    EOT
  }
}


# ---------------------------------
# Cloud SQL PostgreSQL Database
# ---------------------------------

resource "google_sql_database_instance" "hydroserver" {
  name                = "hydroserver-demo"
  database_version    = "POSTGRES_17"
  region              = var.region
  deletion_protection = false

  settings {
    tier = "db-f1-micro"
    edition = "ENTERPRISE"
    ip_configuration {
      ipv4_enabled = true
    }
  }
}

resource "google_sql_user" "hydroserver" {
  name     = local.database_admin_username
  instance = google_sql_database_instance.hydroserver.name
  password = local.database_admin_password

  lifecycle {
    ignore_changes = all
  }
}

resource "google_sql_database" "hydroserver" {
  name     = "hydroserver"
  instance = google_sql_database_instance.hydroserver.name

  lifecycle {
    ignore_changes = all
  }
}


# ---------------------------------
# GCP Cloud Run
# ---------------------------------

resource "google_cloud_run_v2_service" "hydroserver" {
  name                = "hydroserver-demo"
  location            = var.region
  deletion_protection = false

  template {
    containers {
      image   = "${var.region}-docker.pkg.dev/${var.project_id}/hydroserver-demo/hydroserver-api-services:latest"
      command = ["python", "manage.py", "run_demo"]

      resources {
        limits = {
          cpu    = "1"
          memory = "2Gi"
        }
      }

      ports {
        container_port = 8000
      }

      volume_mounts {
        name      = "cloudsql"
        mount_path = "/cloudsql"
      }

      env {
        name  = "USE_CLOUD_SQL_AUTH_PROXY"
        value = "true"
      }

      dynamic "env" {
        for_each = {
          PROXY_BASE_URL             = google_secret_manager_secret.proxy_base_url.id
          DATABASE_URL               = google_secret_manager_secret.database_url.id
          SECRET_KEY                 = google_secret_manager_secret.secret_key.id
          DEFAULT_SUPERUSER_EMAIL    = google_secret_manager_secret.admin_email.id
          DEFAULT_SUPERUSER_PASSWORD = google_secret_manager_secret.admin_password.id
        }
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
    }

    service_account = google_service_account.hydroserver_cloud_run_service_account.email

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.hydroserver.connection_name]
      }
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 1
    }
  }

  depends_on = [
    google_sql_database_instance.hydroserver,
    null_resource.ghcr_to_artifact_registry,
    google_secret_manager_secret_version.proxy_base_url_value,
    google_secret_manager_secret_version.database_url_value,
    google_secret_manager_secret_version.secret_key_value,
    google_secret_manager_secret_version.admin_email_value,
    google_secret_manager_secret_version.admin_password_value,
  ]
}

resource "google_service_account" "hydroserver_cloud_run_service_account" {
  account_id   = "hydroserver-demo"
  display_name = "HydroServer Cloud Run Demo Service Account"
  project      = data.google_project.current.project_id
}

resource "google_cloud_run_service_iam_member" "hydroserver_cloud_run_public_access" {
  location = google_cloud_run_v2_service.hydroserver.location
  service  = google_cloud_run_v2_service.hydroserver.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_project_iam_member" "hydroserver_cloud_run_sql_access" {
  project = data.google_project.current.project_id
  role   = "roles/cloudsql.client"
  member = "serviceAccount:${google_service_account.hydroserver_cloud_run_service_account.email}"
}

resource "google_secret_manager_secret_iam_member" "hydroserver_cloud_run_secret_access" {
  for_each = {
    "proxy_base_url" = google_secret_manager_secret.proxy_base_url.id
    "database_url"   = google_secret_manager_secret.database_url.id
    "secret_key"     = google_secret_manager_secret.secret_key.id
    "admin_email"    = google_secret_manager_secret.admin_email.id
    "admin_password" = google_secret_manager_secret.admin_password.id
  }
  project   = data.google_project.current.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.hydroserver_cloud_run_service_account.email}"
}

resource "google_project_iam_member" "cloud_run_invoker" {
  project = data.google_project.current.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.hydroserver_cloud_run_service_account.email}"
}


# ---------------------------------
# Environment Variables and Secrets
# ---------------------------------

resource "random_password" "admin_password" {
  length      = 20
  lower       = true
  min_lower   = 1
  upper       = true
  min_upper   = 1
  numeric     = true
  min_numeric = 1
  special     = true
  min_special = 1
  override_special = "!@#$%^&*()_+-=:;.,?/"
}

resource "random_password" "rds_password" {
  length           = 15
  upper            = true
  min_upper        = 1
  lower            = true
  min_lower        = 1
  numeric          = true
  min_numeric      = 1
  special          = true
  min_special      = 1
  override_special = "-_~*"
}

resource "random_password" "secret_key" {
  length           = 50
  special          = true
  upper            = true
  lower            = true
  numeric          = true
  override_special = "!@#$%^&*()-_=+{}[]|:;\"'<>,.?/"
}

locals {
  database_admin_username = "hsdbadmin"
  database_admin_password = "a${random_password.rds_password.result}"
  database_url            = "postgresql://${local.database_admin_username}:${local.database_admin_password}@/${google_sql_database.hydroserver.name}?host=/cloudsql/${google_sql_database_instance.hydroserver.connection_name}"
  proxy_base_url          = "https://hydroserver-demo-${data.google_project.current.number}.${var.region}.run.app"
}

resource "google_secret_manager_secret" "proxy_base_url" {
  secret_id = "hydroserver-demo-proxy-base-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "proxy_base_url_value" {
  secret      = google_secret_manager_secret.proxy_base_url.id
  secret_data = local.proxy_base_url
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "hydroserver-demo-database-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url_value" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = local.database_url
}

resource "google_secret_manager_secret" "secret_key" {
  secret_id = "hydroserver-demo-secret-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "secret_key_value" {
  secret      = google_secret_manager_secret.secret_key.id
  secret_data = random_password.secret_key.result
}

resource "google_secret_manager_secret" "admin_email" {
  secret_id = "hydroserver-demo-admin-email"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "admin_email_value" {
  secret      = google_secret_manager_secret.admin_email.id
  secret_data = "admin@hydroserver.org"
}

resource "google_secret_manager_secret" "admin_password" {
  secret_id = "hydroserver-demo-admin-password"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "admin_password_value" {
  secret      = google_secret_manager_secret.admin_password.id
  secret_data = random_password.admin_password.result
}


# ---------------------------------
# Instance Outputs
# ---------------------------------

output "database_url" {
  description = "The PostgreSQL connection string for the Cloud SQL instance"
  value       = local.database_url
  sensitive   = true
}

output "admin_username" {
  description = "The default HydroServer admin username"
  value       = "admin@hydroserver.org"
}

output "admin_password" {
  description = "The default HydroServer admin password"
  value       = random_password.admin_password.result
  sensitive   = true
}

output "service_url" {
  description = "The HydroServer Cloud Run service URL"
  value       = local.proxy_base_url
}

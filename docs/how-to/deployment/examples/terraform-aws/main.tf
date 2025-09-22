terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  description = "The AWS region this HydroServer instance will be deployed in."
  type        = string
}

data "aws_caller_identity" "current" {}


# ---------------------------------
# Networking
# ---------------------------------

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}


# ---------------------------------
# ECR Repository
# ---------------------------------

resource "aws_ecr_repository" "hydroserver" {
  name         = "hydroserver-demo"
  force_delete = true
}

resource "null_resource" "ghcr_to_ecr" {
  depends_on = [aws_ecr_repository.hydroserver]

  provisioner "local-exec" {
    command = <<EOT
      set -euo pipefail

      REGION="${var.region}"
      REPO="${aws_ecr_repository.hydroserver.repository_url}"
      GHCR_IMAGE="ghcr.io/hydroserver2/hydroserver-api-services:latest"

      # ECR Authentication
      aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $(echo $REPO | cut -d/ -f1)

      # Mirror HydroServer GHCR image to ECR
      docker pull --platform linux/amd64 $GHCR_IMAGE  # --platform linux/arm64
      docker tag $GHCR_IMAGE $REPO:latest
      docker push $REPO:latest
    EOT
  }
}


# ---------------------------------
# RDS PostgreSQL Database
# ---------------------------------

resource "aws_db_instance" "hydroserver" {
  identifier     = "hydroserver-demo"
  engine         = "postgres"
  engine_version = "17"
  instance_class = "db.t4g.micro"

  allocated_storage   = 20
  publicly_accessible = true
  skip_final_snapshot = true

  db_name  = "hydroserver"
  username = local.database_admin_username
  password = local.database_admin_password
  port     = "5432"

  vpc_security_group_ids = [aws_security_group.hydroserver_rds.id]
}

resource "aws_security_group" "hydroserver_rds" {
  name        = "hydroserver-rds-sg"
  description = "Allow App Runner to connect to RDS"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_security_group_rule" "hydroserver_rds_inbound" {
  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  security_group_id = aws_security_group.hydroserver_rds.id
  source_security_group_id = aws_security_group.hydroserver_apprunner.id
}


# ---------------------------------
# AWS App Runner
# ---------------------------------

resource "aws_apprunner_service" "hydroserver" {
  service_name = "hydroserver-demo"

  instance_configuration {
    cpu               = "1 vCPU"
    memory            = "2 GB"
    instance_role_arn = aws_iam_role.apprunner_instance_role.arn
  }

  source_configuration {
    image_repository {
      image_identifier      = "${aws_ecr_repository.hydroserver.repository_url}:latest"
      image_repository_type = "ECR"
      image_configuration {
        start_command = "python manage.py run_demo"
        port          = "8000"
        runtime_environment_secrets = {
          PROXY_BASE_URL             = aws_ssm_parameter.proxy_base_url.arn
          DATABASE_URL               = aws_ssm_parameter.database_url.arn
          SECRET_KEY                 = aws_ssm_parameter.secret_key.arn
          DEFAULT_SUPERUSER_EMAIL    = aws_ssm_parameter.admin_email.arn
          DEFAULT_SUPERUSER_PASSWORD = aws_ssm_parameter.admin_password.arn
        }
      }
    }

    auto_deployments_enabled = false

    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_access_role.arn
    }
  }

  network_configuration {
    egress_configuration {
      egress_type = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.hydroserver.arn
    }
    ingress_configuration {
      is_publicly_accessible = true
    }
  }

  health_check_configuration {
    protocol = "HTTP"
    path     = "/health-check"
  }

  depends_on = [
    aws_db_instance.hydroserver,
    null_resource.ghcr_to_ecr,
  ]
}

resource "aws_security_group" "hydroserver_apprunner" {
  vpc_id = data.aws_vpc.default.id
  name   = "hydroserver-demo-app-runner-sg"
}

resource "aws_security_group_rule" "hydroserver_apprunner_outbound" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.hydroserver_apprunner.id
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_apprunner_vpc_connector" "hydroserver" {
  vpc_connector_name = "hydroserver-demo-rds-connector"
  subnets            = data.aws_subnets.default.ids
  security_groups    = [aws_security_group.hydroserver_apprunner.id]
}

resource "null_resource" "update_proxy_base_url" {
  depends_on = [aws_apprunner_service.hydroserver]

  provisioner "local-exec" {
    command = <<EOT
      aws ssm put-parameter \
        --name ${aws_ssm_parameter.proxy_base_url.name} \
        --type String \
        --overwrite \
        --value "https://${aws_apprunner_service.hydroserver.service_url}"

      aws apprunner start-deployment \
        --service-arn ${aws_apprunner_service.hydroserver.arn}
    EOT
  }
}


# ---------------------------------
# IAM Roles
# ---------------------------------

resource "aws_iam_role" "apprunner_access_role" {
  name = "hydroserver-demo-apprunner-access-role"
  path = "/service-role/"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Action    = "sts:AssumeRole"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "app_runner_ecr_access" {
  role       = aws_iam_role.apprunner_access_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role" "apprunner_instance_role" {
  name = "hydroserver-demo-apprunner-instance-role"
  path = "/service-role/"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = { Service = "tasks.apprunner.amazonaws.com" }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "apprunner_ssm_access" {
  name = "hydroserver-demo-apprunner-ssm-access"
  role = aws_iam_role.apprunner_instance_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = [
          "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/hydroserver-demo/*"
        ]
      }
    ]
  })
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
  database_url            = "postgresql://${local.database_admin_username}:${local.database_admin_password}@${aws_db_instance.hydroserver.endpoint}/${aws_db_instance.hydroserver.db_name}"
}

resource "aws_ssm_parameter" "proxy_base_url" {
  name        = "/hydroserver-demo/proxy-base-url"
  type        = "String"
  value       = "https://www.example.com"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "database_url" {
  name        = "/hydroserver-demo/database-url"
  type        = "SecureString"
  value       = local.database_url

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "secret_key" {
  name        = "/hydroserver-demo/secret-key"
  type        = "SecureString"
  value       = random_password.secret_key.result

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "admin_email" {
  name        = "/hydroserver-demo/admin-email"
  type        = "SecureString"
  value       = "admin@hydroserver.org"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "admin_password" {
  name        = "/hydroserver-demo/admin-password"
  type        = "SecureString"
  value       = random_password.admin_password.result

  lifecycle {
    ignore_changes = [value]
  }
}


# ---------------------------------
# Instance Outputs
# ---------------------------------

output "database_url" {
  description = "The PostgreSQL connection string for the RDS instance"
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
  description = "The HydroServer App Runner service URL"
  value       = "https://${aws_apprunner_service.hydroserver.service_url}"
}

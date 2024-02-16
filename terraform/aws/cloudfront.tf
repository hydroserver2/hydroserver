# ------------------------------------------------ #
# HydroServer CloudFront Distribution              #
# ------------------------------------------------ #

resource "aws_cloudfront_distribution" "hydroserver_distribution" {
  origin {
    domain_name = aws_s3_bucket.hydroserver_web_bucket.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.hydroserver_oac.id
    origin_id   = "hydroserver-web"
  }

  origin {
    domain_name = aws_s3_bucket.hydroserver_static_bucket.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.hydroserver_oac.id
    origin_id   = "hydroserver-static"
  }

  origin {
    domain_name = aws_s3_bucket.hydroserver_storage_bucket.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.hydroserver_oac.id
    origin_id   = "hydroserver-storage"
  }

  origin {
    domain_name = aws_elastic_beanstalk_environment.hydroserver_django_env.endpoint_url
    origin_id   = "hydroserver-django"

    custom_origin_config {
      http_port = "80"
      https_port = "443"
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1", "TLSv1.1", "TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id = "hydroserver-web"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    function_association {
      event_type   = "viewer-request"
      function_arn   = aws_cloudfront_function.hydroserver_frontend_routing.arn
    }
  }

  ordered_cache_behavior {
    path_pattern     = "/api/sensorthings/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "hydroserver-django"
    viewer_protocol_policy = "allow-all"
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "hydroserver-django"
    viewer_protocol_policy = "redirect-to-https"
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  ordered_cache_behavior {
    path_pattern     = "/admin/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "hydroserver-django"
    viewer_protocol_policy = "redirect-to-https"
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations        = ["US", "CA"]
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  enabled             = true
  is_ipv6_enabled     = true
  web_acl_id          = aws_wafv2_web_acl.hydroserver_core_rules.arn
}

# ------------------------------------------------ #
# HydroServer CloudFront Access Controls           #
# ------------------------------------------------ #

resource "aws_cloudfront_function" "hydroserver_frontend_routing" {
  name    = "frontend-routing"
  runtime = "cloudfront-js-1.0"
  comment = "Preserve Vue client-side routing."
  code    = file("${path.module}/frontend-routing.js")
  publish = true
}

resource "aws_cloudfront_origin_access_identity" "hydroserver_oai" {}

resource "aws_cloudfront_origin_access_control" "hydroserver_oac" {
  name                              = "hydroserver-${var.instance}-oac"
  description                       = ""
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_wafv2_web_acl" "hydroserver_core_rules" {
  name        = "CoreRulesWebACL"
  scope       = "CLOUDFRONT"
  description = "WAF web ACL with Core Rules"

  default_action {
    allow {}
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "WAF_Common_Protections"
    sampled_requests_enabled   = true
  }

  rule {
    name     = "AWS-AWSManagedRulesCommonRuleSet"
    priority = 0
    override_action {
      none {
      }
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
        rule_action_override {
          action_to_use {
            allow {}
          }
          name = "SizeRestrictions_BODY"
        }
        rule_action_override {
          action_to_use {
            allow {}
          }
          name = "NoUserAgent_HEADER"
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled   = true
    }
  }
}



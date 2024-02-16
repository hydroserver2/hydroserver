# ------------------------------------------------ #
# HydroServer S3 Buckets                           #
# ------------------------------------------------ #

resource "aws_s3_bucket" "hydroserver_web_bucket" {
  bucket = "hydroserver-${var.instance}-web"
}

resource "aws_s3_bucket" "hydroserver_static_bucket" {
  bucket = "hydroserver-${var.instance}-static"
}

resource "aws_s3_bucket" "hydroserver_storage_bucket" {
  bucket = "hydroserver-${var.instance}-storage"
}

# ------------------------------------------------ #
# HydroServer S3 Restrict Public Access            #
# ------------------------------------------------ #

resource "aws_s3_bucket_public_access_block" "hydroserver_web_bucket" {
  bucket = aws_s3_bucket.hydroserver_web_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "hydroserver_static_bucket" {
  bucket = aws_s3_bucket.hydroserver_static_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "hydroserver_storage_bucket" {
  bucket = aws_s3_bucket.hydroserver_storage_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ------------------------------------------------ #
# HydroServer S3 Ownership Controls                #
# ------------------------------------------------ #

resource "aws_s3_bucket_ownership_controls" "hydroserver_web_bucket" {
  bucket = aws_s3_bucket.hydroserver_web_bucket.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
  depends_on = [aws_s3_bucket_public_access_block.hydroserver_web_bucket]
}

resource "aws_s3_bucket_ownership_controls" "hydroserver_static_bucket" {
  bucket = aws_s3_bucket.hydroserver_static_bucket.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
  depends_on = [aws_s3_bucket_public_access_block.hydroserver_static_bucket]
}

resource "aws_s3_bucket_ownership_controls" "hydroserver_storage_bucket" {
  bucket = aws_s3_bucket.hydroserver_storage_bucket.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
  depends_on = [aws_s3_bucket_public_access_block.hydroserver_storage_bucket]
}

# ------------------------------------------------ #
# HydroServer Website Configuration                #
# ------------------------------------------------ #

resource "aws_s3_object" "hydroserver_index_html" {
  bucket       = aws_s3_bucket.hydroserver_web_bucket.id
  key          = "index.html"
  source       = "index.html"
  content_type = "text/html"
}

# ------------------------------------------------ #
# HydroServer S3 Bucket Policies                   #
# ------------------------------------------------ #

resource "aws_s3_bucket_policy" "hydroserver_web_bucket" {
  bucket = aws_s3_bucket.hydroserver_web_bucket.id
  policy = jsonencode({
    Version = "2008-10-17"
    Id      = "PolicyForCloudFrontPrivateContent"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.hydroserver_web_bucket.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.hydroserver_distribution.arn
          }
        }
      }
    ]
  })

  depends_on = [
    aws_cloudfront_distribution.hydroserver_distribution,
    aws_s3_bucket_public_access_block.hydroserver_web_bucket
  ]
}

resource "aws_s3_bucket_policy" "hydroserver_static_bucket" {
  bucket = aws_s3_bucket.hydroserver_static_bucket.id
  policy = jsonencode({
    Version = "2008-10-17"
    Id      = "PolicyForCloudFrontPrivateContent"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.hydroserver_static_bucket.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.hydroserver_distribution.arn
          }
        }
      }
    ]
  })

  depends_on = [
    aws_cloudfront_distribution.hydroserver_distribution,
    aws_s3_bucket_public_access_block.hydroserver_static_bucket
  ]
}

resource "aws_s3_bucket_policy" "hydroserver_storage_bucket" {
  bucket = aws_s3_bucket.hydroserver_storage_bucket.id
  policy = jsonencode({
    Version = "2008-10-17"
    Id      = "PolicyForCloudFrontPrivateContent"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.hydroserver_storage_bucket.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.hydroserver_distribution.arn
          }
        }
      }
    ]
  })

  depends_on = [
    aws_cloudfront_distribution.hydroserver_distribution,
    aws_s3_bucket_public_access_block.hydroserver_storage_bucket
  ]
}
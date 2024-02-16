# ------------------------------------------------ #
# HydroServer Elastic Beanstalk Application        #
# ------------------------------------------------ #

resource "aws_elastic_beanstalk_application" "hydroserver_django_app" {
  name        = "hydroserver-${var.instance}"
  description = "HydroServer Django Application on Elastic Beanstalk"
}

# ------------------------------------------------ #
# HydroServer Elastic Beanstalk Environment        #
# ------------------------------------------------ #

resource "aws_elastic_beanstalk_environment" "hydroserver_django_env" {
  name                = "hydroserver-${var.instance}-env"
  application         = aws_elastic_beanstalk_application.hydroserver_django_app.name
  solution_stack_name = "64bit Amazon Linux 2 v3.5.11 running Python 3.8"

  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "EnvironmentType"
    value     = "LoadBalanced"
  }

  setting {
    namespace = "aws:autoscaling:asg"
    name      = "MaxSize"
    value     = "1"
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "IamInstanceProfile"
    value     = "aws-elasticbeanstalk-ec2-role"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "ADMIN_EMAIL"
    value     = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "ALLOWED_HOSTS"
    value     = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "AWS_ACCESS_KEY_ID"
    value     = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "AWS_SECRET_ACCESS_KEY"
    value     = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "AWS_STORAGE_BUCKET_NAME"
    value     = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "DATABASE_URL"
    value     = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "DEBUG"
    value     = "True"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "DEPLOYED"
    value     = "True"
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "OAUTH_GOOGLE_CLIENT"
    value     = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "OAUTH_GOOGLE_SECRET"
    value     = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "OAUTH_HYDROSHARE_CLIENT"
    value     = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "OAUTH_HYDROSHARE_SECRET"
    value     = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "OAUTH_ORCID_CLIENT"
    value     = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "OAUTH_ORCID_SECRET"
    value     = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "PROXY_BASE_URL"
    value     = ""
  }

  setting {
    namespace = "aws:elasticbeanstalk:application:environment"
    name      = "SECRET_KEY"
    value     = ""
  }
}
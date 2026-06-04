from django.db import models


class Organization(models.Model):
    code = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    link = models.URLField(max_length=2000, blank=True, null=True)
    organization_type = models.CharField(max_length=255)


class OrganizationType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    public = models.BooleanField(default=True)

    def __str__(self):
        return self.name

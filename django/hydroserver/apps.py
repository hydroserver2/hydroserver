from django.contrib.admin.apps import AdminConfig


class HydroServerAdminConfig(AdminConfig):
    default_site = "hydroserver.admin.HydroServerAdminSite"

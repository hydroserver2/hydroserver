from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from core.iam.models import Workspace
from core.sta.cache import invalidate_public_monitoring_site_markers_cache
from core.sta.models import MonitoringSite


@receiver(post_save, sender=MonitoringSite)
@receiver(post_save, sender=Workspace)
@receiver(post_delete, sender=MonitoringSite)
@receiver(post_delete, sender=Workspace)
def invalidate_public_monitoring_site_markers(*args, **kwargs) -> None:
    invalidate_public_monitoring_site_markers_cache()

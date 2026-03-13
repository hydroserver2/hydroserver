from django.db.models.signals import post_save
from django.dispatch import receiver
from domains.iam.models import Workspace
from domains.sta.cache import invalidate_public_thing_markers_cache
from domains.sta.models import Location, Thing


@receiver(post_save, sender=Thing)
@receiver(post_save, sender=Location)
@receiver(post_save, sender=Workspace)
def invalidate_public_thing_markers(*args, **kwargs) -> None:
    invalidate_public_thing_markers_cache()

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from core.iam.models import Workspace
from core.sta.cache import invalidate_public_thing_markers_cache
from core.sta.models import Location, Thing


@receiver(post_save, sender=Thing)
@receiver(post_save, sender=Location)
@receiver(post_save, sender=Workspace)
@receiver(post_delete, sender=Thing)
@receiver(post_delete, sender=Location)
@receiver(post_delete, sender=Workspace)
def invalidate_public_thing_markers(*args, **kwargs) -> None:
    invalidate_public_thing_markers_cache()

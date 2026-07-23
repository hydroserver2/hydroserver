from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import ServiceAccount, Workspace


@receiver(pre_delete, sender=Workspace)
def deactivate_workspace_service_accounts(sender, instance, **kwargs):
    ServiceAccount.objects.filter(workspace=instance).update(
        is_active=False, key_hash=""
    )

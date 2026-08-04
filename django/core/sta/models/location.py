import uuid

from django.db import models

from .thing import Thing


class Location(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    thing = models.ForeignKey(
        Thing, related_name="locations", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    description = models.TextField()
    encoding_type = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=22, decimal_places=16)
    longitude = models.DecimalField(max_digits=22, decimal_places=16)
    elevation_m = models.DecimalField(
        max_digits=22, decimal_places=16, null=True, blank=True
    )
    elevation_datum = models.CharField(max_length=255, null=True, blank=True)
    admin_area_1 = models.CharField(max_length=200, null=True, blank=True)
    admin_area_2 = models.CharField(max_length=200, null=True, blank=True)
    country = models.CharField(max_length=2, null=True, blank=True)

    def __str__(self):
        return f"{self.name} — {self.id}"

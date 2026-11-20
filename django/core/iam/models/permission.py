from django.db import models

from .role import Role

PERMISSION_CHOICES = [
    ("view", "view"),
    ("create", "create"),
    ("edit", "edit"),
    ("delete", "delete"),
]


class Permission(models.Model):
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="permissions"
    )
    resource_type = models.CharField(max_length=50)

    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["role", "resource_type"],
                name="unique_role_resource_type",
            ),
        ]

    def __str__(self):
        perms = [
            label for flag, label in [
                (self.can_view, "view"),
                (self.can_create, "create"),
                (self.can_edit, "edit"),
                (self.can_delete, "delete"),
            ] if flag
        ]
        perm_str = "all" if len(perms) == 4 else (", ".join(perms) or "none")

        return f"{self.role.name} / {self.resource_type} — {perm_str}"

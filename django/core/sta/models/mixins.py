from django.core.exceptions import ValidationError


class LinkedResourceMixin:
    """
    Shared clean() for linked-resource models that store either a hosted
    file or an external link (never both — enforced by each model's own
    file_xor_url CheckConstraint). Once created, the mode can't be switched;
    delete and re-create instead.
    """

    def clean(self):
        if self._state.adding:
            return

        original = type(self).objects.filter(pk=self.pk).first()
        if not original:
            return

        if original.file and self.url:
            raise ValidationError(
                "Cannot switch a linked resource from a hosted file to an "
                "external link — delete it and create a new one instead"
            )
        if original.url and self.file:
            raise ValidationError(
                "Cannot switch a linked resource from an external link to a "
                "hosted file — delete it and create a new one instead"
            )

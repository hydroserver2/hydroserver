from django.db import transaction
from django.http import HttpResponseRedirect
from django.core.management import call_command
from django.contrib import messages
from django.urls import reverse


class VocabularyAdmin:
    @transaction.atomic
    def load_fixtures(self, request, redirect, fixtures):
        try:
            for fixture in fixtures:
                call_command("loaddata", fixture)
            self.message_user(
                request, "Default data loaded successfully!", messages.SUCCESS
            )
        except Exception as e:
            self.message_user(request, f"Error loading data: {str(e)}", messages.ERROR)

        return HttpResponseRedirect(reverse(redirect))

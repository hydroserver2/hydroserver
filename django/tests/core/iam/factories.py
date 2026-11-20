import factory

from typing import TYPE_CHECKING
from factory.django import DjangoModelFactory

from allauth.account.models import EmailAddress

from core.iam.models import (
    Collaborator,
    Role,
    Permission,
    ServiceAccount,
    User,
    Workspace,
)


def name_slug(name):
    return "".join(char for char in name if char.isalpha()).lower()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> User: ...

    username = factory.LazyAttributeSequence(
        lambda obj, seq: f"{name_slug(obj.first_name)}-{name_slug(obj.last_name)}-{seq}"
    )
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    user_type = "Other"

    @factory.post_generation
    def password(user, create, extracted, **kwargs):
        user.set_password(extracted or "password")
        if create:
            user.save(update_fields=["password"])

    @factory.post_generation
    def email_address(user, create, extracted, **kwargs):
        if not create or extracted is False:
            return
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            primary=True,
            verified=kwargs.get("verified", True),
        )

    class Params:
        staff = factory.Trait(is_staff=True)
        superuser = factory.Trait(is_staff=True, is_superuser=True)
        inactive = factory.Trait(is_active=False)


class WorkspaceFactory(DjangoModelFactory):
    class Meta:
        model = Workspace

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> Workspace: ...

    name = factory.Faker("company")
    owner = factory.SubFactory(UserFactory)
    is_private = False

    class Params:
        private = factory.Trait(is_private=True)


class ServiceAccountFactory(DjangoModelFactory):
    class Meta:
        model = ServiceAccount

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> ServiceAccount: ...

    name = factory.Sequence(lambda seq: f"Service Account {seq}")
    workspace = factory.SubFactory(WorkspaceFactory)

    class Params:
        inactive = factory.Trait(is_active=False)


class RoleFactory(DjangoModelFactory):
    class Meta:
        model = Role

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> Role: ...

    name = factory.Sequence(lambda seq: f"Role {seq}")
    workspace = factory.SubFactory(WorkspaceFactory)

    class Params:
        global_role = factory.Trait(workspace=None)


class PermissionFactory(DjangoModelFactory):
    class Meta:
        model = Permission

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> Permission: ...

    role = factory.SubFactory(RoleFactory)
    resource_type = "Workspace"

    class Params:
        full_access = factory.Trait(
            can_view=True,
            can_create=True,
            can_edit=True,
            can_delete=True,
        )


class CollaboratorFactory(DjangoModelFactory):
    class Meta:
        model = Collaborator

    if TYPE_CHECKING:

        def __new__(cls, *args, **kwargs) -> Collaborator: ...

    workspace = factory.SubFactory(WorkspaceFactory)
    service_account = None
    user = factory.Maybe(
        "service_account",
        yes_declaration=None,
        no_declaration=factory.SubFactory(UserFactory),
    )
    role = factory.SubFactory(RoleFactory, global_role=True)

    class Params:
        service_account_collaborator = factory.Trait(
            user=None,
            service_account=factory.SubFactory(ServiceAccountFactory),
        )

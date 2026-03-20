from typing import Optional
from ninja.errors import HttpError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from interfaces.api.service import ServiceUtils
from domains.iam.models import Organization, UserType, OrganizationType
from interfaces.auth.schemas import AccountPostBody, AccountPatchBody

User = get_user_model()


class AccountService(ServiceUtils):
    @staticmethod
    def get(principal: User):
        return principal

    @staticmethod
    def create(data: AccountPostBody):
        try:
            user_body = data.dict(
                include=set(data.model_fields.keys()),
                exclude=["organization"],
                exclude_unset=True,
            )
            organization_body = (
                data.organization.dict(
                    include=set(data.organization.model_fields.keys()),
                    exclude_unset=True,
                )
                if data.organization
                else None
            )

            organization = (
                Organization.objects.create(**organization_body)
                if organization_body
                else None
            )
            user = User.objects.create(organization=organization, **user_body)

            return user

        except ValueError as e:
            raise HttpError(422, str(e))

    @staticmethod
    def update(principal: User, data: AccountPatchBody):
        try:
            user_body = data.dict(
                include=set(data.model_fields.keys()),
                exclude=["organization"],
                exclude_unset=True,
            )
            update_organization = "organization" in data.dict(
                include=["organization"],
                exclude_unset=True,
            )

            organization_body = (
                data.organization.dict(
                    include=set(data.organization.model_fields.keys()),
                    exclude_unset=True,
                )
                if data.organization
                else None
            )

            for field, value in user_body.items():
                setattr(principal, field, value)

            if update_organization:
                if organization_body:
                    if principal.organization:
                        for field, value in organization_body.items():
                            setattr(principal.organization, field, value)
                        principal.organization.save()
                    else:
                        principal.organization = Organization.objects.create(
                            **organization_body
                        )
                else:
                    if principal.organization:
                        principal.organization.delete()
                        principal.organization = None

        except ValueError as e:
            raise HttpError(422, str(e))

        principal.save()

        return principal

    @staticmethod
    def delete(principal: User):
        principal.delete()

        return "User account has been deleted"

    def list_user_types(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = UserType.objects.filter(public=True).order_by(
            f"{'-' if order_desc else ''}name"
        )
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)

    def list_organization_types(
        self,
        response: HttpResponse,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        order_desc: bool = False,
    ):
        queryset = OrganizationType.objects.filter(public=True).order_by(
            f"{'-' if order_desc else ''}name"
        )
        queryset, count = self.apply_pagination(queryset, response, page, page_size)

        return queryset.values_list("name", flat=True)

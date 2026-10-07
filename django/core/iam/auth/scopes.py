from dataclasses import dataclass
from typing import Literal, Optional

DATA_READ = "data:read"
DATA_WRITE = "data:write"
WORKSPACE_READ = "workspace:read"
WORKSPACE_WRITE = "workspace:write"
IAM_READ = "iam:read"
IAM_WRITE = "iam:write"
TASK_READ = "task:read"
TASK_WRITE = "task:write"
TASK_RUN = "task:run"


@dataclass(frozen=True)
class ScopeDefinition:
    """
    How an OIDC scope is described on the consent screen. A warning is shown
    beneath the scope's checkbox; "danger" marks scopes whose effects can
    outlive the app's authorization.
    """

    label: str
    warning: Optional[str] = None
    warning_level: Optional[Literal["caution", "danger"]] = None


SCOPES: dict[str, ScopeDefinition] = {
    DATA_READ: ScopeDefinition(
        "View your monitoring sites, datastreams, and observations",
    ),
    DATA_WRITE: ScopeDefinition(
        "Create, change, and delete your monitoring sites, datastreams, and observations",
    ),
    WORKSPACE_READ: ScopeDefinition(
        "See your workspaces, including owner and pending transfer details",
    ),
    WORKSPACE_WRITE: ScopeDefinition(
        "Create, rename, and delete workspaces, and change their privacy",
    ),
    IAM_READ: ScopeDefinition(
        "See who can access your workspaces: collaborators, roles, and service accounts",
    ),
    IAM_WRITE: ScopeDefinition(
        "Manage access to your workspaces: collaborators, service accounts, and ownership "
        "transfers",
        warning=(
            "This app will be able to add collaborators, create service accounts, and "
            "transfer ownership of your workspaces. Service accounts it creates keep "
            "working after you revoke this app unless you delete them."
        ),
        warning_level="danger",
    ),
    TASK_READ: ScopeDefinition(
        "View your data loading, monitoring, and data product tasks, their settings, and "
        "run history",
    ),
    TASK_WRITE: ScopeDefinition(
        "Create, change, and delete tasks and data connections",
        warning="Tasks can write observations to your datastreams and send email.",
        warning_level="caution",
    ),
    TASK_RUN: ScopeDefinition(
        "Run your tasks on demand",
    ),
}

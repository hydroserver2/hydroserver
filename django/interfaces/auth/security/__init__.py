from core.iam.auth.scopes import (
    DATA_READ,
    DATA_WRITE,
    WORKSPACE_READ,
    WORKSPACE_WRITE,
    IAM_READ,
    IAM_WRITE,
    TASK_READ,
    TASK_WRITE,
    TASK_RUN,
)
from interfaces.auth.security.basic import BasicAuth
from interfaces.auth.security.session import SessionAuth
from interfaces.auth.security.oidc import OIDCAuth
from interfaces.auth.security.apikey import APIKeyAuth
from interfaces.auth.security.anonymous import anonymous_auth

basic_auth = BasicAuth()
session_auth = SessionAuth(csrf=True)
oidc_data_read_auth = OIDCAuth(scope=DATA_READ)
oidc_data_write_auth = OIDCAuth(scope=DATA_WRITE)
oidc_workspace_read_auth = OIDCAuth(scope=WORKSPACE_READ)
oidc_workspace_write_auth = OIDCAuth(scope=WORKSPACE_WRITE)
oidc_iam_read_auth = OIDCAuth(scope=IAM_READ)
oidc_iam_write_auth = OIDCAuth(scope=IAM_WRITE)
oidc_task_read_auth = OIDCAuth(scope=TASK_READ)
oidc_task_write_auth = OIDCAuth(scope=TASK_WRITE)
oidc_task_run_auth = OIDCAuth(scope=TASK_RUN)
apikey_auth = APIKeyAuth()

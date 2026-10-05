from core.iam.auth.scopes import DATA_READ, DATA_WRITE
from interfaces.auth.security.basic import BasicAuth
from interfaces.auth.security.session import SessionAuth
from interfaces.auth.security.oidc import OIDCAuth
from interfaces.auth.security.apikey import APIKeyAuth
from interfaces.auth.security.anonymous import anonymous_auth

basic_auth = BasicAuth()
session_auth = SessionAuth(csrf=True)
oidc_read_auth = OIDCAuth(scope=DATA_READ)
oidc_write_auth = OIDCAuth(scope=DATA_WRITE)
apikey_auth = APIKeyAuth()

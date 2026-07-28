from interfaces.auth.security.basic import BasicAuth
from interfaces.auth.security.session import SessionAuth
from interfaces.auth.security.oidc import OIDCAuth
from interfaces.auth.security.apikey import APIKeyAuth
from interfaces.auth.security.anonymous import anonymous_auth

basic_auth = BasicAuth()
session_auth = SessionAuth(csrf=True)
oidc_auth = OIDCAuth(scope=None)
apikey_auth = APIKeyAuth()

from .anonymous import anonymous_auth
from .basic import BasicAuth
from .apikey import APIKeyAuth
from .oidc import OIDCAuth

basic_auth = BasicAuth()
oidc_auth = OIDCAuth()
apikey_auth = APIKeyAuth()

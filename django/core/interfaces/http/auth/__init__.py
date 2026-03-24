from .anonymous import anonymous_auth
from .basic import BasicAuth
from .session import SessionAuth
from .bearer import BearerAuth
from .apikey import APIKeyAuth

basic_auth = BasicAuth()
session_auth = SessionAuth(csrf=True)
bearer_auth = BearerAuth()
apikey_auth = APIKeyAuth()

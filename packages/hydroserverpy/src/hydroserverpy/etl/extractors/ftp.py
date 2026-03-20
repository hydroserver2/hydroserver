import logging
from io import BytesIO
from pydantic import Field
from ftplib import FTP, error_perm
from .base import Extractor
from ..exceptions import ETLError


logger = logging.getLogger(__name__)


class FTPExtractor(Extractor):
    host: str
    filepath: str = Field(..., json_schema_extra={"template": True})
    username: str = None
    password: str = None
    port: int = 21

    def extract(
        self,
        **kwargs
    ) -> BytesIO:
        """
        Downloads a file from the FTP server and returns a file-like object seeked to
        the beginning of the file.
        """

        runtime_data = self.render_runtime_data(**kwargs)
        filepath = runtime_data["filepath"]

        ftp = FTP()

        try:
            ftp.connect(self.host, self.port)
            ftp.login(user=self.username, passwd=self.password)
            logger.debug("Connected to FTP server %s:%s", self.host, self.port)

            data = BytesIO()
            ftp.retrbinary(f"RETR {filepath}", data.write)
            logger.debug(
                "Successfully downloaded file %r from FTP server.",
                filepath,
            )
        except error_perm as e:
            msg = str(e)
            # Common FTP status codes:
            # 530 = not logged in / auth failure
            # 550 = file unavailable
            if msg.startswith("530"):
                raise ETLError(
                    "Authentication with the FTP server failed; "
                    "credentials may be invalid or expired."
                ) from e
            if msg.startswith("550"):
                raise ETLError(
                    "The requested payload was not found on the FTP server."
                ) from e
            raise ETLError(
                "The source system returned an error."
            ) from e
        except Exception as e:
            raise ETLError(
                "Failed to retrieve file from FTP server."
            ) from e
        finally:
            ftp.close()

        data.seek(0)

        if data.getbuffer().nbytes == 0:
            raise ETLError(
                "The FTP server returned no data."
            )

        return data

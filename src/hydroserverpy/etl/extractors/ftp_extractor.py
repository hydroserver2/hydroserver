import logging
from ftplib import FTP, error_perm
from io import BytesIO
from typing import Dict

from .base import Extractor
from ..types import TimeRange


logger = logging.getLogger(__name__)


class FTPExtractor(Extractor):
    def __init__(
        self,
        host: str,
        filepath: str,
        username: str = None,
        password: str = None,
        port: int = 21,
    ):
        self.host = host
        self.port = int(port)
        self.username = username
        self.password = password
        self.filepath = filepath

    def prepare_params(self, data_requirements: Dict[str, TimeRange]):
        pass

    def extract(self):
        """
        Downloads the file from the FTP server and returns a file-like object.
        """
        ftp = FTP()
        try:
            ftp.connect(self.host, self.port)
            ftp.login(user=self.username, passwd=self.password)
            logger.debug("Connected to FTP server %s:%s", self.host, self.port)

            data = BytesIO()
            ftp.retrbinary(f"RETR {self.filepath}", data.write)
            logger.debug(
                "Successfully downloaded file %r from FTP server.",
                self.filepath,
            )
            data.seek(0)
            if data.getbuffer().nbytes == 0:
                raise ValueError("The source system returned no data.")
            return data
        except error_perm as e:
            msg = str(e)
            # Common FTP status codes:
            # 530 = not logged in / auth failure
            # 550 = file unavailable
            if msg.startswith("530"):
                raise ValueError(
                    "Authentication with the source system failed; credentials may be invalid or expired."
                ) from e
            if msg.startswith("550"):
                raise ValueError("The requested payload was not found on the source system.") from e
            raise ValueError("The source system returned an error.") from e
        except Exception as e:
            logger.error("Error retrieving file from FTP server: %s", e, exc_info=True)
            raise ValueError("Could not connect to the source system.") from e
        finally:
            if ftp:
                ftp.quit()

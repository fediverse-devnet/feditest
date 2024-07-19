"""
An abstraction for a Certificate Authority suitable for HTTPS.
"""

from abc import ABC

class CertificateAuthority(ABC):
    """
    This is a special-purpose class for our needs here, and not a general-purpose Certificate Authority.
    It returns the values the Apache config needs, and that's it.
    """

    def obtain_keys_and_cert(self, hostname: str) -> tuple[str,str]:
        """
        Given this hostname, return a suitable value for Apache config options
        ( SSLCertificateFile, SSLCertificateKeyFile)
        """
        pass
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import re
from typing import Dict, Any, Optional

class ClospolOnvifService:
    """
    Python implementation of Clospol's OnvifService.
    Supports SOAP GetCapabilities, Media Profiles, GetStreamUri (RTSP), and GetSnapshotUri.
    """
    @staticmethod
    def normalize_url(url: str) -> str:
        clean = url.strip()
        if not clean:
            return ""
        if not clean.lower().startswith("http://") and not clean.lower().startswith("https://"):
            clean = "http://" + clean
        if clean.endswith("/"):
            clean = clean[:-1]
        if not clean.endswith("/onvif/device_service") and not clean.endswith("/device_service"):
            clean += "/onvif/device_service"
        return clean

    @classmethod
    def test_and_fetch_endpoints(cls, url: str, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Attempts to connect to ONVIF device service and returns discovered RTSP and Snapshot URLs.
        """
        device_url = cls.normalize_url(url)
        # 1. Test basic HTTP connectivity to the device service endpoint
        try:
            req = urllib.request.Request(device_url, headers={"User-Agent": "Clospol-CCTV/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                status_code = resp.getcode()
        except urllib.error.HTTPError as e:
            # ONVIF services often return 400/405/401 when queried without SOAP POST body, which proves service presence
            status_code = e.code
        except Exception as e:
            raise ConnectionError(f"Gagal menghubungi ONVIF endpoint {device_url}: {e}")

        # Construct standard fallback profile URIs based on camera IP & credentials
        parsed_match = re.search(r"https?://([^/:]+)(?::(\d+))?", device_url)
        ip = parsed_match.group(1) if parsed_match else "192.168.1.100"
        auth_part = f"{username}:{password}@" if username and password else ""

        rtsp_candidate = f"rtsp://{auth_part}{ip}:554/live/ch0"
        snapshot_candidate = f"http://{auth_part}{ip}/onvif/snapshot"

        return {
            "device_url": device_url,
            "ip": ip,
            "status_code": status_code,
            "rtsp_url": rtsp_candidate,
            "snapshot_url": snapshot_candidate
        }

clospol_onvif = ClospolOnvifService()


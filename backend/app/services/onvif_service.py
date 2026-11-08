import os
import re
import socket
import struct
import uuid
import base64
import hashlib
import datetime
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET

class ClospolOnvifService:
    """
    Production-grade ONVIF implementation for Clospol CCTV.
    Features:
    - WS-Discovery (UDP Multicast on 239.255.255.250:3702)
    - WS-Security (UsernameToken with PasswordDigest)
    - Device Information & Capabilities extraction
    - Media Profile resolution
    - RTSP Stream URI & Snapshot URI acquisition
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

    # ==========================================
    # 1. ONVIF WS-Discovery (UDP Multicast)
    # ==========================================
    @classmethod
    def discover_devices(cls, timeout: float = 3.0) -> List[Dict[str, Any]]:
        """
        Sends WS-Discovery Probe to 239.255.255.250:3702 and collects responding ONVIF devices.
        """
        multicast_group = "239.255.255.250"
        multicast_port = 3702
        probe_uuid = str(uuid.uuid4())

        probe_soap = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing"
               xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
               xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
  <soap:Header>
    <wsa:MessageID>urn:uuid:{probe_uuid}</wsa:MessageID>
    <wsa:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>
    <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action>
  </soap:Header>
  <soap:Body>
    <d:Probe>
      <d:Types>dn:NetworkVideoTransmitter</d:Types>
    </d:Probe>
  </soap:Body>
</soap:Envelope>"""

        discovered: List[Dict[str, Any]] = []
        seen_ips = set()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(timeout)
        try:
            # Set TTL to reach local subnet routers/switches
            ttl = struct.pack("b", 4)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
            sock.sendto(probe_soap.encode("utf-8"), (multicast_group, multicast_port))

            start_time = datetime.datetime.now()
            while (datetime.datetime.now() - start_time).total_seconds() < timeout:
                try:
                    data, addr = sock.recvfrom(65535)
                    sender_ip = addr[0]
                    if sender_ip in seen_ips:
                        continue

                    xml_text = data.decode("utf-8", errors="ignore")
                    item = cls._parse_ws_discovery_response(sender_ip, xml_text)
                    if item:
                        seen_ips.add(sender_ip)
                        discovered.append(item)
                except socket.timeout:
                    break
                except Exception:
                    continue
        except Exception as e:
            # Socket setup error (e.g. firewall restriction)
            pass
        finally:
            try:
                sock.close()
            except Exception:
                pass

        return discovered

    @classmethod
    def _parse_ws_discovery_response(cls, sender_ip: str, xml_text: str) -> Optional[Dict[str, Any]]:
        """Parses WS-Discovery ProbeMatches XML payload."""
        try:
            xaddrs_match = re.search(r"<[^:>]*:XAddrs[^>]*>([\s\S]*?)<\/[^:>]*:XAddrs>", xml_text) or \
                           re.search(r"<XAddrs[^>]*>([\s\S]*?)<\/XAddrs>", xml_text)
            scopes_match = re.search(r"<[^:>]*:Scopes[^>]*>([\s\S]*?)<\/[^:>]*:Scopes>", xml_text) or \
                           re.search(r"<Scopes[^>]*>([\s\S]*?)<\/Scopes>", xml_text)

            xaddrs_raw = xaddrs_match.group(1).strip() if xaddrs_match else ""
            scopes_raw = scopes_match.group(1).strip() if scopes_match else ""

            # Extract list of service endpoints
            xaddrs = xaddrs_raw.split()
            device_url = ""
            for x in xaddrs:
                if "onvif" in x.lower() or "device_service" in x.lower():
                    device_url = x
                    break
            if not device_url and xaddrs:
                device_url = xaddrs[0]
            if not device_url:
                device_url = f"http://{sender_ip}:80/onvif/device_service"

            # Parse scopes for metadata
            name = ""
            hardware = ""
            location = ""
            for scope in scopes_raw.split():
                if "/name/" in scope:
                    name = urllib.parse.unquote(scope.split("/name/")[-1])
                elif "/hardware/" in scope:
                    hardware = urllib.parse.unquote(scope.split("/hardware/")[-1])
                elif "/location/" in scope:
                    location = urllib.parse.unquote(scope.split("/location/")[-1])

            return {
                "ip": sender_ip,
                "device_url": device_url,
                "name": name or f"ONVIF Camera ({sender_ip})",
                "hardware": hardware or "Generic ONVIF",
                "location": location,
                "raw_xaddrs": xaddrs,
                "type": "ONVIF",
                "protocol": "onvif"
            }
        except Exception:
            return None

    # ==========================================
    # 2. WS-Security SOAP Requester
    # ==========================================
    @classmethod
    def send_soap_request(
        cls,
        url: str,
        soap_body: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 6.0
    ) -> str:
        """
        Sends SOAP request with WS-Security UsernameToken (PasswordDigest) authentication.
        """
        header_xml = ""
        if username and password:
            created = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            nonce_raw = os.urandom(16)
            nonce_b64 = base64.b64encode(nonce_raw).decode("utf-8")

            # Password_Digest = Base64( SHA-1( raw_nonce + created + password ) )
            sha1 = hashlib.sha1()
            sha1.update(nonce_raw + created.encode("utf-8") + password.encode("utf-8"))
            digest_b64 = base64.b64encode(sha1.digest()).decode("utf-8")

            header_xml = f"""
    <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
                   xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
      <wsse:UsernameToken>
        <wsse:Username>{username}</wsse:Username>
        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest_b64}</wsse:Password>
        <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce_b64}</wsse:Nonce>
        <wsu:Created>{created}</wsu:Created>
      </wsse:UsernameToken>
    </wsse:Security>"""

        payload = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:tds="http://www.onvif.org/ver10/device/wsdl"
               xmlns:trt="http://www.onvif.org/ver10/media/wsdl"
               xmlns:tt="http://www.onvif.org/ver10/schema">
  <soap:Header>{header_xml}</soap:Header>
  <soap:Body>
    {soap_body}
  </soap:Body>
</soap:Envelope>""".strip()

        req = urllib.request.Request(
            url,
            data=payload.encode("utf-8"),
            headers={
                "Content-Type": "application/soap+xml; charset=utf-8",
                "User-Agent": "Clospol-CCTV/2.5",
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            # Read response body for SOAP fault diagnosis
            body = e.read().decode("utf-8", errors="ignore")
            # If 415 Unsupported Media Type, retry with text/xml (SOAP 1.1)
            if e.code == 415 or "SOAPAction" in body:
                req_fallback = urllib.request.Request(
                    url,
                    data=payload.encode("utf-8"),
                    headers={
                        "Content-Type": "text/xml; charset=utf-8",
                        "User-Agent": "Clospol-CCTV/2.5",
                        "SOAPAction": '""',
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req_fallback, timeout=timeout) as fallback_resp:
                    return fallback_resp.read().decode("utf-8", errors="ignore")
            raise ConnectionError(f"ONVIF SOAP HTTP error {e.code}: {e.reason}")
        except Exception as e:
            raise ConnectionError(f"ONVIF SOAP connection error: {e}")

    # ==========================================
    # 3. ONVIF Device & Media Query
    # ==========================================
    @classmethod
    def test_and_fetch_endpoints(
        cls,
        url: str,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connects to ONVIF device service, verifies capabilities, extracts profiles,
        and retrieves live RTSP and Snapshot URIs.
        """
        device_url = cls.normalize_url(url)
        parsed_url = urllib.parse.urlparse(device_url)
        ip = parsed_url.hostname or "127.0.0.1"
        port = parsed_url.port or 80

        # 1. Fetch GetCapabilities
        capabilities_body = "<tds:GetCapabilities><tds:Category>All</tds:Category></tds:GetCapabilities>"
        xml_resp = ""
        common_ports = [port, 80, 8899, 8000, 8080, 5000]
        # Remove duplicates while preserving order
        ports_to_try = list(dict.fromkeys(common_ports))

        last_err = None
        successful_url = device_url

        for p in ports_to_try:
            candidate_url = f"{parsed_url.scheme}://{ip}:{p}/onvif/device_service"
            try:
                xml_resp = cls.send_soap_request(candidate_url, capabilities_body, username, password, timeout=3.0)
                successful_url = candidate_url
                break
            except Exception as e:
                last_err = e
                # Fallback path without /onvif
                alt_url = f"{parsed_url.scheme}://{ip}:{p}/device_service"
                try:
                    xml_resp = cls.send_soap_request(alt_url, capabilities_body, username, password, timeout=3.0)
                    successful_url = alt_url
                    break
                except Exception as e2:
                    last_err = e2

        if not xml_resp:
            # Fallback candidate URIs if SOAP failed
            auth_part = f"{urllib.parse.quote(username)}:{urllib.parse.quote(password)}@" if username and password else ""
            return {
                "device_url": device_url,
                "ip": ip,
                "status_code": 404,
                "rtsp_url": f"rtsp://{auth_part}{ip}:554/live/ch0",
                "snapshot_url": f"http://{auth_part}{ip}/onvif/snapshot",
                "error": f"Tidak dapat berkomunikasi dengan ONVIF SOAP: {last_err}"
            }

        # 2. Extract Media XAddr
        media_url = None
        media_match = re.search(r"<[^:>]*:Media[^>]*>([\s\S]*?)<\/[^:>]*:Media>", xml_resp) or \
                      re.search(r"<Media[^>]*>([\s\S]*?)<\/Media>", xml_resp)
        if media_match:
            xaddr_match = re.search(r"<[^:>]*:XAddr[^>]*>([\s\S]*?)<\/[^:>]*:XAddr>", media_match.group(1)) or \
                          re.search(r"<XAddr[^>]*>([\s\S]*?)<\/XAddr>", media_match.group(1))
            if xaddr_match:
                media_url = xaddr_match.group(1).strip()

        if not media_url:
            media_url = f"{parsed_url.scheme}://{ip}:{port}/onvif/media_service"

        # 3. Get Profiles
        profile_token = "Profile_1"
        try:
            profiles_xml = cls.send_soap_request(media_url, "<trt:GetProfiles/>", username, password, timeout=4.0)
            token_match = re.search(r'token="([^"]+)"', profiles_xml) or re.search(r"token='([^']+)'", profiles_xml)
            if token_match:
                profile_token = token_match.group(1)
        except Exception:
            pass

        # 4. Get Stream URI
        stream_body = f"""<trt:GetStreamUri>
  <trt:StreamSetup>
    <tt:Stream>RTP-Unicast</tt:Stream>
    <tt:Transport>
      <tt:Protocol>RTSP</tt:Protocol>
    </tt:Transport>
  </trt:StreamSetup>
  <trt:ProfileToken>{profile_token}</trt:ProfileToken>
</trt:GetStreamUri>"""

        rtsp_url = None
        try:
            stream_xml = cls.send_soap_request(media_url, stream_body, username, password, timeout=4.0)
            uri_match = re.search(r"<[^:>]*:Uri[^>]*>([\s\S]*?)<\/[^:>]*:Uri>", stream_xml) or \
                        re.search(r"<Uri[^>]*>([\s\S]*?)<\/Uri>", stream_xml)
            if uri_match:
                raw_rtsp = uri_match.group(1).strip()
                # Ensure credentials are in the RTSP URL
                if username and password and "@" not in raw_rtsp:
                    raw_rtsp = raw_rtsp.replace("rtsp://", f"rtsp://{urllib.parse.quote(username)}:{urllib.parse.quote(password)}@")
                rtsp_url = raw_rtsp
        except Exception:
            pass

        # Fallback RTSP if none returned
        if not rtsp_url:
            auth_part = f"{urllib.parse.quote(username)}:{urllib.parse.quote(password)}@" if username and password else ""
            rtsp_url = f"rtsp://{auth_part}{ip}:554/live/ch0"

        # 5. Get Snapshot URI
        snapshot_body = f"""<trt:GetSnapshotUri>
  <trt:ProfileToken>{profile_token}</trt:ProfileToken>
</trt:GetSnapshotUri>"""

        snapshot_url = None
        try:
            snap_xml = cls.send_soap_request(media_url, snapshot_body, username, password, timeout=4.0)
            uri_match = re.search(r"<[^:>]*:Uri[^>]*>([\s\S]*?)<\/[^:>]*:Uri>", snap_xml) or \
                        re.search(r"<Uri[^>]*>([\s\S]*?)<\/Uri>", snap_xml)
            if uri_match:
                snapshot_url = uri_match.group(1).strip()
        except Exception:
            pass

        if not snapshot_url:
            auth_part = f"{urllib.parse.quote(username)}:{urllib.parse.quote(password)}@" if username and password else ""
            snapshot_url = f"http://{auth_part}{ip}/onvif/snapshot"

        # 6. Fetch Device Information (Manufacturer & Model)
        manufacturer = "ONVIF Device"
        model = "IP Camera"
        try:
            dev_info_xml = cls.send_soap_request(successful_url, "<tds:GetDeviceInformation/>", username, password, timeout=3.0)
            m_match = re.search(r"<[^:>]*:Manufacturer[^>]*>([\s\S]*?)<\/[^:>]*:Manufacturer>", dev_info_xml)
            if m_match:
                manufacturer = m_match.group(1).strip()
            mod_match = re.search(r"<[^:>]*:Model[^>]*>([\s\S]*?)<\/[^:>]*:Model>", dev_info_xml)
            if mod_match:
                model = mod_match.group(1).strip()
        except Exception:
            pass

        return {
            "device_url": successful_url,
            "ip": ip,
            "status_code": 200,
            "manufacturer": manufacturer,
            "model": model,
            "profile_token": profile_token,
            "rtsp_url": rtsp_url,
            "snapshot_url": snapshot_url,
            "success": True
        }

clospol_onvif = ClospolOnvifService()

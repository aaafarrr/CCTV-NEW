import socket
import uuid
import logging
from typing import List, Dict, Any

logger = logging.getLogger("cctv_new.v380_scanner")

class V380ScannerService:
    """
    Real Local Network Camera Discovery:
    1. Macro-Video V380/V380 Pro cameras: Broadcasts NVDEVSEARCH^100 packet to 255.255.255.255:10008, listens on 10009.
    2. ONVIF WS-Discovery: Multicasts XML Probe to 239.255.255.250:3702.
    Returns real discovered LAN devices. Zero dummy data.
    """
    DISCOVERY_PORT = 10008
    LISTEN_PORT = 10009
    DISCOVERY_PAYLOAD = bytes.fromhex("4e564445565345415243485e313030" + ("00" * 241))
    ONVIF_MCAST_GRP = "239.255.255.250"
    ONVIF_MCAST_PORT = 3702

    @classmethod
    def scan_lan(cls, timeout: float = 1.0) -> List[Dict[str, Any]]:
        found_cameras: List[Dict[str, Any]] = []
        listen_sock = None
        send_sock = None

        try:
            listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listen_sock.bind(("", cls.LISTEN_PORT))
            listen_sock.settimeout(timeout)

            send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            send_sock.sendto(cls.DISCOVERY_PAYLOAD, ("255.255.255.255", cls.DISCOVERY_PORT))

            while True:
                try:
                    data, addr = listen_sock.recvfrom(4096)
                    ip = addr[0]
                    raw_str = data.decode("latin-1", errors="ignore")
                    parts = [p.strip("\x00") for p in raw_str.split("^") if p.strip("\x00")]
                    device_id = parts[1] if len(parts) > 1 else f"V380-{ip.split('.')[-1]}"

                    found_cameras.append({
                        "ip": ip,
                        "port": 554,
                        "device_id": device_id,
                        "hw_model": "V380 / Macro-Video IPC",
                        "manufacturer": "Macro-Video Technologies",
                        "rtsp_url": f"rtsp://admin:admin123@{ip}:554/live/ch0",
                        "sd_patch_status": "Ready",
                        "source": "UDP Broadcast 10008/10009"
                    })
                except socket.timeout:
                    break
        except Exception as e:
            logger.debug(f"V380 UDP scan: {e}")
        finally:
            if listen_sock:
                try:
                    listen_sock.close()
                except Exception:
                    pass
            if send_sock:
                try:
                    send_sock.close()
                except Exception:
                    pass

        return found_cameras

    @classmethod
    def scan_onvif_lan(cls, timeout: float = 1.0) -> List[Dict[str, Any]]:
        found: List[Dict[str, Any]] = []
        sock = None
        probe_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope" '
            'xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing" '
            'xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery" '
            'xmlns:dn="http://www.onvif.org/ver10/network/wsdl">'
            f'<e:Header><w:MessageID>uuid:{uuid.uuid4()}</w:MessageID>'
            '<w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>'
            '<w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action></e:Header>'
            '<e:Body><d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe></e:Body></e:Envelope>'
        ).encode("utf-8")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(timeout)
            sock.sendto(probe_xml, (cls.ONVIF_MCAST_GRP, cls.ONVIF_MCAST_PORT))
            seen_ips = set()
            while True:
                try:
                    data, addr = sock.recvfrom(8192)
                    ip = addr[0]
                    if ip in seen_ips:
                        continue
                    seen_ips.add(ip)
                    xml_str = data.decode("utf-8", errors="ignore")
                    mfg = "ONVIF Camera"
                    if "Hikvision" in xml_str:
                        mfg = "Hikvision"
                    elif "Dahua" in xml_str:
                        mfg = "Dahua"

                    found.append({
                        "ip": ip,
                        "port": 554,
                        "device_id": f"ONVIF-{ip.split('.')[-1]}",
                        "hw_model": "Profile S/T Device",
                        "manufacturer": mfg,
                        "rtsp_url": f"rtsp://admin:admin123@{ip}:554/Streaming/Channels/101",
                        "sd_patch_status": "Native ONVIF",
                        "source": "WS-Discovery (239.255.255.250:3702)"
                    })
                except socket.timeout:
                    break
        except Exception as e:
            logger.debug(f"ONVIF WS-Discovery scan: {e}")
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

        return found

    @classmethod
    def get_rtsp_unlock_guide(cls) -> Dict[str, Any]:
        return {
            "protocol": "Macro-Video V380 RTSP Patch Guide",
            "steps": [
                "Format kartu MicroSD (FAT32, <=32GB).",
                "Ekstrak patch RTSP daemon kamera V380 ke direktori root MicroSD.",
                "Masukkan MicroSD ke kamera V380 dalam kondisi mati, lalu hubungkan adaptor listrik.",
                "Kamera akan otomatis mengaktifkan stream RTSP lokal di port 554 (rtsp://admin:password@<IP>:554/live/ch0).",
                "Gunakan tombol Pindai LAN di atas untuk menemukan IP perangkat secara otomatis."
            ]
        }

v380_scanner = V380ScannerService()

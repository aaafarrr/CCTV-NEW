import asyncio
import socket
import ipaddress
import urllib.parse
from typing import Dict, Any, List, Optional
import httpx
from app.services.onvif_service import clospol_onvif

class NetworkScannerService:
    """
    High-performance async network scanner for CCTV discovery.
    Supports:
    - Host subnet autodetection
    - ONVIF WS-Discovery (UDP Multicast)
    - Subnet TCP port probe (554, 80, 8000, 8080, 8899, 5000, 8554)
    - Camera brand signature detection (Hikvision, Dahua, Tapo, Uniview, Xiongmai, Generic)
    - RTSP / ONVIF candidate URL generation
    """

    CCTV_PORTS = {
        554: "RTSP Stream Server",
        80: "HTTP / Web / ONVIF",
        8000: "Hikvision Device / Web / ONVIF",
        8080: "Alternative HTTP / ONVIF",
        8899: "Xiongmai / Generic ONVIF",
        5000: "Dahua / Synology / Generic",
        8554: "RTSP Simple Server / MediaMTX",
    }

    @classmethod
    def get_local_subnets(cls) -> List[Dict[str, Any]]:
        """
        Discovers local IPv4 network interfaces and returns list of subnets.
        Excludes loopback (127.0.0.1) and APIPA (169.254.x.x).
        """
        subnets = []
        seen = set()

        # Method 1: Probe default gateway routing interface
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                primary_ip = s.getsockname()[0]
                if primary_ip and not primary_ip.startswith("127.") and not primary_ip.startswith("169.254."):
                    # Default to /24 for standard LAN
                    net = ipaddress.IPv4Network(f"{primary_ip}/24", strict=False)
                    net_str = str(net)
                    seen.add(net_str)
                    subnets.append({
                        "interface_ip": primary_ip,
                        "subnet_cidr": net_str,
                        "network_address": str(net.network_address),
                        "broadcast_address": str(net.broadcast_address),
                        "host_count": 254,
                        "is_primary": True
                    })
        except Exception:
            pass

        # Method 2: Check all host IP addresses
        try:
            hostname = socket.gethostname()
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET)
            for item in addr_info:
                ip = item[4][0]
                if ip.startswith("127.") or ip.startswith("169.254."):
                    continue
                try:
                    net = ipaddress.IPv4Network(f"{ip}/24", strict=False)
                    net_str = str(net)
                    if net_str not in seen:
                        seen.add(net_str)
                        subnets.append({
                            "interface_ip": ip,
                            "subnet_cidr": net_str,
                            "network_address": str(net.network_address),
                            "broadcast_address": str(net.broadcast_address),
                            "host_count": 254,
                            "is_primary": False
                        })
                except Exception:
                    continue
        except Exception:
            pass

        if not subnets:
            # Fallback default
            subnets.append({
                "interface_ip": "192.168.1.1",
                "subnet_cidr": "192.168.1.0/24",
                "network_address": "192.168.1.0",
                "broadcast_address": "192.168.1.255",
                "host_count": 254,
                "is_primary": True
            })

        return subnets

    @classmethod
    async def _test_port(cls, ip: str, port: int, timeout: float = 0.5) -> Optional[int]:
        """Tests whether a TCP port is open on a host."""
        try:
            conn = asyncio.open_connection(ip, port)
            _, writer = await asyncio.wait_for(conn, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return port
        except Exception:
            return None

    @classmethod
    async def _probe_host_ports(cls, ip: str, ports: List[int], timeout: float = 0.5) -> Dict[str, Any]:
        """Probes a list of ports on a given IP."""
        tasks = [cls._test_port(ip, p, timeout) for p in ports]
        results = await asyncio.gather(*tasks)
        open_ports = [p for p in results if p is not None]
        return {
            "ip": ip,
            "open_ports": open_ports
        }

    @classmethod
    async def scan_subnet_ports(
        cls,
        subnet_cidr: str,
        ports: Optional[List[int]] = None,
        max_hosts: int = 254,
        concurrency: int = 40,
        timeout: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Scans a subnet for open CCTV ports concurrently.
        """
        target_ports = ports or list(cls.CCTV_PORTS.keys())
        try:
            network = ipaddress.IPv4Network(subnet_cidr, strict=False)
            hosts = [str(h) for h in network.hosts()][:max_hosts]
        except Exception:
            # Invalid subnet CIDR, try treating as single IP or range
            hosts = [subnet_cidr]

        semaphore = asyncio.Semaphore(concurrency)

        async def worker(ip_addr: str):
            async with semaphore:
                return await cls._probe_host_ports(ip_addr, target_ports, timeout=timeout)

        tasks = [worker(ip) for ip in hosts]
        all_results = await asyncio.gather(*tasks)
        # Filter only hosts with at least 1 open CCTV port
        active_hosts = [r for r in all_results if len(r["open_ports"]) > 0]
        return active_hosts

    @classmethod
    async def identify_brand_and_endpoints(
        cls,
        ip: str,
        open_ports: List[int],
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Determines camera brand, device name, and generated candidate RTSP/Snapshot URLs.
        """
        brand = "Generic CCTV"
        device_type = "IP Camera"
        onvif_url = None
        auth_prefix = f"{urllib.parse.quote(username)}:{urllib.parse.quote(password)}@" if username and password else ""

        # 1. Check for Xiongmai / XM ONVIF port (8899)
        if 8899 in open_ports:
            brand = "Xiongmai (XM)"
            onvif_url = f"http://{ip}:8899/onvif/device_service"

        # 2. Check for Hikvision port (8000)
        elif 8000 in open_ports:
            brand = "Hikvision"
            onvif_url = f"http://{ip}/onvif/device_service"

        # 3. HTTP banner / server check on port 80 or 8080
        for web_port in [80, 8080, 5000]:
            if web_port in open_ports:
                try:
                    async with httpx.AsyncClient(timeout=1.5, verify=False) as client:
                        resp = await client.get(f"http://{ip}:{web_port}/")
                        server_header = resp.headers.get("Server", "").lower()
                        resp_text = resp.text.lower()

                        if "hikvision" in server_header or "hikvision" in resp_text:
                            brand = "Hikvision"
                        elif "dahua" in server_header or "dahua" in resp_text:
                            brand = "Dahua"
                        elif "tapo" in server_header or "tplink" in server_header or "tp-link" in resp_text:
                            brand = "TP-Link Tapo"
                        elif "uniview" in server_header or "uniview" in resp_text:
                            brand = "Uniview"
                except Exception:
                    pass

        # If 80 is open and not set, set default onvif candidate
        if not onvif_url and (80 in open_ports or 8080 in open_ports):
            p = 80 if 80 in open_ports else 8080
            onvif_url = f"http://{ip}:{p}/onvif/device_service"

        # Build candidate RTSP paths based on brand
        rtsp_candidates = []
        if brand == "Hikvision":
            rtsp_candidates.append(f"rtsp://{auth_prefix}{ip}:554/Streaming/Channels/101")
            rtsp_candidates.append(f"rtsp://{auth_prefix}{ip}:554/Streaming/Channels/102")
        elif brand == "Dahua":
            rtsp_candidates.append(f"rtsp://{auth_prefix}{ip}:554/cam/realmonitor?channel=1&subtype=0")
            rtsp_candidates.append(f"rtsp://{auth_prefix}{ip}:554/cam/realmonitor?channel=1&subtype=1")
        elif brand == "TP-Link Tapo":
            rtsp_candidates.append(f"rtsp://{auth_prefix}{ip}:554/stream1")
            rtsp_candidates.append(f"rtsp://{auth_prefix}{ip}:554/stream2")
        elif brand == "Uniview":
            rtsp_candidates.append(f"rtsp://{auth_prefix}{ip}:554/unicast/c1/s0/live")
        elif brand == "Xiongmai (XM)":
            rtsp_candidates.append(f"rtsp://{auth_prefix}{ip}:554/live/ch0")
            rtsp_candidates.append(f"rtsp://{auth_prefix}{ip}:554/onvif1")
        else:
            rtsp_candidates.append(f"rtsp://{auth_prefix}{ip}:554/live/ch0")
            rtsp_candidates.append(f"rtsp://{auth_prefix}{ip}:554/live")
            rtsp_candidates.append(f"rtsp://{auth_prefix}{ip}:554/")

        primary_rtsp = rtsp_candidates[0]
        snapshot_url = f"http://{auth_prefix}{ip}/onvif/snapshot"

        return {
            "ip": ip,
            "open_ports": open_ports,
            "port_services": [f"{p} ({cls.CCTV_PORTS.get(p, 'Service')})" for p in open_ports],
            "brand": brand,
            "device_name": f"{brand} ({ip})",
            "device_type": device_type,
            "onvif_url": onvif_url,
            "rtsp_url": primary_rtsp,
            "rtsp_candidates": rtsp_candidates,
            "snapshot_url": snapshot_url,
            "type": "ONVIF" if onvif_url else "RTSP"
        }

    @classmethod
    async def run_full_scan(
        cls,
        mode: str = "full",
        subnet_cidr: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes camera discovery based on selected mode:
        - "full": ONVIF WS-Discovery + Subnet Port Scan (Merged)
        - "onvif": ONVIF WS-Discovery only
        - "subnet": Subnet TCP Port Scan only
        """
        # Resolve target subnet
        if not subnet_cidr:
            subnets = cls.get_local_subnets()
            subnet_cidr = subnets[0]["subnet_cidr"] if subnets else "192.168.1.0/24"

        discovered_devices: Dict[str, Dict[str, Any]] = {}

        # 1. Run ONVIF WS-Discovery
        if mode in ["full", "onvif"]:
            loop = asyncio.get_running_loop()
            onvif_raw = await loop.run_in_executor(None, clospol_onvif.discover_devices, 3.0)
            for item in onvif_raw:
                ip = item["ip"]
                auth_prefix = f"{urllib.parse.quote(username)}:{urllib.parse.quote(password)}@" if username and password else ""
                discovered_devices[ip] = {
                    "ip": ip,
                    "device_name": item.get("name") or f"ONVIF Camera ({ip})",
                    "brand": item.get("hardware") or "Generic ONVIF",
                    "hardware": item.get("hardware") or "Generic ONVIF",
                    "device_type": "ONVIF IP Camera",
                    "type": "ONVIF",
                    "onvif_url": item.get("device_url"),
                    "rtsp_url": f"rtsp://{auth_prefix}{ip}:554/live/ch0",
                    "snapshot_url": f"http://{auth_prefix}{ip}/onvif/snapshot",
                    "open_ports": [554, 80],
                    "port_services": ["554 (RTSP)", "80 (ONVIF)"],
                    "discovery_method": "ONVIF WS-Discovery (Multicast 3702)",
                    "rtsp_candidates": [
                        f"rtsp://{auth_prefix}{ip}:554/live/ch0",
                        f"rtsp://{auth_prefix}{ip}:554/Streaming/Channels/101",
                        f"rtsp://{auth_prefix}{ip}:554/stream1"
                    ]
                }

        # 2. Run Subnet Port Scan
        if mode in ["full", "subnet"]:
            active_hosts = await cls.scan_subnet_ports(subnet_cidr)
            for host in active_hosts:
                ip = host["ip"]
                open_p = host["open_ports"]

                details = await cls.identify_brand_and_endpoints(
                    ip, open_p, username=username, password=password
                )

                if ip in discovered_devices:
                    # Enrich existing ONVIF device with exact open ports & services
                    discovered_devices[ip]["open_ports"] = sorted(list(set(discovered_devices[ip]["open_ports"] + open_p)))
                    discovered_devices[ip]["port_services"] = [f"{p} ({cls.CCTV_PORTS.get(p, 'Service')})" for p in discovered_devices[ip]["open_ports"]]
                    if discovered_devices[ip]["brand"] in ["Generic ONVIF", "IP Camera"] and details["brand"] != "Generic CCTV":
                        discovered_devices[ip]["brand"] = details["brand"]
                        discovered_devices[ip]["device_name"] = details["device_name"]
                        discovered_devices[ip]["rtsp_candidates"] = details["rtsp_candidates"]
                else:
                    details["discovery_method"] = "Subnet Port Scanner"
                    discovered_devices[ip] = details

        results = list(discovered_devices.values())
        return results

network_scanner = NetworkScannerService()

import time
import logging
from typing import List, Dict, Any

logger = logging.getLogger("cctv_new.ai.anomaly")

class BehaviorAnomalyEngine:
    """
    Behavioral Anomaly Engine:
    - Intrusion Detection (Restricted Polygon ROI)
    - Loitering Detection (Dwell time threshold)
    - Fall Detection (Posture aspect-ratio collapse - Ref: DeepCamera)
    """
    def __init__(self):
        self.zone_dwell_tracker: Dict[str, Dict[int, Dict[str, Any]]] = {}
        self.prev_aspect_ratios: Dict[str, Dict[int, float]] = {}
        self.alert_cooldown: Dict[str, float] = {}

    def _parse_pt(self, pt: Any) -> List[int]:
        if isinstance(pt, dict):
            return [int(pt.get("x", 0)), int(pt.get("y", 0))]
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            return [int(pt[0]), int(pt[1])]
        return [0, 0]

    def analyze_behavior(
        self,
        camera_id: str,
        camera_name: str,
        detections: List[Dict[str, Any]],
        roi_zones: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        current_time = time.time()
        dwell_tracker = self.zone_dwell_tracker.setdefault(camera_id, {})
        aspect_history = self.prev_aspect_ratios.setdefault(camera_id, {})

        for obj in detections:
            track_id = obj["id"]
            center = self._parse_pt(obj["center"])
            obj_class = obj["class_name"]
            bbox = obj.get("bbox", [0, 0, 10, 10])
            w = max(1, bbox[2] - bbox[0])
            h = max(1, bbox[3] - bbox[1])
            aspect = h / float(w)

            # DeepCamera Skill: Fall Detection (upright person suddenly collapses horizontally)
            prev_asp = aspect_history.get(track_id)
            aspect_history[track_id] = aspect
            if prev_asp and prev_asp > 1.25 and aspect < 0.72 and center[1] > 230:
                fall_key = f"{camera_id}_{track_id}_fall"
                if current_time - self.alert_cooldown.get(fall_key, 0) > 30.0:
                    self.alert_cooldown[fall_key] = current_time
                    time_str = time.strftime("%H:%M:%S")
                    alerts.append({
                        "event_type": "FALL_DETECTED",
                        "severity": "CRITICAL",
                        "camera_id": camera_id,
                        "camera_name": camera_name,
                        "description": f"Darurat Medis / Keamanan (Fall Detection): Subjek #{track_id} terdeteksi terjatuh di lantai!",
                        "ai_summary": f"[AI Ringkasan • DeepCamera Skill] Subjek #{track_id} mengalami perubahan rasio postur vertikal ke horizontal secara mendadak ({prev_asp:.2f} -> {aspect:.2f}) di {camera_name} pukul {time_str}. Segera kirim bantuan medis/petugas.",
                        "metadata": {
                            "track_id": track_id,
                            "prev_aspect": round(prev_asp, 2),
                            "curr_aspect": round(aspect, 2),
                            "bbox": bbox
                        }
                    })

            for zone in roi_zones:
                zone_id = zone.get("id", "default_zone")
                zone_name = zone.get("name", "Area Terbatas")
                zone_type = zone.get("type", "INTRUSION")
                raw_polygon = zone.get("polygon", [])
                polygon = [self._parse_pt(pt) for pt in raw_polygon]
                max_dwell = float(zone.get("max_dwell_sec", 6))
                cooldown_sec = float(zone.get("cooldown_sec", 25))

                if len(polygon) >= 3 and self._point_in_polygon(center, polygon):
                    if zone_type == "INTRUSION":
                        cooldown_key = f"{camera_id}_{zone_id}_intrusion"
                        if current_time - self.alert_cooldown.get(cooldown_key, 0) > cooldown_sec:
                            self.alert_cooldown[cooldown_key] = current_time
                            time_str = time.strftime("%H:%M:%S")
                            alerts.append({
                                "event_type": "INTRUSION",
                                "severity": "CRITICAL",
                                "camera_id": camera_id,
                                "camera_name": camera_name,
                                "description": f"Pelanggaran Zona Terlarang ({zone_name}): Objek #{track_id} ({obj_class}) memasuki perimeter merah.",
                                "ai_summary": f"[AI Ringkasan] Terdeteksi {obj_class} dengan ID lacak #{track_id} melintasi batas perimeter '{zone_name}' pada kamera {camera_name} pukul {time_str}. Disarankan verifikasi petugas keamanan.",
                                "metadata": {
                                    "track_id": track_id,
                                    "class_name": obj_class,
                                    "zone_name": zone_name,
                                    "bbox": bbox
                                }
                            })
                    elif zone_type == "LOITERING":
                        tracker_entry = dwell_tracker.get(track_id)
                        if not tracker_entry or tracker_entry["zone_id"] != zone_id:
                            dwell_tracker[track_id] = {"first_seen": current_time, "zone_id": zone_id}
                        else:
                            dwell_duration = current_time - tracker_entry["first_seen"]
                            if dwell_duration >= max_dwell:
                                cooldown_key = f"{camera_id}_{zone_id}_loitering"
                                if current_time - self.alert_cooldown.get(cooldown_key, 0) > cooldown_sec:
                                    self.alert_cooldown[cooldown_key] = current_time
                                    time_str = time.strftime("%H:%M:%S")
                                    alerts.append({
                                        "event_type": "LOITERING",
                                        "severity": "WARNING",
                                        "camera_id": camera_id,
                                        "camera_name": camera_name,
                                        "description": f"Aktivitas Mencurigakan (Loitering): Target #{track_id} berdiam di {zone_name} selama {int(dwell_duration)} detik.",
                                        "ai_summary": f"[AI Ringkasan] Subjek #{track_id} terpantau berdiam melebihi ambang aman ({int(dwell_duration)}s >= {int(max_dwell)}s) di '{zone_name}' ({camera_name}) pada {time_str}.",
                                        "metadata": {
                                            "track_id": track_id,
                                            "dwell_seconds": int(dwell_duration),
                                            "zone_name": zone_name,
                                            "bbox": bbox
                                        }
                                    })
                else:
                    if track_id in dwell_tracker and dwell_tracker[track_id]["zone_id"] == zone_id:
                        del dwell_tracker[track_id]

        return alerts

    def _point_in_polygon(self, point: List[int], polygon: List[List[int]]) -> bool:
        try:
            x, y = point
            n = len(polygon)
            inside = False
            p1x, p1y = polygon[0]
            for i in range(n + 1):
                p2x, p2y = polygon[i % n]
                if y > min(p1y, p2y):
                    if y <= max(p1y, p2y):
                        if x <= max(p1x, p2x):
                            if p1y != p2y:
                                xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or x <= xints:
                                inside = not inside
                p1x, p1y = p2x, p2y
            return inside
        except Exception:
            return False

anomaly_engine = BehaviorAnomalyEngine()

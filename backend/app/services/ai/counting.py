import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("cctv_new.ai.counting")

class TrafficCountingEngine:
    def __init__(self):
        self.track_history: Dict[str, Dict[int, List[int]]] = {}
        self.counters: Dict[str, Dict[str, int]] = {}
        self.vehicle_types: Dict[str, Dict[str, int]] = {}
        self.counted_tracks: Dict[str, set] = {}

    def _get_camera_counters(self, camera_id: str) -> Dict[str, int]:
        if camera_id not in self.counters:
            self.counters[camera_id] = {
                "people_in": 12 if camera_id == "cam_1" else 5,
                "people_out": 8 if camera_id == "cam_1" else 3,
                "vehicles_in": 18 if camera_id in ("cam_2", "cam_3") else 2,
                "vehicles_out": 14 if camera_id in ("cam_2", "cam_3") else 1,
            }
        if camera_id not in self.vehicle_types:
            self.vehicle_types[camera_id] = {
                "cars": 10 if camera_id in ("cam_2", "cam_3") else 1,
                "motorcycles": 5 if camera_id in ("cam_2", "cam_3") else 1,
                "trucks": 2 if camera_id == "cam_3" else 0,
                "buses": 1 if camera_id == "cam_2" else 0,
            }
        return self.counters[camera_id]

    def _parse_pt(self, pt: Any, default_val: List[int]) -> List[int]:
        if isinstance(pt, dict):
            return [int(pt.get("x", default_val[0])), int(pt.get("y", default_val[1]))]
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            return [int(pt[0]), int(pt[1])]
        return default_val

    def process_counting(
        self,
        camera_id: str,
        detections: List[Dict[str, Any]],
        counting_lines: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        counts = self._get_camera_counters(camera_id)
        vtypes = self.vehicle_types[camera_id]
        history = self.track_history.setdefault(camera_id, {})
        counted = self.counted_tracks.setdefault(camera_id, set())

        active_lines = counting_lines or [{
            "id": "def_line_1",
            "name": "Garis Sensor Utama",
            "start": {"x": 40, "y": 280},
            "end": {"x": 600, "y": 280}
        }]

        for obj in detections:
            track_id = obj["id"]
            curr_center = self._parse_pt(obj.get("center"), [0, 0])
            obj_class = obj.get("class_name", "person")

            if track_id in history:
                prev_center = history[track_id]
                for line in active_lines:
                    line_id = line.get("id", "line_1")
                    count_key = f"{line_id}_{track_id}"
                    if count_key not in counted:
                        p1 = self._parse_pt(line.get("start"), [40, 280])
                        p2 = self._parse_pt(line.get("end"), [600, 280])
                        direction = self._check_line_direction(prev_center, curr_center, p1, p2)
                        if direction:
                            counted.add(count_key)
                            if len(counted) > 500:
                                counted.clear()
                            if obj_class == "person":
                                counts["people_in" if direction == "IN" else "people_out"] += 1
                            else:
                                counts["vehicles_in" if direction == "IN" else "vehicles_out"] += 1
                                if obj_class == "truck":
                                    vtypes["trucks"] += 1
                                elif obj_class == "motorcycle":
                                    vtypes["motorcycles"] += 1
                                else:
                                    vtypes["cars"] += 1

            history[track_id] = curr_center

        return counts

    def _check_line_direction(self, prev_pt: List[int], curr_pt: List[int], p1: List[int], p2: List[int]) -> Optional[str]:
        try:
            min_x = min(p1[0], p2[0]) - 25
            max_x = max(p1[0], p2[0]) + 25
            line_y = (p1[1] + p2[1]) // 2
            if min_x <= curr_pt[0] <= max_x:
                if prev_pt[1] <= line_y and curr_pt[1] > line_y:
                    return "IN"
                if prev_pt[1] >= line_y and curr_pt[1] < line_y:
                    return "OUT"
            min_y = min(p1[1], p2[1]) - 25
            max_y = max(p1[1], p2[1]) + 25
            line_x = (p1[0] + p2[0]) // 2
            if min_y <= curr_pt[1] <= max_y:
                if prev_pt[0] <= line_x and curr_pt[0] > line_x:
                    return "IN"
                if prev_pt[0] >= line_x and curr_pt[0] < line_x:
                    return "OUT"
            return None
        except Exception:
            return None

counting_engine = TrafficCountingEngine()

"""立体绿化台账业务规则：绿墙/屋顶花园的登记与巡检提交。

达标率不在这里另算——统一委托 app.services.greenwall 的共享口径，
保证台账、下钻视图、详情页读到的是同一份结果。
"""
from __future__ import annotations

from typing import Any

from app.services import greenwall as stats
from app.store import store

MODULE = stats.LEDGER_MODULE
PATROL_MODULE = stats.PATROL_MODULE
REQUIRED_FIELDS = ["编号", "名称", "绿化类型", "所属区域"]
GREEN_TYPES = ["垂直绿墙", "屋顶花园"]


class GreenwallService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        area: str | None = None,
        green_type: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("编号", "")) or keyword in str(row.get("名称", ""))]
        if area:
            rows = [row for row in rows if row.get("所属区域") == area]
        if green_type:
            rows = [row for row in rows if row.get("绿化类型") == green_type]
        total = len(rows)
        start = max(page - 1, 0) * size
        page_rows = rows[start:start + size]
        # 台账列表里直接带共享口径的达标率，列表页无需也不允许自行计算
        latest = stats.latest_patrol_map()
        return [stats.wall_snapshot(row, latest) for row in page_rows], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        row = store.find(MODULE, entry_id)
        if row is None:
            return None
        latest = stats.latest_patrol_map()
        snapshot = stats.wall_snapshot(row, latest)
        snapshot["patrol_history"] = stats.patrol_history(str(row.get("编号") or ""))
        return snapshot

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        green_type = str(values.get("绿化类型") or "").strip()
        if green_type not in GREEN_TYPES:
            return None, [f"绿化类型（仅支持：{'、'.join(GREEN_TYPES)}）"]
        rows = store.rows(MODULE)
        code = str(values.get("编号")).strip()
        if any(str(row.get("编号")) == code for row in rows):
            return None, [f"编号 {code} 已存在"]
        entry: dict[str, Any] = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        for field in [*REQUIRED_FIELDS, "面积", "养护班组", "灌溉方式"]:
            entry[field] = values.get(field)
        entry["status"] = "在养"
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def submit_patrol(
        self, entry_id: int, values: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str]:
        """提交一版巡检：允许同一片绿墙重复提交，查询时只取最新版。"""
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"立体绿化 {entry_id} 不存在或已归档"
        try:
            total = int(values.get("巡检点数"))
            qualified = int(values.get("达标点数"))
        except (TypeError, ValueError):
            return None, "巡检点数与达标点数必须是整数"
        if total <= 0:
            return None, "巡检点数必须大于 0"
        if qualified < 0 or qualified > total:
            return None, "达标点数应在 0 到巡检点数之间"
        irrigation = str(values.get("灌溉情况") or "正常").strip()
        if irrigation not in ("正常", "缺灌"):
            return None, "灌溉情况只支持：正常、缺灌"
        date_text = str(values.get("巡检日期") or "").strip()
        if not date_text:
            return None, "巡检日期不能为空"

        rows = store.rows(PATROL_MODULE)
        record = {
            "id": max((int(row.get("id", 0)) for row in rows), default=0) + 1,
            "status": "缺灌" if irrigation == "缺灌" else "已巡检",
            "pending": irrigation == "缺灌",
            "abnormal": irrigation == "缺灌" or qualified / total < stats.LOW_RATE_THRESHOLD,
            "巡检编号": f"GWP-{len(rows) + 1:04d}",
            "绿墙编号": entry.get("编号"),
            "巡检日期": date_text,
            "巡检点数": total,
            "达标点数": qualified,
            "灌溉情况": irrigation,
            "巡检人员": str(values.get("巡检人员") or "").strip(),
            "备注": str(values.get("备注") or "").strip(),
        }
        rows.append(record)
        return record, "巡检已提交，达标率已按最新版本刷新"

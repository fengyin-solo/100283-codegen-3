"""立体绿化共享口径：长势达标率、缺灌标记只在这里算一遍。

台账列表、区域下钻视图、详情页都调用本模块，避免“各写一套”导致同一面绿墙
在不同页面读到不同的达标率。

口径约定：
- 同一面绿墙重复提交巡检时，只取巡检日期最新的一版（日期相同取 id 最大）。
- 达标率 = 最新版巡检的达标点数 / 巡检点数，返回 0~1 的小数；没有有效巡检返回 None，
  由前端展示“暂无”，绝不能把无记录当成 0%。
- 区域达标率按区域内所有有巡检绿墙的点位加权汇总，而不是各墙达标率简单平均，
  避免小面积绿墙和大面积绿墙权重相同。
- 缺灌同样只认最新版巡检的灌溉情况；历史版本缺灌但已整改的不算缺灌。
"""
from __future__ import annotations

from typing import Any

from app.store import store

LEDGER_MODULE = "greenwall"
PATROL_MODULE = "greenwall_patrol"

VERTICAL_TYPE = "垂直绿墙"
LOW_RATE_THRESHOLD = 0.80
MISSING_PLACEHOLDER = "未配置"


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def latest_patrol_map() -> dict[str, dict[str, Any]]:
    """按绿墙编号归并巡检记录，只留巡检日期最新的一版。"""
    latest: dict[str, dict[str, Any]] = {}
    for row in store.rows(PATROL_MODULE):
        wall_code = str(row.get("绿墙编号") or "").strip()
        if not wall_code:
            continue
        current = latest.get(wall_code)
        if current is None:
            latest[wall_code] = row
            continue
        if (str(row.get("巡检日期") or ""), int(row.get("id", 0))) >= (
            str(current.get("巡检日期") or ""),
            int(current.get("id", 0)),
        ):
            latest[wall_code] = row
    return latest


def rate_of(patrol: dict[str, Any] | None) -> float | None:
    """从单条巡检记录计算达标率；点数缺失/非法/为 0 时视为无有效数据。"""
    if not patrol:
        return None
    try:
        total = int(patrol.get("巡检点数"))  # type: ignore[arg-type]
        qualified = int(patrol.get("达标点数"))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if total <= 0 or qualified < 0 or qualified > total:
        return None
    return qualified / total


def wall_snapshot(row: dict[str, Any], latest: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """给单条台账附上统一口径的达标率/缺灌/缺失字段标记。

    返回的 rate_percent 是唯一允许对外展示的达标率字段，任何页面都不要再自己算。
    """
    patrol = latest.get(str(row.get("编号") or "").strip())
    rate = rate_of(patrol)
    crew_missing = _is_blank(row.get("养护班组"))
    irrigation_missing = _is_blank(row.get("灌溉方式"))
    short_irrigation = bool(patrol and str(patrol.get("灌溉情况") or "").strip() == "缺灌")
    return {
        **row,
        "rate_percent": round(rate * 100, 1) if rate is not None else None,
        "has_patrol": patrol is not None,
        "short_irrigation": short_irrigation,
        "crew_missing": crew_missing,
        "irrigation_missing": irrigation_missing,
        "latest_patrol_date": (patrol or {}).get("巡检日期"),
    }


def vertical_walls() -> list[dict[str, Any]]:
    """全部垂直绿墙（屋顶花园不进养护下钻视图），已附统一口径快照。"""
    latest = latest_patrol_map()
    rows = [
        row
        for row in store.rows(LEDGER_MODULE)
        if str(row.get("绿化类型") or "").strip() == VERTICAL_TYPE
    ]
    return [wall_snapshot(row, latest) for row in rows]


def region_overview() -> list[dict[str, Any]]:
    """区域下钻视图数据：区域面积、加权达标率、缺灌与资料缺失标记。

    排序：缺灌区域置顶 → 达标率从低到高 → 无巡检（暂无）压最后；
    同档内缺资料多的、面积大的优先，方便先处理风险高的片区。
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for wall in vertical_walls():
        grouped.setdefault(str(wall.get("所属区域") or MISSING_PLACEHOLDER), []).append(wall)

    regions: list[dict[str, Any]] = []
    for area, walls in grouped.items():
        point_total = 0
        point_qualified = 0.0
        latest = latest_patrol_map()
        for wall in walls:
            patrol = latest.get(str(wall.get("编号") or "").strip())
            rate = rate_of(patrol)
            if rate is None or not patrol:
                continue
            point_total += int(patrol["巡检点数"])
            point_qualified += int(patrol["达标点数"])
        inspected = [w for w in walls if w["has_patrol"]]
        regions.append({
            "所属区域": area,
            "绿墙数量": len(walls),
            "总面积": round(sum(float(w.get("面积") or 0) for w in walls), 1),
            "rate_percent": round(point_qualified / point_total * 100, 1) if point_total else None,
            "inspected_count": len(inspected),
            "short_irrigation": any(w["short_irrigation"] for w in walls),
            "crew_missing_count": sum(1 for w in walls if w["crew_missing"]),
            "irrigation_missing_count": sum(1 for w in walls if w["irrigation_missing"]),
            "low_rate": (
                point_total > 0
                and point_qualified / point_total < LOW_RATE_THRESHOLD
            ),
        })

    def sort_key(region: dict[str, Any]) -> tuple[int, float, int, float]:
        rate = region["rate_percent"]
        missing = region["crew_missing_count"] + region["irrigation_missing_count"]
        # 0 档：缺灌；1 档：有达标率且偏低/正常按数值升序；2 档：暂无巡检
        bucket = 0 if region["short_irrigation"] else (2 if rate is None else 1)
        return bucket, rate if rate is not None else 0, -missing, -float(region["总面积"])

    return sorted(regions, key=sort_key)


def walls_of_region(area: str) -> list[dict[str, Any]]:
    """展开某个区域时返回其下绿墙明细，排序口径与区域列表一致。"""
    walls = [w for w in vertical_walls() if str(w.get("所属区域") or "") == area]

    def sort_key(wall: dict[str, Any]) -> tuple[int, float, float]:
        rate = wall["rate_percent"]
        bucket = 0 if wall["short_irrigation"] else (2 if rate is None else 1)
        return bucket, rate if rate is not None else 0, -float(wall.get("面积") or 0)

    return sorted(walls, key=sort_key)


def patrol_history(wall_code: str) -> list[dict[str, Any]]:
    """某面绿墙的全部巡检版本，最新版在前。"""
    rows = [
        row for row in store.rows(PATROL_MODULE)
        if str(row.get("绿墙编号") or "").strip() == wall_code
    ]
    rows.sort(key=lambda row: (str(row.get("巡检日期") or ""), int(row.get("id", 0))), reverse=True)
    return rows

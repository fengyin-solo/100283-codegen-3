"""立体绿化（垂直绿墙）业务规则。

达标率只有一个口径，就放在本模块：
- 巡检去重：同一片绿墙重复提交巡检时，只保留提交时间最新的一版（latest_inspection）；
- 绿墙达标率 = 最新一版巡检的「长势达标率」，没有任何巡检时为 None（前端显示「暂无」，而不是 0）；
- 区域达标率 = 区域内「有巡检的绿墙」按面积加权汇总，整片区域都没巡检时为 None。

区域下钻视图（region_summaries）与绿墙详情（build_wall_view）都调用同一份 build_wall_views，
保证列表页和详情页读到的达标率永远一致，不会各算一套。
"""
from __future__ import annotations

from typing import Any

from app.store import store

WALL_MODULE = "greenwall"
INSPECTION_MODULE = "greenwall_inspection"

# 达标率低于该阈值视为偏低，用于排序与标记
LOW_RATE_THRESHOLD = 0.85

# 巡检结果里这些灌溉结论都算「缺灌」
IRRIGATION_DEFECTS = {"缺灌", "滴灌堵塞", "滴灌带破损"}


def _clean(value: Any) -> str:
    """台账字段可能缺登记（None）或只填空格，统一收口成空串方便判断。"""
    return str(value).strip() if value is not None else ""


def parse_area(value: Any) -> float:
    """把面积文本解析成平方米；解析不出来按 0 处理，不参与加权。"""
    text = _clean(value)
    if not text:
        return 0.0
    digits = "".join(ch for ch in text if ch.isdigit() or ch in ".")
    try:
        area = float(digits) if digits else 0.0
    except ValueError:
        return 0.0
    if "万" in text:  # 形如「1.2万㎡」
        area *= 10000
    return area


def _parse_rate(value: Any) -> float | None:
    """达标率支持 86 / 86% / 0.86 三种写法，统一成 0~1 的小数。"""
    text = _clean(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit() or ch in ".")
    if not digits:
        return None
    try:
        rate = float(digits)
    except ValueError:
        return None
    if rate > 1:  # 86 或 86%
        rate /= 100
    return min(max(rate, 0.0), 1.0)


def _latest_submitted_at(inspection: dict[str, Any]) -> str:
    """提交时间缺失时退回巡检日期，保证去重排序稳定。"""
    return _clean(inspection.get("提交时间")) or _clean(inspection.get("巡检日期"))


def latest_inspections() -> dict[int, dict[str, Any]]:
    """按绿墙编号归并巡检，同一片绿墙只留提交时间最新的一版。"""
    latest: dict[int, dict[str, Any]] = {}
    for row in store.rows(INSPECTION_MODULE):
        try:
            wall_id = int(row.get("绿墙id", 0))
        except (TypeError, ValueError):
            continue
        current = latest.get(wall_id)
        if current is None or _latest_submitted_at(row) >= _latest_submitted_at(current):
            latest[wall_id] = row
    return latest


def build_wall_views() -> list[dict[str, Any]]:
    """把绿墙台账和最新巡检拼成一份带达标率的视图。列表页与详情页共用此结果。"""
    latest = latest_inspections()
    views: list[dict[str, Any]] = []
    for wall in store.rows(WALL_MODULE):
        wall_id = int(wall.get("id", 0))
        inspection = latest.get(wall_id)
        crew = _clean(wall.get("养护班组"))
        irrigation_method = _clean(wall.get("灌溉方式"))
        rate = _parse_rate(inspection.get("长势达标率")) if inspection else None
        irrigation_result = _clean(inspection.get("灌溉情况")) if inspection else ""
        views.append(
            {
                "id": wall_id,
                "绿墙编号": wall.get("绿墙编号"),
                "绿墙名称": wall.get("绿墙名称"),
                "所属区域": _clean(wall.get("所属区域")) or "未划分区域",
                "面积": _clean(wall.get("面积")),
                "面积平方米": parse_area(wall.get("面积")),
                "养护班组": crew,
                "灌溉方式": irrigation_method,
                "班组缺失": not crew,
                "灌溉方式缺失": not irrigation_method,
                "植物配置": wall.get("植物配置"),
                "绿墙状态": wall.get("绿墙状态"),
                "has_inspection": inspection is not None,
                "达标率": rate,
                "长势评价": _clean(inspection.get("长势评价")) if inspection else "",
                "灌溉情况": irrigation_result,
                "缺灌": inspection is not None and irrigation_result in IRRIGATION_DEFECTS,
                "达标率偏低": rate is not None and rate < LOW_RATE_THRESHOLD,
                "latest_inspection": inspection,
            }
        )
    return views


def _rank_key(view: dict[str, Any]) -> tuple[Any, ...]:
    """缺灌最靠前，其次达标率从低到高；无巡检（暂无）排在有数值之后，再按面积大到小。"""
    rate = view["达标率"]
    rate_order = 2.0 if rate is None else float(rate)
    return (
        0 if view["缺灌"] else 1,
        rate_order,
        -float(view["面积平方米"]),
        str(view["绿墙编号"]),
    )


def _weighted_rate(views: list[dict[str, Any]]) -> float | None:
    """区域达标率：有巡检的绿墙按面积加权；一片都没巡检则为 None（暂无）。"""
    inspected = [v for v in views if v["has_inspection"]]
    total_area = sum(float(v["面积平方米"]) for v in inspected)
    if total_area <= 0:
        # 面积台账缺失时退化成算术平均，仍然只算有巡检的绿墙
        rates = [float(v["达标率"]) for v in inspected if v["达标率"] is not None]
        return sum(rates) / len(rates) if rates else None
    return sum(
        float(v["达标率"]) * float(v["面积平方米"])
        for v in inspected
        if v["达标率"] is not None
    ) / total_area


def build_region_summaries() -> list[dict[str, Any]]:
    """按区域汇总垂直绿墙面积与达标率，并挂上排好序的绿墙明细供下钻展开。"""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for view in build_wall_views():
        grouped.setdefault(view["所属区域"], []).append(view)

    summaries: list[dict[str, Any]] = []
    for region, views in grouped.items():
        walls = sorted(views, key=_rank_key)
        rate = _weighted_rate(views)
        summaries.append(
            {
                "所属区域": region,
                "绿墙数量": len(views),
                "总面积平方米": round(sum(float(v["面积平方米"]) for v in views), 2),
                "达标率": round(rate, 4) if rate is not None else None,
                "has_inspection": any(v["has_inspection"] for v in views),
                "缺灌数量": sum(1 for v in views if v["缺灌"]),
                "无巡检数量": sum(1 for v in views if not v["has_inspection"]),
                "低达标数量": sum(1 for v in views if v["达标率偏低"]),
                "班组缺失数量": sum(1 for v in views if v["班组缺失"]),
                "灌溉方式缺失数量": sum(1 for v in views if v["灌溉方式缺失"]),
                "walls": walls,
            }
        )

    # 区域排序复用同一套优先级：缺灌 > 达标率低 > 暂无
    summaries.sort(
        key=lambda s: (
            0 if s["缺灌数量"] else 1,
            2.0 if s["达标率"] is None else float(s["达标率"]),
            -float(s["总面积平方米"]),
            s["所属区域"],
        )
    )
    return summaries


class GreenwallService:
    def region_summaries(self) -> list[dict[str, Any]]:
        return build_region_summaries()

    def get_wall_view(self, wall_id: int) -> dict[str, Any] | None:
        for view in build_wall_views():
            if view["id"] == wall_id:
                return view
        return None

    def inspection_history(self, wall_id: int) -> list[dict[str, Any]]:
        """一片绿墙的全部巡检版本，按提交时间倒序（最新一版在最前）。"""
        rows = [
            row
            for row in store.rows(INSPECTION_MODULE)
            if int(row.get("绿墙id", 0) or 0) == wall_id
        ]
        return sorted(rows, key=_latest_submitted_at, reverse=True)

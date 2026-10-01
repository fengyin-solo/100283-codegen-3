"""立体绿化（垂直绿墙）接口：区域达标率下钻视图与绿墙详情。

达标率由 services.greenwall 统一计算，本层只负责把结果暴露出去，
保证区域视图、绿墙详情以及其它页面取到的是同一份口径。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.greenwall import GreenwallService

router = APIRouter(prefix="/api/greenwall", tags=["立体绿化"])

service = GreenwallService()


@router.get("/regions")
def region_summaries() -> dict[str, object]:
    """区域下钻视图：区域面积/达标率置顶排列，walls 字段为该区域的绿墙明细。"""
    items = service.region_summaries()
    return {"items": items, "total": len(items)}


@router.get("/walls/{wall_id}")
def wall_detail(wall_id: int) -> dict[str, object]:
    """绿墙详情：达标率与区域视图来自同一计算结果，另附全部巡检版本。"""
    wall = service.get_wall_view(wall_id)
    if wall is None:
        raise HTTPException(status_code=404, detail=f"垂直绿墙 {wall_id} 不存在或已归档")
    return {"wall": wall, "inspections": service.inspection_history(wall_id)}


@router.get("/walls/{wall_id}/rate")
def wall_rate(wall_id: int) -> dict[str, object]:
    """给其它页面用的达标率读数：没有巡检时 rate=null、has_inspection=false，绝不返回 0 冒充。"""
    wall = service.get_wall_view(wall_id)
    if wall is None:
        raise HTTPException(status_code=404, detail=f"垂直绿墙 {wall_id} 不存在或已归档")
    return {
        "id": wall["id"],
        "绿墙编号": wall["绿墙编号"],
        "达标率": wall["达标率"],
        "has_inspection": wall["has_inspection"],
    }

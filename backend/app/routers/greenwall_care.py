"""垂直绿墙养护下钻视图接口：区域汇总 + 区域内绿墙明细。

只读视图，不保存任何达标率结果——全部实时调用共享口径服务，
保证和立体绿化台账、详情页读到的达标率永远是同一份。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services import greenwall as stats

router = APIRouter(prefix="/api/greenwall-care", tags=["垂直绿墙养护视图"])


@router.get("/regions")
def list_regions() -> dict[str, object]:
    """按区域列出垂直绿墙面积与加权长势达标率。

    排序：缺灌 → 达标率偏低升序 → 暂无巡检压最后。
    """
    regions = stats.region_overview()
    return {
        "items": regions,
        "total": len(regions),
        "low_rate_threshold": stats.LOW_RATE_THRESHOLD,
    }


@router.get("/regions/{area}/walls")
def list_region_walls(area: str) -> dict[str, object]:
    """下钻：展开某区域下的具体绿墙，未巡检的达标率为 null（前端显示“暂无”）。"""
    walls = stats.walls_of_region(area)
    if not walls:
        raise HTTPException(status_code=404, detail=f"区域「{area}」下没有垂直绿墙")
    return {"area": area, "items": walls, "total": len(walls)}

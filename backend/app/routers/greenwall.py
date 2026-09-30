"""立体绿化台账接口：垂直绿墙/屋顶花园的登记、筛选、详情与巡检提交。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.greenwall_crud import GreenwallService

router = APIRouter(prefix="/api/greenwall", tags=["立体绿化台账"])

service = GreenwallService()

LIST_FIELDS = ["编号", "名称", "绿化类型", "所属区域", "面积", "养护班组", "灌溉方式"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按编号或名称检索"),
    area: str | None = Query(default=None, description="按所属区域筛选"),
    green_type: str | None = Query(default=None, description="垂直绿墙或屋顶花园"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """立体绿化台账列表；每条记录直接带共享口径算出的 rate_percent。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(
        keyword=keyword, area=area, green_type=green_type, page=page, size=size
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """立体绿化详情：含统一口径达标率与全部历史巡检版本。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"立体绿化 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一片垂直绿墙或屋顶花园；养护班组、灌溉方式允许后补，但会在视图中标缺。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="立体绿化已登记", entry=entry)


@router.post("/{entry_id}/patrols", response_model=ActionResult)
def submit_patrol(entry_id: int, payload: EntryPayload) -> ActionResult:
    """提交一版巡检；重复提交后各页面只认最新版。"""
    record, message = service.submit_patrol(entry_id, payload.values)
    if record is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=record)

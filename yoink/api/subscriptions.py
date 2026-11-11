from fastapi import APIRouter, HTTPException, Request

from .. import db, scheduler
from ..models import SubscriptionIn, SubscriptionOut

router = APIRouter()


@router.get("/subscriptions")
async def list_subscriptions() -> list[SubscriptionOut]:
    return [SubscriptionOut.from_row(row) for row in db.list_subscriptions()]


@router.post("/subscriptions", status_code=201)
async def create_subscription(sub: SubscriptionIn) -> SubscriptionOut:
    sub_id = db.create_subscription(
        sub.name, sub.url, sub.preset_id, sub.enabled, sub.check_interval_minutes,
        sub.filters.model_dump_json(),
    )
    return SubscriptionOut.from_row(db.get_subscription(sub_id))


@router.put("/subscriptions/{sub_id}")
async def update_subscription(sub_id: int, sub: SubscriptionIn) -> SubscriptionOut:
    if not db.update_subscription(
        sub_id, sub.name, sub.url, sub.preset_id, sub.enabled, sub.check_interval_minutes,
        sub.filters.model_dump_json(),
    ):
        raise HTTPException(404, "no such subscription")
    return SubscriptionOut.from_row(db.get_subscription(sub_id))


@router.delete("/subscriptions/{sub_id}")
async def delete_subscription(sub_id: int) -> dict:
    if not db.delete_subscription(sub_id):
        raise HTTPException(404, "no such subscription")
    return {"ok": True}


@router.post("/subscriptions/{sub_id}/check")
async def check_now(sub_id: int, request: Request) -> dict:
    if db.get_subscription(sub_id) is None:
        raise HTTPException(404, "no such subscription")
    return await scheduler.check_subscription(
        sub_id, request.app.state.jobs, request.app.state.broadcaster
    )


@router.post("/subscriptions/{sub_id}/seed")
async def seed(sub_id: int) -> dict:
    try:
        count = await scheduler.seed_subscription(sub_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        raise HTTPException(422, str(exc))
    return {"seeded": count}

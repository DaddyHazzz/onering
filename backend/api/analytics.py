from fastapi import APIRouter, Query
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

router = APIRouter()

class RingEarnings(BaseModel):
	date: str
	total: float


def _mock_fetch_user_posts(user_id: str, start: datetime, end: datetime) -> List[Dict[str, Any]]:
	# TODO: replace with real DB queries (currently deterministic mock)
	return [
		{"createdAt": start + timedelta(hours=1), "ringEarned": 25},
		{"createdAt": start + timedelta(hours=12), "ringEarned": 40},
		{"createdAt": end - timedelta(hours=2), "ringEarned": 15},
	]


def _aggregate(posts: List[Dict[str, Any]], key_fn) -> List[Dict[str, Any]]:
	"""Pure deterministic reducer used for both daily/weekly buckets."""
	buckets: Dict[str, float] = {}
	for p in posts:
		key = key_fn(p["createdAt"])
		buckets[key] = buckets.get(key, 0.0) + float(p.get("ringEarned", 0))
	return [RingEarnings(date=k, total=v).model_dump() for k, v in sorted(buckets.items())]


@router.get("/ring/daily")
def ring_daily(userId: str = Query(..., description="Clerk user id")) -> Dict[str, Any]:
	now = datetime.now(timezone.utc)
	start = now - timedelta(days=7)
	posts = _mock_fetch_user_posts(userId, start, now)
	series = _aggregate(posts, lambda dt: dt.strftime("%Y-%m-%d")) if posts else []
	return {"userId": userId, "range": "7d", "series": series}


@router.get("/ring/weekly")
def ring_weekly(userId: str = Query(..., description="Clerk user id")) -> Dict[str, Any]:
	now = datetime.now(timezone.utc)
	start = now - timedelta(days=35)
	posts = _mock_fetch_user_posts(userId, start, now)

	def week_key(dt: datetime) -> str:
		iso_year, iso_week, _ = dt.isocalendar()
		return f"{iso_year}-W{iso_week:02d}"

	series = _aggregate(posts, week_key) if posts else []
	return {"userId": userId, "range": "5w", "series": series}

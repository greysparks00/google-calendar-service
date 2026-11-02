import json
import logging
from datetime import date, datetime, time
from typing import Any, Callable
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Query, HTTPException, Response
from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import HttpError
from pydantic import BaseModel, Field, field_validator

from calendar_client import (
	get_future_events,
	get_event,
	create_calendar_event,
	delete_calendar_event
)

router = APIRouter()
logger = logging.getLogger(__name__)

TIME_ZONE = ZoneInfo("America/Chicago")

# converts Google Calendar errors to HTTP errors
def handle_google_error(error: HttpError) -> HTTPException:
	status = error.resp.status

	if status == 400:
		return HTTPException(
			status_code=400,
			detail="Invalid calendar request."
		)

	if status == 401:
		return HTTPException(
			status_code=503,
			detail="Google authentication needs renewal."
		)

	if status == 403:
		# Google can also return 403 for rate limits
		try:
			data = json.loads(error.content)
			reasons = {
				item.get("reason")
				for item in data.get("error", {}).get("errors", [])
				if isinstance(item, dict)
			}
		except (ValueError, TypeError, AttributeError):
			reasons = set()

		if reasons.intersection({
			"rateLimitExceeded",
			"userRateLimitExceeded",
			"quotaExceeded",
			"dailyLimitExceeded"
		}):
			return HTTPException(
				status_code=503,
				detail="Google Calendar rate limit reached."
			)

		return HTTPException(
			status_code=403,
			detail="Google Calendar denied the request."
		)

	if status == 404:
		return HTTPException(
			status_code=404,
			detail="Event not found."
		)

	if status == 409:
		return HTTPException(
			status_code=409,
			detail="Calendar event conflict."
		)

	if status == 429:
		return HTTPException(
			status_code=503,
			detail="Google Calendar rate limit reached."
		)

	if status >= 500:
		return HTTPException(
			status_code=502,
			detail="Google Calendar is temporarily unavailable."
		)

	return HTTPException(
		status_code=502,
		detail="Google Calendar request failed."
	)

# runs a Calendar operation and handles service errors
def run_google_call(
	function: Callable[..., Any],
	*args: Any,
	**kwargs: Any
) -> Any:
	try:
		return function(*args, **kwargs)

	except HttpError as error:
		logger.warning(
			"Google Calendar returned HTTP %s",
			error.resp.status
		)
		raise handle_google_error(error) from error

	except httpx.HTTPStatusError as error:
		logger.error(
			"GoogleAuth returned HTTP %s",
			error.response.status_code
		)
		raise HTTPException(
			status_code=503,
			detail="Unable to obtain Google credentials."
		) from error

	except httpx.TimeoutException as error:
		logger.warning("GoogleAuth request timed out.")
		raise HTTPException(
			status_code=503,
			detail="Google authentication service timed out."
		) from error

	except httpx.RequestError as error:
		logger.warning(
			"GoogleAuth connection failed: %s",
			type(error).__name__
		)
		raise HTTPException(
			status_code=503,
			detail="Google authentication service is unavailable."
		) from error

	except GoogleAuthError as error:
		logger.exception("Google authentication failed.")
		raise HTTPException(
			status_code=503,
			detail="Google authentication failed."
		) from error

# returns calendar events
@router.get("/events")
def get_events(
	limit: int = Query(10, ge=1, le=100),
	start: date | None = None,
	end: date | None = None
):
	start_at = (
		datetime.combine(start, time.min, tzinfo=TIME_ZONE)
		if start is not None
		else datetime.now(TIME_ZONE)
	)

	end_at = (
		datetime.combine(end, time.min, tzinfo=TIME_ZONE)
		if end is not None
		else None
	)

	if end_at is not None and start_at >= end_at:
		raise HTTPException(
			status_code=400,
			detail="End must be after start."
		)

	events = run_google_call(
		get_future_events,
		limit,
		start_at.isoformat(),
		end_at.isoformat() if end_at else None
	)

	if not isinstance(events, dict) or not isinstance(
		events.get("items"), list
	):
		logger.error("Unexpected Google Calendar events response.")
		raise HTTPException(
			status_code=502,
			detail="Invalid response from Google Calendar."
		)

	return {
		"data": {
			"events": events["items"]
		}
	}

# returns an individual calendar event
@router.get("/events/{event_id}")
def get_event_from_id(event_id: str):
	event = run_google_call(get_event, event_id)

	return {
		"data": {
			"event": event
		}
	}

# request schema for creating events
class CreateEventRequest(BaseModel):
	summary: str = Field(min_length=1)
	description: str = ""
	start: datetime
	end: datetime

	@field_validator("summary")
	@classmethod
	def validate_summary(cls, value: str) -> str:
		value = value.strip()

		if not value:
			raise ValueError("Event title cannot be empty.")

		return value

# converts supplied timestamps to Chicago time
def normalize_datetime(value: datetime) -> datetime:
	if value.tzinfo is None:
		return value.replace(tzinfo=TIME_ZONE)

	return value.astimezone(TIME_ZONE)

# creates a calendar event
@router.post("/events", status_code=201)
def create_event(request: CreateEventRequest):
	start = normalize_datetime(request.start)
	end = normalize_datetime(request.end)

	if end.timestamp() <= start.timestamp():
		raise HTTPException(
			status_code=400,
			detail="End must be after start."
		)

	event = run_google_call(
		create_calendar_event,
		summary=request.summary,
		description=request.description,
		start=start.isoformat(),
		end=end.isoformat()
	)

	return {
		"data": {
			"event": event
		}
	}

# deletes a calendar event
@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: str):
	run_google_call(delete_calendar_event, event_id)

	return Response(status_code=204)
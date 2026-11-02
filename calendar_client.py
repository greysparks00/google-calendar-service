from googleapiclient.discovery import build
from google_auth_client import get_google_credentials

# creates the google calendar credential object for the calendar
def get_calendar_service():
	return build(
		"calendar",
		"v3",
		credentials=get_google_credentials()
	)

# returns future events
def get_future_events(limit, start, end):
    service = get_calendar_service()

    params = {
        "calendarId": "primary",
        "timeMin": start,
        "maxResults": limit,
        "singleEvents": True,
        "orderBy": "startTime"
    }

    if end is not None:
        params["timeMax"] = end

    return service.events().list(**params).execute()

# returns an event from a provided id
def get_event(event_id: str):
    service = get_calendar_service()
    
    event = service.events().get(
        calendarId="primary",
        eventId=event_id
    ).execute()
    
    return event

# creates a google calendar event
def create_calendar_event(summary: str, description: str, start: str, end: str):
    service = get_calendar_service()

    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start,
            "timeZone": "America/Chicago"
        },
        "end": {
            "dateTime": end,
            "timeZone": "America/Chicago"
        }
    }

    return service.events().insert(calendarId="primary", body=event).execute()

# deletes a calendar event
def delete_calendar_event(event_id: str):
    service = get_calendar_service()

    service.events().delete(
        calendarId="primary",
        eventId=event_id
    ).execute()
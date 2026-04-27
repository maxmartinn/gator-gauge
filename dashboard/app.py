import re
from datetime import date, datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import charts
import data_access
import model as gym_model
import transforms


DATA_CACHE_VERSION = 2
LOCAL_TZ = ZoneInfo("America/New_York")

CLASS_SCHEDULE_ROWS = [
    {"date": "Thu, 4/23/2026", "time": "10:00am", "name": "HIIT Pilates (60)", "location": "Southwest 3", "instructor": "Lana", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=378eae7b-0d6d-4f8a-837e-48f72138946c"},
    {"date": "Thu, 4/23/2026", "time": "12:00pm", "name": "Total Body (45)", "location": "Southwest 3", "instructor": "Paige", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=92da19bf-18a3-4c7e-ba87-79b41de0580e"},
    {"date": "Thu, 4/23/2026", "time": "5:00pm", "name": "Cycle Circuits (60)", "location": "Southwest 1", "instructor": "Abby", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=1681069e-b4eb-4407-96ca-0c1b53d9a7ae"},
    {"date": "Thu, 4/23/2026", "time": "7:00pm", "name": "Cycle (45)", "location": "Student Rec 1", "instructor": "Camila", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=1681069e-b4eb-4407-96ca-0c1b53d9a7ae"},
    {"date": "Thu, 4/23/2026", "time": "8:30pm", "name": "Hip Hop Cardio (60)", "location": "Student Rec 2", "instructor": "Steph", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=536a8377-b6c1-45d8-805f-6487588d25ed"},
    {"date": "Thu, 4/23/2026", "time": "9:00pm", "name": "Gentle Yoga (60)", "location": "Southwest 3", "instructor": "Jaylynn", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=2aea470a-1d3e-40a1-9246-f3079427720f"},
    {"date": "Fri, 4/24/2026", "time": "8:30am", "name": "Cycle (45)", "location": "Student Rec 1", "instructor": "Ella", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=e42c53c7-5ba3-4774-8b75-d4d3e47e9325"},
    {"date": "Fri, 4/24/2026", "time": "9:30am", "name": "Total Body (45)", "location": "Student Rec 2", "instructor": "Camila", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=e4c6ec4c-2abd-4f07-85d4-7a5a49150b4c"},
    {"date": "Fri, 4/24/2026", "time": "10:00am", "name": "Yogalates (60)", "location": "Student Rec 3", "instructor": "Julia", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=f8109061-688b-4c36-9e54-ed957e2b8439"},
    {"date": "Fri, 4/24/2026", "time": "3:30pm", "name": "Yogalates (60)", "location": "Student Rec 3", "instructor": "Marley", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=f8109061-688b-4c36-9e54-ed957e2b8439"},
    {"date": "Fri, 4/24/2026", "time": "5:00pm", "name": "Hip Hop Cardio (60)", "location": "Student Rec 3", "instructor": "Steph", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=7e1b08ab-468b-4a9d-a24d-eb089d1fd0d2"},
    {"date": "Fri, 4/24/2026", "time": "7:15pm", "name": "Cycle Circuits (60)", "location": "Southwest 1", "instructor": "Grace R.", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=1681069e-b4eb-4407-96ca-0c1b53d9a7ae"},
    {"date": "Sat, 4/25/2026", "time": "9:00am", "name": "Vinyasa Yoga (60)", "location": "Southwest 3", "instructor": "Kate", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=c3d4feef-5bc8-4507-9814-2e9cfe4b87af"},
    {"date": "Sat, 4/25/2026", "time": "12:30pm", "name": "Total Body (45)", "location": "Student Rec 2", "instructor": "Camila", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=e4c6ec4c-2abd-4f07-85d4-7a5a49150b4c"},
    {"date": "Sat, 4/25/2026", "time": "1:45pm", "name": "Mat Pilates (60)", "location": "Southwest 3", "instructor": "Sydney", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=f57f66bb-7391-4c4d-9fe8-64336c01e2d1"},
    {"date": "Sat, 4/25/2026", "time": "4:30pm", "name": "Hip Hop Cardio (60)", "location": "Student Rec 2", "instructor": "Steph", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=536a8377-b6c1-45d8-805f-6487588d25ed"},
    {"date": "Sun, 4/26/2026", "time": "10:00am", "name": "Vinyasa Yoga (60)", "location": "Southwest 3", "instructor": "Kate", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=c3d4feef-5bc8-4507-9814-2e9cfe4b87af"},
    {"date": "Sun, 4/26/2026", "time": "12:30pm", "name": "Cycle (45)", "location": "Student Rec 1", "instructor": "Ella", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=e42c53c7-5ba3-4774-8b75-d4d3e47e9325"},
    {"date": "Sun, 4/26/2026", "time": "3:00pm", "name": "Yogalates (60)", "location": "Student Rec 3", "instructor": "Natanya", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=f8109061-688b-4c36-9e54-ed957e2b8439"},
    {"date": "Sun, 4/26/2026", "time": "5:30pm", "name": "Gentle Yoga (60)", "location": "Southwest 3", "instructor": "Jaylynn", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=2aea470a-1d3e-40a1-9246-f3079427720f"},
    {"date": "Mon, 4/27/2026", "time": "8:30am", "name": "Vinyasa Yoga (60)", "location": "Southwest 3", "instructor": "Kate", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=c3d4feef-5bc8-4507-9814-2e9cfe4b87af"},
    {"date": "Mon, 4/27/2026", "time": "10:15am", "name": "Cycle (45)", "location": "Student Rec 1", "instructor": "Camila", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=e42c53c7-5ba3-4774-8b75-d4d3e47e9325"},
    {"date": "Mon, 4/27/2026", "time": "10:00am", "name": "Abs, Booty, & Core (45)", "location": "Southwest 3", "instructor": "Allison", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=301af7e0-130f-4699-91e7-ebbd0d929cc8"},
    {"date": "Mon, 4/27/2026", "time": "11:30am", "name": "Total Body (45)", "location": "Student Rec 2", "instructor": "Caroline", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=e4c6ec4c-2abd-4f07-85d4-7a5a49150b4c"},
    {"date": "Mon, 4/27/2026", "time": "12:00pm", "name": "Yogalates (60)", "location": "Student Rec 3", "instructor": "Marley", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=f8109061-688b-4c36-9e54-ed957e2b8439"},
    {"date": "Mon, 4/27/2026", "time": "6:30pm", "name": "Hip Hop Cardio (60)", "location": "Student Rec 3", "instructor": "Sydney", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=7e1b08ab-468b-4a9d-a24d-eb089d1fd0d2"},
    {"date": "Tue, 4/28/2026", "time": "8:30am", "name": "Vinyasa Yoga (60)", "location": "Southwest 3", "instructor": "Kate", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=c3d4feef-5bc8-4507-9814-2e9cfe4b87af"},
    {"date": "Tue, 4/28/2026", "time": "10:30am", "name": "Mat Pilates (60)", "location": "Student Rec 3", "instructor": "Sydney", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=be72886e-4355-4bdf-be1a-192ae47a6a1d"},
    {"date": "Tue, 4/28/2026", "time": "10:15am", "name": "Cycle (45)", "location": "Student Rec 1", "instructor": "Camila", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=e42c53c7-5ba3-4774-8b75-d4d3e47e9325"},
    {"date": "Tue, 4/28/2026", "time": "11:30am", "name": "Total Body (45)", "location": "Student Rec 2", "instructor": "Caroline", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=e4c6ec4c-2abd-4f07-85d4-7a5a49150b4c"},
    {"date": "Tue, 4/28/2026", "time": "2:00pm", "name": "Pilates Fusion (60)", "location": "Student Rec 3", "instructor": "Cait", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=ef8b2128-7eb6-4ee8-a814-53f283e91e69"},
    {"date": "Tue, 4/28/2026", "time": "4:30pm", "name": "Studio Cycle (45) - Senior Send-Off!", "location": "Southwest 1", "instructor": "Madi C.", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=94de92b6-50bb-4d4d-85bc-b7d8ff6702a0"},
    {"date": "Tue, 4/28/2026", "time": "7:15pm", "name": "Vinyasa Yoga (60)", "location": "Southwest 3", "instructor": "Jaiden B.", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=c3d4feef-5bc8-4507-9814-2e9cfe4b87af"},
    {"date": "Tue, 4/28/2026", "time": "7:30pm", "name": "Hip Hop Cardio (60)", "location": "Student Rec 2", "instructor": "Steph", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=536a8377-b6c1-45d8-805f-6487588d25ed"},
    {"date": "Wed, 4/29/2026", "time": "8:00am", "name": "Cycle Circuits (60)", "location": "Southwest 1", "instructor": "Abby", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=1681069e-b4eb-4407-96ca-0c1b53d9a7ae"},
    {"date": "Wed, 4/29/2026", "time": "9:30am", "name": "Vinyasa Yoga (60)", "location": "Southwest 3", "instructor": "Kate", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=c3d4feef-5bc8-4507-9814-2e9cfe4b87af"},
    {"date": "Wed, 4/29/2026", "time": "10:30am", "name": "Total Body (45)", "location": "Student Rec 2", "instructor": "Caroline", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=e4c6ec4c-2abd-4f07-85d4-7a5a49150b4c"},
    {"date": "Wed, 4/29/2026", "time": "2:00pm", "name": "Pilates Fusion (60)", "location": "Student Rec 3", "instructor": "Cait", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=ef8b2128-7eb6-4ee8-a814-53f283e91e69"},
    {"date": "Wed, 4/29/2026", "time": "3:30pm", "name": "Abs, Booty, & Core (45)", "location": "Student Rec 2", "instructor": "Allison", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=4fd9157f-7349-4e57-8b05-c90f4cefe76b"},
    {"date": "Wed, 4/29/2026", "time": "4:30pm", "name": "Cycle Circuits (60)", "location": "Southwest 1", "instructor": "Grace R.", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=1681069e-b4eb-4407-96ca-0c1b53d9a7ae"},
    {"date": "Wed, 4/29/2026", "time": "6:00pm", "name": "Power Yoga (60)", "location": "Student Rec 3", "instructor": "Kayla", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=081a9637-7dd5-4765-8839-92957ce4d283"},
    {"date": "Wed, 4/29/2026", "time": "7:00pm", "name": "Hip Hop Cardio (60)", "location": "Student Rec 2", "instructor": "Steph", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=536a8377-b6c1-45d8-805f-6487588d25ed"},
    {"date": "Thu, 4/30/2026", "time": "10:30am", "name": "Cycle (45)", "location": "Student Rec 1", "instructor": "Camila", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=e42c53c7-5ba3-4774-8b75-d4d3e47e9325"},
    {"date": "Thu, 4/30/2026", "time": "12:00pm", "name": "Total Body (45)", "location": "Student Rec 2", "instructor": "Paige", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=e4c6ec4c-2abd-4f07-85d4-7a5a49150b4c"},
    {"date": "Thu, 4/30/2026", "time": "6:30pm", "name": "Power Yoga (60)", "location": "Student Rec 3", "instructor": "Kayla", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=e4c6ec4c-2abd-4f07-85d4-7a5a49150b4c"},
    {"date": "Thu, 4/30/2026", "time": "8:30pm", "name": "Yin Yoga (60)", "location": "Southwest 3", "instructor": "Jaylynn", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=d9b9e48a-101b-49df-8d1b-f7a57eb5e8de"},
    {"date": "Fri, 5/1/2026", "time": "12:00pm", "name": "Cycle (45)", "location": "Student Rec 1", "instructor": "Camila", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=e4c6ec4c-2abd-4f07-85d4-7a5a49150b4c"},
    {"date": "Fri, 5/1/2026", "time": "5:15pm", "name": "Power Yoga (60)", "location": "Southwest 3", "instructor": "Kayla", "url": "https://rsconnect.recsports.ufl.edu/Program/GetProgramDetails?courseId=82db239e-a6e6-43a0-ac19-3cc4abb94223"},
]

CAMERA_SECTIONS = [
    {
        "title": "SWRC Weight Room 1",
        "image_url": "https://recsports.ufl.edu/cam/cam1.jpg",
        "members": ["SWRC Weight Room"],
    },
    {
        "title": "SWRC Weight Room 2",
        "image_url": "https://recsports.ufl.edu/cam/cam4.jpg",
        "members": ["SWRC Weight Room"],
    },
    {
        "title": "SWRC Cardio",
        "image_url": "https://recsports.ufl.edu/cam/cam5.jpg",
        "members": ["SWRC Cardio Room 1", "SWRC Cardio Room 2"],
    },
    {
        "title": "SWRC Courts 1 & 2",
        "image_url": "https://recsports.ufl.edu/cam/cam3.jpg",
        "members": ["Multi-Purpose Court 1", "Multi-Purpose Court 2"],
    },
    {
        "title": "SWRC Courts 3 & 4",
        "image_url": "https://recsports.ufl.edu/cam/cam2.jpg",
        "members": ["Multi-Purpose Court 3", "Multi-Purpose Court 4"],
    },
    {
        "title": "SWRC Courts 5 & 6",
        "image_url": "https://recsports.ufl.edu/cam/cam6.jpg",
        "members": ["Multi-Purpose Court 5", "Multi-Purpose Court 6"],
    },
    {
        "title": "SRFC Weight Room North",
        "image_url": "https://recsports.ufl.edu/cam/cam8.jpg",
        "members": ["SRFC Weight Room"],
    },
    {
        "title": "SRFC Weight Room South",
        "image_url": "https://recsports.ufl.edu/cam/cam7.jpg",
        "members": ["SRFC Weight Room"],
    },
]


def format_hour(hour: int) -> str:
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour} {suffix}"


def parse_class_datetime(class_row: dict) -> datetime:
    date_text = class_row["date"].split(", ", 1)[1]
    time_text = class_row["time"].upper()
    return datetime.strptime(
        f"{date_text} {time_text}",
        "%m/%d/%Y %I:%M%p",
    ).replace(tzinfo=LOCAL_TZ)


def class_duration_minutes(class_name: str) -> int:
    match = re.search(r"\((\d+)\)", class_name)
    return int(match.group(1)) if match else 60


def class_category(class_name: str) -> str:
    lowered = class_name.lower()
    if "cycle" in lowered:
        return "Cycle"
    if "yoga" in lowered or "pilates" in lowered or "sound bath" in lowered or "yin" in lowered:
        return "Mind & Body"
    if "hip hop" in lowered or "dance" in lowered:
        return "Dance"
    if "hiit" in lowered or "total body" in lowered or "core" in lowered or "booty" in lowered:
        return "Strength"
    return "Cardio"


def format_class_datetime(class_row: dict) -> str:
    start = parse_class_datetime(class_row)
    return start.strftime("%a, %b %-d at %-I:%M %p")


def ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def make_class_ics(class_row: dict) -> bytes:
    start = parse_class_datetime(class_row)
    end = start + timedelta(minutes=class_duration_minutes(class_row["name"]))
    uid_base = f"{class_row['name']}-{class_row['date']}-{class_row['time']}-{class_row['location']}"
    uid = re.sub(r"[^A-Za-z0-9]+", "-", uid_base).strip("-").lower()
    description = (
        f"Instructor: {class_row['instructor']}\\n"
        f"Class details: {class_row['url']}\\n"
        "Source: UF RecSports Classes"
    )
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Gator Gauge//UF RecSports Classes//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}@gator-gauge.local",
        f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;TZID=America/New_York:{start.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID=America/New_York:{end.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{ics_escape(class_row['name'])}",
        f"LOCATION:{ics_escape(class_row['location'])}",
        f"DESCRIPTION:{ics_escape(description)}",
        f"URL:{class_row['url']}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


def class_filename(class_row: dict) -> str:
    start = parse_class_datetime(class_row)
    slug = re.sub(r"[^a-z0-9]+", "-", class_row["name"].lower()).strip("-")
    return f"{start.strftime('%Y%m%d-%H%M')}-{slug}.ics"


def format_timestamp(value) -> str:
    if pd.isna(value):
        return "No update time"
    local = pd.Timestamp(value)
    if local.tzinfo is None:
        local = local.tz_localize("UTC")
    local = local.tz_convert("America/New_York")
    return local.strftime("%b %d, %I:%M %p").replace(" 0", " ")


def occupancy_tone(percent_full: float) -> tuple[str, str]:
    if pd.isna(percent_full):
        return "No Count", "neutral"
    if percent_full >= 80:
        return "Very Busy", "danger"
    if percent_full >= 60:
        return "Busy", "warning"
    if percent_full >= 30:
        return "Moderate", "notice"
    return "Not Busy", "good"


st.set_page_config(
    page_title="Gator Gauge - UF Gym Dashboard",
    layout="wide",
)

st.title("Gator Gauge - UF Gym Occupancy Dashboard")
st.caption("Historical trends and Ridge regression occupancy predictions for UF recreational facilities.")

st.markdown(
    """
    <style>
    .camera-page {
        border-top: 6px solid #0021a5;
        padding-top: 1rem;
    }
    .camera-kicker {
        color: #fa4616;
        font-weight: 800;
        letter-spacing: .08em;
        text-transform: uppercase;
        margin-bottom: .25rem;
    }
    .camera-hero {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 1rem;
        border-bottom: 1px solid #d7dce5;
        margin-bottom: 1.25rem;
        padding-bottom: 1rem;
    }
    .camera-hero h2 {
        color: #0021a5;
        font-size: 2.2rem;
        font-weight: 900;
        margin: 0;
    }
    .camera-hero__meta {
        color: #4d5d73;
        font-size: .95rem;
        text-align: right;
    }
    .camera-alert {
        background: #fff3ef;
        border-left: 5px solid #fa4616;
        color: #882700;
        font-size: 1.05rem;
        font-weight: 800;
        margin: .5rem 0 1.5rem;
        padding: .85rem 1rem;
    }
    .camera-card {
        background: #ffffff;
        border: 1px solid #d8dee8;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 33, 165, .08);
        margin-bottom: 1.5rem;
        overflow: hidden;
    }
    .camera-card__header {
        align-items: center;
        background: #0021a5;
        display: flex;
        justify-content: space-between;
        gap: .75rem;
        padding: .8rem 1rem;
    }
    .camera-card__header h3 {
        color: #ffffff;
        font-size: 1.05rem;
        font-weight: 800;
        margin: 0;
    }
    .camera-card__status {
        border-radius: 999px;
        color: #ffffff;
        flex: 0 0 auto;
        font-size: .75rem;
        font-weight: 800;
        padding: .25rem .55rem;
    }
    .camera-card__status--good { background: #16833a; }
    .camera-card__status--notice { background: #2f6fbd; }
    .camera-card__status--warning { background: #b65c00; }
    .camera-card__status--danger { background: #b42318; }
    .camera-card__status--neutral { background: #687386; }
    .camera-card__image {
        aspect-ratio: 16 / 9;
        display: block;
        object-fit: cover;
        width: 100%;
    }
    .camera-card__footer {
        align-items: center;
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        padding: .85rem 1rem 1rem;
    }
    .camera-card__count {
        color: #0021a5;
        font-size: 1.6rem;
        font-weight: 900;
        line-height: 1.1;
    }
    .camera-card__percent {
        color: #4d5d73;
        font-weight: 700;
        margin-top: .15rem;
    }
    .camera-card__updated {
        color: #687386;
        font-size: .85rem;
        text-align: right;
    }
    .classes-page {
        border-top: 6px solid #fa4616;
        padding-top: 1rem;
    }
    .classes-hero {
        border-bottom: 1px solid #d7dce5;
        margin-bottom: 1rem;
        padding-bottom: 1rem;
    }
    .classes-hero h2 {
        color: #0021a5;
        font-size: 2.2rem;
        font-weight: 900;
        margin: 0;
    }
    .classes-subhead {
        color: #27364a;
        font-size: 1rem;
        margin-top: .35rem;
    }
    .color-guide {
        display: grid;
        gap: .6rem;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        margin: 1rem 0 1.25rem;
    }
    .color-guide__item {
        border: 1px solid #d8dee8;
        border-radius: 8px;
        font-size: .88rem;
        font-weight: 800;
        padding: .55rem .7rem;
    }
    .class-card {
        border: 1px solid #d8dee8;
        border-left: 6px solid #687386;
        border-radius: 8px;
        margin-bottom: .85rem;
        padding: .85rem 1rem;
    }
    .class-card--strength { border-left-color: #16833a; }
    .class-card--mind-body { border-left-color: #b42318; }
    .class-card--cycle { border-left-color: #2f6fbd; }
    .class-card--dance { border-left-color: #d95f02; }
    .class-card--cardio { border-left-color: #7a3db8; }
    .class-card__time {
        color: #fa4616;
        font-size: .9rem;
        font-weight: 900;
        letter-spacing: .03em;
        text-transform: uppercase;
    }
    .class-card__title {
        color: #0021a5;
        font-size: 1.15rem;
        font-weight: 900;
        margin-top: .1rem;
    }
    .class-card__meta {
        color: #4d5d73;
        font-weight: 700;
        margin-top: .25rem;
    }
    .class-card__category {
        color: #27364a;
        font-size: .86rem;
        font-weight: 800;
        margin-top: .35rem;
    }
    @media (max-width: 760px) {
        .camera-hero {
            align-items: flex-start;
            flex-direction: column;
        }
        .camera-hero__meta,
        .camera-card__updated {
            text-align: left;
        }
        .camera-card__footer {
            align-items: flex-start;
            flex-direction: column;
        }
        .color-guide {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Catalog: locations + available date range ─────────────────────────────────
# Both functions are @st.cache_data(ttl=3600) inside data_access, so this is fast after first run.

all_locations = data_access.get_available_locations()
available_dates = data_access.get_available_dates()

if not all_locations:
    st.error("Cannot reach S3 or no location partitions were found. Check AWS credentials.")
    st.stop()

if not available_dates:
    st.error("No date partitions found under bronze/gym_counts. The bucket may be empty.")
    st.stop()

min_data_date = available_dates[0]
max_data_date = available_dates[-1]
default_start_date = min_data_date


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Settings")
    st.caption(f"S3 data: {min_data_date} → {max_data_date}")

    st.markdown("**Historical Date Range**")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "From",
            value=default_start_date,
            min_value=min_data_date,
            max_value=max_data_date,
        )
    with col2:
        end_date = st.date_input(
            "To",
            value=max_data_date,
            min_value=min_data_date,
            max_value=max_data_date,
        )

    if start_date > end_date:
        st.error("Start date must be before end date.")
        st.stop()

    st.markdown("**Locations**")
    selected_locations = st.multiselect(
        "Filter locations",
        options=all_locations,
        default=(
            ["SWRC Fitness Total"]
            if "SWRC Fitness Total" in all_locations
            else all_locations[:6]
        ),
    )
    if not selected_locations:
        st.info("Select at least one location to load data.")
        st.stop()

    st.markdown("**Historical Chart**")
    show_occupancy_line = st.checkbox(
        "Show occupancy %",
        value=True,
        help="Adds percent-full lines for the selected locations.",
    )
    show_count_line = st.checkbox(
        "Show people count",
        value=False,
        help="Adds people-count lines for the selected locations.",
    )
    show_capacity_line = st.checkbox(
        "Show max occupancy",
        value=False,
        help="Adds max occupancy lines. With people count enabled, this shows total capacity; otherwise it shows 100%.",
    )
    if not any([show_occupancy_line, show_count_line, show_capacity_line]):
        st.info("Select at least one historical chart line to display.")

    st.markdown("---")
    st.markdown("**Prediction Model**")
    use_all_for_training = st.checkbox(
        "Train on all locations",
        value=True,
        help="Recommended. More locations give the regression model a stronger baseline.",
    )
    training_start = st.date_input(
        "Training start",
        value=min_data_date,
        min_value=min_data_date,
        max_value=max_data_date,
    )
    training_end = st.date_input(
        "Training end",
        value=max_data_date,
        min_value=min_data_date,
        max_value=max_data_date,
    )
    if training_start > training_end:
        st.error("Training start must be before training end.")
        st.stop()


# ── Data loading helpers ──────────────────────────────────────────────────────

@st.cache_data(ttl=600)
def load_and_preprocess(start: date, end: date, locs: tuple, cache_version: int) -> pd.DataFrame:
    """Load from S3 and preprocess. Cached 10 min. Uses tuple for hashable cache key."""
    df = data_access.load_data_from_s3(start, end, list(locs))
    if df.empty:
        return df
    return transforms.preprocess_data(df)


@st.cache_data(ttl=600)
def get_trained_model(start: date, end: date, locs: tuple):
    """Train the Ridge model. Cached per (date-range, locations) combo."""
    df = load_and_preprocess(start, end, locs, DATA_CACHE_VERSION)
    if df.empty:
        raise ValueError("No data loaded for the selected training range.")
    return gym_model.train_model(df)


@st.cache_data(ttl=300)
def load_camera_counts(as_of_date: date, cache_version: int) -> dict:
    """Load latest per-area counts for the camera page."""
    member_locations = sorted(
        {
            member
            for section in CAMERA_SECTIONS
            for member in section["members"]
        }
    )
    df = data_access.load_data_from_s3(as_of_date, as_of_date, member_locations)
    if df.empty:
        return {}

    df["pulled_at_utc"] = pd.to_datetime(df["pulled_at_utc"], utc=True, format="mixed")
    latest_by_location = (
        df.sort_values("pulled_at_utc")
        .groupby("location_name", as_index=False)
        .tail(1)
        .set_index("location_name")
    )

    summary_count = latest_by_location["last_count"].sum()
    summary_capacity = latest_by_location["total_capacity"].sum()
    counts = {
        "__summary__": {
            "count": int(summary_count),
            "capacity": int(summary_capacity),
            "percent_full": round((summary_count / summary_capacity) * 100, 1)
            if summary_capacity
            else 0,
            "updated_at": latest_by_location["pulled_at_utc"].max(),
        }
    }
    for section in CAMERA_SECTIONS:
        rows = latest_by_location.loc[
            latest_by_location.index.intersection(section["members"])
        ]
        if rows.empty:
            counts[section["title"]] = None
            continue
        count = rows["last_count"].sum()
        capacity = rows["total_capacity"].sum()
        percent = round((count / capacity) * 100, 1) if capacity else 0
        counts[section["title"]] = {
            "count": int(count),
            "capacity": int(capacity),
            "percent_full": percent,
            "updated_at": rows["pulled_at_utc"].max(),
            "locations": sorted(rows.index.tolist()),
        }
    return counts


def camera_card(section: dict, count_info) -> None:
    cache_bust = int(datetime.now().timestamp() // 300)
    image_url = f"{section['image_url']}?t={cache_bust}"
    if count_info is None:
        count_text = "No current count"
        percent_text = ""
        updated_text = "No S3 reading for this area"
        status_label, tone = "No Count", "neutral"
    else:
        count_text = f"{count_info['count']:,} / {count_info['capacity']:,}"
        percent_text = f"{count_info['percent_full']:.1f}% full"
        updated_text = f"Updated {format_timestamp(count_info['updated_at'])}"
        status_label, tone = occupancy_tone(count_info["percent_full"])

    st.markdown(
        f"""
        <article class="camera-card">
            <div class="camera-card__header">
                <h3>{escape(section["title"])}</h3>
                <span class="camera-card__status camera-card__status--{tone}">{escape(status_label)}</span>
            </div>
            <img class="camera-card__image" src="{escape(image_url)}" alt="{escape(section["title"])} camera feed" />
            <div class="camera-card__footer">
                <div>
                    <div class="camera-card__count">{escape(count_text)}</div>
                    <div class="camera-card__percent">{escape(percent_text)}</div>
                </div>
                <div class="camera-card__updated">{escape(updated_text)}</div>
            </div>
        </article>
        """,
        unsafe_allow_html=True,
    )


# ── Load view data ────────────────────────────────────────────────────────────

with st.spinner("Loading historical data from S3..."):
    df_view = load_and_preprocess(
        start_date,
        end_date,
        tuple(selected_locations),
        DATA_CACHE_VERSION,
    )

if df_view.empty:
    st.warning(f"No data found between {start_date} and {end_date} for the selected locations.")


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs(
    ["Historical Analysis", "Predict Occupancy", "Classes", "Cameras & Counts"]
)


# ═══════════════════════════════════════════════════════════════════
# TAB 1 — Historical Analysis
# ═══════════════════════════════════════════════════════════════════

with tab1:
    if df_view.empty:
        st.info("Adjust the date range or locations in the sidebar to load data.")
    else:
        df_agg = transforms.aggregate_by_hour_location(df_view)

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("Avg Occupancy", f"{df_view['percent_full'].mean():.1f}%")
        with col2:
            st.metric("Peak Occupancy", f"{df_view['percent_full'].max():.1f}%")
        with col3:
            st.metric("Avg Count", f"{df_view['last_count'].mean():.0f}")
        with col4:
            st.metric("Peak Count", f"{df_view['last_count'].max():.0f}")
        with col5:
            st.metric("Locations", df_view["location_name"].nunique())
        with col6:
            st.metric("Data Points", f"{len(df_view):,}")

        st.markdown("---")
        st.subheader("Occupancy Over Time")
        st.plotly_chart(
            charts.line_chart_occupancy(
                df_agg,
                selected_locations,
                show_occupancy=show_occupancy_line,
                show_count=show_count_line,
                show_capacity=show_capacity_line,
            ),
            use_container_width=True,
        )

        st.subheader("Busiest Times: Hour × Day of Week")
        st.caption("Red = crowded · Green = quiet · All times Eastern")
        st.plotly_chart(charts.heatmap_hourly_occupancy(df_view), use_container_width=True)

        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.subheader("Average Occupancy by Facility")
            st.plotly_chart(charts.bar_chart_by_facility(df_view), use_container_width=True)
        with col_b:
            st.subheader("Top 10 Busiest Slots")
            peak_table = charts.peak_hours_table(df_view, top_n=10)
            st.dataframe(peak_table, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════
# TAB 2 — Predict Occupancy
# ═══════════════════════════════════════════════════════════════════

with tab2:
    training_locations = all_locations if use_all_for_training else selected_locations

    with st.spinner("Training Ridge regression model from S3 data..."):
        try:
            pipeline, metrics, filter_report = get_trained_model(
                training_start,
                training_end,
                tuple(training_locations),
            )
        except Exception as exc:
            st.error(f"Model could not be trained: {exc}")
            st.stop()

    with st.expander("Model Details and Training Report", expanded=False):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("R² Score", metrics["r2"])
        with col_b:
            st.metric("Mean Abs Error", f"±{metrics['mae']}%")
        with col_c:
            st.metric("RMSE", f"±{metrics['rmse']}%")

        st.markdown(
            f"Trained on **{metrics['n_train']:,}** samples · "
            f"tested on **{metrics['n_test']:,}** held-out samples · "
            f"**{metrics['n_locations']}** locations."
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Closed removed", filter_report["closed_removed"])
        with col2:
            st.metric("Impossible values", filter_report["impossible_values_removed"])
        with col3:
            st.metric("Off-hours removed", filter_report["off_hours_removed"])
        with col4:
            st.metric("Outliers removed", filter_report["outliers_removed"])

        st.info(
            "Model: Ridge Linear Regression. "
            "Features: cyclical hour, cyclical day-of-week, cyclical month, "
            "weekend flag, one-hot location. "
            "Predictions are estimates, not live counts."
        )

    st.markdown("---")
    st.subheader("Predict Occupancy at a Specific Time")

    col_loc, col_date, col_hour = st.columns([2, 1, 1])
    with col_loc:
        pred_location = st.selectbox("Location", options=all_locations, index=0)
    with col_date:
        pred_date = st.date_input(
            "Date",
            value=date.today(),
            min_value=date.today(),
            max_value=date.today() + timedelta(days=30),
        )
    with col_hour:
        pred_hour = st.select_slider(
            "Hour (Eastern)",
            options=list(range(5, 24)),
            value=14,
            format_func=format_hour,
        )

    pred_dt = datetime(pred_date.year, pred_date.month, pred_date.day, pred_hour)
    predicted_pct = gym_model.predict_single(pipeline, pred_location, pred_dt)
    badge_label, badge_color = gym_model.occupancy_label(predicted_pct)

    col_gauge, col_detail = st.columns([1, 2])

    with col_gauge:
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=predicted_pct,
                number={"suffix": "%", "font": {"size": 40}},
                title={
                    "text": (
                        f"{pred_location}<br>"
                        f"<span style='font-size:18px'>"
                        f"{pred_date.strftime('%A, %b %d')} at {format_hour(pred_hour)}"
                        f"</span>"
                    )
                },
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1},
                    "bar": {"color": badge_color},
                    "steps": [
                        {"range": [0, 30],  "color": "#d4f1d4"},
                        {"range": [30, 60], "color": "#fff3cd"},
                        {"range": [60, 80], "color": "#ffe5cc"},
                        {"range": [80, 100],"color": "#f8d7da"},
                    ],
                    "threshold": {
                        "line": {"color": "black", "width": 3},
                        "thickness": 0.75,
                        "value": predicted_pct,
                    },
                },
            )
        )
        fig_gauge.update_layout(height=280, margin=dict(t=60, b=20, l=20, r=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.markdown(
            f"<h3 style='text-align:center; color:{badge_color}'>{badge_label}</h3>",
            unsafe_allow_html=True,
        )
        st.caption(f"Confidence band: ±{metrics['rmse']}% (model RMSE)")

    with col_detail:
        st.markdown(f"**Predicted occupancy all day — {pred_date.strftime('%A, %B %d')}**")
        curve_df = gym_model.predict_day_curve(pipeline, pred_location, pred_date, metrics["rmse"])
        rec = gym_model.best_time_to_go(curve_df)

        bcol1, bcol2 = st.columns(2)
        with bcol1:
            best_label, _ = gym_model.occupancy_label(rec["best_predicted"])
            st.success(
                f"**Best time to go:** {format_hour(rec['best_hour'])}\n\n"
                f"Predicted {rec['best_predicted']:.1f}% full — {best_label}"
            )
        with bcol2:
            worst_label, _ = gym_model.occupancy_label(rec["worst_predicted"])
            st.error(
                f"**Avoid:** {format_hour(rec['worst_hour'])}\n\n"
                f"Predicted {rec['worst_predicted']:.1f}% full — {worst_label}"
            )

        fig_curve = go.Figure()
        fig_curve.add_trace(go.Scatter(
            x=list(curve_df["hour"]) + list(curve_df["hour"])[::-1],
            y=list(curve_df["upper_bound"]) + list(curve_df["lower_bound"])[::-1],
            fill="toself",
            fillcolor="rgba(99,110,250,0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name=f"±{metrics['rmse']}% band",
            hoverinfo="skip",
        ))
        fig_curve.add_trace(go.Scatter(
            x=curve_df["hour"],
            y=curve_df["predicted"],
            customdata=curve_df["hour"].map(format_hour),
            mode="lines+markers",
            name="Predicted % full",
            line=dict(color="rgb(99,110,250)", width=2),
            marker=dict(size=6),
            hovertemplate="Time: %{customdata}<br>Predicted: %{y:.1f}%<extra></extra>",
        ))
        fig_curve.add_vline(
            x=rec["best_hour"], line_dash="dot", line_color="green",
            annotation_text="Best", annotation_position="top",
        )
        fig_curve.add_vline(
            x=rec["worst_hour"], line_dash="dot", line_color="red",
            annotation_text="Avoid", annotation_position="top",
        )
        if pred_date == date.today():
            fig_curve.add_vline(
                x=datetime.now().hour, line_dash="dash", line_color="gray",
                annotation_text="Now", annotation_position="bottom",
            )
        fig_curve.update_layout(
            height=270,
            margin=dict(t=20, b=40, l=10, r=10),
            xaxis=dict(
                title="Hour of day (Eastern)",
                tickmode="array",
                tickvals=list(range(0, 24, 2)),
                ticktext=[format_hour(hour) for hour in range(0, 24, 2)],
            ),
            yaxis=dict(title="% Full", range=[0, 100]),
            hovermode="x unified",
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig_curve, use_container_width=True)

    st.markdown("---")
    st.subheader(f"All Locations at {format_hour(pred_hour)} on {pred_date.strftime('%A, %b %d')}")
    st.caption("Find the quietest option at your target time.")

    all_preds = []
    for loc in all_locations:
        pct = gym_model.predict_single(pipeline, loc, pred_dt)
        label, _ = gym_model.occupancy_label(pct)
        all_preds.append({"Location": loc, "Predicted % Full": round(pct, 1), "Status": label})

    preds_df = pd.DataFrame(all_preds).sort_values("Predicted % Full")
    fig_all = px.bar(
        preds_df,
        x="Predicted % Full",
        y="Location",
        orientation="h",
        color="Predicted % Full",
        color_continuous_scale=["green", "yellow", "orange", "red"],
        range_color=[0, 100],
        text="Predicted % Full",
    )
    fig_all.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig_all.update_layout(
        height=550,
        margin=dict(t=10, b=10, l=10, r=80),
        coloraxis_showscale=False,
        xaxis=dict(range=[0, 110], title="Predicted Occupancy (%)"),
        yaxis=dict(title=""),
    )
    st.plotly_chart(fig_all, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════
# TAB 3 — Classes
# ═══════════════════════════════════════════════════════════════════

with tab3:
    class_df = pd.DataFrame(CLASS_SCHEDULE_ROWS)
    class_df["start"] = class_df.apply(parse_class_datetime, axis=1)
    class_df["category"] = class_df["name"].map(class_category)
    class_df["day"] = class_df["start"].dt.strftime("%a, %b %-d")
    class_df["display_time"] = class_df["start"].dt.strftime("%-I:%M %p")

    st.markdown(
        """
        <section class="classes-page">
            <div class="camera-kicker">RecSports</div>
            <div class="classes-hero">
                <h2>Classes</h2>
                <div class="classes-subhead">ADJUSTED Hours (4/23-5/1)</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="color-guide">
            <div class="color-guide__item" style="border-left: 6px solid #16833a;">Strength</div>
            <div class="color-guide__item" style="border-left: 6px solid #b42318;">Mind & Body</div>
            <div class="color-guide__item" style="border-left: 6px solid #2f6fbd;">Cycle</div>
            <div class="color-guide__item" style="border-left: 6px solid #d95f02;">Dance</div>
            <div class="color-guide__item" style="border-left: 6px solid #7a3db8;">Cardio</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 1])
    with filter_col1:
        selected_day = st.selectbox(
            "Day",
            options=["All"] + class_df["day"].drop_duplicates().tolist(),
        )
    with filter_col2:
        selected_location = st.selectbox(
            "Location",
            options=["All"] + sorted(class_df["location"].unique().tolist()),
        )
    with filter_col3:
        selected_category = st.selectbox(
            "Format",
            options=["All"] + sorted(class_df["category"].unique().tolist()),
        )

    filtered_classes = class_df.copy()
    if selected_day != "All":
        filtered_classes = filtered_classes[filtered_classes["day"] == selected_day]
    if selected_location != "All":
        filtered_classes = filtered_classes[filtered_classes["location"] == selected_location]
    if selected_category != "All":
        filtered_classes = filtered_classes[filtered_classes["category"] == selected_category]

    st.metric("Classes Shown", len(filtered_classes))

    if filtered_classes.empty:
        st.info("No classes match the selected filters.")
    else:
        for _, class_row in filtered_classes.sort_values("start").iterrows():
            row = class_row.to_dict()
            category_class = row["category"].lower().replace(" & ", "-").replace(" ", "-")
            st.markdown(
                f"""
                <div class="class-card class-card--{escape(category_class)}">
                    <div class="class-card__time">{escape(format_class_datetime(row))}</div>
                    <div class="class-card__title">{escape(row["name"])}</div>
                    <div class="class-card__meta">{escape(row["location"])} · Instructor: {escape(row["instructor"])}</div>
                    <div class="class-card__category">{escape(row["category"])} · {class_duration_minutes(row["name"])} minutes</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            action_col1, action_col2 = st.columns([1, 1])
            with action_col1:
                st.download_button(
                    "Download calendar file",
                    data=make_class_ics(row),
                    file_name=class_filename(row),
                    mime="text/calendar",
                    key=f"download-{row['date']}-{row['time']}-{row['name']}-{row['location']}",
                )
            with action_col2:
                st.link_button("Class details", row["url"])


# ═══════════════════════════════════════════════════════════════════
# TAB 4 — Cameras & Counts
# ═══════════════════════════════════════════════════════════════════

with tab4:
    camera_counts = load_camera_counts(max_data_date, DATA_CACHE_VERSION)
    summary_counts = camera_counts.get("__summary__")
    latest_update = summary_counts["updated_at"] if summary_counts else pd.NaT

    st.markdown(
        f"""
        <section class="camera-page">
            <div class="camera-kicker">RecSports</div>
            <div class="camera-hero">
                <h2>Cameras & Counts</h2>
                <div class="camera-hero__meta">Latest counts: {escape(format_timestamp(latest_update))}</div>
            </div>
            <div class="camera-alert">Cameras are Currently Down. Thank you for your patience</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if summary_counts:
        summary_col1, summary_col2, summary_col3 = st.columns(3)
        with summary_col1:
            st.metric("Camera Areas Count", f"{summary_counts['count']:,}")
        with summary_col2:
            st.metric("Camera Areas Capacity", f"{summary_counts['capacity']:,}")
        with summary_col3:
            st.metric("Camera Areas Occupancy", f"{summary_counts['percent_full']:.1f}%")
    else:
        st.warning("No current count data found for the camera areas.")

    for i in range(0, len(CAMERA_SECTIONS), 2):
        left, right = st.columns(2)
        with left:
            section = CAMERA_SECTIONS[i]
            camera_card(section, camera_counts.get(section["title"]))
        if i + 1 < len(CAMERA_SECTIONS):
            with right:
                section = CAMERA_SECTIONS[i + 1]
                camera_card(section, camera_counts.get(section["title"]))


st.markdown("---")
st.caption(
    "Gator Gauge | S3 data from UF Rec Services | "
    "Ridge regression estimates | All times in America/New_York"
)

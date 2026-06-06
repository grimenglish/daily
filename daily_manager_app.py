
import sqlite3
from pathlib import Path
from datetime import datetime, date, time, timedelta
from io import BytesIO
import calendar

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


APP_TITLE = "일상 관리 프로그램"
DB_PATH = Path("daily_manager.db")


# =========================
# 기본 설정
# =========================
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🗓️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1520px;
    }

    .main-title {
        font-size: 2.05rem;
        font-weight: 950;
        letter-spacing: -0.05em;
        margin-bottom: 0.15rem;
    }

    .sub-title {
        color: #6b7280;
        margin-bottom: 1rem;
    }

    .section-title {
        font-size: 1.2rem;
        font-weight: 900;
        letter-spacing: -0.04em;
        margin: 0.3rem 0 0.7rem 0;
    }

    .task-card {
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 0.8rem 0.9rem;
        margin-bottom: 0.65rem;
        background: #ffffff;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.035);
    }

    .task-today {
        border-left: 7px solid #2563eb;
        background: #f8fbff;
    }

    .task-overdue {
        border-left: 7px solid #ef4444;
        background: #fff7f7;
    }

    .task-upcoming {
        border-left: 7px solid #10b981;
        background: #f8fffb;
    }

    .task-title {
        font-weight: 900;
        font-size: 1.02rem;
        letter-spacing: -0.03em;
    }

    .pill {
        display: inline-block;
        padding: 0.16rem 0.48rem;
        border-radius: 999px;
        background: #f3f4f6;
        border: 1px solid #e5e7eb;
        color: #374151;
        font-size: 0.78rem;
        margin-right: 0.18rem;
        margin-top: 0.24rem;
    }

    .red {background:#fee2e2; color:#991b1b; border-color:#fecaca;}
    .blue {background:#dbeafe; color:#1e40af; border-color:#bfdbfe;}
    .green {background:#d1fae5; color:#065f46; border-color:#a7f3d0;}
    .yellow {background:#fef3c7; color:#92400e; border-color:#fde68a;}

    .calendar-box {
        border: 1px solid #e5e7eb;
        border-radius: 20px;
        padding: 1rem;
        background: #ffffff;
        box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
    }

    .weekday {
        text-align: center;
        font-weight: 900;
        color: #4b5563;
        padding: 0.45rem 0;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 0.35rem;
    }

    .day-info {
        min-height: 54px;
        padding: 0.2rem 0.1rem 0.45rem 0.1rem;
        text-align: center;
        font-size: 0.78rem;
    }

    .today-mark {
        color: #2563eb;
        font-weight: 900;
    }

    .selected-day {
        color: #111827;
        font-weight: 900;
        background: #eef2ff;
        border-radius: 10px;
        padding: 0.3rem;
        margin-bottom: 0.5rem;
    }

    .muted {
        color: #9ca3af;
    }

    .alarm-box {
        padding: 1rem;
        border-radius: 16px;
        background: #fff4f4;
        border: 1px solid #ffb8b8;
        margin-bottom: 1rem;
    }

    .alarm-title {
        font-size: 1.1rem;
        font-weight: 900;
        color: #c62828;
        margin-bottom: 0.5rem;
    }

    div.stButton > button {
        min-height: 38px;
        font-weight: 800;
        border-radius: 12px;
    }

    div[data-testid="stMetricValue"] {
        font-weight: 950;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# DB
# =========================
def connect_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


conn = connect_db()


def q(sql, params=()):
    cur = conn.execute(sql, params)
    conn.commit()
    return cur


def df(sql, params=()):
    return pd.read_sql_query(sql, conn, params=params)


def table_columns(table_name):
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]


def add_column_if_missing(table_name, column_name, column_sql):
    if column_name not in table_columns(table_name):
        q(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def init_db():
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            detail TEXT DEFAULT '',
            category TEXT DEFAULT '개인',
            priority TEXT DEFAULT '보통',
            due_date TEXT,
            due_time TEXT,
            status TEXT DEFAULT '대기',
            repeat_type TEXT DEFAULT '없음',
            tags TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            completed_at TEXT,
            notified_at TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            detail TEXT DEFAULT '',
            category TEXT DEFAULT '개인',
            schedule_date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            location TEXT DEFAULT '',
            alarm_minutes INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            notified_at TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            pinned INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()

    add_column_if_missing("tasks", "notified_at", "notified_at TEXT")
    add_column_if_missing("schedules", "notified_at", "notified_at TEXT")


init_db()


# =========================
# 유틸
# =========================
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str():
    return date.today().isoformat()


def combine_datetime(d, t):
    if not d:
        return None
    try:
        if t:
            return datetime.fromisoformat(f"{d} {t}")
        return datetime.fromisoformat(f"{d} 23:59:59")
    except Exception:
        return None


def next_repeat_date(due_date, repeat_type):
    if not due_date or repeat_type == "없음":
        return None

    d = date.fromisoformat(due_date)

    if repeat_type == "매일":
        return d + timedelta(days=1)

    if repeat_type == "매주":
        return d + timedelta(weeks=1)

    if repeat_type == "매월":
        month = d.month + 1
        year = d.year
        if month == 13:
            month = 1
            year += 1

        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, min(d.day, last_day))

    if repeat_type == "매년":
        try:
            return date(d.year + 1, d.month, d.day)
        except ValueError:
            return date(d.year + 1, 2, 28)

    return None


def task_group(row):
    if row["status"] == "완료":
        return "done"

    dt = combine_datetime(row["due_date"], row["due_time"])

    if dt and dt < datetime.now():
        return "overdue"

    if row["due_date"] == today_str():
        return "today"

    return "upcoming"


def status_label(status):
    if status == "완료":
        return "✅ 완료"
    if status == "진행":
        return "🟡 진행"
    if status == "보류":
        return "⏸️ 보류"
    return "대기"


def priority_label(priority):
    if priority == "높음":
        return "🔥 높음"
    if priority == "낮음":
        return "낮음"
    return "보통"


def page_title(title, desc=""):
    st.markdown(f'<div class="main-title">{title}</div>', unsafe_allow_html=True)
    if desc:
        st.markdown(f'<div class="sub-title">{desc}</div>', unsafe_allow_html=True)


def safe_tasks_df():
    data = df("SELECT * FROM tasks ORDER BY due_date ASC, due_time ASC, created_at DESC")
    if data.empty:
        return pd.DataFrame(columns=[
            "id", "title", "detail", "category", "priority", "due_date", "due_time",
            "status", "repeat_type", "tags", "created_at", "completed_at", "notified_at"
        ])
    return data


def safe_schedules_df():
    data = df("SELECT * FROM schedules ORDER BY schedule_date ASC, start_time ASC")
    if data.empty:
        return pd.DataFrame(columns=[
            "id", "title", "detail", "category", "schedule_date", "start_time",
            "end_time", "location", "alarm_minutes", "created_at", "notified_at"
        ])
    return data


def safe_memos_df():
    data = df("SELECT * FROM memos ORDER BY pinned DESC, updated_at DESC")
    if data.empty:
        return pd.DataFrame(columns=[
            "id", "title", "content", "tags", "pinned", "created_at", "updated_at"
        ])
    return data


def download_excel():
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        safe_tasks_df().to_excel(writer, index=False, sheet_name="할일")
        safe_schedules_df().to_excel(writer, index=False, sheet_name="일정")
        safe_memos_df().to_excel(writer, index=False, sheet_name="메모")
    return output.getvalue()


def download_db():
    return DB_PATH.read_bytes() if DB_PATH.exists() else b""


# =========================
# 알림
# =========================
def get_due_alerts():
    now = datetime.now()
    alerts = []

    tasks = df(
        """
        SELECT * FROM tasks
        WHERE status != '완료'
          AND due_date IS NOT NULL
          AND due_date != ''
          AND notified_at IS NULL
        """
    )

    if not tasks.empty:
        for _, row in tasks.iterrows():
            due_dt = combine_datetime(row["due_date"], row["due_time"])
            if due_dt and now >= due_dt:
                alerts.append({
                    "type": "할 일",
                    "id": int(row["id"]),
                    "title": row["title"],
                    "time": due_dt.strftime("%Y-%m-%d %H:%M"),
                    "message": f"할 일 시간입니다: {row['title']}",
                })

    schedules = df(
        """
        SELECT * FROM schedules
        WHERE schedule_date IS NOT NULL
          AND schedule_date != ''
          AND start_time IS NOT NULL
          AND start_time != ''
          AND notified_at IS NULL
        """
    )

    if not schedules.empty:
        for _, row in schedules.iterrows():
            start_dt = combine_datetime(row["schedule_date"], row["start_time"])
            if not start_dt:
                continue

            alarm_minutes = int(row["alarm_minutes"] or 0)
            alarm_dt = start_dt - timedelta(minutes=alarm_minutes)

            if alarm_dt <= now <= start_dt + timedelta(hours=24):
                msg = f"{alarm_minutes}분 후 일정입니다: {row['title']}" if alarm_minutes else f"일정 시작입니다: {row['title']}"
                alerts.append({
                    "type": "일정",
                    "id": int(row["id"]),
                    "title": row["title"],
                    "time": start_dt.strftime("%Y-%m-%d %H:%M"),
                    "message": msg,
                })

    return alerts


def mark_alerts_notified(alerts):
    stamp = now_str()
    for a in alerts:
        if a["type"] == "할 일":
            q("UPDATE tasks SET notified_at=? WHERE id=?", (stamp, a["id"]))
        elif a["type"] == "일정":
            q("UPDATE schedules SET notified_at=? WHERE id=?", (stamp, a["id"]))


def render_alarm(alerts):
    if not alerts:
        return

    html_lines = "".join(
        f"<li><b>{a['type']}</b> · {a['time']} · {a['title']}</li>"
        for a in alerts
    )

    st.markdown(
        f"""
        <div class="alarm-box">
            <div class="alarm-title">🔔 알림</div>
            <ul>{html_lines}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    msg = "\\n".join([a["message"] for a in alerts])
    msg = msg.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

    components.html(
        f"""
        <script>
        const msg = `{msg}`;

        async function ringAlarm() {{
            try {{
                if ("Notification" in window) {{
                    if (Notification.permission === "granted") {{
                        new Notification("일상 관리 알림", {{ body: msg }});
                    }} else if (Notification.permission !== "denied") {{
                        Notification.requestPermission().then(function(permission) {{
                            if (permission === "granted") {{
                                new Notification("일상 관리 알림", {{ body: msg }});
                            }}
                        }});
                    }}
                }}
            }} catch(e) {{}}

            try {{
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                const ctx = new AudioContext();
                if (ctx.state === "suspended") await ctx.resume();

                function beep(freq, start, duration) {{
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.frequency.value = freq;
                    osc.type = "sine";
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    gain.gain.setValueAtTime(0.0001, ctx.currentTime + start);
                    gain.gain.exponentialRampToValueAtTime(0.32, ctx.currentTime + start + 0.02);
                    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + start + duration);
                    osc.start(ctx.currentTime + start);
                    osc.stop(ctx.currentTime + start + duration + 0.04);
                }}

                beep(880, 0.00, 0.24);
                beep(1046, 0.32, 0.24);
                beep(880, 0.64, 0.24);
            }} catch(e) {{}}
        }}

        ringAlarm();
        </script>
        """,
        height=0,
    )


def auto_refresh(seconds):
    components.html(
        f"""
        <script>
        setTimeout(function() {{
            window.parent.location.reload();
        }}, {int(seconds) * 1000});
        </script>
        """,
        height=0,
    )


# =========================
# 액션
# =========================
def complete_task(row_id):
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (row_id,)).fetchone()
    if not row:
        return

    q("UPDATE tasks SET status='완료', completed_at=? WHERE id=?", (now_str(), row_id))

    next_d = next_repeat_date(row["due_date"], row["repeat_type"])
    if next_d:
        q(
            """
            INSERT INTO tasks
            (title, detail, category, priority, due_date, due_time, status, repeat_type, tags, created_at, notified_at)
            VALUES (?, ?, ?, ?, ?, ?, '대기', ?, ?, ?, NULL)
            """,
            (
                row["title"], row["detail"], row["category"], row["priority"],
                next_d.isoformat(), row["due_time"], row["repeat_type"], row["tags"], now_str()
            ),
        )


def render_task_card(row, key_prefix):
    group = task_group(row)

    css = "task-card"
    group_badge = "예정"
    group_cls = "green"

    if group == "today":
        css += " task-today"
        group_badge = "오늘"
        group_cls = "blue"
    elif group == "overdue":
        css += " task-overdue"
        group_badge = "기한지남"
        group_cls = "red"
    elif group == "done":
        group_badge = "완료"
        group_cls = "green"
    else:
        css += " task-upcoming"

    priority_cls = "red" if row["priority"] == "높음" else "yellow" if row["priority"] == "보통" else ""

    st.markdown(
        f"""
        <div class="{css}">
            <div class="task-title">{row['title']}</div>
            <span class="pill {group_cls}">{group_badge}</span>
            <span class="pill">{row['category']}</span>
            <span class="pill {priority_cls}">{priority_label(row['priority'])}</span>
            <span class="pill">⏰ {row['due_date'] or '-'} {row['due_time'] or ''}</span>
            {f"<div class='muted' style='margin-top:0.35rem;'>{row['detail'][:70]}</div>" if row['detail'] else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)

    if row["status"] != "완료":
        if c1.button("완료", key=f"{key_prefix}_done_{row['id']}", use_container_width=True):
            complete_task(int(row["id"]))
            st.rerun()
    else:
        if c1.button("미완료", key=f"{key_prefix}_undo_{row['id']}", use_container_width=True):
            q("UPDATE tasks SET status='대기', completed_at=NULL WHERE id=?", (int(row["id"]),))
            st.rerun()

    if c2.button("진행", key=f"{key_prefix}_progress_{row['id']}", use_container_width=True):
        q("UPDATE tasks SET status='진행' WHERE id=?", (int(row["id"]),))
        st.rerun()

    if c3.button("삭제", key=f"{key_prefix}_delete_{row['id']}", use_container_width=True):
        q("DELETE FROM tasks WHERE id=?", (int(row["id"]),))
        st.rerun()


# =========================
# 진짜 달력
# =========================
def init_calendar_state():
    if "calendar_year" not in st.session_state:
        st.session_state.calendar_year = date.today().year
    if "calendar_month" not in st.session_state:
        st.session_state.calendar_month = date.today().month
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = today_str()


def move_month(delta):
    y = int(st.session_state.calendar_year)
    m = int(st.session_state.calendar_month) + delta

    if m < 1:
        y -= 1
        m = 12
    elif m > 12:
        y += 1
        m = 1

    st.session_state.calendar_year = y
    st.session_state.calendar_month = m


def set_today_calendar():
    today = date.today()
    st.session_state.calendar_year = today.year
    st.session_state.calendar_month = today.month
    st.session_state.selected_date = today.isoformat()


def render_real_calendar(tasks, schedules):
    init_calendar_state()

    year = int(st.session_state.calendar_year)
    month = int(st.session_state.calendar_month)

    st.markdown('<div class="calendar-box">', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1, 3, 1, 1])
    if c1.button("◀ 이전", use_container_width=True):
        move_month(-1)
        st.rerun()

    c2.markdown(
        f"<div style='font-size:1.45rem;font-weight:950;text-align:center;letter-spacing:-0.04em;'>{year}년 {month}월</div>",
        unsafe_allow_html=True,
    )

    if c3.button("오늘", use_container_width=True):
        set_today_calendar()
        st.rerun()

    if c4.button("다음 ▶", use_container_width=True):
        move_month(1)
        st.rerun()

    st.markdown("")

    weekdays = ["일", "월", "화", "수", "목", "금", "토"]
    header_cols = st.columns(7)
    for i, day_name in enumerate(weekdays):
        header_cols[i].markdown(f"<div class='weekday'>{day_name}</div>", unsafe_allow_html=True)

    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdatescalendar(year, month)

    selected = st.session_state.selected_date

    for week in weeks:
        cols = st.columns(7)
        for idx, d in enumerate(week):
            d_str = d.isoformat()
            is_current_month = d.month == month
            is_today = d == date.today()
            is_selected = selected == d_str

            day_tasks = tasks[tasks["due_date"] == d_str] if not tasks.empty else pd.DataFrame()
            day_schedules = schedules[schedules["schedule_date"] == d_str] if not schedules.empty else pd.DataFrame()

            task_count = len(day_tasks)
            schedule_count = len(day_schedules)
            done_count = len(day_tasks[day_tasks["status"] == "완료"]) if not day_tasks.empty else 0

            with cols[idx]:
                label = f"{d.day}"
                if is_today:
                    label = f"📍 {d.day}"

                disabled = not is_current_month
                button_type = "primary" if is_selected else "secondary"

                if st.button(label, key=f"cal_day_{d_str}", use_container_width=True, disabled=disabled, type=button_type):
                    st.session_state.selected_date = d_str
                    st.rerun()

                if not is_current_month:
                    st.markdown("<div class='day-info muted'>다른 달</div>", unsafe_allow_html=True)
                else:
                    info = []
                    if task_count:
                        info.append(f"<span class='pill red'>할 일 {task_count}</span>")
                    if schedule_count:
                        info.append(f"<span class='pill blue'>일정 {schedule_count}</span>")
                    if done_count:
                        info.append(f"<span class='pill green'>완료 {done_count}</span>")

                    if info:
                        st.markdown("<div class='day-info'>" + "<br>".join(info) + "</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div class='day-info muted'>-</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# 사이드바
# =========================
with st.sidebar:
    st.title("🗓️ 일상 관리")

    menu = st.radio(
        "메뉴",
        ["대시보드", "할 일", "일정", "메모장", "백업/설정"],
        label_visibility="collapsed",
    )

    st.divider()

    alarm_enabled = st.toggle("🔔 알림 자동 확인", value=True)
    refresh_seconds = st.selectbox(
        "확인 주기",
        [15, 30, 60, 120, 300],
        index=2,
        format_func=lambda x: f"{x}초마다",
    )
    st.caption("앱 화면이 열려 있어야 알림이 울립니다.")

    if st.button("🔊 알림 테스트", use_container_width=True):
        render_alarm([{
            "type": "테스트",
            "id": 0,
            "title": "알림 테스트",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "message": "알림 테스트입니다.",
        }])

    st.divider()

    st.caption(f"오늘: {date.today().strftime('%Y-%m-%d')}")
    st.download_button(
        "📦 엑셀 백업",
        data=download_excel(),
        file_name=f"일상관리_백업_{today_str()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


if alarm_enabled:
    due_alerts = get_due_alerts()
    if due_alerts:
        render_alarm(due_alerts)
        mark_alerts_notified(due_alerts)
    auto_refresh(refresh_seconds)


# =========================
# 대시보드
# =========================
if menu == "대시보드":
    page_title("대시보드", "왼쪽은 할 일, 오른쪽은 실제 달력. 날짜를 누르면 그날 상세가 바로 보입니다.")

    tasks = safe_tasks_df()
    schedules = safe_schedules_df()
    memos = safe_memos_df()

    incomplete = tasks[tasks["status"] != "완료"] if not tasks.empty else pd.DataFrame()
    overdue = incomplete[incomplete.apply(lambda r: task_group(r) == "overdue", axis=1)] if not incomplete.empty else pd.DataFrame()
    today_tasks = incomplete[incomplete["due_date"] == today_str()] if not incomplete.empty else pd.DataFrame()
    today_schedules = schedules[schedules["schedule_date"] == today_str()] if not schedules.empty else pd.DataFrame()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("오늘 할 일", len(today_tasks))
    m2.metric("기한 지남", len(overdue))
    m3.metric("미완료 전체", len(incomplete))
    m4.metric("오늘 일정", len(today_schedules))

    with st.expander("➕ 빠른 등록", expanded=False):
        tab1, tab2, tab3 = st.tabs(["할 일", "일정", "메모"])

        with tab1:
            with st.form("quick_task", clear_on_submit=True):
                c1, c2, c3, c4, c5 = st.columns([2.4, 1, 1, 1, 1])
                title = c1.text_input("할 일", placeholder="예: 택배 확인 / 거래처 연락")
                category = c2.selectbox("분류", ["개인", "업무", "식혜명가", "결혼준비", "기타"])
                priority = c3.selectbox("중요도", ["보통", "높음", "낮음"])
                due_date = c4.date_input("날짜", value=date.today())
                due_time = c5.time_input("시간", value=time(18, 0))
                detail = st.text_area("상세", height=70)
                submitted = st.form_submit_button("등록", use_container_width=True)

                if submitted and title.strip():
                    q(
                        """
                        INSERT INTO tasks
                        (title, detail, category, priority, due_date, due_time, status, repeat_type, tags, created_at, notified_at)
                        VALUES (?, ?, ?, ?, ?, ?, '대기', '없음', '', ?, NULL)
                        """,
                        (title.strip(), detail.strip(), category, priority, due_date.isoformat(), due_time.strftime("%H:%M"), now_str()),
                    )
                    st.success("등록했습니다.")
                    st.rerun()

        with tab2:
            with st.form("quick_schedule", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([2.4, 1, 1, 1])
                title = c1.text_input("일정", placeholder="예: 미팅 / 납품 / 병원")
                schedule_date = c2.date_input("날짜", value=date.today(), key="q_sch_date")
                start_time = c3.time_input("시작", value=time(9, 0), key="q_sch_start")
                alarm_minutes = c4.selectbox("알림", [0, 5, 10, 30, 60, 120, 1440], format_func=lambda x: "시작시간" if x == 0 else f"{x}분 전")
                location = st.text_input("장소")
                submitted = st.form_submit_button("등록", use_container_width=True)

                if submitted and title.strip():
                    q(
                        """
                        INSERT INTO schedules
                        (title, detail, category, schedule_date, start_time, end_time, location, alarm_minutes, created_at, notified_at)
                        VALUES (?, '', '개인', ?, ?, '', ?, ?, ?, NULL)
                        """,
                        (title.strip(), schedule_date.isoformat(), start_time.strftime("%H:%M"), location.strip(), int(alarm_minutes), now_str()),
                    )
                    st.success("등록했습니다.")
                    st.rerun()

        with tab3:
            with st.form("quick_memo", clear_on_submit=True):
                title = st.text_input("메모 제목")
                content = st.text_area("내용", height=100)
                submitted = st.form_submit_button("저장", use_container_width=True)

                if submitted and title.strip():
                    q(
                        """
                        INSERT INTO memos
                        (title, content, tags, pinned, created_at, updated_at)
                        VALUES (?, ?, '', 0, ?, ?)
                        """,
                        (title.strip(), content.strip(), now_str(), now_str()),
                    )
                    st.success("저장했습니다.")
                    st.rerun()

    st.divider()

    left, right = st.columns([1.0, 1.25], gap="large")

    with left:
        st.markdown('<div class="section-title">✅ 지금 볼 할 일</div>', unsafe_allow_html=True)

        view = st.radio(
            "보기",
            ["오늘 중심", "기한 지남", "다가오는 일", "전체 미완료"],
            horizontal=True,
            label_visibility="collapsed",
        )

        if incomplete.empty:
            display_tasks = pd.DataFrame()
        elif view == "오늘 중심":
            display_tasks = pd.concat([overdue, today_tasks]).drop_duplicates(subset=["id"]).head(12)
        elif view == "기한 지남":
            display_tasks = overdue.head(12)
        elif view == "다가오는 일":
            display_tasks = incomplete[incomplete["due_date"] > today_str()].head(12)
        else:
            display_tasks = incomplete.head(20)

        if display_tasks.empty:
            st.info("표시할 할 일이 없습니다.")
        else:
            for _, row in display_tasks.iterrows():
                render_task_card(row, "dash")

    with right:
        st.markdown('<div class="section-title">📅 달력</div>', unsafe_allow_html=True)
        render_real_calendar(tasks, schedules)

        selected_date = st.session_state.get("selected_date", today_str())
        st.markdown(f"<div class='section-title'>📌 {selected_date} 상세</div>", unsafe_allow_html=True)

        selected_tasks = tasks[tasks["due_date"] == selected_date] if not tasks.empty else pd.DataFrame()
        selected_schedules = schedules[schedules["schedule_date"] == selected_date] if not schedules.empty else pd.DataFrame()

        st.markdown("**할 일**")
        if selected_tasks.empty:
            st.caption("해당 날짜 할 일이 없습니다.")
        else:
            for _, row in selected_tasks.sort_values(["due_time"]).iterrows():
                st.write(f"- `{row['due_time'] or '-'}` {status_label(row['status'])} **{row['title']}**")

        st.markdown("**일정**")
        if selected_schedules.empty:
            st.caption("해당 날짜 일정이 없습니다.")
        else:
            for _, row in selected_schedules.sort_values(["start_time"]).iterrows():
                alarm_txt = "시작시간" if not row["alarm_minutes"] else f"{int(row['alarm_minutes'])}분 전"
                st.write(f"- `{row['start_time'] or '-'}` **{row['title']}** · 알림 {alarm_txt}")


# =========================
# 할 일
# =========================
elif menu == "할 일":
    page_title("할 일 관리", "할 일 등록, 상태 변경, 반복, 시간 알림까지 관리합니다.")

    with st.expander("➕ 새 할 일 등록", expanded=True):
        with st.form("task_form", clear_on_submit=True):
            title = st.text_input("할 일 제목")
            detail = st.text_area("상세 내용", height=90)
            c1, c2, c3, c4 = st.columns(4)
            category = c1.selectbox("분류", ["개인", "업무", "식혜명가", "결혼준비", "기타"])
            priority = c2.selectbox("중요도", ["보통", "높음", "낮음"])
            due_date = c3.date_input("날짜", value=date.today())
            due_time = c4.time_input("시간", value=time(18, 0))
            c5, c6 = st.columns(2)
            repeat_type = c5.selectbox("반복", ["없음", "매일", "매주", "매월", "매년"])
            tags = c6.text_input("태그", placeholder="예: 택배,정산,청소")
            submitted = st.form_submit_button("등록", use_container_width=True)

            if submitted and title.strip():
                q(
                    """
                    INSERT INTO tasks
                    (title, detail, category, priority, due_date, due_time, status, repeat_type, tags, created_at, notified_at)
                    VALUES (?, ?, ?, ?, ?, ?, '대기', ?, ?, ?, NULL)
                    """,
                    (title.strip(), detail.strip(), category, priority, due_date.isoformat(), due_time.strftime("%H:%M"), repeat_type, tags.strip(), now_str()),
                )
                st.success("등록했습니다.")
                st.rerun()

    st.divider()

    tasks = safe_tasks_df()

    if tasks.empty:
        st.info("등록된 할 일이 없습니다.")
    else:
        c1, c2, c3, c4 = st.columns([1.6, 1, 1, 1])
        keyword = c1.text_input("검색", placeholder="제목, 내용, 태그")
        status_filter = c2.selectbox("상태", ["전체", "대기", "진행", "보류", "완료"])
        category_filter = c3.selectbox("분류", ["전체", "개인", "업무", "식혜명가", "결혼준비", "기타"])
        priority_filter = c4.selectbox("중요도", ["전체", "높음", "보통", "낮음"])

        filtered = tasks.copy()

        if keyword:
            filtered = filtered[
                filtered["title"].str.contains(keyword, case=False, na=False)
                | filtered["detail"].str.contains(keyword, case=False, na=False)
                | filtered["tags"].str.contains(keyword, case=False, na=False)
            ]
        if status_filter != "전체":
            filtered = filtered[filtered["status"] == status_filter]
        if category_filter != "전체":
            filtered = filtered[filtered["category"] == category_filter]
        if priority_filter != "전체":
            filtered = filtered[filtered["priority"] == priority_filter]

        st.caption(f"총 {len(filtered)}개")

        for _, row in filtered.iterrows():
            render_task_card(row, "task_page")


# =========================
# 일정
# =========================
elif menu == "일정":
    page_title("일정 관리", "시작 시간, 알림 시간, 장소를 포함해 일정을 관리합니다.")

    with st.expander("➕ 새 일정 등록", expanded=True):
        with st.form("schedule_form", clear_on_submit=True):
            title = st.text_input("일정명")
            detail = st.text_area("상세 내용", height=90)
            c1, c2, c3, c4 = st.columns(4)
            category = c1.selectbox("분류", ["개인", "업무", "식혜명가", "결혼준비", "기타"], key="schedule_category")
            schedule_date = c2.date_input("날짜", value=date.today(), key="schedule_date")
            start_time = c3.time_input("시작", value=time(9, 0), key="schedule_start")
            end_time = c4.time_input("종료", value=time(10, 0), key="schedule_end")
            c5, c6 = st.columns(2)
            location = c5.text_input("장소")
            alarm_minutes = c6.selectbox("알림", [0, 5, 10, 30, 60, 120, 1440], format_func=lambda x: "시작시간" if x == 0 else f"{x}분 전")
            submitted = st.form_submit_button("일정 등록", use_container_width=True)

            if submitted and title.strip():
                q(
                    """
                    INSERT INTO schedules
                    (title, detail, category, schedule_date, start_time, end_time, location, alarm_minutes, created_at, notified_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (title.strip(), detail.strip(), category, schedule_date.isoformat(), start_time.strftime("%H:%M"), end_time.strftime("%H:%M"), location.strip(), int(alarm_minutes), now_str()),
                )
                st.success("등록했습니다.")
                st.rerun()

    st.divider()

    tasks = safe_tasks_df()
    schedules = safe_schedules_df()

    tab1, tab2 = st.tabs(["달력 보기", "목록 보기"])

    with tab1:
        render_real_calendar(tasks, schedules)

        selected_date = st.session_state.get("selected_date", today_str())
        selected_schedules = schedules[schedules["schedule_date"] == selected_date] if not schedules.empty else pd.DataFrame()

        st.markdown(f"<div class='section-title'>📌 {selected_date} 일정</div>", unsafe_allow_html=True)

        if selected_schedules.empty:
            st.info("해당 날짜 일정이 없습니다.")
        else:
            for _, row in selected_schedules.sort_values(["start_time"]).iterrows():
                alarm_txt = "시작시간" if not row["alarm_minutes"] else f"{int(row['alarm_minutes'])}분 전"
                with st.expander(f"{row['start_time']} · {row['title']} · 알림 {alarm_txt}"):
                    if row["location"]:
                        st.write(f"장소: {row['location']}")
                    if row["detail"]:
                        st.write(row["detail"])
                    c1, c2 = st.columns(2)
                    if c1.button("🔔 다시 알림", key=f"sch_reset_cal_{row['id']}", use_container_width=True):
                        q("UPDATE schedules SET notified_at=NULL WHERE id=?", (int(row["id"]),))
                        st.rerun()
                    if c2.button("삭제", key=f"sch_del_cal_{row['id']}", use_container_width=True):
                        q("DELETE FROM schedules WHERE id=?", (int(row["id"]),))
                        st.rerun()

    with tab2:
        if schedules.empty:
            st.info("등록된 일정이 없습니다.")
        else:
            c1, c2 = st.columns([1.6, 1])
            keyword = c1.text_input("검색", placeholder="일정명, 내용, 장소")
            only_future = c2.checkbox("오늘 이후만 보기", value=True)

            filtered = schedules.copy()

            if keyword:
                filtered = filtered[
                    filtered["title"].str.contains(keyword, case=False, na=False)
                    | filtered["detail"].str.contains(keyword, case=False, na=False)
                    | filtered["location"].str.contains(keyword, case=False, na=False)
                ]

            if only_future:
                filtered = filtered[filtered["schedule_date"] >= today_str()]

            for _, row in filtered.iterrows():
                alarm_txt = "시작시간" if not row["alarm_minutes"] else f"{int(row['alarm_minutes'])}분 전"
                with st.expander(f"{row['schedule_date']} {row['start_time']} · {row['title']} · 알림 {alarm_txt}"):
                    if row["location"]:
                        st.write(f"장소: {row['location']}")
                    if row["detail"]:
                        st.write(row["detail"])
                    c1, c2 = st.columns(2)
                    if c1.button("🔔 다시 알림", key=f"sch_reset_list_{row['id']}", use_container_width=True):
                        q("UPDATE schedules SET notified_at=NULL WHERE id=?", (int(row["id"]),))
                        st.rerun()
                    if c2.button("삭제", key=f"sch_del_list_{row['id']}", use_container_width=True):
                        q("DELETE FROM schedules WHERE id=?", (int(row["id"]),))
                        st.rerun()


# =========================
# 메모장
# =========================
elif menu == "메모장":
    page_title("메모장", "빠른 메모, 고정, 검색, 수정을 지원합니다.")

    with st.expander("➕ 새 메모", expanded=True):
        with st.form("memo_form", clear_on_submit=True):
            title = st.text_input("제목")
            content = st.text_area("내용", height=160)
            c1, c2 = st.columns([2, 1])
            tags = c1.text_input("태그", placeholder="예: 아이디어,구매,업무")
            pinned = c2.checkbox("상단 고정")
            submitted = st.form_submit_button("저장", use_container_width=True)

            if submitted and title.strip():
                q(
                    """
                    INSERT INTO memos
                    (title, content, tags, pinned, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (title.strip(), content.strip(), tags.strip(), 1 if pinned else 0, now_str(), now_str()),
                )
                st.success("저장했습니다.")
                st.rerun()

    st.divider()

    memos = safe_memos_df()

    if memos.empty:
        st.info("등록된 메모가 없습니다.")
    else:
        keyword = st.text_input("검색", placeholder="제목, 내용, 태그")

        if keyword:
            memos = memos[
                memos["title"].str.contains(keyword, case=False, na=False)
                | memos["content"].str.contains(keyword, case=False, na=False)
                | memos["tags"].str.contains(keyword, case=False, na=False)
            ]

        for _, row in memos.iterrows():
            pin = "📌 " if row["pinned"] else ""
            with st.expander(f"{pin}{row['title']} · {row['updated_at']}"):
                if row["tags"]:
                    st.caption(f"태그: {row['tags']}")
                st.write(row["content"] or "내용 없음")

                with st.form(f"edit_memo_{row['id']}"):
                    new_title = st.text_input("제목 수정", value=row["title"])
                    new_content = st.text_area("내용 수정", value=row["content"], height=130)
                    new_tags = st.text_input("태그 수정", value=row["tags"])
                    new_pinned = st.checkbox("상단 고정", value=bool(row["pinned"]))
                    save = st.form_submit_button("수정 저장", use_container_width=True)

                    if save and new_title.strip():
                        q(
                            """
                            UPDATE memos
                            SET title=?, content=?, tags=?, pinned=?, updated_at=?
                            WHERE id=?
                            """,
                            (new_title.strip(), new_content.strip(), new_tags.strip(), 1 if new_pinned else 0, now_str(), int(row["id"])),
                        )
                        st.success("수정했습니다.")
                        st.rerun()

                if st.button("삭제", key=f"memo_delete_{row['id']}", use_container_width=True):
                    q("DELETE FROM memos WHERE id=?", (int(row["id"]),))
                    st.rerun()


# =========================
# 백업/설정
# =========================
elif menu == "백업/설정":
    page_title("백업/설정", "데이터 백업과 초기화를 관리합니다.")

    st.info("알림은 앱 화면이 켜져 있을 때만 작동합니다. 소리가 안 나면 페이지를 한 번 클릭한 뒤 알림 테스트를 눌러보세요.")

    c1, c2 = st.columns(2)
    c1.download_button(
        "📊 엑셀로 내보내기",
        data=download_excel(),
        file_name=f"일상관리_백업_{today_str()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    c2.download_button(
        "🗄️ DB 파일 백업",
        data=download_db(),
        file_name=f"daily_manager_{today_str()}.db",
        mime="application/octet-stream",
        use_container_width=True,
    )

    st.divider()

    c1, c2, c3 = st.columns(3)
    c1.metric("할 일", int(df("SELECT COUNT(*) AS n FROM tasks")["n"][0]))
    c2.metric("일정", int(df("SELECT COUNT(*) AS n FROM schedules")["n"][0]))
    c3.metric("메모", int(df("SELECT COUNT(*) AS n FROM memos")["n"][0]))

    st.divider()

    st.subheader("초기화")
    st.warning("초기화 전 백업을 먼저 받으세요.")

    target = st.selectbox("초기화 대상", ["선택 안 함", "완료된 할 일만 삭제", "할 일 전체", "일정 전체", "메모 전체", "전체 데이터"])
    confirm = st.text_input("실행하려면 삭제 입력")

    if st.button("초기화 실행", type="primary", use_container_width=True):
        if confirm != "삭제":
            st.error("확인 문구가 맞지 않습니다.")
        else:
            if target == "완료된 할 일만 삭제":
                q("DELETE FROM tasks WHERE status='완료'")
            elif target == "할 일 전체":
                q("DELETE FROM tasks")
            elif target == "일정 전체":
                q("DELETE FROM schedules")
            elif target == "메모 전체":
                q("DELETE FROM memos")
            elif target == "전체 데이터":
                q("DELETE FROM tasks")
                q("DELETE FROM schedules")
                q("DELETE FROM memos")
            else:
                st.error("초기화 대상을 선택하세요.")
                st.stop()

            st.success("초기화했습니다.")
            st.rerun()

    st.divider()

    st.code("pip install streamlit pandas openpyxl\nstreamlit run daily_manager_app.py", language="bash")

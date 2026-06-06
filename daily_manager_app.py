
import sqlite3
from pathlib import Path
from datetime import datetime, date, time, timedelta
from io import BytesIO
import calendar
import html

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


APP_TITLE = "일상 관리 프로그램"
DB_PATH = Path("daily_manager.db")


# =========================
# 페이지 설정 / 디자인
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
        max-width: 1500px;
    }

    .app-title {
        font-size: 2.1rem;
        font-weight: 950;
        letter-spacing: -0.05em;
        margin-bottom: 0.2rem;
    }

    .app-subtitle {
        color: #6b7280;
        font-size: 0.95rem;
        margin-bottom: 1rem;
    }

    .section-title {
        font-size: 1.25rem;
        font-weight: 900;
        margin: 0.4rem 0 0.8rem 0;
        letter-spacing: -0.04em;
    }

    .mini-muted {
        color: #6b7280;
        font-size: 0.85rem;
    }

    .dashboard-box {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 20px;
        padding: 1rem;
        box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
        margin-bottom: 1rem;
    }

    .task-card {
        border: 1px solid #e5e7eb;
        background: #ffffff;
        border-radius: 16px;
        padding: 0.8rem 0.9rem;
        margin-bottom: 0.65rem;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.035);
    }

    .task-card-overdue {
        border-left: 7px solid #ef4444;
        background: #fff7f7;
    }

    .task-card-today {
        border-left: 7px solid #2563eb;
        background: #f8fbff;
    }

    .task-card-upcoming {
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
        padding: 0.16rem 0.5rem;
        border-radius: 999px;
        background: #f3f4f6;
        border: 1px solid #e5e7eb;
        color: #374151;
        font-size: 0.78rem;
        margin-right: 0.2rem;
        margin-top: 0.25rem;
    }

    .pill-red {background:#fee2e2; color:#991b1b; border-color:#fecaca;}
    .pill-blue {background:#dbeafe; color:#1e40af; border-color:#bfdbfe;}
    .pill-green {background:#d1fae5; color:#065f46; border-color:#a7f3d0;}
    .pill-yellow {background:#fef3c7; color:#92400e; border-color:#fde68a;}

    .quick-panel {
        background: linear-gradient(180deg, #ffffff 0%, #f9fafb 100%);
        border: 1px solid #e5e7eb;
        border-radius: 20px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    .calendar-wrap {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 22px;
        padding: 1rem;
        box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
    }

    .calendar-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 0.75rem;
    }

    .calendar-month {
        font-size: 1.35rem;
        font-weight: 950;
        letter-spacing: -0.04em;
    }

    .calendar-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 6px;
        table-layout: fixed;
    }

    .calendar-table th {
        text-align: center;
        color: #6b7280;
        font-size: 0.82rem;
        padding-bottom: 0.25rem;
    }

    .calendar-cell {
        height: 86px;
        vertical-align: top;
        border: 1px solid #e5e7eb;
        border-radius: 15px;
        background: #fafafa;
        padding: 0.45rem;
        overflow: hidden;
    }

    .calendar-cell.empty {
        background: #ffffff;
        border-color: transparent;
    }

    .calendar-cell.today {
        border: 2px solid #2563eb;
        background: #eff6ff;
    }

    .calendar-day {
        font-weight: 900;
        font-size: 0.92rem;
        margin-bottom: 0.25rem;
    }

    .calendar-count {
        display: inline-block;
        font-size: 0.72rem;
        padding: 0.11rem 0.36rem;
        border-radius: 999px;
        margin-right: 0.12rem;
        margin-bottom: 0.12rem;
    }

    .count-task {
        background: #fee2e2;
        color: #991b1b;
    }

    .count-schedule {
        background: #dbeafe;
        color: #1e40af;
    }

    .count-done {
        background: #d1fae5;
        color: #065f46;
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
# 공통 유틸
# =========================
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str():
    return date.today().isoformat()


def parse_date(s):
    try:
        return date.fromisoformat(str(s))
    except Exception:
        return None


def combine_datetime(d, t):
    if not d:
        return None
    try:
        if t:
            return datetime.fromisoformat(f"{d} {t}")
        return datetime.fromisoformat(f"{d} 23:59:59")
    except Exception:
        return None


def priority_badge(priority):
    if priority == "높음":
        return "🔥 높음"
    if priority == "낮음":
        return "낮음"
    return "보통"


def status_badge(status):
    if status == "완료":
        return "✅ 완료"
    if status == "진행":
        return "🟡 진행"
    if status == "보류":
        return "⏸️ 보류"
    return "대기"


def task_group(row):
    if row["status"] == "완료":
        return "done"
    dt = combine_datetime(row["due_date"], row["due_time"])
    if dt and dt < datetime.now():
        return "overdue"
    if row["due_date"] == today_str():
        return "today"
    return "upcoming"


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
        last_days = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        return date(year, month, min(d.day, last_days[month - 1]))
    if repeat_type == "매년":
        try:
            return date(d.year + 1, d.month, d.day)
        except ValueError:
            return date(d.year + 1, 2, 28)
    return None


def render_tags(tags):
    if not tags:
        return ""
    parts = [x.strip() for x in tags.replace("#", "").split(",") if x.strip()]
    return " ".join([f'<span class="pill">#{html.escape(p)}</span>' for p in parts])


def section_title(title, desc=""):
    st.markdown(f'<div class="app-title">{title}</div>', unsafe_allow_html=True)
    if desc:
        st.markdown(f'<div class="app-subtitle">{desc}</div>', unsafe_allow_html=True)


def download_excel():
    tasks = df("SELECT * FROM tasks ORDER BY created_at DESC")
    schedules = df("SELECT * FROM schedules ORDER BY schedule_date DESC, start_time DESC")
    memos = df("SELECT * FROM memos ORDER BY pinned DESC, updated_at DESC")

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        tasks.to_excel(writer, index=False, sheet_name="할일")
        schedules.to_excel(writer, index=False, sheet_name="일정")
        memos.to_excel(writer, index=False, sheet_name="메모")
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
                    "message": f"할 일 시간입니다: {row['title']}"
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
                msg = f"{alarm_minutes}분 후 일정입니다: {row['title']}" if alarm_minutes > 0 else f"일정 시작입니다: {row['title']}"
                alerts.append({
                    "type": "일정",
                    "id": int(row["id"]),
                    "title": row["title"],
                    "time": start_dt.strftime("%Y-%m-%d %H:%M"),
                    "message": msg
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

    lines = "".join(
        f"<li><b>{html.escape(a['type'])}</b> · {html.escape(a['time'])} · {html.escape(a['title'])}</li>"
        for a in alerts
    )

    st.markdown(
        f"""
        <div class="alarm-box">
            <div class="alarm-title">🔔 알림</div>
            <ul>{lines}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    joined = "\\n".join([a["message"] for a in alerts])
    safe_msg = joined.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

    components.html(
        f"""
        <script>
        const msg = `{safe_msg}`;
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
                    gain.gain.exponentialRampToValueAtTime(0.35, ctx.currentTime + start + 0.02);
                    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + start + duration);
                    osc.start(ctx.currentTime + start);
                    osc.stop(ctx.currentTime + start + duration + 0.03);
                }}

                beep(880, 0.00, 0.25);
                beep(1046, 0.32, 0.25);
                beep(880, 0.64, 0.25);
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
# 대시보드용 컴포넌트
# =========================
def render_task_card(row, key_prefix, compact=False):
    group = task_group(row)
    css = {
        "overdue": "task-card task-card-overdue",
        "today": "task-card task-card-today",
        "upcoming": "task-card task-card-upcoming",
        "done": "task-card",
    }[group]

    time_label = row["due_time"] or "--:--"
    date_label = row["due_date"] or "날짜없음"
    priority_class = "pill-red" if row["priority"] == "높음" else "pill-yellow" if row["priority"] == "보통" else ""
    group_label = "기한지남" if group == "overdue" else "오늘" if group == "today" else "완료" if group == "done" else "예정"
    group_class = "pill-red" if group == "overdue" else "pill-blue" if group == "today" else "pill-green" if group == "upcoming" else ""

    st.markdown(
        f"""
        <div class="{css}">
            <div class="task-title">{html.escape(row['title'])}</div>
            <div style="margin-top:0.35rem;">
                <span class="pill {group_class}">{group_label}</span>
                <span class="pill">{html.escape(row['category'])}</span>
                <span class="pill {priority_class}">{priority_badge(row['priority'])}</span>
                <span class="pill">⏰ {html.escape(date_label)} {html.escape(time_label)}</span>
            </div>
            {f'<div class="mini-muted" style="margin-top:0.4rem;">{html.escape(row["detail"][:80])}</div>' if row["detail"] else ''}
            {render_tags(row["tags"]) if row["tags"] else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1, 1, 1])
    if row["status"] != "완료":
        if c1.button("완료", key=f"{key_prefix}_done_{row['id']}", use_container_width=True):
            q("UPDATE tasks SET status='완료', completed_at=? WHERE id=?", (now_str(), row["id"]))

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
            st.rerun()
    else:
        if c1.button("미완료", key=f"{key_prefix}_undo_{row['id']}", use_container_width=True):
            q("UPDATE tasks SET status='대기', completed_at=NULL WHERE id=?", (row["id"],))
            st.rerun()

    if c2.button("진행", key=f"{key_prefix}_progress_{row['id']}", use_container_width=True):
        q("UPDATE tasks SET status='진행' WHERE id=?", (row["id"],))
        st.rerun()

    if c3.button("삭제", key=f"{key_prefix}_del_{row['id']}", use_container_width=True):
        q("DELETE FROM tasks WHERE id=?", (row["id"],))
        st.rerun()


def month_calendar_html(year, month, tasks, schedules):
    cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
    weeks = cal.monthdayscalendar(year, month)

    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(year, month + 1, 1) - timedelta(days=1)

    tasks_in_month = tasks.copy()
    schedules_in_month = schedules.copy()

    if not tasks_in_month.empty:
        tasks_in_month = tasks_in_month[
            (tasks_in_month["due_date"] >= month_start.isoformat()) &
            (tasks_in_month["due_date"] <= month_end.isoformat())
        ]
    if not schedules_in_month.empty:
        schedules_in_month = schedules_in_month[
            (schedules_in_month["schedule_date"] >= month_start.isoformat()) &
            (schedules_in_month["schedule_date"] <= month_end.isoformat())
        ]

    task_counts = tasks_in_month.groupby("due_date").size().to_dict() if not tasks_in_month.empty else {}
    schedule_counts = schedules_in_month.groupby("schedule_date").size().to_dict() if not schedules_in_month.empty else {}
    done_counts = tasks_in_month[tasks_in_month["status"] == "완료"].groupby("due_date").size().to_dict() if not tasks_in_month.empty else {}

    html_rows = []
    for week in weeks:
        tds = []
        for day in week:
            if day == 0:
                tds.append('<td class="calendar-cell empty"></td>')
                continue

            d = date(year, month, day)
            d_str = d.isoformat()
            is_today = d == date.today()
            cls = "calendar-cell today" if is_today else "calendar-cell"

            task_count = int(task_counts.get(d_str, 0))
            schedule_count = int(schedule_counts.get(d_str, 0))
            done_count = int(done_counts.get(d_str, 0))

            badges = ""
            if task_count:
                badges += f'<span class="calendar-count count-task">할일 {task_count}</span>'
            if schedule_count:
                badges += f'<span class="calendar-count count-schedule">일정 {schedule_count}</span>'
            if done_count:
                badges += f'<span class="calendar-count count-done">완료 {done_count}</span>'

            tds.append(
                f"""
                <td class="{cls}">
                    <div class="calendar-day">{day}</div>
                    {badges}
                </td>
                """
            )
        html_rows.append("<tr>" + "".join(tds) + "</tr>")

    return f"""
    <div class="calendar-wrap">
        <div class="calendar-header">
            <div class="calendar-month">{year}년 {month}월</div>
            <div class="mini-muted">빨강=할 일 · 파랑=일정</div>
        </div>
        <table class="calendar-table">
            <thead>
                <tr>
                    <th>일</th><th>월</th><th>화</th><th>수</th><th>목</th><th>금</th><th>토</th>
                </tr>
            </thead>
            <tbody>
                {''.join(html_rows)}
            </tbody>
        </table>
    </div>
    """


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
    refresh_seconds = st.selectbox("확인 주기", [15, 30, 60, 120, 300], index=2, format_func=lambda x: f"{x}초마다")
    st.caption("앱 화면이 열려 있어야 알림이 울립니다.")

    if st.button("🔊 알림 테스트", use_container_width=True):
        render_alarm([{
            "type": "테스트",
            "id": 0,
            "title": "알림 테스트",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "message": "알림 테스트입니다."
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
    section_title("대시보드", "왼쪽은 할 일, 오른쪽은 달력. 오늘 할 일을 바로 보고 바로 처리합니다.")

    tasks_all = df("SELECT * FROM tasks ORDER BY due_date ASC, due_time ASC, priority DESC")
    schedules_all = df("SELECT * FROM schedules ORDER BY schedule_date ASC, start_time ASC")
    memos_all = df("SELECT * FROM memos ORDER BY pinned DESC, updated_at DESC")

    if tasks_all.empty:
        tasks_all = pd.DataFrame(columns=["id","title","detail","category","priority","due_date","due_time","status","repeat_type","tags","created_at","completed_at","notified_at"])
    if schedules_all.empty:
        schedules_all = pd.DataFrame(columns=["id","title","detail","category","schedule_date","start_time","end_time","location","alarm_minutes","created_at","notified_at"])

    incomplete = tasks_all[tasks_all["status"] != "완료"]
    overdue = incomplete[incomplete.apply(lambda r: task_group(r) == "overdue", axis=1)] if not incomplete.empty else pd.DataFrame()
    today_tasks = incomplete[incomplete["due_date"] == today_str()] if not incomplete.empty else pd.DataFrame()
    upcoming = incomplete[incomplete["due_date"] > today_str()].head(8) if not incomplete.empty else pd.DataFrame()
    today_schedules = schedules_all[schedules_all["schedule_date"] == today_str()] if not schedules_all.empty else pd.DataFrame()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("오늘 할 일", len(today_tasks))
    m2.metric("기한 지남", len(overdue))
    m3.metric("미완료 전체", len(incomplete))
    m4.metric("오늘 일정", len(today_schedules))

    st.markdown("")

    # 빠른 등록
    with st.expander("➕ 빠른 등록", expanded=False):
        tab_task, tab_schedule, tab_memo = st.tabs(["할 일", "일정", "메모"])
        with tab_task:
            with st.form("dash_quick_task", clear_on_submit=True):
                c1, c2, c3, c4, c5 = st.columns([2.2, 1, 1, 1, 1])
                title = c1.text_input("할 일", placeholder="예: 거래처 연락 / 택배 확인")
                category = c2.selectbox("분류", ["개인", "업무", "식혜명가", "결혼준비", "기타"])
                priority = c3.selectbox("중요도", ["보통", "높음", "낮음"])
                due_date = c4.date_input("날짜", value=date.today())
                due_time = c5.time_input("시간", value=time(18, 0))
                detail = st.text_area("상세 내용", height=70)
                submitted = st.form_submit_button("할 일 등록", use_container_width=True)
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

        with tab_schedule:
            with st.form("dash_quick_schedule", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([2.2, 1, 1, 1])
                title = c1.text_input("일정", placeholder="예: 미팅 / 납품 / 병원")
                schedule_date = c2.date_input("날짜", value=date.today(), key="dash_sch_date")
                start_time = c3.time_input("시작", value=time(9, 0), key="dash_sch_start")
                alarm_minutes = c4.selectbox("알림", [0, 5, 10, 30, 60, 120, 1440], format_func=lambda x: "시작시간" if x == 0 else f"{x}분 전")
                location = st.text_input("장소")
                submitted = st.form_submit_button("일정 등록", use_container_width=True)
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

        with tab_memo:
            with st.form("dash_quick_memo", clear_on_submit=True):
                title = st.text_input("메모 제목")
                content = st.text_area("내용", height=100)
                submitted = st.form_submit_button("메모 등록", use_container_width=True)
                if submitted and title.strip():
                    q(
                        """
                        INSERT INTO memos
                        (title, content, tags, pinned, created_at, updated_at)
                        VALUES (?, ?, '', 0, ?, ?)
                        """,
                        (title.strip(), content.strip(), now_str(), now_str()),
                    )
                    st.success("등록했습니다.")
                    st.rerun()

    left, right = st.columns([1.03, 1.17], gap="large")

    with left:
        st.markdown('<div class="section-title">✅ 지금 볼 할 일</div>', unsafe_allow_html=True)

        view_filter = st.radio(
            "보기",
            ["오늘 중심", "기한 지남", "다가오는 일", "전체 미완료"],
            horizontal=True,
            label_visibility="collapsed",
        )

        if view_filter == "오늘 중심":
            display_tasks = pd.concat([overdue, today_tasks]).drop_duplicates(subset=["id"]).head(12)
        elif view_filter == "기한 지남":
            display_tasks = overdue.head(12)
        elif view_filter == "다가오는 일":
            display_tasks = upcoming.head(12)
        else:
            display_tasks = incomplete.head(20)

        if display_tasks.empty:
            st.info("표시할 할 일이 없습니다. 빠른 등록에서 하나 추가하세요.")
        else:
            for _, row in display_tasks.iterrows():
                render_task_card(row, key_prefix=f"dash_{view_filter}")

    with right:
        now_date = date.today()
        c_y, c_m = st.columns(2)
        cal_year = int(c_y.number_input("연도", min_value=2000, max_value=2100, value=now_date.year))
        cal_month = int(c_m.number_input("월", min_value=1, max_value=12, value=now_date.month))
        st.markdown(month_calendar_html(cal_year, cal_month, tasks_all, schedules_all), unsafe_allow_html=True)

        selected_day = st.date_input("날짜별 상세 보기", value=date.today(), key="dashboard_selected_day")
        selected_str = selected_day.isoformat()

        day_tasks = tasks_all[tasks_all["due_date"] == selected_str] if not tasks_all.empty else pd.DataFrame()
        day_schedules = schedules_all[schedules_all["schedule_date"] == selected_str] if not schedules_all.empty else pd.DataFrame()

        st.markdown(f'<div class="section-title">📌 {selected_str} 상세</div>', unsafe_allow_html=True)

        st.markdown("**할 일**")
        if day_tasks.empty:
            st.caption("해당 날짜 할 일이 없습니다.")
        else:
            for _, row in day_tasks.sort_values(["due_time"]).iterrows():
                st.write(f"- `{row['due_time'] or '-'}` {status_badge(row['status'])} **{row['title']}**")

        st.markdown("**일정**")
        if day_schedules.empty:
            st.caption("해당 날짜 일정이 없습니다.")
        else:
            for _, row in day_schedules.sort_values(["start_time"]).iterrows():
                alarm_txt = "시작시간" if not row["alarm_minutes"] else f"{int(row['alarm_minutes'])}분 전"
                st.write(f"- `{row['start_time'] or '-'}` **{row['title']}** · 알림 {alarm_txt}")


# =========================
# 할 일 페이지
# =========================
elif menu == "할 일":
    section_title("할 일 관리", "등록, 검색, 상태 변경, 반복, 시간 알림까지 관리합니다.")

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

    tasks = df("SELECT * FROM tasks ORDER BY due_date ASC, due_time ASC, created_at DESC")
    if tasks.empty:
        st.info("등록된 할 일이 없습니다.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
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
            render_task_card(row, key_prefix="task_page")


# =========================
# 일정 페이지
# =========================
elif menu == "일정":
    section_title("일정 관리", "일정 등록, 알림 시간, 월별 보기, 날짜별 목록을 관리합니다.")

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

    schedules = df("SELECT * FROM schedules ORDER BY schedule_date ASC, start_time ASC")
    tasks = df("SELECT * FROM tasks ORDER BY due_date ASC, due_time ASC")
    if schedules.empty:
        st.info("등록된 일정이 없습니다.")
    else:
        tab1, tab2 = st.tabs(["월간 달력", "목록"])
        with tab1:
            now_date = date.today()
            c1, c2 = st.columns(2)
            y = int(c1.number_input("연도", 2000, 2100, now_date.year, key="sch_y"))
            m = int(c2.number_input("월", 1, 12, now_date.month, key="sch_m"))
            st.markdown(month_calendar_html(y, m, tasks, schedules), unsafe_allow_html=True)

        with tab2:
            c1, c2 = st.columns([1.5, 1])
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
                    st.write(f"분류: {row['category']}")
                    if row["location"]:
                        st.write(f"장소: {row['location']}")
                    if row["detail"]:
                        st.write(row["detail"])
                    c1, c2 = st.columns(2)
                    if c1.button("🔔 다시 알림", key=f"sch_reset_{row['id']}", use_container_width=True):
                        q("UPDATE schedules SET notified_at=NULL WHERE id=?", (row["id"],))
                        st.rerun()
                    if c2.button("삭제", key=f"sch_del_{row['id']}", use_container_width=True):
                        q("DELETE FROM schedules WHERE id=?", (row["id"],))
                        st.rerun()


# =========================
# 메모장
# =========================
elif menu == "메모장":
    section_title("메모장", "빠른 메모, 고정, 검색 기능을 제공합니다.")

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
    memos = df("SELECT * FROM memos ORDER BY pinned DESC, updated_at DESC")
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
                    st.markdown(render_tags(row["tags"]), unsafe_allow_html=True)
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
                            (new_title.strip(), new_content.strip(), new_tags.strip(), 1 if new_pinned else 0, now_str(), row["id"]),
                        )
                        st.rerun()

                if st.button("삭제", key=f"memo_del_{row['id']}", use_container_width=True):
                    q("DELETE FROM memos WHERE id=?", (row["id"],))
                    st.rerun()


# =========================
# 백업/설정
# =========================
elif menu == "백업/설정":
    section_title("백업/설정", "데이터 백업과 초기화를 관리합니다.")

    st.info("알림은 앱 화면이 켜져 있을 때만 작동합니다. 소리가 안 나면 페이지를 한 번 클릭한 뒤 알림 테스트를 누르세요.")

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
    st.subheader("데이터 현황")
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

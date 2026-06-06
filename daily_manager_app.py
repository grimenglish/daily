
import sqlite3
from pathlib import Path
from datetime import datetime, date, time, timedelta
from io import BytesIO
import html

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
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    .main-title {
        font-size: 2.0rem;
        font-weight: 900;
        margin-bottom: 0.15rem;
    }
    .sub-title {
        color: #666;
        margin-bottom: 1.2rem;
    }
    .tag {
        display: inline-block;
        padding: 0.18rem 0.48rem;
        border-radius: 999px;
        background: #f0f2f6;
        margin-right: 0.25rem;
        font-size: 0.82rem;
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
    .small-muted {color:#777; font-size:0.88rem;}
    .danger {color:#d64545; font-weight:700;}
    .success {color:#168038; font-weight:700;}
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
    cols = table_columns(table_name)
    if column_name not in cols:
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

    # 기존 DB를 쓰는 경우 자동 마이그레이션
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
        last_days = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        day = min(d.day, last_days[month - 1])
        return date(year, month, day)
    if repeat_type == "매년":
        try:
            return date(d.year + 1, d.month, d.day)
        except ValueError:
            return date(d.year + 1, 2, 28)
    return None


def priority_badge(priority):
    if priority == "높음":
        return "🔥 높음"
    if priority == "낮음":
        return "⬇️ 낮음"
    return "● 보통"


def status_badge(status):
    if status == "완료":
        return "✅ 완료"
    if status == "진행":
        return "🟡 진행"
    if status == "보류":
        return "⏸️ 보류"
    return "⬜ 대기"


def is_overdue(due_date, due_time, status):
    if status == "완료" or not due_date:
        return False
    dt = combine_datetime(due_date, due_time)
    return dt is not None and dt < datetime.now()


def render_tags(tags):
    if not tags:
        return ""
    parts = [x.strip() for x in tags.replace("#", "").split(",") if x.strip()]
    return " ".join([f'<span class="tag">#{p}</span>' for p in parts])


def section_title(title, desc=""):
    st.markdown(f'<div class="main-title">{title}</div>', unsafe_allow_html=True)
    if desc:
        st.markdown(f'<div class="sub-title">{desc}</div>', unsafe_allow_html=True)


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
    if DB_PATH.exists():
        return DB_PATH.read_bytes()
    return b""


# =========================
# 알림 기능
# =========================
def get_due_alerts():
    """알림이 필요한 항목을 찾는다. 이미 울린 항목은 notified_at으로 중복 방지."""
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
                    "message": f"할 일 마감시간입니다: {row['title']}"
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

            # 너무 오래 지난 일정이 갑자기 울리지 않게 24시간 이내만 처리
            if alarm_dt <= now <= start_dt + timedelta(hours=24):
                if alarm_minutes > 0:
                    msg = f"{alarm_minutes}분 후 일정입니다: {row['title']}"
                else:
                    msg = f"일정 시작시간입니다: {row['title']}"

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

                async function beep(freq, start, duration) {{
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

                if (ctx.state === "suspended") {{
                    await ctx.resume();
                }}

                beep(880, 0.00, 0.25);
                beep(1046, 0.32, 0.25);
                beep(880, 0.64, 0.25);
            }} catch(e) {{
                console.log("sound blocked", e);
            }}
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
    refresh_seconds = st.selectbox("확인 주기", [15, 30, 60, 120, 300], index=1, format_func=lambda x: f"{x}초마다")
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
    st.caption("데이터는 daily_manager.db에 저장됩니다.")

    st.divider()
    st.download_button(
        "📦 전체 엑셀 백업",
        data=download_excel(),
        file_name=f"일상관리_백업_{today_str()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


# 알림 자동 확인
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
    section_title("대시보드", "오늘 할 일, 오늘 일정, 최근 메모를 한눈에 봅니다.")

    tasks_all = df("SELECT * FROM tasks")
    schedules_all = df("SELECT * FROM schedules")
    memos_all = df("SELECT * FROM memos")

    today_tasks = tasks_all[
        (tasks_all["due_date"] == today_str()) & (tasks_all["status"] != "완료")
    ] if not tasks_all.empty else pd.DataFrame()

    overdue_count = 0
    if not tasks_all.empty:
        overdue_count = sum(
            is_overdue(row["due_date"], row["due_time"], row["status"])
            for _, row in tasks_all.iterrows()
        )

    today_schedules = schedules_all[
        schedules_all["schedule_date"] == today_str()
    ] if not schedules_all.empty else pd.DataFrame()

    incomplete_count = int((tasks_all["status"] != "완료").sum()) if not tasks_all.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("오늘 할 일", len(today_tasks))
    c2.metric("미완료 할 일", incomplete_count)
    c3.metric("기한 지남", overdue_count)
    c4.metric("오늘 일정", len(today_schedules))

    st.divider()

    left, right = st.columns([1.2, 1])

    with left:
        st.subheader("⚡ 빠른 등록")

        tab1, tab2, tab3 = st.tabs(["할 일", "일정", "메모"])

        with tab1:
            with st.form("quick_task_form", clear_on_submit=True):
                title = st.text_input("할 일", placeholder="예: 택배 송장 확인")
                cols = st.columns(4)
                category = cols[0].selectbox("분류", ["개인", "업무", "식혜명가", "결혼준비", "기타"])
                priority = cols[1].selectbox("중요도", ["보통", "높음", "낮음"])
                due_date = cols[2].date_input("마감일", value=date.today())
                due_time = cols[3].time_input("마감 시간", value=datetime.now().time().replace(second=0, microsecond=0))
                submitted = st.form_submit_button("등록", use_container_width=True)
                if submitted and title.strip():
                    q(
                        """
                        INSERT INTO tasks
                        (title, detail, category, priority, due_date, due_time, status, repeat_type, tags, created_at, notified_at)
                        VALUES (?, '', ?, ?, ?, ?, '대기', '없음', '', ?, NULL)
                        """,
                        (title.strip(), category, priority, due_date.isoformat(), due_time.strftime("%H:%M"), now_str()),
                    )
                    st.success("할 일을 등록했습니다.")
                    st.rerun()

        with tab2:
            with st.form("quick_schedule_form", clear_on_submit=True):
                title = st.text_input("일정명", placeholder="예: 미팅 / 병원 / 납품")
                cols = st.columns(4)
                schedule_date = cols[0].date_input("날짜", value=date.today(), key="quick_sch_date")
                start_time = cols[1].time_input("시작", value=time(9, 0), key="quick_sch_start")
                alarm_minutes = cols[2].selectbox("알림", [0, 10, 30, 60, 120], format_func=lambda x: "시작시간" if x == 0 else f"{x}분 전")
                category = cols[3].selectbox("분류", ["개인", "업무", "식혜명가", "결혼준비", "기타"], key="quick_sch_cat")
                submitted = st.form_submit_button("등록", use_container_width=True)
                if submitted and title.strip():
                    q(
                        """
                        INSERT INTO schedules
                        (title, detail, category, schedule_date, start_time, end_time, location, alarm_minutes, created_at, notified_at)
                        VALUES (?, '', ?, ?, ?, '', '', ?, ?, NULL)
                        """,
                        (title.strip(), category, schedule_date.isoformat(), start_time.strftime("%H:%M"), int(alarm_minutes), now_str()),
                    )
                    st.success("일정을 등록했습니다.")
                    st.rerun()

        with tab3:
            with st.form("quick_memo_form", clear_on_submit=True):
                title = st.text_input("메모 제목", placeholder="예: 아이디어 / 구매할 것")
                content = st.text_area("내용", height=100)
                pinned = st.checkbox("고정")
                submitted = st.form_submit_button("등록", use_container_width=True)
                if submitted and title.strip():
                    q(
                        """
                        INSERT INTO memos
                        (title, content, tags, pinned, created_at, updated_at)
                        VALUES (?, ?, '', ?, ?, ?)
                        """,
                        (title.strip(), content.strip(), 1 if pinned else 0, now_str(), now_str()),
                    )
                    st.success("메모를 등록했습니다.")
                    st.rerun()

    with right:
        st.subheader("📌 오늘 요약")

        st.markdown("**오늘 할 일**")
        if today_tasks.empty:
            st.info("오늘 마감인 할 일이 없습니다.")
        else:
            for _, row in today_tasks.sort_values(["due_time"]).iterrows():
                st.write(f"- `{row['due_time'] or '-'}` {priority_badge(row['priority'])} **{row['title']}**  `{row['category']}`")

        st.markdown("**오늘 일정**")
        if today_schedules.empty:
            st.info("오늘 일정이 없습니다.")
        else:
            for _, row in today_schedules.sort_values(["start_time"]).iterrows():
                t = row["start_time"] or ""
                alarm_txt = "시작시간" if not row["alarm_minutes"] else f"{int(row['alarm_minutes'])}분 전"
                st.write(f"- `{t}` **{row['title']}**  알림: {alarm_txt}")

        st.markdown("**최근 메모**")
        recent_memos = memos_all.sort_values(["pinned", "updated_at"], ascending=[False, False]).head(5) if not memos_all.empty else pd.DataFrame()
        if recent_memos.empty:
            st.info("메모가 없습니다.")
        else:
            for _, row in recent_memos.iterrows():
                pin = "📌 " if row["pinned"] else ""
                st.write(f"- {pin}**{row['title']}**")


# =========================
# 할 일
# =========================
elif menu == "할 일":
    section_title("할 일 관리", "할 일 등록, 완료 처리, 반복 업무, 시간 알림, 검색/필터 기능을 제공합니다.")

    with st.expander("➕ 새 할 일 등록", expanded=True):
        with st.form("task_form", clear_on_submit=True):
            title = st.text_input("할 일 제목")
            detail = st.text_area("상세 내용", height=90)
            c1, c2, c3, c4 = st.columns(4)
            category = c1.selectbox("분류", ["개인", "업무", "식혜명가", "결혼준비", "기타"])
            priority = c2.selectbox("중요도", ["보통", "높음", "낮음"])
            due_date = c3.date_input("마감일", value=date.today())
            due_time = c4.time_input("알림/마감 시간", value=time(18, 0))

            c5, c6 = st.columns(2)
            repeat_type = c5.selectbox("반복", ["없음", "매일", "매주", "매월", "매년"])
            tags = c6.text_input("태그", placeholder="예: 택배,정산,청소")

            submitted = st.form_submit_button("할 일 등록", use_container_width=True)
            if submitted and title.strip():
                q(
                    """
                    INSERT INTO tasks
                    (title, detail, category, priority, due_date, due_time, status, repeat_type, tags, created_at, notified_at)
                    VALUES (?, ?, ?, ?, ?, ?, '대기', ?, ?, ?, NULL)
                    """,
                    (
                        title.strip(),
                        detail.strip(),
                        category,
                        priority,
                        due_date.isoformat(),
                        due_time.strftime("%H:%M"),
                        repeat_type,
                        tags.strip(),
                        now_str(),
                    ),
                )
                st.success("등록했습니다.")
                st.rerun()

    st.divider()

    tasks = df("SELECT * FROM tasks ORDER BY due_date ASC, due_time ASC, created_at DESC")

    f1, f2, f3, f4 = st.columns([1.4, 1, 1, 1])
    keyword = f1.text_input("검색", placeholder="제목, 내용, 태그 검색")
    status_filter = f2.selectbox("상태", ["전체", "대기", "진행", "보류", "완료"])
    category_filter = f3.selectbox("분류", ["전체", "개인", "업무", "식혜명가", "결혼준비", "기타"])
    priority_filter = f4.selectbox("중요도", ["전체", "높음", "보통", "낮음"])

    c_opt1, c_opt2 = st.columns(2)
    show_overdue_only = c_opt1.checkbox("기한 지난 할 일만 보기")
    show_notified = c_opt2.checkbox("이미 알림 울린 항목 포함", value=True)

    if not tasks.empty:
        if keyword:
            mask = (
                tasks["title"].str.contains(keyword, case=False, na=False)
                | tasks["detail"].str.contains(keyword, case=False, na=False)
                | tasks["tags"].str.contains(keyword, case=False, na=False)
            )
            tasks = tasks[mask]
        if status_filter != "전체":
            tasks = tasks[tasks["status"] == status_filter]
        if category_filter != "전체":
            tasks = tasks[tasks["category"] == category_filter]
        if priority_filter != "전체":
            tasks = tasks[tasks["priority"] == priority_filter]
        if show_overdue_only:
            tasks = tasks[
                tasks.apply(lambda r: is_overdue(r["due_date"], r["due_time"], r["status"]), axis=1)
            ]
        if not show_notified:
            tasks = tasks[tasks["notified_at"].isna()]

    st.caption(f"총 {len(tasks)}개")

    if tasks.empty:
        st.info("표시할 할 일이 없습니다.")
    else:
        for _, row in tasks.iterrows():
            overdue = is_overdue(row["due_date"], row["due_time"], row["status"])
            title_prefix = "🚨 " if overdue else ""
            notified = " · 🔔알림완료" if pd.notna(row["notified_at"]) and row["notified_at"] else ""
            with st.expander(f"{title_prefix}{row['title']}  ·  {status_badge(row['status'])}  ·  {priority_badge(row['priority'])}{notified}"):
                meta = f"분류: `{row['category']}`  |  알림/마감: `{row['due_date'] or '-'} {row['due_time'] or ''}`  |  반복: `{row['repeat_type']}`"
                st.markdown(meta)
                if overdue:
                    st.markdown('<span class="danger">기한이 지났습니다.</span>', unsafe_allow_html=True)
                if row["notified_at"]:
                    st.caption(f"알림 울림: {row['notified_at']}")
                if row["detail"]:
                    st.write(row["detail"])
                if row["tags"]:
                    st.markdown(render_tags(row["tags"]), unsafe_allow_html=True)

                c1, c2, c3, c4, c5 = st.columns(5)

                if row["status"] != "완료":
                    if c1.button("✅ 완료", key=f"done_{row['id']}", use_container_width=True):
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
                                    row["title"],
                                    row["detail"],
                                    row["category"],
                                    row["priority"],
                                    next_d.isoformat(),
                                    row["due_time"],
                                    row["repeat_type"],
                                    row["tags"],
                                    now_str(),
                                ),
                            )
                        st.rerun()
                else:
                    if c1.button("↩️ 미완료", key=f"undo_{row['id']}", use_container_width=True):
                        q("UPDATE tasks SET status='대기', completed_at=NULL WHERE id=?", (row["id"],))
                        st.rerun()

                new_status = c2.selectbox(
                    "상태 변경",
                    ["대기", "진행", "보류", "완료"],
                    index=["대기", "진행", "보류", "완료"].index(row["status"]),
                    key=f"status_{row['id']}",
                    label_visibility="collapsed",
                )
                if c2.button("상태 저장", key=f"save_status_{row['id']}", use_container_width=True):
                    completed_at = now_str() if new_status == "완료" else None
                    q("UPDATE tasks SET status=?, completed_at=? WHERE id=?", (new_status, completed_at, row["id"]))
                    st.rerun()

                if c3.button("🔔 다시 알림", key=f"reset_task_alarm_{row['id']}", use_container_width=True):
                    q("UPDATE tasks SET notified_at=NULL WHERE id=?", (row["id"],))
                    st.rerun()

                if c4.button("복제", key=f"copy_task_{row['id']}", use_container_width=True):
                    q(
                        """
                        INSERT INTO tasks
                        (title, detail, category, priority, due_date, due_time, status, repeat_type, tags, created_at, notified_at)
                        VALUES (?, ?, ?, ?, ?, ?, '대기', ?, ?, ?, NULL)
                        """,
                        (
                            row["title"] + " 복사본",
                            row["detail"],
                            row["category"],
                            row["priority"],
                            row["due_date"],
                            row["due_time"],
                            row["repeat_type"],
                            row["tags"],
                            now_str(),
                        ),
                    )
                    st.rerun()

                if c5.button("🗑️ 삭제", key=f"del_task_{row['id']}", use_container_width=True):
                    q("DELETE FROM tasks WHERE id=?", (row["id"],))
                    st.rerun()


# =========================
# 일정
# =========================
elif menu == "일정":
    section_title("일정 관리", "날짜별 일정 등록, 시간 알림, 월별 보기, 다가오는 일정 확인 기능을 제공합니다.")

    with st.expander("➕ 새 일정 등록", expanded=True):
        with st.form("schedule_form", clear_on_submit=True):
            title = st.text_input("일정명")
            detail = st.text_area("상세 내용", height=90)

            c1, c2, c3, c4 = st.columns(4)
            category = c1.selectbox("분류", ["개인", "업무", "식혜명가", "결혼준비", "기타"], key="sch_cat")
            schedule_date = c2.date_input("날짜", value=date.today(), key="sch_date")
            start_time = c3.time_input("시작 시간", value=time(9, 0), key="sch_start")
            end_time = c4.time_input("종료 시간", value=time(10, 0), key="sch_end")

            c5, c6 = st.columns(2)
            location = c5.text_input("장소")
            alarm_minutes = c6.selectbox(
                "알림",
                [0, 5, 10, 30, 60, 120, 1440],
                format_func=lambda x: "시작 시간에 알림" if x == 0 else f"{x}분 전 알림",
            )

            submitted = st.form_submit_button("일정 등록", use_container_width=True)
            if submitted and title.strip():
                q(
                    """
                    INSERT INTO schedules
                    (title, detail, category, schedule_date, start_time, end_time, location, alarm_minutes, created_at, notified_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        title.strip(),
                        detail.strip(),
                        category,
                        schedule_date.isoformat(),
                        start_time.strftime("%H:%M"),
                        end_time.strftime("%H:%M"),
                        location.strip(),
                        int(alarm_minutes),
                        now_str(),
                    ),
                )
                st.success("등록했습니다.")
                st.rerun()

    schedules = df("SELECT * FROM schedules ORDER BY schedule_date ASC, start_time ASC")

    st.divider()

    view_tab, list_tab = st.tabs(["월별 보기", "일정 목록"])

    with view_tab:
        c1, c2 = st.columns(2)
        year = c1.number_input("연도", min_value=2000, max_value=2100, value=date.today().year)
        month = c2.number_input("월", min_value=1, max_value=12, value=date.today().month)

        if schedules.empty:
            st.info("등록된 일정이 없습니다.")
        else:
            month_str = f"{int(year):04d}-{int(month):02d}"
            month_schedules = schedules[schedules["schedule_date"].str.startswith(month_str)]

            if month_schedules.empty:
                st.info("해당 월 일정이 없습니다.")
            else:
                summary = (
                    month_schedules.groupby("schedule_date")["title"]
                    .apply(lambda x: " / ".join(list(x)[:3]) + (" ..." if len(x) > 3 else ""))
                    .reset_index()
                )
                summary.columns = ["날짜", "일정"]
                st.dataframe(summary, use_container_width=True, hide_index=True)

    with list_tab:
        c1, c2, c3 = st.columns([1.4, 1, 1])
        keyword = c1.text_input("검색", placeholder="일정명, 내용, 장소 검색", key="sch_search")
        category_filter = c2.selectbox("분류", ["전체", "개인", "업무", "식혜명가", "결혼준비", "기타"], key="sch_filter_cat")
        only_upcoming = c3.checkbox("오늘 이후만 보기", value=True)

        filtered = schedules.copy()
        if not filtered.empty:
            if keyword:
                filtered = filtered[
                    filtered["title"].str.contains(keyword, case=False, na=False)
                    | filtered["detail"].str.contains(keyword, case=False, na=False)
                    | filtered["location"].str.contains(keyword, case=False, na=False)
                ]
            if category_filter != "전체":
                filtered = filtered[filtered["category"] == category_filter]
            if only_upcoming:
                filtered = filtered[filtered["schedule_date"] >= today_str()]

        st.caption(f"총 {len(filtered)}개")

        if filtered.empty:
            st.info("표시할 일정이 없습니다.")
        else:
            for _, row in filtered.iterrows():
                alarm_txt = "시작 시간" if not row["alarm_minutes"] else f"{int(row['alarm_minutes'])}분 전"
                notified = " · 🔔알림완료" if pd.notna(row["notified_at"]) and row["notified_at"] else ""
                with st.expander(f"{row['schedule_date']} {row['start_time'] or ''} · {row['title']} · 알림 {alarm_txt}{notified}"):
                    st.markdown(f"분류: `{row['category']}`  |  시간: `{row['start_time'] or '-'} ~ {row['end_time'] or '-'}`")
                    if row["location"]:
                        st.write(f"장소: {row['location']}")
                    st.write(f"알림: {alarm_txt}")
                    if row["notified_at"]:
                        st.caption(f"알림 울림: {row['notified_at']}")
                    if row["detail"]:
                        st.write(row["detail"])

                    c1, c2, c3 = st.columns(3)
                    if c1.button("🔔 다시 알림", key=f"reset_schedule_alarm_{row['id']}", use_container_width=True):
                        q("UPDATE schedules SET notified_at=NULL WHERE id=?", (row["id"],))
                        st.rerun()

                    if c2.button("복제", key=f"copy_schedule_{row['id']}", use_container_width=True):
                        q(
                            """
                            INSERT INTO schedules
                            (title, detail, category, schedule_date, start_time, end_time, location, alarm_minutes, created_at, notified_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                            """,
                            (
                                row["title"] + " 복사본",
                                row["detail"],
                                row["category"],
                                row["schedule_date"],
                                row["start_time"],
                                row["end_time"],
                                row["location"],
                                row["alarm_minutes"],
                                now_str(),
                            ),
                        )
                        st.rerun()

                    if c3.button("🗑️ 삭제", key=f"del_schedule_{row['id']}", use_container_width=True):
                        q("DELETE FROM schedules WHERE id=?", (row["id"],))
                        st.rerun()


# =========================
# 메모장
# =========================
elif menu == "메모장":
    section_title("메모장", "아이디어, 기록, 체크 내용을 빠르게 저장하고 검색합니다.")

    with st.expander("➕ 새 메모 등록", expanded=True):
        with st.form("memo_form", clear_on_submit=True):
            title = st.text_input("제목")
            content = st.text_area("내용", height=180)
            c1, c2 = st.columns([2, 1])
            tags = c1.text_input("태그", placeholder="예: 아이디어,구매,업무")
            pinned = c2.checkbox("상단 고정")
            submitted = st.form_submit_button("메모 등록", use_container_width=True)
            if submitted and title.strip():
                q(
                    """
                    INSERT INTO memos
                    (title, content, tags, pinned, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (title.strip(), content.strip(), tags.strip(), 1 if pinned else 0, now_str(), now_str()),
                )
                st.success("등록했습니다.")
                st.rerun()

    st.divider()

    memos = df("SELECT * FROM memos ORDER BY pinned DESC, updated_at DESC")
    c1, c2 = st.columns([2, 1])
    keyword = c1.text_input("검색", placeholder="제목, 내용, 태그 검색")
    pinned_only = c2.checkbox("고정 메모만 보기")

    if not memos.empty:
        if keyword:
            memos = memos[
                memos["title"].str.contains(keyword, case=False, na=False)
                | memos["content"].str.contains(keyword, case=False, na=False)
                | memos["tags"].str.contains(keyword, case=False, na=False)
            ]
        if pinned_only:
            memos = memos[memos["pinned"] == 1]

    st.caption(f"총 {len(memos)}개")

    if memos.empty:
        st.info("표시할 메모가 없습니다.")
    else:
        for _, row in memos.iterrows():
            pin = "📌 " if row["pinned"] else ""
            with st.expander(f"{pin}{row['title']} · 수정 {row['updated_at']}"):
                if row["tags"]:
                    st.markdown(render_tags(row["tags"]), unsafe_allow_html=True)
                st.write(row["content"] if row["content"] else "내용 없음")

                with st.form(f"edit_memo_{row['id']}"):
                    new_title = st.text_input("제목 수정", value=row["title"])
                    new_content = st.text_area("내용 수정", value=row["content"], height=160)
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
                            (
                                new_title.strip(),
                                new_content.strip(),
                                new_tags.strip(),
                                1 if new_pinned else 0,
                                now_str(),
                                row["id"],
                            ),
                        )
                        st.success("수정했습니다.")
                        st.rerun()

                if st.button("🗑️ 메모 삭제", key=f"del_memo_{row['id']}", use_container_width=True):
                    q("DELETE FROM memos WHERE id=?", (row["id"],))
                    st.rerun()


# =========================
# 백업/설정
# =========================
elif menu == "백업/설정":
    section_title("백업/설정", "엑셀 백업, DB 백업, 데이터 초기화를 관리합니다.")

    st.subheader("알림 안내")
    st.info(
        "알림은 앱 화면이 켜져 있을 때만 작동합니다. "
        "사이드바에서 '알림 자동 확인'을 켜두면 설정한 주기마다 시간을 확인하고, "
        "해당 시간이 되면 화면 알림과 소리 알림이 울립니다. "
        "소리가 안 나면 브라우저에서 페이지를 한 번 클릭한 뒤 알림 테스트를 눌러보세요."
    )

    st.divider()

    st.subheader("백업")
    c1, c2 = st.columns(2)

    with c1:
        st.download_button(
            "📊 엑셀로 내보내기",
            data=download_excel(),
            file_name=f"일상관리_백업_{today_str()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with c2:
        st.download_button(
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

    st.subheader("데이터 초기화")
    st.warning("초기화하면 복구가 어렵습니다. 먼저 백업을 다운로드하세요.")

    target = st.selectbox("초기화 대상", ["선택 안 함", "완료된 할 일만 삭제", "할 일 전체", "일정 전체", "메모 전체", "전체 데이터"])
    confirm = st.text_input("초기화하려면 아래 칸에 삭제 라고 입력")

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

    st.subheader("실행 도움말")
    st.code("pip install streamlit pandas openpyxl\nstreamlit run daily_manager_app.py", language="bash")

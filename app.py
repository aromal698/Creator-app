"""CampusConnect student app. Campus content is read-only here; creator tools live in creator_app.py."""

from datetime import date, datetime, timedelta, timezone
from html import escape
import os
import re
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client


DEPARTMENTS = ["CSE", "IT", "ECE", "EEE", "Mechanical", "Civil", "Chemical", "Biotechnology", "Other"]
SEMESTERS = list(range(1, 9))
NAV_PAGES = ["Home", "Study Groups", "Group Chat", "Campus Calendar", "Campus Activities", "Notices", "AI Study Buddy", "AI Search", "WhatsApp", "Feedback"]
try:
    INDIA_TZ = ZoneInfo("Asia/Kolkata")
except ZoneInfoNotFoundError:
    INDIA_TZ = timezone(timedelta(hours=5, minutes=30))

st.set_page_config(page_title="CampusConnect | B.Tech community", page_icon="🎓", layout="wide")


def secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.getenv(name, default)


def clear_login():
    for key in ("supabase_access_token", "supabase_refresh_token", "campus_user_id", "display_name"):
        st.session_state.pop(key, None)


def save_auth_response(response, default_name=""):
    session = getattr(response, "session", None)
    user = getattr(response, "user", None)
    if not session or not user:
        return False
    st.session_state.supabase_access_token = session.access_token
    st.session_state.supabase_refresh_token = session.refresh_token
    st.session_state.campus_user_id = str(user.id)
    metadata = getattr(user, "user_metadata", {}) or {}
    st.session_state.display_name = metadata.get("display_name") or default_name or "Student"
    return True


def get_authenticated_client():
    url = secret("SUPABASE_URL")
    public_key = secret("SUPABASE_ANON_KEY") or secret("SUPABASE_PUBLISHABLE_KEY")
    if not url or not public_key:
        return None, None, "Add SUPABASE_URL and SUPABASE_ANON_KEY to this app's Streamlit Secrets."
    client = create_client(url, public_key)
    access = st.session_state.get("supabase_access_token")
    refresh = st.session_state.get("supabase_refresh_token")
    if not access or not refresh:
        return client, None, None
    try:
        client.auth.set_session(access, refresh)
        user_response = client.auth.get_user()
        user = user_response.user
        refreshed = client.auth.get_session()
        if refreshed:
            st.session_state.supabase_access_token = refreshed.access_token
            st.session_state.supabase_refresh_token = refreshed.refresh_token
        st.session_state.campus_user_id = str(user.id)
        return client, user, None
    except Exception:
        clear_login()
        return client, None, "Your session expired. Please sign in again."


def sign_in_callback(email, password):
    url = secret("SUPABASE_URL")
    public_key = secret("SUPABASE_ANON_KEY") or secret("SUPABASE_PUBLISHABLE_KEY")
    try:
        client = create_client(url, public_key)
        response = client.auth.sign_in_with_password({"email": email.strip(), "password": password})
        if save_auth_response(response):
            st.session_state.nav_page = "Home"
            st.session_state.auth_notice = "Signed in successfully."
        else:
            st.session_state.auth_notice = "Sign-in did not return a session. Check your email confirmation settings."
    except Exception:
        st.session_state.auth_notice = "Sign-in failed. Check the email and password, then try again."


def signup_callback(name, email, password):
    url = secret("SUPABASE_URL")
    public_key = secret("SUPABASE_ANON_KEY") or secret("SUPABASE_PUBLISHABLE_KEY")
    try:
        client = create_client(url, public_key)
        response = client.auth.sign_up(
            {"email": email.strip(), "password": password, "options": {"data": {"display_name": name.strip()}}}
        )
        if save_auth_response(response, name.strip()):
            st.session_state.nav_page = "Home"
            st.session_state.auth_notice = "Account created. You are signed in."
        else:
            st.session_state.auth_notice = "Account created. Check your email to confirm it, then sign in."
    except Exception:
        st.session_state.auth_notice = "Account could not be created. Check the email, password, and Supabase Auth settings."


def sign_out_callback():
    clear_login()
    st.session_state.pop("active_group_id", None)
    st.session_state.nav_page = "Home"


def go_home():
    st.session_state.nav_page = "Home"


def toggle_theme():
    st.session_state.dark_theme = not st.session_state.get("dark_theme", False)


def go_to_chat(group_id):
    st.session_state.active_group_id = group_id
    st.session_state.nav_page = "Group Chat"


def join_group_callback(group_id):
    client, user, error = get_authenticated_client()
    if client and user and not error:
        try:
            client.table("group_members").insert(
                {"group_id": group_id, "user_id": str(user.id), "display_name": st.session_state.get("display_name", "Student")}
            ).execute()
        except Exception:
            # A duplicate membership means the student already joined.
            pass
        go_to_chat(group_id)


def groq_completion(messages, use_browser_search=False):
    """Call Groq's free-tier API; web search is enabled only for AI Search."""
    api_key = str(secret("GROQ_API_KEY", "")).strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing from this app's Streamlit Secrets.")

    payload = {
        "model": secret("GROQ_MODEL", "openai/gpt-oss-20b"),
        "messages": messages,
        "max_completion_tokens": 1400,
        "reasoning_effort": "low",
    }
    if use_browser_search:
        payload["tools"] = [{"type": "browser_search"}]
        payload["tool_choice"] = "required"

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    try:
        result = response.json()
    except ValueError:
        result = {}
    if not response.ok:
        error = result.get("error", {}) if isinstance(result, dict) else {}
        message = error.get("message", response.text[:400]) if isinstance(error, dict) else str(error)
        raise RuntimeError(f"Groq API returned HTTP {response.status_code}: {message}")

    message = result["choices"][0]["message"]
    answer = message.get("content") or "I couldn't create an answer. Try a more specific question."
    sources = []
    for tool in message.get("executed_tools") or []:
        search_results = tool.get("search_results") or {}
        rows = search_results.get("results", []) if isinstance(search_results, dict) else search_results
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and row.get("url"):
                    sources.append({"title": row.get("title") or "Web source", "url": row["url"]})
    unique_sources = {source["url"]: source for source in sources}
    return answer, list(unique_sources.values())


def render_ai_markdown(answer):
    """Render common LaTeX math returned by AI as readable Streamlit math."""
    text = str(answer or "")
    # Streamlit understands math enclosed in $...$ or $$...$$. Many models
    # instead return the equivalent LaTeX delimiters used in other viewers.
    text = text.replace(r"\[", "\n$$\n").replace(r"\]", "\n$$\n")
    text = text.replace(r"\(", "$").replace(r"\)", "$")

    rendered_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # Repair bare display equations such as: [ p + \frac{1}{2}\rho v^{2} = ... ]
        if (
            stripped
            and not stripped.startswith(("$", "- ", "* ", ">", "```"))
            and "=" in stripped
            and re.search(r"\\(?:frac|rho|theta|pi|sqrt|sum|int|text|cdot|times|Delta|alpha|beta)", stripped)
        ):
            equation = stripped
            if equation.startswith("[") and equation.endswith("]"):
                equation = equation[1:-1].strip()
            line = f"$${equation}$$"
            line = f"$$\n{equation}\n$$"
        else:
            # Make standalone raw math commands in explanatory sentences readable too.
            line = line.replace(r"\rho", "ρ").replace(r"\theta", "θ").replace(r"\pi", "π")
            line = line.replace(r"\times", "×").replace(r"\cdot", "·")
        rendered_lines.append(line)
    st.markdown("\n".join(rendered_lines))
    text = "\n".join(rendered_lines)

    # Render display equations with Streamlit's dedicated LaTeX renderer.
    # st.markdown can leave literal $$...$$ visible for some response formats.
    parts = re.split(r"(\$\$.*?\$\$)", text, flags=re.DOTALL)
    for part in parts:
        if not part:
            continue
        if part.startswith("$$") and part.endswith("$$"):
            equation = part[2:-2].strip()
            if equation:
                st.latex(equation)
        else:
            st.markdown(part)


def show_post(post):
    with st.container(border=True):
        flags = []
        if post.get("is_important"):
            flags.append("📌 Important")
        if post.get("is_special"):
            flags.append("✨ Special day")
        st.caption(" · ".join([post["kind"], str(post["event_date"]), post["audience"], *flags]))
        st.subheader(post["title"])
        st.write(post["body"])
        st.caption(f"Posted by {post['created_by_name']}")


def google_calendar_event_url(post):
    event_day = date.fromisoformat(str(post["event_date"])[:10])
    details = f"{post.get('body', '')}\nAudience: {post.get('audience', 'All departments')}"
    query = urlencode({"action": "TEMPLATE", "text": post["title"], "dates": f"{event_day:%Y%m%d}/{(event_day + timedelta(days=1)):%Y%m%d}", "details": details})
    return f"https://calendar.google.com/calendar/render?{query}"


def groq_browser_search(question):
    """Answer a question using Groq's GPT-OSS model and built-in browser search."""
    return groq_completion(
        [
            {
                "role": "system",
                "content": (
                    "You are CampusConnect's research helper. Use the browser search tool, answer clearly, "
                    "cite sources in your response, note uncertainty, and never claim certainty beyond sources. "
                    "For equations, use standard LaTeX wrapped in $...$ for inline math or $$...$$ for a display equation. "
                    "Never show raw LaTeX commands such as \\frac or \\rho without math delimiters. "
                    "After each important equation, explain in plain words what it means and define every symbol."
                ),
            },
            {"role": "user", "content": question},
        ],
        use_browser_search=True,
    )


@st.fragment(run_every=8)
def render_group_chat_messages(database, group_id, user_id, display_name):
    try:
        rows = database.table("group_messages").select("*").eq("group_id", group_id).order("created_at", desc=True).limit(100).execute().data or []
        if not rows:
            st.caption("No messages yet. Say hello to your group!")
        for item in reversed(rows):
            mine = item["sender_id"] == user_id
            bubble_class = "chat-own" if mine else "chat-other"
            who = "You" if mine else escape(str(item["display_name"]))
            when = escape(str(item["created_at"])[:16].replace("T", " "))
            text = escape(str(item["message"]))
            st.markdown(f"<div class='chat-bubble {bubble_class}'><div class='chat-meta'>{who} · {when}</div>{text}</div>", unsafe_allow_html=True)
    except Exception:
        st.error("Chat messages could not be loaded. Check the group membership policies.")
    message = st.chat_input("Message your group…", max_chars=2000, key=f"chat_message_{group_id}")
    if message:
        try:
            database.table("group_messages").insert(
                {"group_id": group_id, "sender_id": user_id, "display_name": display_name, "message": message.strip()}
            ).execute()
            st.rerun()
        except Exception:
            st.error("Message could not be sent. Confirm that you are a member of this group.")


def apply_theme():
    dark_css = """
    .stApp { background:#101a16 !important; color:#e7eee9; }
    [data-testid="stSidebar"] { background:#17251f !important; }
    h1,h2,h3,p,label,[data-testid="stMarkdownContainer"] { color:#e7eee9; }
    .hero,.date-card { background:#20392d; border-color:#315542; color:#e7eee9; }
    .hero h2,.hero p { color:#e7eee9; }
    [data-testid="stMetric"] { background:#1b2b23; border-color:#315542; }
    .chat-other { background:#26342c; color:#e7eee9; }
    """ if st.session_state.get("dark_theme") else ""
    st.markdown(
        """<style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
        html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
        h1,h2,h3 { font-family:'Manrope',sans-serif; letter-spacing:-.03em; color:#173d32; }
        .eyebrow { color:#176b5b; font-size:.72rem; font-weight:700; letter-spacing:.16em; margin-bottom:.45rem; }
        .hero { padding:1.8rem 2rem; border-radius:22px; background:linear-gradient(120deg,#e3f1e8,#f2f6ee 70%,#e8f2ed); border:1px solid #d2e3d8; }
        .hero h2 { margin:0 0 .5rem; color:#153b33; font-size:2rem; }
        .hero p { color:#334e47; margin:0; line-height:1.65; max-width:760px; }
        .date-card { background:#edf5ef; border-left:5px solid #176b5b; padding:1rem 1.25rem; border-radius:12px; }
        [data-testid="stSidebar"] { background:#edf3ef; }
        div.stButton > button { border-radius:12px; border-color:#176b5b; color:#14584c; font-weight:600; }
        div.stButton > button:hover { background:#e5f2ec; border-color:#14584c; color:#103f36; }
        div.stButton > button:focus-visible { outline:3px solid #176b5b; outline-offset:2px; }
        [data-testid="stMetric"] { background:#fff; border:1px solid #dbe5df; padding:1rem; border-radius:16px; }
        .chat-bubble { max-width:78%; padding:.7rem .95rem; border-radius:16px; margin:.45rem 0; white-space:pre-wrap; overflow-wrap:anywhere; box-shadow:0 1px 2px #0001; }
        .chat-own { margin-left:auto; background:#d9fdd3; border-bottom-right-radius:4px; color:#15251b; }
        .chat-other { margin-right:auto; background:#fff; border-bottom-left-radius:4px; color:#15251b; }
        .chat-meta { font-size:.72rem; opacity:.7; margin-bottom:.25rem; }
        .st-key-theme_bulb { position:fixed; z-index:9999; top:0; right:1.5rem; padding-top:20px; }
        .st-key-theme_bulb:before { content:''; position:absolute; top:0; left:50%; height:19px; border-left:2px solid #ae8d50; }
        .st-key-theme_bulb button { border-radius:0 0 22px 22px; min-width:54px; min-height:46px; font-size:1.45rem; background:#fff7d9; border:1px solid #d6b66a; box-shadow:0 3px 12px #0002; }
        """ + dark_css + "</style>",
        unsafe_allow_html=True,
    )


def show_login():
    st.markdown("<div class='eyebrow'>STUDENT SIGN IN</div>", unsafe_allow_html=True)
    st.title("Welcome to CampusConnect")
    st.write("Sign in or create a student account to join groups and chat. Use your college email if your campus requires it.")
    if st.session_state.get("auth_notice"):
        st.info(st.session_state.pop("auth_notice"))
    if not secret("SUPABASE_URL") or not (secret("SUPABASE_ANON_KEY") or secret("SUPABASE_PUBLISHABLE_KEY")):
        st.error("Student sign-in is not configured yet. Add the Supabase URL and publishable/anon key in Streamlit Secrets after setting up the database.")
        return
    sign_tab, create_tab = st.tabs(["Sign in", "Create account"])
    with sign_tab:
        with st.form("sign_in_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary")
        if submitted:
            sign_in_callback(email, password)
            st.rerun()
    with create_tab:
        with st.form("create_account_form"):
            name = st.text_input("Display name")
            email = st.text_input("College email")
            password = st.text_input("Create password", type="password", help="Use at least 8 characters.")
            submitted = st.form_submit_button("Create account", type="primary")
        if submitted:
            if not name.strip() or len(password) < 8:
                st.warning("Enter a display name and a password of at least 8 characters.")
            else:
                signup_callback(name, email, password)
                st.rerun()


apply_theme()
client, auth_user, auth_error = get_authenticated_client()
if not client or not auth_user:
    if auth_error:
        st.warning(auth_error)
    show_login()
    st.stop()

st.session_state.setdefault("display_name", (getattr(auth_user, "user_metadata", {}) or {}).get("display_name", "Student"))
st.session_state.setdefault("active_group_id", None)
today = datetime.now(INDIA_TZ).date()
today_iso = today.isoformat()

with st.sidebar:
    st.markdown("# 🎓 CampusConnect")
    st.caption("One campus. Every department.")
    display_name = st.text_input("Display name", key="display_name")
    department = st.selectbox("Department", DEPARTMENTS, key="profile_department")
    semester = st.selectbox("Semester", SEMESTERS, key="profile_semester")
    st.caption("Notices and activities are published by campus creators.")
    st.divider()
    page = st.radio(
        "Navigate",
        NAV_PAGES,
        key="nav_page",
        label_visibility="collapsed",
    )
    st.caption(auth_user.email or "Signed-in student")
    st.button("Sign out", on_click=sign_out_callback)

heading, bulb = st.columns([12, 1])
with heading:
    st.markdown("<div class='eyebrow'>B.TECH STUDENT COMMUNITY</div>", unsafe_allow_html=True)
    st.title(page)
with bulb:
    st.button("💡", key="theme_bulb", on_click=toggle_theme, help="Toggle light and dark theme")
if page != "Home":
    st.button("← Back to home", on_click=go_home)

uid = str(auth_user.id)
name = display_name.strip() or "Student"

if page == "Home":
    st.markdown(
        "<div class='hero'><h2>Good ideas grow across departments.</h2><p>Join a semester group, chat with classmates, and keep up with today's campus activities and important notices.</p></div>",
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        f"<div class='date-card'><b>Today · {today.strftime('%A, %d %B %Y')}</b><br>Today's special day is highlighted below when a campus creator posts one.</div>",
        unsafe_allow_html=True,
    )
    try:
        all_posts = client.table("campus_posts").select("*").eq("status", "published").order("event_date").execute().data or []
        groups = client.table("campus_groups").select("id").eq("is_active", True).execute().data or []
        mine = client.table("group_members").select("group_id").eq("user_id", uid).execute().data or []
        today_activities = [p for p in all_posts if p["kind"] == "Activity" and str(p["event_date"]) == today_iso]
        specials = [p for p in today_activities if p.get("is_special")]
        notices = [p for p in all_posts if p["kind"] == "Notice"]
        important = [p for p in notices if p.get("is_important")]
        m1, m2, m3 = st.columns(3)
        m1.metric("Study groups", len(groups))
        m2.metric("Groups you joined", len(mine))
        m3.metric("Activities today", len(today_activities))
        left, right = st.columns([1.1, 0.9])
        with left:
            st.subheader("📅 Today's campus activities")
            if today_activities:
                for post in today_activities:
                    show_post(post)
            else:
                st.info("No campus activities have been posted for today.")
            st.subheader("✨ Today's special day")
            if specials:
                for post in specials:
                    show_post(post)
            else:
                st.info("No special day has been highlighted today.")
        with right:
            st.subheader("📌 Important campus notices")
            if important:
                for post in sorted(important, key=lambda p: str(p["event_date"]), reverse=True)[:5]:
                    show_post(post)
            else:
                st.info("No important notices have been posted.")
            st.subheader("📰 Latest notices")
            if notices:
                for post in sorted(notices, key=lambda p: str(p["created_at"]), reverse=True)[:5]:
                    show_post(post)
            else:
                st.info("Published campus notices will appear here.")
            upcoming = [p for p in all_posts if p["kind"] == "Activity" and str(p["event_date"])[:10] >= today_iso]
            st.subheader("🗓️ Coming up on campus")
            if upcoming:
                for post in sorted(upcoming, key=lambda p: str(p["event_date"]))[:3]:
                    st.write(f"**{post['event_date']} · {post['title']}**")
            else:
                st.caption("No upcoming activities have been posted.")
            st.button("View campus calendar →", on_click=lambda: st.session_state.update(nav_page="Campus Calendar"))
    except Exception:
        st.error("Campus data could not be loaded. Check that the Supabase tables and student access policies are set up.")

elif page == "Study Groups":
    st.caption("Browse department and semester groups. Joining a group opens its chat.")
    browse_tab, mine_tab, create_tab = st.tabs(["Browse groups", "My groups", "Create a group"])
    try:
        groups = client.table("campus_groups").select("*").eq("is_active", True).order("department").order("semester").execute().data or []
        mine = client.table("group_members").select("group_id").eq("user_id", uid).execute().data or []
        joined_ids = {row["group_id"] for row in mine}
    except Exception:
        groups, joined_ids = [], set()
        st.error("Groups could not be loaded. Check Supabase setup and row access policies.")
    with browse_tab:
        f1, f2 = st.columns(2)
        dep_filter = f1.selectbox("Department", ["All departments", *DEPARTMENTS], key="groups_department_filter")
        sem_filter = f2.selectbox("Semester", ["All semesters", *SEMESTERS], key="groups_semester_filter")
        visible = [g for g in groups if (dep_filter == "All departments" or g["department"] == dep_filter) and (sem_filter == "All semesters" or g.get("semester") == sem_filter)]
        for group in visible:
            with st.container(border=True):
                info, action = st.columns([4, 1.2])
                with info:
                    st.subheader(group["name"])
                    st.write(group.get("description") or "Student study and discussion group.")
                    st.caption(f"{group['department']} · {('Semester ' + str(group['semester'])) if group.get('semester') else 'All semesters'}")
                with action:
                    if group["id"] in joined_ids:
                        st.button("Open chat", key=f"group_open_{group['id']}", type="primary", on_click=go_to_chat, args=(group["id"],))
                    else:
                        st.button("Join group", key=f"group_join_{group['id']}", disabled=not display_name.strip(), on_click=join_group_callback, args=(group["id"],))
    with mine_tab:
        mine_groups = [g for g in groups if g["id"] in joined_ids]
        if not mine_groups:
            st.info("You haven't joined a group yet. Browse groups to find your department and semester.")
        for group in mine_groups:
            with st.container(border=True):
                st.subheader(group["name"])
                st.write(group.get("description") or "Student study and discussion group.")
                st.button("Open group chat", key=f"mine_open_{group['id']}", type="primary", on_click=go_to_chat, args=(group["id"],))
    with create_tab:
        with st.form("new_group_form", clear_on_submit=True):
            group_name = st.text_input("Group name", placeholder="e.g. Robotics project team")
            group_description = st.text_area("Group purpose", placeholder="Subjects, project goals, or study plan")
            c1, c2 = st.columns(2)
            group_department = c1.selectbox("Department", ["Cross-department", *DEPARTMENTS])
            group_semester = c2.selectbox("Semester", ["Any semester", *SEMESTERS])
            create_group = st.form_submit_button("Create group and join", type="primary")
        if create_group:
            if not group_name.strip():
                st.warning("Enter a group name first.")
            else:
                try:
                    result = client.table("campus_groups").insert(
                        {
                            "name": group_name.strip(),
                            "department": group_department,
                            "semester": None if group_semester == "Any semester" else group_semester,
                            "description": group_description.strip(),
                            "created_by": uid,
                            "created_by_name": name,
                        }
                    ).select("id").execute().data
                    group_id = result[0]["id"]
                    client.table("group_members").insert({"group_id": group_id, "user_id": uid, "display_name": name}).execute()
                    st.session_state.active_group_id = group_id
                    st.session_state.nav_page = "Group Chat"
                    st.rerun()
                except Exception:
                    st.error("The group could not be created. Check the Supabase group policies and try again.")

elif page == "Group Chat":
    try:
        memberships = client.table("group_members").select("group_id").eq("user_id", uid).execute().data or []
        member_ids = {row["group_id"] for row in memberships}
        groups = client.table("campus_groups").select("*").in_("id", list(member_ids)).execute().data if member_ids else []
    except Exception:
        groups = []
        st.error("Your joined groups could not be loaded.")
    if not groups:
        st.info("Join a study group to open its chat.")
        st.button("← Back to study groups", on_click=lambda: st.session_state.update(nav_page="Study Groups"))
    else:
        by_id = {g["id"]: g for g in groups}
        ids = list(by_id)
        active = st.session_state.get("active_group_id")
        idx = ids.index(active) if active in ids else 0
        group_id = st.selectbox("Choose a group chat", ids, index=idx, format_func=lambda value: by_id[value]["name"])
        st.caption("Only signed-in group members can read and send messages. This chat refreshes about every 8 seconds while open.")
        render_group_chat_messages(client, group_id, uid, name)

elif page in ("Campus Activities", "Notices"):
    kind = "Activity" if page == "Campus Activities" else "Notice"
    st.caption("Only creator-approved, published campus updates appear here.")
    try:
        records = client.table("campus_posts").select("*").eq("status", "published").eq("kind", kind).order("event_date").execute().data or []
        if not records:
            st.info(f"No published {kind.lower()}s yet.")
        for post in records:
            show_post(post)
    except Exception:
        st.error("Campus updates could not be loaded. Please try again later.")

elif page == "Campus Calendar":
    st.caption(f"Campus dates · {datetime.now(INDIA_TZ).strftime('%A, %d %B %Y · %I:%M %p')} IST")
    st.write("Creator-published events appear below. Google Calendar can show the public campus calendar and special dates configured by your campus.")
    selected_day = st.date_input("Choose a day to see campus events", value=today, key="calendar_day")
    try:
        all_posts = client.table("campus_posts").select("*").eq("status", "published").order("event_date").execute().data or []
        selected_events = [p for p in all_posts if str(p["event_date"])[:10] == selected_day.isoformat()]
        if selected_events:
            for post in selected_events:
                show_post(post)
                st.link_button("＋ Add to Google Calendar", google_calendar_event_url(post))
        else:
            st.info("No creator-published campus events for this date.")
    except Exception:
        st.error("Campus calendar events could not be loaded. Check the Supabase connection.")

    embed_url = str(secret("GOOGLE_CALENDAR_EMBED_URL", "")).strip()
    if embed_url.startswith("https://calendar.google.com/calendar/embed"):
        st.subheader("Google Calendar")
        components.iframe(embed_url, height=650, scrolling=True)
        st.caption("Google Calendar is public in this view. Do not include private student or staff information in that calendar.")
    else:
        st.info("Optional: configure GOOGLE_CALENDAR_EMBED_URL in Streamlit Secrets to embed your public campus Google Calendar here.")

elif page == "AI Search":
    st.caption("Ask a question that needs current web information. Free-tier Groq AI searches the web and provides sources when available.")
    st.info("AI answers can still be wrong or out of date. Verify important academic, medical, legal, or safety information with an official source.")
    st.warning("Don't enter personal, sensitive, or confidential information. Free-tier requests are subject to usage limits.")
    with st.form("ai_search_form"):
        search_question = st.text_input("What do you want to find?", placeholder="e.g. Explain recent advances in battery recycling")
        search_submit = st.form_submit_button("🔎 Search with free AI", type="primary")
    if search_submit:
        if not search_question.strip():
            st.warning("Enter a question to search.")
        elif not secret("GROQ_API_KEY"):
            st.error("Free AI is not configured. Add GROQ_API_KEY to the student app's Streamlit Secrets.")
        else:
            with st.spinner("Searching the web and preparing an answer…"):
                try:
                    answer, sources = groq_browser_search(search_question.strip())
                    st.session_state.ai_search_result = {"question": search_question.strip(), "answer": answer, "sources": sources}
                except Exception as exc:
                    key = str(secret("GROQ_API_KEY", ""))
                    detail = str(exc).replace(key, "[hidden API key]") if key else str(exc)
                    st.error(f"AI Search failed ({type(exc).__name__}). Details: {detail[:500]}")
    result = st.session_state.get("ai_search_result")
    if result:
        st.markdown(f"**Your question:** {result['question']}")
        render_ai_markdown(result["answer"])
        if result["sources"]:
            st.markdown("**Sources**")
            for source in result["sources"]:
                st.markdown(f"- [{source['title']}]({source['url']})")
        else:
            st.caption("No separate source links were returned. Check citations in the answer and verify important details.")

elif page == "WhatsApp":
    st.write("Join the campus WhatsApp spaces for announcements and community discussion. These open in WhatsApp; the links are managed by campus creators.")
    community_url = str(secret("WHATSAPP_COMMUNITY_URL", "")).strip()
    channel_url = str(secret("WHATSAPP_CHANNEL_URL", "")).strip()
    left, right = st.columns(2)
    with left:
        if community_url.startswith("https://"):
            st.link_button("Open WhatsApp Community", community_url, type="primary", use_container_width=True)
        else:
            st.info("The campus creator has not added a WhatsApp Community link yet.")
    with right:
        if channel_url.startswith("https://"):
            st.link_button("Follow WhatsApp Channel", channel_url, use_container_width=True)
        else:
            st.info("The campus creator has not added a WhatsApp Channel link yet.")

elif page == "AI Study Buddy":
    st.caption("Ask for a concept explanation, study plan, or hints. Check important course details with your faculty.")
    st.warning("This AI uses a free plan with usage limits. Don't enter personal, sensitive, or confidential information.")
    chat = st.session_state.setdefault("study_chat", [])
    for message in chat:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    question = st.chat_input("Ask something you are learning…")
    if question:
        chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking through it…"):
                answer = ""
                try:
                    key = secret("GROQ_API_KEY")
                    if not key:
                        answer = "The free AI study buddy is not configured yet. Ask the app owner to add GROQ_API_KEY in Streamlit Secrets."
                    else:
                        messages = [
                            {
                                "role": "system",
                                "content": (
                                    "You are CampusConnect's friendly B.Tech study buddy. Explain step by step, "
                                    "give assignment hints rather than dishonest submissions, and say when uncertain. "
                                    "For equations, use standard LaTeX wrapped in $...$ for inline math or $$...$$ for a display equation. "
                                    "Never show raw LaTeX commands such as \\frac or \\rho without math delimiters. "
                                    "Then explain the equation in simple words, define each symbol with its unit when applicable, "
                                    "and show a small worked example when useful."
                                ),
                            }
                        ]
                        messages.extend(
                            {"role": item["role"], "content": item["content"]}
                            for item in chat[:-1][-8:]
                        )
                        messages.append({"role": "user", "content": question})
                        answer, _ = groq_completion(messages)
                except Exception as exc:
                    key = str(secret("GROQ_API_KEY", ""))
                    detail = str(exc).replace(key, "[hidden API key]") if key else str(exc)
                    answer = f"Free AI request failed ({type(exc).__name__}). Details: {detail[:500]}"
                render_ai_markdown(answer)
        chat.append({"role": "assistant", "content": answer})

elif page == "Feedback":
    st.caption("Help the student community improve CampusConnect.")
    with st.form("feedback_form", clear_on_submit=True):
        topic = st.selectbox("Feedback topic", ["App idea", "Bug or problem", "Study groups", "Campus notices", "Accessibility", "Other"])
        message = st.text_area("Your feedback", max_chars=2000)
        send = st.form_submit_button("Send feedback", type="primary")
    if send:
        if not message.strip():
            st.warning("Write a short message before sending.")
        else:
            try:
                client.table("student_feedback").insert(
                    {"user_id": uid, "display_name": name, "topic": topic, "message": message.strip()}
                ).execute()
                st.success("Thank you. Your feedback was sent to the campus creators.")
            except Exception:
                st.error("Feedback could not be sent. Please try again later.")

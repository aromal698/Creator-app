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
THEMES = [
    {"name": "White", "bg": "#f7faf8", "side": "#edf3ef", "surface": "#ffffff", "text": "#172b27", "muted": "#526861", "accent": "#176b5b", "soft": "#e3f1e8", "border": "#d2e3d8", "hero1": "#e3f1e8", "hero2": "#f2f6ee"},
    {"name": "Dark", "bg": "#101820", "side": "#17242d", "surface": "#1c2a34", "text": "#edf5f7", "muted": "#b3c4cb", "accent": "#59c3a5", "soft": "#203a3b", "border": "#35515a", "hero1": "#1b3a3b", "hero2": "#26384a"},
    {"name": "Blue", "bg": "#f2f7ff", "side": "#e7effc", "surface": "#ffffff", "text": "#172b49", "muted": "#526987", "accent": "#2563eb", "soft": "#dceaff", "border": "#c8d9f5", "hero1": "#dceaff", "hero2": "#f0f5ff"},
    {"name": "Purple", "bg": "#f8f5ff", "side": "#eee8fb", "surface": "#ffffff", "text": "#302347", "muted": "#706184", "accent": "#7650c8", "soft": "#eee5ff", "border": "#ddd0f5", "hero1": "#eee5ff", "hero2": "#f9f4ff"},
    {"name": "Amber", "bg": "#fffaf1", "side": "#f7eedc", "surface": "#ffffff", "text": "#3b2d17", "muted": "#786343", "accent": "#bb6b0a", "soft": "#ffefcf", "border": "#efdbb4", "hero1": "#ffefcf", "hero2": "#fff9ee"},
    {"name": "Rose", "bg": "#fff6f7", "side": "#f8e9ec", "surface": "#ffffff", "text": "#40252d", "muted": "#80616a", "accent": "#c13e68", "soft": "#ffe2e9", "border": "#f1cbd6", "hero1": "#ffe2e9", "hero2": "#fff5f7"},
    {"name": "Teal", "bg": "#f0fbfb", "side": "#e1f2f1", "surface": "#ffffff", "text": "#173537", "muted": "#537174", "accent": "#078080", "soft": "#d7f2ef", "border": "#c0e3df", "hero1": "#d7f2ef", "hero2": "#f1fbf7"},
]
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
    for key in (
        "supabase_access_token", "supabase_refresh_token", "campus_user_id", "display_name",
        "student_email", "student_profile_complete", "profile_department", "profile_semester",
    ):
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
    try:
        client = create_client(url, public_key)
    except Exception:
        return None, None, "CampusConnect could not initialize Supabase. Check that SUPABASE_URL is the project URL and the student key is the project's publishable/anon key."
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


def auth_setup_help(error):
    """Turn common Supabase auth failures into safe, actionable hints; never echo secrets."""
    message = str(error).lower()
    if any(term in message for term in ("invalid login credentials", "invalid credentials", "email or password is incorrect")):
        return "Email or password is incorrect. If this is your first visit, choose Create profile first. Otherwise, check that you are using the same email and password you registered with."
    if any(term in message for term in ("email not confirmed", "email_not_confirmed", "email is not confirmed")):
        return "This account is waiting for email confirmation. Turn off Authentication → Sign In / Providers → Email → Confirm email for new accounts. This already-created account may still need its existing confirmation email or help from the project owner before it can log in."
    if any(term in message for term in ("user already registered", "already been registered", "already registered")):
        return "An account already exists for this email. Choose Log in and use its existing password. If you never set a password, reset that account in Supabase Auth or use another email."
    if any(term in message for term in ("password should be at least", "password is too short", "weak_password")):
        return "Choose a longer password and try creating the profile again. CampusConnect asks for at least 8 characters."
    if any(term in message for term in ("invalid api key", "invalid api_key", "invalid jwt", "unauthorized", "401")):
        return (
            "Supabase rejected the student app key. In this Streamlit app's Secrets, check SUPABASE_URL "
            "and SUPABASE_ANON_KEY (or SUPABASE_PUBLISHABLE_KEY). Use the public/anon key, not the service-role key."
        )
    if any(term in message for term in ("connecterror", "connecttimeout", "readtimeout", "timed out", "network", "name or service not known")):
        return "CampusConnect could not connect to Supabase. Check your internet, project URL, and Supabase project status, then retry."
    if any(term in message for term in ("signups not allowed", "signup is disabled", "sign up is disabled", "user signups are disabled")):
        return "New student profiles are disabled. In Supabase, open Authentication → Sign In / Providers → Email and enable new user sign-ups."
    if any(term in message for term in ("rate limit", "email rate limit")):
        return "Supabase temporarily limited email requests. Wait a little before trying again."
    return (
        "Supabase returned an unexpected authentication error. Check this app's SUPABASE_URL and public/anon key, "
        "then open Supabase → Authentication logs to see the matching error. Never paste a service-role key into the student app."
    )


def student_signup_callback(name, email, password, department, semester):
    url = secret("SUPABASE_URL")
    public_key = secret("SUPABASE_ANON_KEY") or secret("SUPABASE_PUBLISHABLE_KEY")
    if not url or not public_key:
        st.session_state.auth_notice = "Student sign-in is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY to this app's Streamlit Secrets."
        return
    try:
        client = create_client(url, public_key)
        response = client.auth.sign_up({
            "email": email.strip(),
            "password": password,
            "options": {"data": {
                "display_name": name.strip(),
                "college_email": email.strip(),
                "department": department,
                "semester": semester,
            }},
        })
        if save_auth_response(response):
            st.session_state.student_email = email.strip()
            st.session_state.profile_department = department
            st.session_state.profile_semester = semester
            st.session_state.nav_page = "Home"
            st.session_state.auth_notice = "Your student profile is ready."
            return
        st.session_state.auth_notice = "Your account was created. Check your inbox for Supabase's email confirmation, then log in. To skip signup confirmation for new accounts, turn off Confirm email in Supabase Email provider settings before students create their profiles."
    except Exception as auth_error:
        st.session_state.auth_notice = auth_setup_help(auth_error)


def student_login_callback(email, password):
    url = secret("SUPABASE_URL")
    public_key = secret("SUPABASE_ANON_KEY") or secret("SUPABASE_PUBLISHABLE_KEY")
    if not url or not public_key:
        st.session_state.auth_notice = "Student sign-in is not configured. Add SUPABASE_URL and the public Supabase key to Streamlit Secrets."
        return
    try:
        client = create_client(url, public_key)
        response = client.auth.sign_in_with_password({"email": email.strip(), "password": password})
        if save_auth_response(response):
            st.session_state.student_email = email.strip()
            st.session_state.nav_page = "Home"
            st.session_state.auth_notice = "You are signed in."
            return
        st.session_state.auth_notice = "Supabase did not finish sign-in. Check your details and try again."
    except Exception as auth_error:
        st.session_state.auth_notice = auth_setup_help(auth_error)


def sign_out_callback():
    clear_login()
    st.session_state.pop("active_group_id", None)
    st.session_state.pop("last_logged_view_page", None)
    st.session_state.nav_page = "Home"


def go_home():
    st.session_state.nav_page = "Home"


def toggle_theme():
    st.session_state.theme_index = (int(st.session_state.get("theme_index", 0)) + 1) % len(THEMES)


def theme_control():
    current_theme = THEMES[int(st.session_state.get("theme_index", 0)) % len(THEMES)]["name"]
    st.button("💡", key="theme_bulb", on_click=toggle_theme, help=f"Current theme: {current_theme}. Click to cycle through all 7 themes.")
    st.caption(f"Theme: {current_theme}")


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
    """Turn common AI LaTeX fragments into readable plain-text math before display."""
    text = str(answer or "")
    # Convert TeX fractions, units, symbols and powers to text that stays
    # understandable even when a Markdown/LaTeX renderer is unavailable.
    text = re.sub(r"\\(?:text|mathrm|operatorname)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"\1/\2", text)
    text = re.sub(r"\\frac\s*([0-9])([0-9])", r"\1/\2", text)
    text = re.sub(r"\\sqrt\{([^{}]*)\}", r"√(\1)", text)
    text = re.sub(r"\\dot\{([^{}]*)\}", r"\1̇", text)

    superscripts = str.maketrans("0123456789+-=()in", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁱⁿ")
    subscripts = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")
    text = re.sub(r"\^\{([^{}]+)\}", lambda m: m.group(1).translate(superscripts), text)
    text = re.sub(r"_\{([^{}]+)\}", lambda m: m.group(1).translate(subscripts), text)
    text = re.sub(r"\^([0-9+-])", lambda m: m.group(1).translate(superscripts), text)
    text = re.sub(r"_([0-9])", lambda m: m.group(1).translate(subscripts), text)

    replacements = {
        r"\rho": "ρ", r"\theta": "θ", r"\pi": "π", r"\alpha": "α",
        r"\beta": "β", r"\Delta": "Δ", r"\times": "×", r"\cdot": "·",
        r"\Rightarrow": "⇒", r"\rightarrow": "→", r"\pm": "±", r"\approx": "≈",
        r"\le": "≤", r"\ge": "≥", r"\,": " ", r"\;": " ", r"\!": "",
        r"\ ": " ",
    }
    for latex, readable in replacements.items():
        text = text.replace(latex, readable)
    # Remove math wrappers and common layout-only TeX commands; keep the formula itself.
    text = re.sub(r"\\(?:left|right|displaystyle)\b", "", text)
    text = text.replace(r"\(", "").replace(r"\)", "")
    text = text.replace(r"\[", "").replace(r"\]", "")
    text = text.replace("$$", "").replace("$", "")
    st.markdown(text)


def show_post(post):
    with st.container(border=True):
        flags = []
        if post.get("is_important"):
            flags.append("📌 Important")
        if post.get("is_special"):
            flags.append("✨ Special day")
        st.caption(" · ".join([post["kind"], str(post["event_date"]), post["audience"], *flags]))
        st.subheader(post["title"])
        poster_url = str(post.get("poster_url") or "").strip()
        if poster_url.startswith("https://"):
            st.image(poster_url, use_container_width=True)
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
                    "Never use LaTeX markup, dollar-sign math delimiters, or backslash commands. Write equations as plain text using readable symbols and units, "
                    "for example: p + (1/2) × ρ × v² + ρ × g × z = constant; explain each symbol. "
                    "After each important equation, explain in plain words what it means and define every symbol. "
                    "Use ordinary numbered citations like [1] only; never expose internal reference markers such as [1†L8-L11]."
                ),
            },
            {"role": "user", "content": question},
        ],
        use_browser_search=True,
    )


@st.cache_data(ttl=86400, show_spinner=False)
def campus_quote_of_the_day(day_key):
    """Create one original, unattributed campus study quote per day for all visitors."""
    answer, _ = groq_completion(
        [
            {
                "role": "system",
                "content": (
                    "Write one short, original inspirational line for engineering students. "
                    "Do not quote or attribute it to a real person. Return only the line, without quotation marks."
                ),
            },
            {"role": "user", "content": f"Create today's fresh campus study thought for {day_key}."},
        ]
    )
    return answer.strip().strip('"“”')


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
    theme = THEMES[int(st.session_state.get("theme_index", 0)) % len(THEMES)]
    scheme = "dark" if theme["name"] == "Dark" else "light"
    theme_css = f"""
    .stApp {{ color-scheme:{scheme}; --primary-color:{theme['accent']}; --background-color:{theme['bg']}; --secondary-background-color:{theme['side']}; --text-color:{theme['text']}; background:{theme['bg']} !important; color:{theme['text']} !important; }}
    .stApp [data-testid="stSidebar"] {{ background:{theme['side']} !important; }}
    .stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp p,.stApp label,.stApp legend,.stApp [data-testid="stMarkdownContainer"],.stApp [data-testid="stWidgetLabel"],.stApp [data-testid="stWidgetLabel"] p {{ color:{theme['text']} !important; }}
    .stApp [data-testid="stCaptionContainer"],.stApp [data-testid="stCaptionContainer"] p {{ color:{theme['muted']} !important; }}
    .stApp .eyebrow,.stApp .quote-label {{ color:{theme['accent']} !important; }}
    .stApp .hero {{ background:linear-gradient(120deg,{theme['hero1']},{theme['hero2']}); border-color:{theme['border']}; }}
    .stApp .hero h2,.stApp .hero p,.stApp .date-card,.stApp .quote-card,.stApp .quote-text,.stApp .quote-note {{ color:{theme['text']} !important; }}
    .stApp .date-card,.stApp .quote-card,.stApp .chat-header {{ background:{theme['soft']} !important; border-color:{theme['border']} !important; }}
    .stApp [data-testid="stMetric"],.stApp [data-testid="stVerticalBlockBorderWrapper"] > div {{ background:{theme['surface']} !important; border-color:{theme['border']} !important; color:{theme['text']} !important; }}
    .stApp input,.stApp textarea,.stApp [data-baseweb="input"] > div,.stApp [data-baseweb="textarea"] > div,.stApp [data-baseweb="select"] > div {{ background:{theme['surface']} !important; color:{theme['text']} !important; border-color:{theme['border']} !important; }}
    .stApp input::placeholder,.stApp textarea::placeholder {{ color:{theme['muted']} !important; opacity:1; }}
    .stApp [data-baseweb="select"] *,.stApp [role="combobox"],.stApp [role="listbox"],.stApp [role="option"] {{ color:{theme['text']} !important; }}
    .stApp [role="listbox"],.stApp [role="option"] {{ background:{theme['surface']} !important; }}
    .stApp [role="option"]:hover {{ background:{theme['soft']} !important; }}
    .stApp [data-testid="stAlert"] {{ background:{theme['soft']} !important; border:1px solid {theme['border']} !important; }}
    .stApp [data-testid="stAlert"] p {{ color:{theme['text']} !important; }}
    .stApp [data-testid="stDataFrame"],.stApp [data-testid="stTable"] {{ background:{theme['surface']} !important; color:{theme['text']} !important; }}
    .stApp [data-testid="stTabs"] button {{ color:{theme['text']} !important; }}
    .stApp a {{ color:{theme['accent']} !important; }}
    .stApp div.stButton > button,.stApp [data-testid="stFormSubmitButton"] button,.stApp [data-testid="stDownloadButton"] button,.stApp [data-testid="stLinkButton"] a {{ border-color:{theme['accent']} !important; color:{theme['accent']} !important; }}
    .stApp div.stButton > button:hover,.stApp [data-testid="stFormSubmitButton"] button:hover,.stApp [data-testid="stDownloadButton"] button:hover {{ background:{theme['soft']} !important; }}
    .stApp .st-key-theme_bulb button {{ background:#fff7d9 !important; color:#704f00 !important; border-color:#d6b66a !important; }}
    .stApp [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {{ background:{theme['surface']} !important; border-color:{theme['border']} !important; color:{theme['text']} !important; }}
    .stApp [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {{ background:{theme['soft']} !important; border-color:{theme['accent']} !important; }}
    """
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
        .quote-card { text-align:center; background:linear-gradient(135deg,#e6f3e9,#f7f6e9); border:1px solid #c8dfce; border-radius:22px; padding:1.3rem 1.8rem; margin:.6rem 0 1.3rem; box-shadow:0 8px 24px #1d553010; }
        .quote-label { color:#176b5b; font-weight:700; font-size:.7rem; letter-spacing:.15em; margin-bottom:.45rem; }
        .quote-text { color:#173d32; font-family:'Manrope',sans-serif; font-size:1.2rem; line-height:1.5; }
        .quote-note { color:#577065; font-size:.8rem; margin-top:.45rem; }
        .chat-header { display:flex; align-items:center; gap:.85rem; background:#e7f3ec; border:1px solid #d3e6d9; padding:.8rem 1rem; border-radius:18px; margin:.4rem 0 1rem; }
        .chat-avatar { display:grid; place-items:center; width:42px; height:42px; flex:0 0 42px; border-radius:50%; background:#176b5b; color:white; font-weight:700; }
        .chat-header-title { color:#173d32; font-weight:700; }
        .chat-header-subtitle { color:#577065; font-size:.82rem; }
        [data-testid="stSidebar"] { background:#edf3ef; }
        div.stButton > button { border-radius:12px; border-color:#176b5b; color:#14584c; font-weight:600; }
        div.stButton > button:hover { background:#e5f2ec; border-color:#14584c; color:#103f36; }
        div.stButton > button:focus-visible { outline:3px solid #176b5b; outline-offset:2px; }
        [data-testid="stMetric"] { background:#fff; border:1px solid #dbe5df; padding:1rem; border-radius:16px; }
        .chat-bubble { max-width:78%; padding:.7rem .95rem; border-radius:16px; margin:.45rem 0; white-space:pre-wrap; overflow-wrap:anywhere; box-shadow:0 1px 2px #0001; }
        .chat-own { margin-left:auto; background:#d9fdd3; border-bottom-right-radius:4px; color:#15251b; }
        .chat-other { margin-right:auto; background:#fff; border-bottom-left-radius:4px; color:#15251b; }
        .chat-meta { font-size:.72rem; opacity:.7; margin-bottom:.25rem; }
        [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] { gap:.42rem; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] { border:1px solid #d6e4da; border-radius:999px; padding:.48rem .8rem; background:#f8fbf8; box-shadow:0 2px 5px #183c2b0b; transition:all .16s ease; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover { background:#e6f3e9; border-color:#8ab59a; transform:translateY(-1px); }
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) { background:#d9eee0; border-color:#4b9870; box-shadow:0 3px 8px #1c59331c; }
        .st-key-theme_bulb { position:fixed; z-index:99999; top:3.35rem; right:1.2rem; width:48px; padding-top:18px; }
        .st-key-theme_bulb:before { content:''; position:absolute; top:0; left:50%; height:19px; border-left:2px solid #ae8d50; }
        .st-key-theme_bulb button { border-radius:50% 50% 45% 45%; width:48px; min-width:48px; height:48px; min-height:48px; padding:0; font-size:1.5rem; background:#fff7d9; border:2px solid #d6b66a; box-shadow:0 3px 12px #0003; }
        .st-key-theme_bulb button:hover { background:#ffe894; box-shadow:0 5px 18px #9b741b55; transform:translateY(2px); }
        """ + theme_css + "</style>",
        unsafe_allow_html=True,
    )


def show_login():
    bulb_space, bulb_column = st.columns([12, 1])
    with bulb_column:
        theme_control()
    st.markdown("<div class='eyebrow'>STUDENT ENTRY</div>", unsafe_allow_html=True)
    st.title("Welcome to CampusConnect")
    st.write("Create a student profile with your email and password. Use the same email and password whenever you return.")
    auth_notice = st.session_state.pop("auth_notice", None)
    if auth_notice and "sign-in failed" not in auth_notice.lower():
        st.info(auth_notice)
    if not secret("SUPABASE_URL") or not (secret("SUPABASE_ANON_KEY") or secret("SUPABASE_PUBLISHABLE_KEY")):
        st.error("Student sign-in is not configured yet. Add the Supabase URL and publishable/anon key in Streamlit Secrets after setting up the database.")
        return
    auth_choice = st.radio("Choose an option", ["Create profile", "Log in"], horizontal=True, key="student_auth_choice")
    if auth_choice == "Create profile":
        st.caption("Create your account with email and password, then enter your student details.")
        with st.form("student_create_account"):
            new_name = st.text_input("Name")
            new_email = st.text_input("Email address")
            new_department = st.selectbox("Department", DEPARTMENTS)
            new_semester = st.selectbox("Semester", SEMESTERS)
            new_password = st.text_input("Create password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")
            create_submitted = st.form_submit_button("Create student profile", type="primary", use_container_width=True)
        if create_submitted:
            if not new_name.strip() or "@" not in new_email or "." not in new_email.rsplit("@", 1)[-1]:
                st.warning("Enter your name and a valid email address.")
            elif len(new_password) < 8:
                st.warning("Choose a password with at least 8 characters.")
            elif new_password != confirm_password:
                st.warning("The passwords do not match.")
            else:
                student_signup_callback(new_name, new_email, new_password, new_department, new_semester)
                st.rerun()
    else:
        st.caption("Use the same email address and password you chose when creating your profile.")
        with st.form("student_login_form"):
            email = st.text_input("Email address", key="student_login_email")
            password = st.text_input("Password", type="password", key="student_login_password")
            login_submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
        if login_submitted:
            if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
                st.warning("Enter a valid email address.")
            elif not password:
                st.warning("Enter your password.")
            else:
                student_login_callback(email, password)
                if st.session_state.get("campus_user_id"):
                    st.rerun()
                st.error(st.session_state.pop("auth_notice", "Could not sign in. Try again."))

apply_theme()
client, auth_user, auth_error = get_authenticated_client()
if not client or not auth_user:
    if auth_error:
        st.warning(auth_error)
    show_login()
    st.stop()

try:
    campus_settings = {
        row["key"]: row["value"]
        for row in (client.table("campus_settings").select("key,value").execute().data or [])
    }
except Exception:
    # Backward compatible until the creator reruns the updated SQL schema.
    campus_settings = {}


def campus_setting(key, legacy_secret):
    if key in campus_settings:
        return str(campus_settings[key] or "").strip()
    return str(secret(legacy_secret, "")).strip()

user_metadata = getattr(auth_user, "user_metadata", {}) or {}
st.session_state.setdefault("student_email", user_metadata.get("college_email", ""))
profile_ready = bool(user_metadata.get("display_name") and user_metadata.get("department") and user_metadata.get("semester"))
if not profile_ready:
    st.markdown("<div class='eyebrow'>ONE-TIME STUDENT PROFILE</div>", unsafe_allow_html=True)
    st.title("Tell us about yourself")
    st.caption(f"Signed-in email: {st.session_state.get('student_email', '')}")
    st.info("After saving your name, department, and semester, you can join study groups and chats.")
    with st.form("student_profile_setup"):
        profile_name = st.text_input("Your name", key="setup_display_name")
        profile_department = st.selectbox("Department", DEPARTMENTS, key="setup_department")
        profile_semester = st.selectbox("Semester", SEMESTERS, key="setup_semester")
        profile_submitted = st.form_submit_button("Save profile and enter", type="primary", use_container_width=True)
    if profile_submitted:
        if not profile_name.strip():
            st.warning("Enter your name to continue.")
        else:
            try:
                client.auth.update_user({
                    "data": {
                        "display_name": profile_name.strip(),
                        "college_email": st.session_state.get("student_email", ""),
                        "department": profile_department,
                        "semester": profile_semester,
                    }
                })
                st.session_state.display_name = profile_name.strip()
                st.session_state.profile_department = profile_department
                st.session_state.profile_semester = profile_semester
                st.rerun()
            except Exception:
                st.error("Could not save your profile. Please try again.")
    st.stop()

st.session_state.setdefault("display_name", user_metadata.get("display_name", "Student"))
st.session_state.setdefault("profile_department", user_metadata.get("department", DEPARTMENTS[0]))
st.session_state.setdefault("profile_semester", user_metadata.get("semester", SEMESTERS[0]))
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
    st.caption(st.session_state.get("student_email") or "Email-only student session")
    st.button("Sign out", on_click=sign_out_callback)

# Store one anonymous view each time a signed-in student opens a different page.
# No student ID, email, or message is sent to this aggregate analytics table.
if st.session_state.get("last_logged_view_page") != page:
    try:
        client.table("campus_app_views").insert({"page_name": page}).execute()
    except Exception:
        # Keep the student app working if the optional analytics table is not installed yet.
        pass
    st.session_state["last_logged_view_page"] = page

heading, bulb = st.columns([12, 1])
with heading:
    st.markdown("<div class='eyebrow'>B.TECH STUDENT COMMUNITY</div>", unsafe_allow_html=True)
    st.title(page)
with bulb:
    theme_control()
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
    try:
        all_posts = client.table("campus_posts").select("*").eq("status", "published").order("event_date").execute().data or []
        groups = client.table("campus_groups").select("id").eq("is_active", True).execute().data or []
        mine = client.table("group_members").select("group_id").eq("user_id", uid).execute().data or []
        today_activities = [p for p in all_posts if p["kind"] == "Activity" and str(p["event_date"]) == today_iso]
        specials = [p for p in today_activities if p.get("is_special")]
        notices = [p for p in all_posts if p["kind"] == "Notice"]
        important = [p for p in notices if p.get("is_important")]
        top_left, top_right = st.columns(2)
        with top_left:
            st.markdown(
                f"<div class='date-card'><b>Today · {today.strftime('%A, %d %B %Y')}</b><br>Today's special day is highlighted below when a campus creator posts one.</div>",
                unsafe_allow_html=True,
            )
        with top_right:
            with st.container(border=True):
                st.subheader("📌 Important campus notice")
                if important:
                    featured_notice = sorted(important, key=lambda p: str(p.get("created_at", "")), reverse=True)[0]
                    st.caption(f"{featured_notice['event_date']} · {featured_notice['audience']}")
                    st.markdown(f"**{featured_notice['title']}**")
                    poster_url = str(featured_notice.get("poster_url") or "")
                    if poster_url.startswith("https://"):
                        st.image(poster_url, use_container_width=True)
                    st.write(featured_notice["body"])
                else:
                    st.info("There are no pinned important notices right now.")
        m1, m2, m3 = st.columns(3)
        m1.metric("Study groups", len(groups))
        m2.metric("Groups you joined", len(mine))
        m3.metric("Activities today", len(today_activities))
        latest_notices = sorted(
            [post for post in notices if not post.get("is_important")],
            key=lambda p: str(p.get("created_at", "")),
            reverse=True,
        )
        if latest_notices:
            st.subheader("📰 Latest campus notices")
            for post in latest_notices[:3]:
                show_post(post)
        elif not notices:
            st.subheader("📌 Campus notices")
            st.info("Published campus notices will appear here.")

        try:
            daily_quote = campus_quote_of_the_day(today_iso)
        except Exception:
            daily_quote = ""
        if daily_quote:
            _, quote_column, _ = st.columns([1, 6, 1])
            with quote_column:
                st.markdown(
                    f"<div class='quote-card'><div class='quote-label'>✦ AI-GENERATED CAMPUS THOUGHT</div><div class='quote-text'>“{escape(daily_quote)}”</div><div class='quote-note'>An original thought for today · {today.strftime('%d %B')}</div></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Today's AI campus thought is unavailable right now. Try again later.")

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
            upcoming = [p for p in all_posts if p["kind"] == "Activity" and str(p["event_date"])[:10] >= today_iso]
            st.subheader("🗓️ Coming up on campus")
            if upcoming:
                for post in sorted(upcoming, key=lambda p: str(p["event_date"]))[:3]:
                    st.write(f"**{post['event_date']} · {post['title']}**")
            else:
                st.caption("No upcoming activities have been posted.")
            st.button("View campus calendar →", on_click=lambda: st.session_state.update(nav_page="Campus Calendar"))
            community_url = campus_setting("whatsapp_community_url", "WHATSAPP_COMMUNITY_URL")
            channel_url = campus_setting("whatsapp_channel_url", "WHATSAPP_CHANNEL_URL")
            if community_url.startswith("https://") or channel_url.startswith("https://"):
                st.subheader("💬 WhatsApp campus spaces")
                if community_url.startswith("https://"):
                    st.link_button("Join WhatsApp Community", community_url, use_container_width=True)
                if channel_url.startswith("https://"):
                    st.link_button("Follow WhatsApp Channel", channel_url, use_container_width=True)
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
        current_group = by_id[group_id]
        initials = escape("".join(part[0] for part in str(current_group["name"]).split()[:2]).upper()) or "G"
        group_title = escape(str(current_group["name"]))
        st.markdown(
            f"<div class='chat-header'><div class='chat-avatar'>{initials}</div><div><div class='chat-header-title'>{group_title}</div><div class='chat-header-subtitle'>{escape(str(current_group['department']))} · WhatsApp-style group chat</div></div></div>",
            unsafe_allow_html=True,
        )
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

    embed_url = campus_setting("google_calendar_embed_url", "GOOGLE_CALENDAR_EMBED_URL")
    if embed_url.startswith("https://calendar.google.com/calendar/embed"):
        st.subheader("Google Calendar")
        components.iframe(embed_url, height=650, scrolling=True)
        st.caption("Google Calendar is public in this view. Do not include private student or staff information in that calendar.")
    else:
        st.info("The campus creator can add the public Google Calendar embed link in Creator Studio → Campus links. Creator-published events are listed above.")

elif page == "AI Search":
    st.caption("Ask a question that needs current web information. Free-tier Groq AI searches the web and provides sources when available.")
    st.info("AI answers can still be wrong or out of date. Verify important academic, medical, legal, or safety information with an official source.")
    response_language = st.selectbox(
        "Answer language", ["English", "Malayalam", "Manglish (Malayalam in English letters)"], key="search_answer_language"
    )
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
                    language_instruction = {
                        "English": "Answer in clear, simple English.",
                        "Malayalam": "Answer in natural Malayalam using Malayalam script. Keep equations and standard technical terms readable, and explain each technical term in Malayalam.",
                        "Manglish (Malayalam in English letters)": "Answer in Manglish: speak Malayalam, but write it using English/Latin letters. Do not switch to Malayalam script. Keep equations readable and explain technical terms simply.",
                    }[response_language]
                    answer, sources = groq_browser_search(f"{language_instruction}\n\nQuestion: {search_question.strip()}")
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
    community_url = campus_setting("whatsapp_community_url", "WHATSAPP_COMMUNITY_URL")
    channel_url = campus_setting("whatsapp_channel_url", "WHATSAPP_CHANNEL_URL")
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
    response_language = st.selectbox(
        "Answer language", ["English", "Malayalam", "Manglish (Malayalam in English letters)"], key="study_answer_language"
    )
    chat = st.session_state.setdefault("study_chat", [])
    for message in chat:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_ai_markdown(message["content"])
            else:
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
                                    f"Reply in {response_language}. For Manglish, write Malayalam words using English/Latin letters, not Malayalam script. "
                                    "Never use LaTeX markup, dollar-sign math delimiters, or backslash commands. Write equations as plain text using readable symbols and units, "
                                    "for example: F = k × x; k = 250 N/m; x = 0.08 m. "
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

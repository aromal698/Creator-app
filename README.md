# CampusConnect

A two-app Streamlit campus community for B.Tech students. Both apps use one Supabase database.

- `app.py` — student app: accounts, pebble-style navigation, join-to-chat groups, WhatsApp-style chats, front-page campus notices, daily AI study thought, activities, calendar, AI study buddy, web search, WhatsApp links, and feedback.
- `creator_app.py` — separate password-protected Creator Studio: AI-assisted notice/activity/calendar drafts, special-day highlighting, publish/edit/delete, and AI-assisted group administration.
- `supabase_schema.sql` — shared tables, initial department and semester groups, and student access policies.
- `.streamlit/secrets.toml.example` — example settings only. Never put real keys in this file or GitHub.

Student pages show published campus content. Creator drafts and edit controls remain in Creator Studio. Groq free-tier AI helps with study explanations, web search, the daily original campus thought, and creator drafts. A creator reviews content before publishing. AI cannot guarantee factual accuracy. Free access has usage limits, and all app users share the app owner's quota.

## 1. Create the shared database

1. Create a project at [Supabase](https://supabase.com/).
2. In the project, open **SQL Editor → New query**.
3. Open `supabase_schema.sql`, copy its full contents, paste into the SQL Editor, and click **Run**. This creates groups for the listed departments and semesters 1–8, chats, campus posts, feedback, and database access policies.
4. In **Authentication → Providers**, enable email sign-in. Email confirmation is recommended.
5. Find the project URL and publishable/anon key in the Supabase API key settings. Keep the service-role/secret key for the server-side Creator Studio only.

## 2. Create a public campus Google Calendar (optional)

The app calendar always lists creator-published events saved in Supabase. Creators manage these from **Creator Studio → Manage campus calendar** or **Manage notices & activities**; activity dates and special-day flags appear in the student calendar. Each event has an **Add to Google Calendar** link. You can also embed a public Google Calendar to show campus holidays or other dates maintained in Google Calendar.

1. Create/select a campus calendar in Google Calendar and add the special dates/events you want to share.
2. Make it public only if the calendar is safe for all students and the public to see. Google notes an embedded calendar is only visible to people with permission unless it is public.
3. On a computer, open Calendar **Settings → select that calendar → Integrate calendar → Customize**.
4. Copy the embed code and use only the URL between its `src="..."` quotes. Put that full URL in the student app's `GOOGLE_CALENDAR_EMBED_URL` secret.

A creator-published Supabase event does not automatically get written into the Google Calendar. The Add to Google Calendar button lets a student add that event to their own calendar. If you want it also displayed in the embedded campus calendar, an authorized person must add it to that Google Calendar too. [Google Calendar embed instructions](https://support.google.com/calendar/answer/41207?hl=en).

## 3. Prepare WhatsApp links (optional)

Create your WhatsApp Community and Channel, then copy their invite/share URLs. Add them as `WHATSAPP_COMMUNITY_URL` and `WHATSAPP_CHANNEL_URL` in the student app's Streamlit Secrets. The app links to WhatsApp; it does not read or send WhatsApp messages.

## 4. Upload code to GitHub

Upload and commit these files to your repository root:

- `app.py`
- `creator_app.py`
- `supabase_schema.sql`
- `requirements.txt`
- `README.md`
- `.gitignore`
- `.streamlit/config.toml`
- optionally `.streamlit/secrets.toml.example`

Do **not** upload `.streamlit/secrets.toml`, API keys, database keys, or creator passwords. `.gitignore` hides the local `secrets.toml` from Git, but do not rely on that as your only safeguard: check carefully before committing.

## 5. Create a Groq API key (free plan)

1. Create/sign in to a Groq account at [console.groq.com](https://console.groq.com/).
2. Open [API Keys](https://console.groq.com/keys) and create a key for CampusConnect.
3. Keep the account on its Free plan if you want to avoid usage charges. The free plan has limits; if the app's shared quota is used up, AI requests stop until the limit resets. Never commit the key to GitHub.

The student and creator apps each need the same `GROQ_API_KEY` added separately to their own Streamlit Secrets.

## 6. Deploy the student app

1. Sign in at [Streamlit Community Cloud](https://share.streamlit.io/), select **Create app**, then choose your GitHub repository and branch.
2. Set **Main file path** to `app.py`.
3. Open **Advanced settings → Secrets** and enter your real values in TOML format:

```toml
SUPABASE_URL = "your-supabase-project-url"
SUPABASE_ANON_KEY = "your-supabase-publishable-or-anon-key"
GROQ_API_KEY = "your-groq-api-key"
GROQ_MODEL = "openai/gpt-oss-20b"
GOOGLE_CALENDAR_EMBED_URL = "https://calendar.google.com/calendar/embed?src=your-public-calendar"
WHATSAPP_COMMUNITY_URL = "https://chat.whatsapp.com/your-community-invite"
WHATSAPP_CHANNEL_URL = "https://whatsapp.com/channel/your-channel"
```

Replace all examples with your real settings. If you have not configured a calendar or WhatsApp link, omit that line. Click **Deploy**. Streamlit's docs show the entrypoint and secrets fields in the deploy workflow. [Deploy an app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app).

## 7. Deploy Creator Studio as another app

1. In Streamlit Community Cloud, choose **Create app** again.
2. Select the same repository and branch, but set **Main file path** to `creator_app.py`.
3. Add a separate secrets block for this app:

```toml
SUPABASE_URL = "your-supabase-project-url"
SUPABASE_SERVICE_ROLE_KEY = "your-supabase-secret-or-service-role-key"
CAMPUS_CREATOR_PASSWORD = "choose-a-long-private-password"
CAMPUS_CREATOR_NAME = "Campus Creator"
GROQ_API_KEY = "your-groq-api-key"
GROQ_MODEL = "openai/gpt-oss-20b"
```

The Creator Studio password is shared in this starter version. Anyone who has it can manage campus updates and groups. Keep the Creator Studio URL and password for authorized creators. The service-role key can bypass student row policies; never add it to the student app's secrets or GitHub. [Supabase API key safety](https://supabase.com/docs/guides/getting-started/api-keys).

## 7. Use CampusConnect

- Students create an account, browse department/semester groups, and join. Joining opens that group's chat. Chats use message bubbles styled after WhatsApp; WhatsApp Community and Channel buttons open external links.
- The student Home page shows today's date, today's activities, special-day items, important campus notices, recent notices, and upcoming activities.
- **Campus Calendar** shows published event details by selected date, Google Calendar (if configured), and Add to Google Calendar links.
- **AI Study Buddy, AI Search, and Creator Studio drafting** use Groq's `openai/gpt-oss-20b`; AI Search enables the built-in browser search tool. Search results and AI answers can still be incomplete or wrong. [Groq model and browser search docs](https://console.groq.com/docs/tool-use/built-in-tools/browser-search).
- Groq's free plan is rate-limited. Because every student shares this app's API key, a public app can use up its free quota; check the current limits before sharing widely. [Groq rate limits](https://console.groq.com/docs/rate-limits).
- Feedback is the final page in the student navigation. Every non-home page has a Back to home button.
- The hanging bulb at top-right switches between light and dark themes.

Before a campus-wide launch, configure college email verification, protect Creator Studio credentials, review the access policies, and try the apps with separate student accounts. Never put private information in a public calendar or AI prompt.

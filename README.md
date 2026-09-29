# CampusConnect

A two-app Streamlit campus community for B.Tech students. Both apps use one Supabase database.

- `app.py` — student app: email/password profiles, department and semester groups, WhatsApp-style chat with photo/camera and emoji support, daily red/yellow/green alerts, private creator chat, campus updates, calendar, and AI study tools.
- `creator_app.py` — Creator Studio sign-in asks for a creator name and the shared creator password; it includes campus post tools, group administration, private student inbox, and page-view totals.
- `supabase_schema.sql` — shared database setup, including public and code-protected private groups, chats, daily choices, private creator inbox, page views, and private group-photo storage.
- `.streamlit/secrets.toml.example` — example settings only. Never put real keys in this file or GitHub.

Student pages show published campus content. Creator drafts and edit controls remain in Creator Studio. Groq AI helps with study explanations, web search, the daily original campus thought, and creator drafts. Poster reading uses Groq's image-capable Qwen model and may require paid model access; the creator app asks before sending an uploaded image. A creator reviews content before publishing. AI cannot guarantee factual accuracy. Usage limits apply, and all app users share the app owner's quota.

## 1. Create the shared database

1. Create a project at [Supabase](https://supabase.com/).
2. In the project, open **SQL Editor → New query**.
3. Open `supabase_schema.sql`, copy its full contents, paste into the SQL Editor, and click **Run**. This creates groups for the listed departments and semesters 1–8, chats, daily alerts, a private creator inbox, page-view counts, storage buckets, and access policies.
   If the database already exists, run the updated SQL again. It adds missing columns/tables and refreshes policies without deleting existing posts or messages.
4. In **Authentication → Sign In / Providers → Email**, enable **Allow new users to sign up**. Turn **Confirm email** off if students should start using the app immediately after creating their profile. The app does not use anonymous sign-ins.
5. No Magic Link template is needed for this password-based flow. Students select **Create profile** to enter name, email, department, semester, and password. The next time they choose **Log in** and use the same email and password. Supabase’s supported password sign-in is documented [here](https://supabase.com/docs/reference/python/auth-signinwithpassword).
6. Find the project URL and publishable/anon key in the Supabase API key settings. Keep the service-role/secret key for the server-side Creator Studio only.

## 2. Create a public campus Google Calendar (optional)

The app calendar always lists creator-published events saved in Supabase. Creators manage these from **Creator Studio → Manage campus calendar** or **Manage notices & activities**; activity dates and special-day flags appear in the student calendar. AI summarizes only the creator-highlighted special entries for today's Home highlight; it does not import or guess events from the embedded Google Calendar. Each event has an **Add to Google Calendar** link. The creator can set the optional public Google Calendar embed link from **Creator Studio → Campus links**. Embedded Google Calendar items do not sync with CampusConnect posts.

1. Create/select a campus calendar in Google Calendar and add the special dates/events you want to share.
2. Make it public only if the calendar is safe for all students and the public to see. Google notes an embedded calendar is only visible to people with permission unless it is public.
3. On a computer, open Calendar **Settings → select that calendar → Integrate calendar → Customize**.
4. Copy the embed code and use only the URL between its `src="..."` quotes. An authorized creator saves that URL in **Creator Studio → Campus links**.

A creator-published Supabase event does not automatically get written into the Google Calendar. The Add to Google Calendar button lets a student add that event to their own calendar. If you want it also displayed in the embedded campus calendar, an authorized person must add it to that Google Calendar too. [Google Calendar embed instructions](https://support.google.com/calendar/answer/41207?hl=en).

## 3. Prepare WhatsApp links (optional)

Create your WhatsApp Community and Channel, then copy their invite/share URLs. In **Creator Studio → Campus links**, save those URLs, paste the public student app URL into **Public student app link**, and set **Creator name / Feedback signature**. Students see the WhatsApp Community, Channel, and app-sharing buttons only on the student app's **Home** page. To show the app on a WhatsApp Business profile, add its URL to the Business profile's Website field. CampusConnect opens WhatsApp links; it does not read or send WhatsApp messages.

## 4. Student login, page views, and notice posters

- New students create an email/password account and profile. Returning students sign in with that same email and password. With **Confirm email** off, Supabase does not require an email confirmation before the account can be used.
- A small red/yellow/green alert panel appears at the lower right of student pages. Students can choose once per day: red opens a private chat with the creator, yellow shows snowfall, and green adds ₹5 of in-app credit. This is not a cash payment.
- Group chat photos and camera pictures are stored in a private bucket. Only members of the matching group can view them. Emoji and captions can also be sent. Select one or more of your own messages and use **Delete selected** to remove them; other students' messages cannot be selected or deleted by you.
- The Creator Studio **Student inbox** page receives and replies to the private chats started by students.
- The creator dashboard counts app page openings in **App page views** and **Views today**. These are not unique-student counts: returning to the same page during one login session is counted once. The log stores only the page name and timestamp, not a student ID, email, or chat message.
- In **Creator Studio → Manage notices & activities**, add event details, optionally upload a photo, then select **Create poster picture from these details**. You can also upload a finished poster and attach it directly. Review the preview, then save or publish. Students see the attached image with the notice/activity.
- Poster image storage uses a public Supabase Storage bucket so student browsers can display images. Upload only artwork intended to be public. An uploaded background photo is sent to Supabase only when saving or publishing; poster reading sends the selected file to Groq only after you confirm in the app.
- Running the updated `supabase_schema.sql` creates the poster bucket and page-view table. `Pillow` in `requirements.txt` enables local poster design generation.

## 5. Upload code to GitHub

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

## 6. Create a Groq API key (free plan)

1. Create/sign in to a Groq account at [console.groq.com](https://console.groq.com/).
2. Open [API Keys](https://console.groq.com/keys) and create a key for CampusConnect.
3. Keep the account on its Free plan for supported free-tier text requests. Free usage has limits; if the app's shared quota is used up, AI requests stop until the limit resets. Poster image reading uses a vision model with separate pricing/access and asks for confirmation in Creator Studio before sending an image. Never commit the key to GitHub.

The student and creator apps each need the same `GROQ_API_KEY` added separately to their own Streamlit Secrets.

## 7. Deploy the student app

1. Sign in at [Streamlit Community Cloud](https://share.streamlit.io/), select **Create app**, then choose your GitHub repository and branch.
2. Set **Main file path** to `app.py`.
3. Open **Advanced settings → Secrets** and enter your real values in TOML format:

```toml
SUPABASE_URL = "your-supabase-project-url"
SUPABASE_ANON_KEY = "your-supabase-publishable-or-anon-key"
GROQ_API_KEY = "your-groq-api-key"
GROQ_MODEL = "openai/gpt-oss-20b"
```

Replace all examples with your real settings and click **Deploy**. Calendar and WhatsApp URLs are entered later by the creator in Creator Studio → Campus links. Streamlit's docs show the entrypoint and secrets fields in the deploy workflow. [Deploy an app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app).

## 8. Deploy Creator Studio as another app

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
GROQ_VISION_MODEL = "qwen/qwen3.8-27b"
```

The poster-reading model may incur usage charges; you can omit `GROQ_VISION_MODEL` to use its default, but the creator must still confirm before each poster analysis.

The Creator Studio password is shared in this starter version. Anyone who has it can manage campus updates and groups; the creator name is used as the signed-in display name, not as a separate account or password. Keep the Creator Studio URL and password for authorized creators. The service-role key can bypass student row policies; never add it to the student app's secrets or GitHub. [Supabase API key safety](https://supabase.com/docs/guides/getting-started/api-keys).

## 9. Use CampusConnect

- Students create their profile once with email, password, name, department, and semester. On later visits they choose **Log in** and use that same email and password to return to their saved profile.
- Students get a separate seeded chat group for each department and semester (for example, CSE · Semester 3). The Study Groups page starts filtered to the student's own department and semester; students can also browse other groups or create a new group. Joining opens that group's chat.
- The creator makes private groups in **Creator Studio → Group admin** and shares the generated invite code with selected students. The database stores only a hash of the code. Students join through **Study Groups → Join with code**; a successful join opens that group's chat. Private groups stay hidden from students who have not joined. Students can create public groups only.
- The student Home page puts the important notice and all published campus notices near the top; notices are arranged in three columns. It shows today's activities and creator-highlighted special days from the campus calendar, and generates a daily AI study thought in English and Malayalam. The AI summary only uses events the creator marked as special.
- **Campus Calendar** shows published event details by selected date, Google Calendar (if configured), and Add to Google Calendar links.
- **AI Study Buddy, AI Search, and Creator Studio drafting** use Groq's `openai/gpt-oss-20b`; AI Search enables the built-in browser search tool. Search results and AI answers can still be incomplete or wrong. [Groq model and browser search docs](https://console.groq.com/docs/tool-use/built-in-tools/browser-search).
- Groq's free plan is rate-limited. Because every student shares this app's API key, a public app can use up its free quota; check the current limits before sharing widely. [Groq rate limits](https://console.groq.com/docs/rate-limits).
- Feedback is the final page in the student navigation and ends with the campus creator's name/sign on the lower right. Every non-home page has a Back to home button.
- Click the hanging bulb at top-right to cycle through seven color themes: White, Dark, Blue, Purple, Amber, Rose, and Teal. The current theme name appears below the bulb.
- The student sidebar uses a theme-aware vertical icon-card menu. Each page is a separate menu item, and the current page is highlighted.
- Set the public student app URL and creator name in **Creator Studio → Campus links**. Students can then share the app through WhatsApp.

Before a campus-wide launch, choose an identity method that students can recover, protect Creator Studio credentials, review the access policies, and try the apps with separate student accounts. Never put private information in a public calendar or AI prompt.

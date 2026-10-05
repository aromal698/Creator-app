# CampusConnect

A two-app Streamlit campus community for B.Tech students. Both apps use one Supabase database.

- `app.py` — student app: direct Home access with anonymous Supabase sessions and profiles, department and semester groups, WhatsApp-style chat with photo/camera and emoji support, daily red/yellow/green alerts, private creator chat, campus updates, calendar, and AI study tools.
- `creator_app.py` — Creator Studio sign-in asks for a creator name and the shared creator password; it includes campus post tools, group administration, private student inbox, and page-view totals.
- `supabase_schema.sql` — shared database setup, including public and code-protected private groups, chats, daily choices, private creator inbox, page views, and private group-photo storage.
- `.streamlit/secrets.toml.example` — example settings only. Never put real keys in this file or GitHub.

Student pages show published campus content. Creator drafts and edit controls remain in Creator Studio. Students and creators can choose Groq or Cloudflare Workers AI for text. Each request calls only the selected provider; there is no automatic fallback between them. Poster reading in Creator Studio uses Gemini separately. This setup does not use live web-search grounding. A creator reviews AI content before publishing. Each service has usage limits shared by its account.

## 1. Create the shared database

1. Create a project at [Supabase](https://supabase.com/).
2. In the project, open **SQL Editor → New query**.
3. Open `supabase_schema.sql`, copy its full contents, paste into the SQL Editor, and click **Run**. This creates groups for the listed departments and semesters 1–8, chats, daily alerts, a private creator inbox, page-view counts, storage buckets, and access policies.
   If the database already exists, run the updated SQL again. It adds missing columns/tables and refreshes policies without deleting existing posts or messages.
4. In Supabase **Authentication** settings, enable **Anonymous Sign-Ins**. The student app needs this so students can enter without an email/password screen while database access remains tied to a private Supabase user ID. Email confirmation is not used by the student app.
5. Students enter the Home dashboard, then save their registration number, name, department, and semester in the sidebar profile form. Anonymous profiles cannot be recovered after a browser session is lost or on a different device; a registration number by itself does not prove who owns that profile. For a permanent student account, add a recoverable sign-in method later.
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

## 4. Student profile, page views, and notice posters

- Students open Home without an email/password form. Their registration number, name, department, and semester are saved in the current anonymous Supabase profile. A lost anonymous session cannot be recovered using only the registration number.
- A small red/yellow/green alert panel appears near the top right of student pages. Students can choose once per day: red opens a private chat with the creator, yellow shows snowfall, and green adds ₹5 of in-app credit. This is not a cash payment.
- Group chat photos and camera pictures are stored in a private bucket. Only members of the matching group can view them. Emoji and captions can also be sent. Select one or more of your own messages and use **Delete selected** to remove them; other students' messages cannot be selected or deleted by you.
- The Creator Studio **Student inbox** page receives and replies to the private chats started by students.
- The creator dashboard counts app page openings in **App page views** and **Views today**. These are not unique-student counts: returning to the same page during one login session is counted once. The log stores only the page name and timestamp, not a student ID, email, or chat message.
- In **Creator Studio → Manage notices & activities**, add event details, optionally upload a photo, then select **Create poster picture from these details**. You can also upload a finished poster and attach it directly. Review the preview, then save or publish. Students see the attached image with the notice/activity.
- Poster image storage uses a public Supabase Storage bucket so student browsers can display images. Upload only artwork intended to be public. An uploaded background photo is sent to Supabase only when saving or publishing; poster reading sends the selected file to Gemini only after you confirm in the app. Text drafting uses the AI provider selected in the app; image reading remains Gemini-only.
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

## 6. Set up AI for the student and creator apps

1. Create a Groq API key at [Groq Console API Keys](https://console.groq.com/keys). In the app Secrets, set `GROQ_API_KEY` to that private key and `GROQ_MODEL = "openai/gpt-oss-20b"`. This code locks the model to one listed on Groq's Free Plan Limits. Groq limits are shared at organization level; check your account's current limits and do not upgrade to a paid plan if you want to stay free. [Groq Free Plan Limits](https://console.groq.com/docs/rate-limits).
2. Create a Cloudflare account, open **Workers AI → Use REST API**, and create a Workers AI API token. Copy the token and account ID. If you create a token manually, Cloudflare says it needs **Workers AI - Read** and **Workers AI - Edit** permissions.
3. Keep Cloudflare on **Workers Free**. Its free allocation is 10,000 Neurons per day; requests stop when that daily allowance runs out. If the account is on Workers Paid, usage beyond the allocation is billable. [Cloudflare free allocation and billing](https://developers.cloudflare.com/workers-ai/platform/pricing/).
4. Add `GROQ_API_KEY`, `GROQ_MODEL = "openai/gpt-oss-20b"`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, and `CLOUDFLARE_MODEL = "@cf/google/gemma-4-26b-a4b-it"` to the Secrets for each app. Students choose one in their sidebar; creators choose one in Creator Studio's sidebar. Each request goes only to that selected service. If it is out of quota, manually switch to the other one. Creator Studio's optional poster image reading uses Gemini separately and needs `GEMINI_API_KEY`.
5. AI Search uses the models' built-in knowledge, not live internet search. Answers can be wrong or out of date. Never commit API keys to GitHub. [Groq chat API](https://console.groq.com/docs/api-reference), [Cloudflare model availability](https://developers.cloudflare.com/workers-ai/models/).

Each app has its own Streamlit Secrets. Add the keys separately to the student app and Creator Studio.

## 7. Deploy the student app

1. Sign in at [Streamlit Community Cloud](https://share.streamlit.io/), select **Create app**, then choose your GitHub repository and branch.
2. Set **Main file path** to `app.py`.
3. Open **Advanced settings → Secrets** and enter your real values in TOML format:

```toml
SUPABASE_URL = "your-supabase-project-url"
SUPABASE_ANON_KEY = "your-supabase-publishable-or-anon-key"
GROQ_API_KEY = "your-groq-api-key"
GROQ_MODEL = "openai/gpt-oss-20b"
CLOUDFLARE_ACCOUNT_ID = "your-cloudflare-account-id"
CLOUDFLARE_API_TOKEN = "your-cloudflare-workers-ai-token"
CLOUDFLARE_MODEL = "@cf/google/gemma-4-26b-a4b-it"
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
CLOUDFLARE_ACCOUNT_ID = "your-cloudflare-account-id"
CLOUDFLARE_API_TOKEN = "your-cloudflare-workers-ai-token"
CLOUDFLARE_MODEL = "@cf/google/gemma-4-26b-a4b-it"
# Optional: Creator Studio poster image reading only
GEMINI_API_KEY = "your-gemini-api-key"
GEMINI_MODEL = "gemini-3.5-flash-lite"
```

Keep Groq on its Free plan and Cloudflare on Workers Free if you want no paid usage. Poster reading still uses Gemini separately.

The Creator Studio password is shared in this starter version. Anyone who has it can manage campus updates and groups; the creator name is used as the signed-in display name, not as a separate account or password. Keep the Creator Studio URL and password for authorized creators. The service-role key can bypass student row policies; never add it to the student app's secrets or GitHub. [Supabase API key safety](https://supabase.com/docs/guides/getting-started/api-keys).

## 9. Use CampusConnect

- Students open the Home dashboard directly. The app silently creates a Supabase anonymous session, then asks for registration number, name, department, and semester in the sidebar. The alert choices are at the top-right of the student page. Anonymous profiles are temporary identities; if a student loses the browser session or changes device, a registration number alone cannot recover the same identity.
- Students get a separate seeded chat group for each department and semester (for example, CSE · Semester 3). The Study Groups page starts filtered to the student's own department and semester; students can also browse other groups or create a new group. Joining opens that group's chat.
- The creator makes private groups in **Creator Studio → Group admin** and shares the generated invite code with selected students. The database stores only a hash of the code. If a code is lost, choose **Manage groups and members → Generate / replace invite code**; this invalidates the previous code but keeps current members. Students join through **Study Groups → Join with code**; a successful join opens that group's chat. Private groups stay hidden from students who have not joined. Students can create public groups only.
- The student Home page puts the important notice and all published campus notices near the top; notices are arranged in three columns. It shows today's activities and creator-highlighted special days from the campus calendar, and generates a daily AI study thought in English and Malayalam. The AI summary only uses events the creator marked as special.
- **Campus Calendar** shows published event details by selected date, Google Calendar (if configured), and Add to Google Calendar links.
- **AI Study Buddy, AI Search, and Creator Studio text drafting** let the user choose Groq or Cloudflare Workers AI. A request goes to only that service; there is no automatic switching. AI Search uses model knowledge, not live web search, and answers can be wrong or out of date. Check current claims with trusted sources. The student app has **Print / Save as PDF** below AI Search results and the latest Study Buddy answer; choose **Save as PDF** in your browser's print dialog.
- Free tiers have limits shared by all users of each account. Cloudflare Workers Free includes 10,000 Neurons a day; Groq Free limits depend on the selected model and account. When one service reaches its limit, manually select the other service. [Cloudflare pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/), [Groq free limits](https://console.groq.com/docs/rate-limits).
- Feedback is the final page in the student navigation and ends with the campus creator's name/sign on the lower right. Every non-home page has a Back to home button.
- Click the hanging bulb at top-right to cycle through seven color themes: White, Dark, Blue, Purple, Amber, Rose, and Teal. The current theme name appears below the bulb.
- The student sidebar uses a theme-aware vertical icon-card menu. Each page is a separate menu item, and the current page is highlighted.
- Set the public student app URL and creator name in **Creator Studio → Campus links**. Students can then share the app through WhatsApp.

Before a campus-wide launch, choose an identity method that students can recover, protect Creator Studio credentials, review the access policies, and try the apps with separate student accounts. Never put private information in a public calendar or AI prompt.

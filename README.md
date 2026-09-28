# CampusConnect

A two-app Streamlit campus community for B.Tech students. Both apps use one Supabase database.

- `app.py` — student app: password-free email-code login (name and email on first account creation; email plus a fresh one-time code for later sign-ins), seven bulb-cycled color themes, pebble-style navigation, join-to-chat groups, WhatsApp-style chats, front-page campus notices, daily AI study thought, activities, calendar, AI study buddy, web search, WhatsApp links, and feedback.
- `creator_app.py` — separate password-protected Creator Studio: seven bulb-cycled color themes, AI-assisted notice/activity/calendar drafts, poster reading and poster creation/upload, special-day highlighting, public campus links, publish/edit/delete, group administration, and anonymous page-view totals.
- `supabase_schema.sql` — shared tables, initial department and semester groups, campus links, anonymous page-view counts, poster storage bucket, and student access policies.
- `.streamlit/secrets.toml.example` — example settings only. Never put real keys in this file or GitHub.

Student pages show published campus content. Creator drafts and edit controls remain in Creator Studio. Groq AI helps with study explanations, web search, the daily original campus thought, and creator drafts. Poster reading uses Groq's image-capable Qwen model and may require paid model access; the creator app asks before sending an uploaded image. A creator reviews content before publishing. AI cannot guarantee factual accuracy. Usage limits apply, and all app users share the app owner's quota.

## 1. Create the shared database

1. Create a project at [Supabase](https://supabase.com/).
2. In the project, open **SQL Editor → New query**.
3. Open `supabase_schema.sql`, copy its full contents, paste into the SQL Editor, and click **Run**. This creates groups for the listed departments and semesters 1–8, chats, campus posts, feedback, campus links, anonymous page-view counts, the public poster bucket, and database access policies.
   If the database already exists, run the updated SQL again. It adds missing columns/tables and refreshes policies without deleting existing posts or messages.
4. In **Authentication → Sign In / Providers → Email**, enable email sign-in. In **Authentication → Email Templates → Magic Link or OTP**, edit the message so it includes the one-time code variable `{{ .Token }}`. For example, the email body can say: `Your CampusConnect code is {{ .Token }}. Enter it in the app to verify your email.` The app asks students to enter this code.
5. Supabase's default email sender has strict limits and may only send to authorized team email addresses. Since your project already showed an email-rate-limit error, either wait for its limit to reset for a small test or set up a custom SMTP provider in **Authentication settings → SMTP Settings** before inviting students. [Supabase email templates](https://supabase.com/docs/guides/auth/auth-email-templates) · [Supabase custom SMTP setup](https://supabase.com/docs/guides/auth/auth-smtp).
6. Find the project URL and publishable/anon key in the Supabase API key settings. Keep the service-role/secret key for the server-side Creator Studio only.

## 2. Create a public campus Google Calendar (optional)

The app calendar always lists creator-published events saved in Supabase. Creators manage these from **Creator Studio → Manage campus calendar** or **Manage notices & activities**; activity dates and special-day flags appear in the student calendar. Each event has an **Add to Google Calendar** link. The creator can set the optional public Google Calendar embed link from **Creator Studio → Campus links**. Embedded Google Calendar items do not sync with CampusConnect posts.

1. Create/select a campus calendar in Google Calendar and add the special dates/events you want to share.
2. Make it public only if the calendar is safe for all students and the public to see. Google notes an embedded calendar is only visible to people with permission unless it is public.
3. On a computer, open Calendar **Settings → select that calendar → Integrate calendar → Customize**.
4. Copy the embed code and use only the URL between its `src="..."` quotes. An authorized creator saves that URL in **Creator Studio → Campus links**.

A creator-published Supabase event does not automatically get written into the Google Calendar. The Add to Google Calendar button lets a student add that event to their own calendar. If you want it also displayed in the embedded campus calendar, an authorized person must add it to that Google Calendar too. [Google Calendar embed instructions](https://support.google.com/calendar/answer/41207?hl=en).

## 3. Prepare WhatsApp links (optional)

Create your WhatsApp Community and Channel, then copy their invite/share URLs. A creator can save them in **Creator Studio → Campus links**; the student app shows those links on Home and the WhatsApp page. The app links to WhatsApp; it does not read or send WhatsApp messages.

## 4. Student login, page views, and notice posters

- First-time students open **First time? Create account**, enter their name and email, and verify the code emailed to them. Returning students open **Returning student? Sign in**, enter their email, and verify a fresh one-time code. Students do not set or remember an app password. [Supabase email OTP sign-in](https://supabase.com/docs/reference/python/auth-signinwithotp) · [Verify the code](https://supabase.com/docs/reference/python/auth-verifyotp).
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

The Creator Studio password is shared in this starter version. Anyone who has it can manage campus updates and groups. Keep the Creator Studio URL and password for authorized creators. The service-role key can bypass student row policies; never add it to the student app's secrets or GitHub. [Supabase API key safety](https://supabase.com/docs/guides/getting-started/api-keys).

## 9. Use CampusConnect

- Students create an account, browse department/semester groups, and join. Joining opens that group's chat. Chats use message bubbles styled after WhatsApp; WhatsApp Community and Channel buttons open external links.
- The student Home page shows today's date, today's activities, special-day items, important campus notices, recent notices, and upcoming activities.
- **Campus Calendar** shows published event details by selected date, Google Calendar (if configured), and Add to Google Calendar links.
- **AI Study Buddy, AI Search, and Creator Studio drafting** use Groq's `openai/gpt-oss-20b`; AI Search enables the built-in browser search tool. Search results and AI answers can still be incomplete or wrong. [Groq model and browser search docs](https://console.groq.com/docs/tool-use/built-in-tools/browser-search).
- Groq's free plan is rate-limited. Because every student shares this app's API key, a public app can use up its free quota; check the current limits before sharing widely. [Groq rate limits](https://console.groq.com/docs/rate-limits).
- Feedback is the final page in the student navigation. Every non-home page has a Back to home button.
- Click the hanging bulb at top-right to cycle through seven color themes: White, Dark, Blue, Purple, Amber, Rose, and Teal. The current theme name appears below the bulb.
- The student Home page places one pinned important notice in a box in the upper-right half, beside the date card.

Before a campus-wide launch, configure college email verification, protect Creator Studio credentials, review the access policies, and try the apps with separate student accounts. Never put private information in a public calendar or AI prompt.

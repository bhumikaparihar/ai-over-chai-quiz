# AI Over Chai — MCP Knowledge Challenge

<!--
Asset metadata
Client / Engagement: Internal — AI Over Chai webinar series
Status: Draft
Owner: Internal Events
Contains customer data: No
-->

A lightweight Streamlit quiz for the "AI Over Chai" internal webinar on MCP
(Model Context Protocol) and how Snowflake supports it. Participants scan a
QR code on the closing slide, take a 7-question quiz on their phone, and
their score is saved to Google Sheets for a lucky draw.

---

## 1. What's in this project

```text
AI_Over_Chai_Quiz/
│
├── app.py                  # The entire app
├── requirements.txt
├── README.md
├── get_refresh_token.py    # One-time local script — generates the OAuth refresh token (Section 5)
│
└── .streamlit/
    └── secrets.toml        # Example only — fill in your own, never commit real values
```

`oauth_client.json` (downloaded in Section 5.4) and a real, filled-in
`secrets.toml` also live in this folder once you're set up — neither is
included here, and neither should ever be committed to git.

---

## 2. Prerequisites

- Python 3.9 or later
- A Google account with access to Google Cloud Console and Google Sheets
- ~20–30 minutes for the Google Cloud setup (one-time)

---

## 3. Install dependencies

```bash
# 1. Move into the project folder
cd AI_Over_Chai_Quiz

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
# macOS / Linux:
source venv/bin/activate
# Windows (PowerShell):
venv\Scripts\Activate.ps1

# 4. Install requirements
pip install -r requirements.txt
```

---

## 4. Create the Google Sheet

1. Go to [Google Sheets](https://sheets.google.com) and create a new spreadsheet.
2. Rename it exactly to: `AI Over Chai Quiz Responses`
   (the app looks it up by this exact name).
3. You do **not** need to create the "Responses" tab or headers yourself —
   the app creates the worksheet and header row automatically on first run.
   If you'd rather set it up yourself, create a tab named `Responses` with
   this header row in row 1:

   ```text
   Timestamp | Name | Email | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 | Score | Total
   ```

---

## 5. Connect to Google Sheets (OAuth — no service-account key)

Some Google Cloud organizations enforce the `iam.disableServiceAccountKeyCreation`
policy, which blocks downloading a service-account JSON key entirely. This
app authenticates a different way as a result: it uses an **OAuth user
credential** — a one-time browser login that produces a long-lived refresh
token — instead of a service-account key. The refresh token goes in
`secrets.toml` exactly where a service-account key would have gone.
(An OAuth client ID is a different kind of credential from a service-account
key, so this policy doesn't block it.)

### 5.1 Create a Google Cloud project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one) — e.g. `ai-over-chai-quiz`.

### 5.2 Enable the required APIs

In the search bar, enable both:
- **Google Sheets API**
- **Google Drive API**

### 5.3 Configure the OAuth consent screen

1. Go to **APIs & Services → OAuth consent screen**.
2. **User type**: choose **Internal** if it's offered (it will be if your
   Cloud project belongs to a Google Workspace or Cloud Identity
   organization — likely, given the org policy above). Internal apps skip
   verification and test-user limits entirely. If Internal isn't offered,
   choose **External**.
3. Fill in the app name (e.g. "AI Over Chai Quiz"), your support email, and
   developer contact email → **Save and Continue**.
4. Add scopes: `.../auth/spreadsheets` and `.../auth/drive` → **Save and
   Continue**.
5. **External only**: add your own Google account (and anyone else who'll
   run the quiz) under **Test users** → **Save and Continue**.
6. **External only, important**: go back to the OAuth consent screen page
   and click **Publish App** to move it out of "Testing" status. Tokens
   issued while an External app is still in Testing status expire after
   **7 days** — publishing avoids that. You may see an "unverified app"
   warning the first time you authorize (Step 5.5) — since this is your
   own account authorizing your own small internal tool, it's fine to
   click **Advanced → Go to [app name] (unsafe)** to proceed. Internal
   apps never show this warning and don't need publishing.

### 5.4 Create an OAuth Client ID (Desktop app)

1. Go to **APIs & Services → Credentials → Create Credentials → OAuth
   client ID**.
2. **Application type**: **Desktop app**. Name it e.g. `quiz-local-auth` →
   **Create**.
3. Click **Download JSON**. Save it in your project folder as
   `oauth_client.json` — this is an OAuth client secret, not a
   service-account key, so it isn't blocked by your org's policy. Keep it
   private and never commit it.

### 5.5 Generate your refresh token (one-time, local)

This project includes `get_refresh_token.py` for exactly this step.

```bash
# with your venv still active, inside AI_Over_Chai_Quiz
pip install google-auth-oauthlib
python get_refresh_token.py
```

Your browser opens; sign in with the Google account that has (or will
have) Editor access to the `AI Over Chai Quiz Responses` sheet, and
approve access. The script prints a ready-to-paste `[gcp_oauth_credentials]`
block — copy it into `.streamlit/secrets.toml` (see 5.7).

`google-auth-oauthlib` is only needed for this one-time local step — it is
**not** in `requirements.txt` and is not needed by the deployed app.

### 5.6 Share the Google Sheet

Make sure the Google account you authorized in 5.5 has Editor access to
`AI Over Chai Quiz Responses`. If you created the sheet with that same
account, it already does. Otherwise, open the sheet, click **Share**,
add that account's email with **Editor** access.

### 5.7 Configure `.streamlit/secrets.toml`

Paste the block `get_refresh_token.py` printed into `.streamlit/secrets.toml`.
It should end up looking like this shape (placeholders shown — use your
real values locally, never here):

```toml
[gcp_oauth_credentials]
client_id = "YOUR_OAUTH_CLIENT_ID.apps.googleusercontent.com"
client_secret = "YOUR_OAUTH_CLIENT_SECRET"
refresh_token = "YOUR_REFRESH_TOKEN"
token_uri = "https://oauth2.googleapis.com/token"
```

Save the file, then stop and restart `streamlit run app.py` so it picks
up the new secrets.

**Never commit this file to a public git repository.** If deploying via
Streamlit Community Cloud, you'll paste these same values into the app's
"Secrets" settings instead of uploading the file (see deployment section).

---

## 6. Run the application locally

```bash
streamlit run app.py
```

Streamlit will print a local URL (usually `http://localhost:8501`). Open it
in your browser to test the full flow: welcome screen → 7 questions →
result screen → row appears in the Google Sheet.

To test the mobile layout locally, open the same local URL from your phone
if it's on the same Wi-Fi network (Streamlit will also print a "Network URL"
you can use), or resize your desktop browser window down to ~375px wide.

---

## 7. Deploy the application

The simplest option for a one-day turnaround is **Streamlit Community Cloud**:

1. Push this project to a GitHub repository (a **private** repo is fine).
   Make sure `.streamlit/secrets.toml` with real values is **not** committed —
   add it to `.gitignore` first.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   GitHub.
3. Click **New app**, select your repository, branch, and set the main file
   to `app.py`.
4. Before (or right after) deploying, open **App settings → Secrets** and
   paste in the full contents of your real `secrets.toml` (the
   `[gcp_oauth_credentials]` block with your actual values).
5. Deploy. You'll get a public URL like
   `https://your-app-name.streamlit.app` — this is what your QR code should
   point to.

Other options (Render, Railway, an internal server) work too — the only
requirement is that the Google OAuth credentials are supplied via Streamlit
secrets (or environment variables you adapt the code to read), never
hardcoded in `app.py`. Do not upload `oauth_client.json` or run
`get_refresh_token.py` anywhere but your own machine — the deployed app
only ever needs the four values already sitting in secrets.

---

## 8. Generate the QR code

Once you have the deployed URL, use any QR code generator (e.g.
[qr-code-generator.com](https://www.qr-code-generator.com/) or a Python
snippet with the `qrcode` package) to create a QR code pointing to it, and
add it to your final presentation slide.

---

## 9. Testing checklist before the webinar

- [ ] Fresh browser / incognito window: welcome screen loads correctly
- [ ] Submitting with an empty name shows an error and does not proceed
- [ ] Submitting with an empty email shows an error and does not proceed
- [ ] Submitting with an invalid email (no `@`, no domain) shows an error
- [ ] A brand-new email successfully starts the quiz
- [ ] The same email cannot start the quiz twice ("already submitted" message)
- [ ] Each question requires a selection before "Next"/"Submit" is enabled
- [ ] Progress bar and "Question X of 7" update correctly on every question
- [ ] Final score and percentage on the result screen are correct
  (cross-check against your known answer key)
- [ ] Exactly **one** new row appears in the Google Sheet per completed quiz
- [ ] Refreshing the browser mid-quiz or on the result screen does **not**
  create a duplicate row in the sheet
- [ ] Temporarily revoke the authorized account's sheet access (or rename
  the sheet) and confirm the app shows a friendly error instead of
  crashing or silently letting duplicates through
- [ ] Test the full flow on an actual phone (not just a resized browser),
  on both Wi-Fi and mobile data
- [ ] Confirm no stack traces, credentials, or file paths are ever shown
  to the participant
- [ ] Load test: have 3–5 people submit at roughly the same time and confirm
  all rows land correctly with no errors

---

## 10. Notes

- This is intentionally a single-file app (`app.py`) — there was no strong
  reason to split it up, and keeping it in one file makes it easier to
  review and debug in a single day.
- The quiz is beginner-friendly by design — it checks whether someone paid
  attention to the webinar, not deep MCP expertise.
- No login system, leaderboard, or admin dashboard is included, per the
  original scope — the Google Sheet itself is the "admin view" for the
  lucky draw.
- The Google Sheets connection uses an OAuth refresh token tied to a real
  Google account, not a service-account key, because this Google Cloud
  organization's `iam.disableServiceAccountKeyCreation` policy blocks
  downloadable service-account keys. If the OAuth consent screen was left
  in "Testing" status (Section 5.3, External apps only), the refresh token
  expires after 7 days and the app will start showing "couldn't verify
  your submission" until you rerun `get_refresh_token.py` and update
  secrets — publishing the app (or using an Internal consent screen)
  avoids this.
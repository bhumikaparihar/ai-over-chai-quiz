# =============================================================================
# Claroda — AI Over Chai
# Asset: MCP Knowledge Challenge (Streamlit quiz app)
# Status: Draft
# Owner: Internal Events / AI Over Chai
# Purpose: Post-webinar live quiz, captured to Google Sheets for a lucky draw.
# Contains no customer or contract data — internal-audience use only.
# Note: Google Sheets auth uses an OAuth user refresh token, not a
# service-account key, per this org's iam.disableServiceAccountKeyCreation
# policy. See get_refresh_token.py and README.md.
# =============================================================================

import random
import re
from datetime import datetime

import streamlit as st

try:
    import gspread
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


# -----------------------------------------------------------------------------
# App config
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="MCP Knowledge Challenge | AI Over Chai",
    page_icon="☕",
    layout="centered",
    initial_sidebar_state="collapsed",
)

SPREADSHEET_NAME = "AI Over Chai Quiz Responses"
WORKSHEET_NAME = "Responses"
SHEET_HEADER = ["Timestamp", "Name", "Email", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Score", "Total"]

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# -----------------------------------------------------------------------------
# Quiz content
# -----------------------------------------------------------------------------
QUESTIONS = [
    {
        "question": "What does MCP stand for?",
        "options": [
            "Model Context Protocol",
            "Machine Control Program",
            "Model Computing Platform",
            "Machine Context Process",
        ],
        "correct": 0,
    },
    {
        "question": "What is the main purpose of MCP?",
        "options": [
            "To connect AI applications with tools and data",
            "To train AI models",
            "To create websites",
            "To store images",
        ],
        "correct": 0,
    },
    {
        "question": "In simple words, what does an MCP server provide to an AI application?",
        "options": [
            "Tools and data that the AI can use",
            "A new AI model",
            "A computer monitor",
            "Internet speed",
        ],
        "correct": 0,
    },
    {
        "question": "Which of these can an MCP server connect an AI application to?",
        "options": [
            "External tools and data sources",
            "Only a keyboard",
            "Only a web browser",
            "Only an email account",
        ],
        "correct": 0,
    },
    {
        "question": "What is one benefit of MCP?",
        "options": [
            "It provides a standard way for AI to interact with tools",
            "It makes computers faster",
            "It removes the need for data",
            "It automatically trains an AI model",
        ],
        "correct": 0,
    },
    {
        "question": "What does Snowflake's Managed MCP Server help AI applications do?",
        "options": [
            "Interact with Snowflake capabilities through MCP",
            "Replace Snowflake completely",
            "Build a new programming language",
            "Increase internet speed",
        ],
        "correct": 0,
    },
    {
        "question": "In a banking AI assistant, MCP could help the AI:",
        "options": [
            "Access approved banking data and tools to answer questions",
            "Automatically approve loans",
            "Replace all bank employees",
            "Access any banking data without permission",
        ],
        "correct": 0,
    },
]

TOTAL_QUESTIONS = len(QUESTIONS)

# NOTE: In the source question list, the correct answer is always the first
# option. If shown in that fixed order, participants could tell each other
# "always pick the first option" during a live webinar. To prevent that,
# each participant gets their own shuffled option order, generated once when
# they start the quiz and kept stable in session_state for the rest of their
# attempt (so navigating forward never reshuffles an already-seen question).


def build_shuffled_questions():
    """Returns a fresh, per-participant shuffled copy of QUESTIONS."""
    shuffled = []
    for q in QUESTIONS:
        order = list(range(len(q["options"])))
        random.shuffle(order)
        shuffled.append(
            {
                "question": q["question"],
                "options": [q["options"][i] for i in order],
                "correct": order.index(q["correct"]),
            }
        )
    return shuffled


# -----------------------------------------------------------------------------
# Styling — Claroda dark / cyan theme
# -----------------------------------------------------------------------------
def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');

        :root {
            --c-deep: #041120;
            --c-teal: #017793;
            --c-blue: #1c8fb3;
            --c-sky: #2aa2d8;
            --c-pale: #acd4e4;
            --c-cyan: #00d4ff;
        }

        html, body, [class*="css"] {
            font-family: 'DM Sans', sans-serif;
        }

        .stApp {
            background: radial-gradient(circle at 20% 0%, #0a2338 0%, var(--c-deep) 55%) fixed;
            color: #eaf6fb;
        }

        #MainMenu, footer, header {visibility: hidden;}

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 640px;
        }

        .chai-badge {
            display: inline-block;
            padding: 0.3rem 0.9rem;
            border-radius: 999px;
            border: 1px solid var(--c-cyan);
            color: var(--c-cyan);
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 1rem;
        }

        .chai-title {
            font-size: 2.1rem;
            font-weight: 800;
            line-height: 1.15;
            background: linear-gradient(90deg, var(--c-cyan), var(--c-sky) 60%, var(--c-pale));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.4rem;
        }

        .chai-subtitle {
            color: var(--c-pale);
            font-size: 1.02rem;
            line-height: 1.5;
            margin-bottom: 1.4rem;
        }

        .chai-card {
            background: linear-gradient(160deg, rgba(28,143,179,0.14), rgba(4,17,32,0.35));
            border: 1px solid rgba(0,212,255,0.25);
            border-radius: 18px;
            padding: 1.4rem 1.3rem;
            box-shadow: 0 8px 30px rgba(0,0,0,0.35);
            margin-bottom: 1.2rem;
        }

        .chai-pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0.8rem 0 0.2rem 0;
        }

        .chai-pill {
            background: rgba(0,212,255,0.10);
            border: 1px solid rgba(0,212,255,0.35);
            color: var(--c-pale);
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
        }

        .qcounter {
            color: var(--c-cyan);
            font-weight: 700;
            letter-spacing: 0.08em;
            font-size: 0.85rem;
            text-transform: uppercase;
            margin-bottom: 0.4rem;
        }

        .qtext {
            font-size: 1.3rem;
            font-weight: 700;
            line-height: 1.4;
            color: #f4fbfd;
            margin-bottom: 0.2rem;
        }

        .progress-track {
            width: 100%;
            height: 10px;
            border-radius: 999px;
            background: rgba(255,255,255,0.08);
            overflow: hidden;
            margin: 0.6rem 0 1.4rem 0;
        }

        .progress-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, var(--c-teal), var(--c-cyan));
            transition: width 0.35s ease;
        }

        div.stButton > button {
            width: 100%;
            background: linear-gradient(90deg, var(--c-teal), var(--c-sky));
            color: white;
            font-weight: 700;
            font-size: 1.02rem;
            padding: 0.75rem 1rem;
            border-radius: 14px;
            border: none;
            box-shadow: 0 6px 18px rgba(0,212,255,0.25);
            transition: transform 0.12s ease, box-shadow 0.12s ease;
        }
        div.stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 8px 22px rgba(0,212,255,0.4);
            color: white;
        }
        div.stButton > button:active {
            transform: translateY(0px);
        }
        div.stButton > button:disabled {
            background: rgba(255,255,255,0.08);
            color: rgba(255,255,255,0.35);
            box-shadow: none;
        }

        div[data-testid="stRadio"] > label {
            display: none;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] > label {
            background: rgba(255,255,255,0.04);
            border: 1.5px solid rgba(172,212,228,0.25);
            border-radius: 14px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.6rem;
            width: 100%;
            font-size: 1.02rem;
            transition: border-color 0.15s ease, background 0.15s ease;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
            border-color: var(--c-cyan);
            background: rgba(0,212,255,0.06);
        }

        .stTextInput > div > div > input {
            background: rgba(255,255,255,0.05);
            border: 1.5px solid rgba(172,212,228,0.25);
            border-radius: 12px;
            color: #eaf6fb;
            padding: 0.7rem 0.9rem;
        }
        .stTextInput > div > div > input:focus {
            border-color: var(--c-cyan);
            box-shadow: 0 0 0 1px var(--c-cyan);
        }
        .stTextInput label {
            color: var(--c-pale) !important;
            font-weight: 600;
        }

        .score-big {
            font-size: 3.2rem;
            font-weight: 800;
            text-align: center;
            background: linear-gradient(90deg, var(--c-cyan), var(--c-pale));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0.4rem 0 0 0;
        }
        .score-pct {
            text-align: center;
            color: var(--c-pale);
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.6rem;
        }
        .score-msg {
            text-align: center;
            font-size: 1.15rem;
            font-weight: 700;
            color: #f4fbfd;
            margin: 0.6rem 0 1rem 0;
        }
        .score-footer {
            text-align: center;
            color: var(--c-pale);
            font-size: 0.95rem;
            line-height: 1.6;
        }

        .stAlert {
            border-radius: 14px;
        }

        @media (max-width: 480px) {
            .chai-title { font-size: 1.65rem; }
            .qtext { font-size: 1.12rem; }
            .score-big { font-size: 2.6rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Google Sheets helpers
# -----------------------------------------------------------------------------
class SheetsUnavailableError(Exception):
    """Raised when Google Sheets cannot be reached or is misconfigured."""


@st.cache_resource(show_spinner=False)
def get_worksheet():
    """
    Returns a gspread Worksheet handle. Cached for the life of the app
    process so we don't re-authenticate on every rerun.
    Raises SheetsUnavailableError on any failure — callers must handle it
    explicitly rather than assuming success.

    Authentication note: this uses an OAuth *user* credential (a refresh
    token tied to a real Google account) rather than a downloadable
    service-account key, because some Google Cloud organizations disable
    service-account key creation via the `iam.disableServiceAccountKeyCreation`
    org policy. See README.md / get_refresh_token.py for how the refresh
    token in secrets is generated (one-time, local, never in this repo).
    """
    if not GSPREAD_AVAILABLE:
        raise SheetsUnavailableError("gspread/google-auth are not installed.")

    try:
        oauth_creds = st.secrets["gcp_oauth_credentials"]
    except Exception as exc:
        raise SheetsUnavailableError("Google OAuth secrets are missing.") from exc

    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials(
            token=None,
            refresh_token=oauth_creds["refresh_token"],
            token_uri=oauth_creds.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=oauth_creds["client_id"],
            client_secret=oauth_creds["client_secret"],
            scopes=scopes,
        )
        # Force an immediate refresh so a bad/expired/revoked refresh token
        # fails clearly here, rather than surfacing as a confusing error
        # deep inside the first Sheets API call.
        credentials.refresh(Request())
        client = gspread.authorize(credentials)
    except Exception as exc:
        raise SheetsUnavailableError("Could not authenticate with Google.") from exc

    try:
        spreadsheet = client.open(SPREADSHEET_NAME)
    except Exception as exc:
        raise SheetsUnavailableError(
            f"Could not open the spreadsheet '{SPREADSHEET_NAME}'."
        ) from exc

    try:
        try:
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=len(SHEET_HEADER))
            worksheet.append_row(SHEET_HEADER)
        # Make sure header exists if worksheet was created empty by hand.
        first_row = worksheet.row_values(1)
        if first_row != SHEET_HEADER:
            if not first_row:
                worksheet.append_row(SHEET_HEADER)
    except Exception as exc:
        raise SheetsUnavailableError("Could not access the 'Responses' worksheet.") from exc

    return worksheet


def email_already_submitted(worksheet, email: str) -> bool:
    """
    Returns True only if we positively confirmed the email exists.
    Raises SheetsUnavailableError on any read failure — the caller must NOT
    treat a failed check as "email is new".
    """
    try:
        email_col = worksheet.col_values(3)  # Column C = Email
    except Exception as exc:
        raise SheetsUnavailableError("Could not verify prior submissions.") from exc

    email_norm = email.strip().lower()
    existing = {e.strip().lower() for e in email_col[1:]}  # skip header
    return email_norm in existing


def append_submission(worksheet, name: str, email: str, answer_labels: list, score: int, total: int):
    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        name.strip(),
        email.strip().lower(),
        *answer_labels,
        score,
        total,
    ]
    try:
        worksheet.append_row(row, value_input_option="USER_ENTERED")
    except Exception as exc:
        raise SheetsUnavailableError("Could not save your response.") from exc


# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
def init_state():
    defaults = {
        "stage": "welcome",       # welcome -> quiz -> result
        "name": "",
        "email": "",
        "q_index": 0,
        "answers": [None] * TOTAL_QUESTIONS,   # selected option index per question
        "score": 0,
        "submitted_to_sheets": False,
        "start_error": None,
        "quiz_questions": None,   # set to a shuffled copy of QUESTIONS on start
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_quiz():
    st.session_state.stage = "welcome"
    st.session_state.name = ""
    st.session_state.email = ""
    st.session_state.q_index = 0
    st.session_state.answers = [None] * TOTAL_QUESTIONS
    st.session_state.score = 0
    st.session_state.submitted_to_sheets = False
    st.session_state.start_error = None
    st.session_state.quiz_questions = None


# -----------------------------------------------------------------------------
# Screens
# -----------------------------------------------------------------------------
def render_header(badge_text="CLARODA • AI OVER CHAI"):
    st.markdown(f'<div class="chai-badge">{badge_text}</div>', unsafe_allow_html=True)


def render_welcome():
    render_header()
    st.markdown('<div class="chai-title">MCP Knowledge Challenge</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="chai-subtitle">Think you were paying attention? ☕<br>'
        "Put your MCP knowledge to the test.</div>",
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown('<div class="chai-card">', unsafe_allow_html=True)
        name = st.text_input("Your name", value=st.session_state.name, placeholder="e.g. Aditi Sharma")
        email = st.text_input("Email", value=st.session_state.email, placeholder="e.g. aditi@gmail.com")
        st.markdown(
            f'<div class="chai-pill-row">'
            f'<span class="chai-pill">🧠 {TOTAL_QUESTIONS} Questions</span>'
            f'<span class="chai-pill">🌱 Beginner Friendly</span>'
            f'<span class="chai-pill">🎁 Lucky Draw Entry</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        start_clicked = st.button("START CHALLENGE →", key="start_btn")

    if st.session_state.start_error:
        st.error(st.session_state.start_error)

    if start_clicked:
        name_clean = name.strip()
        email_clean = email.strip().lower()

        if not name_clean:
            st.session_state.start_error = "Please enter your name to continue."
        elif not email_clean:
            st.session_state.start_error = "Please enter your work email to continue."
        elif not EMAIL_REGEX.match(email_clean):
            st.session_state.start_error = "That email address doesn't look right. Please check it."
        else:
            try:
                worksheet = get_worksheet()
                already_done = email_already_submitted(worksheet, email_clean)
            except SheetsUnavailableError:
                st.session_state.start_error = (
                    "We couldn't verify your submission right now. Please try again in a moment."
                )
            else:
                if already_done:
                    st.session_state.start_error = "This email has already submitted the quiz."
                else:
                    st.session_state.name = name_clean
                    st.session_state.email = email_clean
                    st.session_state.start_error = None
                    st.session_state.stage = "quiz"
                    st.session_state.q_index = 0
                    st.session_state.answers = [None] * TOTAL_QUESTIONS
                    st.session_state.quiz_questions = build_shuffled_questions()
                    st.rerun()
        if st.session_state.start_error:
            st.rerun()


def render_quiz():
    idx = st.session_state.q_index
    if not st.session_state.quiz_questions:
        # Defensive fallback — should not normally happen, but guarantees
        # the app never crashes if state was somehow reset mid-quiz.
        st.session_state.quiz_questions = build_shuffled_questions()
    question = st.session_state.quiz_questions[idx]
    progress_pct = int(((idx) / TOTAL_QUESTIONS) * 100)

    render_header()
    st.markdown(f'<div class="qcounter">Question {idx + 1} of {TOTAL_QUESTIONS}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="progress-track"><div class="progress-fill" style="width:{progress_pct}%;"></div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="chai-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="qtext">{question["question"]}</div>', unsafe_allow_html=True)

    current_answer = st.session_state.answers[idx]
    selected = st.radio(
        label="options",
        options=list(range(len(question["options"]))),
        format_func=lambda i: question["options"][i],
        index=current_answer if current_answer is not None else None,
        key=f"radio_q{idx}",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.session_state.answers[idx] = selected

    is_last = idx == TOTAL_QUESTIONS - 1
    button_label = "SUBMIT QUIZ ✓" if is_last else "NEXT QUESTION →"
    disabled = selected is None

    if st.button(button_label, key=f"next_btn_{idx}", disabled=disabled):
        if not is_last:
            st.session_state.q_index += 1
            st.rerun()
        else:
            finalize_quiz()
            st.rerun()

    if disabled:
        st.caption("Select an answer to continue.")


def finalize_quiz():
    """Compute score and persist to Google Sheets exactly once."""
    score = 0
    answer_labels = []
    questions = st.session_state.quiz_questions or QUESTIONS
    for i, q in enumerate(questions):
        chosen = st.session_state.answers[i]
        if chosen == q["correct"]:
            score += 1
        answer_labels.append(q["options"][chosen] if chosen is not None else "")

    st.session_state.score = score

    if not st.session_state.submitted_to_sheets:
        try:
            worksheet = get_worksheet()
            # Re-check duplicate right before writing, in case of a race
            # between two tabs / a page refresh during a live webinar.
            if not email_already_submitted(worksheet, st.session_state.email):
                append_submission(
                    worksheet,
                    st.session_state.name,
                    st.session_state.email,
                    answer_labels,
                    score,
                    TOTAL_QUESTIONS,
                )
            st.session_state.submitted_to_sheets = True
            st.session_state.save_error = None
        except SheetsUnavailableError:
            st.session_state.save_error = (
                "We couldn't save your response right now. Please screenshot your score "
                "and let the organizers know."
            )

    st.session_state.stage = "result"


def render_result():
    score = st.session_state.score
    pct = int(round((score / TOTAL_QUESTIONS) * 100))

    render_header()
    st.markdown('<div class="chai-title">You\'re All Done! 🎉</div>', unsafe_allow_html=True)

    st.markdown('<div class="chai-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="score-big">{score} / {TOTAL_QUESTIONS}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="score-pct">{pct}%</div>', unsafe_allow_html=True)

    if pct == 100:
        message = "MCP Master! 🔥"
    elif pct >= 70:
        message = "Great job! You clearly understood the MCP basics."
    elif pct >= 50:
        message = "Nice attempt! You picked up the key ideas."
    else:
        message = "Thanks for playing along — MCP takes a little getting used to!"

    st.markdown(f'<div class="score-msg">{message}</div>', unsafe_allow_html=True)

    if st.session_state.get("save_error"):
        st.warning(st.session_state.save_error)
    else:
        st.markdown(
            '<div class="score-footer">Your response has been recorded.<br>'
            "Good luck in the lucky draw! ☕</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    init_state()
    inject_css()

    try:
        if st.session_state.stage == "welcome":
            render_welcome()
        elif st.session_state.stage == "quiz":
            render_quiz()
        elif st.session_state.stage == "result":
            render_result()
        else:
            reset_quiz()
            st.rerun()
    except Exception:
        # Never leak stack traces / internals to a live webinar audience.
        st.error("Something went wrong. Please refresh the page and try again.")


if __name__ == "__main__":
    main()
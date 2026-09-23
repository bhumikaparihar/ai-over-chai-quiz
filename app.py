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
    page_title="MCP Knowledge Quiz | AI Over Chai",
    page_icon="☕",
    layout="centered",
    initial_sidebar_state="collapsed",
)

SPREADSHEET_NAME = "AI Over Chai Quiz Responses"
WORKSHEET_NAME = "Responses"

SHEET_HEADER = [
    "Timestamp",
    "Name",
    "Email",
    "Q1",
    "Q2",
    "Q3",
    "Q4",
    "Q5",
    "Q6",
    "Q7",
    "Score",
    "Total",
]

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


# NOTE:
# The correct answer is always the first option in the source question list.
# We shuffle the options separately for each participant so that participants
# cannot simply choose the first option every time.
def build_shuffled_questions():
    """Return a fresh, per-participant shuffled copy of QUESTIONS."""
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
# Styling — fixed Claroda light theme
# -----------------------------------------------------------------------------
def inject_css():
    st.markdown(
        """
        <style>

        /* ================================================================
           GLOBAL THEME
           Everything below is explicitly styled so Streamlit/browser
           light or dark mode does not change text visibility.
           ================================================================ */

        @import url(
            'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap'
        );

        :root {
            --c-bg: #f4f9fc;
            --c-navy: #12345b;
            --c-deep: #0b2948;
            --c-teal: #017793;
            --c-sky: #2aa2d8;
            --c-cyan: #00a9d6;
            --c-pale-blue: #e5f3fa;
            --c-border: #cfe3ee;
            --c-muted: #58718a;
            --c-white: #ffffff;
        }

        html,
        body,
        [class*="css"] {
            font-family: 'DM Sans', sans-serif;
        }

        html,
        body,
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"] {
            background: #f4f9fc !important;
        }

        .stApp {
            background:
                radial-gradient(
                    circle at 0% 0%,
                    rgba(42, 162, 216, 0.10) 0%,
                    transparent 28%
                ),
                radial-gradient(
                    circle at 100% 45%,
                    rgba(1, 119, 147, 0.07) 0%,
                    transparent 25%
                ),
                #f4f9fc !important;

            color: #12345b !important;
        }

        /* Force the main app text to remain dark */
        .stApp,
        .stApp * {
            font-family: 'DM Sans', sans-serif;
        }

        /* Hide Streamlit chrome */
        #MainMenu,
        footer,
        header {
            visibility: hidden;
        }

        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 3rem;
            max-width: 760px;
        }


        /* ================================================================
           CLARODA LOGO
           ================================================================ */

        .claroda-logo {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 0.35rem;
        }

        .claroda-logo img {
            max-height: 58px;
            width: auto;
            object-fit: contain;
        }


        /* ================================================================
           EVENT HEADER
           ================================================================ */

        .event-label {
            text-align: center;
            color: #00a9d6 !important;
            -webkit-text-fill-color: #00a9d6 !important;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            margin-bottom: 0.85rem;
        }

        .chai-title {
            text-align: center;
            font-size: 2.25rem;
            font-weight: 800;
            line-height: 1.15;

            color: #12345b !important;
            -webkit-text-fill-color: #12345b !important;

            margin-bottom: 0.45rem;
        }

        .chai-subtitle {
            text-align: center;

            color: #58718a !important;
            -webkit-text-fill-color: #58718a !important;

            font-size: 1rem;
            line-height: 1.55;
            margin-bottom: 1.5rem;
        }


        /* ================================================================
           CARDS
           ================================================================ */

        .chai-card {
            background: #ffffff !important;
            border: 1px solid #cfe3ee !important;
            border-radius: 18px;
            padding: 1.45rem 1.4rem;
            box-shadow: 0 8px 28px rgba(18, 52, 91, 0.08);
            margin-bottom: 1.2rem;

            color: #12345b !important;
        }


        /* ================================================================
           PILLS
           ================================================================ */

        .chai-pill-row {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin: 1rem 0 0.2rem 0;
        }

        .chai-pill {
            background: #e5f3fa !important;
            border: 1px solid #b9dceb !important;

            color: #12345b !important;
            -webkit-text-fill-color: #12345b !important;

            padding: 0.38rem 0.8rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
        }


        /* ================================================================
           QUIZ COUNTER
           ================================================================ */

        .qcounter {
            color: #017793 !important;
            -webkit-text-fill-color: #017793 !important;

            font-weight: 800;
            letter-spacing: 0.08em;
            font-size: 0.85rem;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }


        /* ================================================================
           PROGRESS BAR
           ================================================================ */

        .progress-track {
            width: 100%;
            height: 9px;
            border-radius: 999px;
            background: #dceaf2 !important;
            overflow: hidden;
            margin: 0.5rem 0 1.35rem 0;
        }

        .progress-fill {
            height: 100%;
            border-radius: 999px;

            background: linear-gradient(
                90deg,
                #017793,
                #2aa2d8
            ) !important;

            transition: width 0.35s ease;
        }


        /* ================================================================
           QUESTION TEXT
           ================================================================ */

        .qtext {
            font-size: 1.35rem;
            font-weight: 800;
            line-height: 1.4;

            color: #12345b !important;
            -webkit-text-fill-color: #12345b !important;

            margin-bottom: 0.8rem;
        }


        /* ================================================================
           TEXT INPUTS
           Explicit light background + dark text.
           ================================================================ */

        .stTextInput > div > div > input {
            background: #ffffff !important;

            border: 1.5px solid #c9dce7 !important;
            border-radius: 11px;

            color: #12345b !important;
            -webkit-text-fill-color: #12345b !important;

            padding: 0.7rem 0.9rem;

            caret-color: #12345b !important;
        }

        .stTextInput > div > div > input::placeholder {
            color: #8aa1b2 !important;
            -webkit-text-fill-color: #8aa1b2 !important;
            opacity: 1 !important;
        }

        .stTextInput > div > div > input:focus {
            border-color: #2aa2d8 !important;
            box-shadow: 0 0 0 1px #2aa2d8 !important;
        }

        .stTextInput label {
            color: #12345b !important;
            -webkit-text-fill-color: #12345b !important;

            font-weight: 700;
        }

        .stTextInput label *,
        .stTextInput label p,
        .stTextInput label span {
            color: #12345b !important;
            -webkit-text-fill-color: #12345b !important;
        }


        /* ================================================================
           RADIO OPTIONS
           
           This is the most important fix.

           Streamlit's radio widget contains nested elements whose colors
           can be changed by the active Streamlit/browser theme. We force
           every nested element to dark navy.
           ================================================================ */

        /* Hide Streamlit's default radio widget label */
        div[data-testid="stRadio"] > label {
            display: none !important;
        }

        /* Radio group */
        div[data-testid="stRadio"] div[role="radiogroup"] {
            display: flex !important;
            flex-direction: column !important;
            gap: 0 !important;
        }

        /* Individual option */
        div[data-testid="stRadio"]
        div[role="radiogroup"]
        > label {
            background: #ffffff !important;

            border: 1.5px solid #c9dce7 !important;
            border-radius: 12px !important;

            padding: 0.85rem 1rem !important;
            margin-bottom: 0.6rem !important;

            width: 100% !important;

            color: #12345b !important;
            -webkit-text-fill-color: #12345b !important;

            font-size: 1rem !important;
            font-weight: 500 !important;

            box-sizing: border-box !important;

            transition:
                border-color 0.15s ease,
                background 0.15s ease,
                box-shadow 0.15s ease;
        }

        /* Force every nested text element inside the option to dark navy */
        div[data-testid="stRadio"]
        div[role="radiogroup"]
        > label,

        div[data-testid="stRadio"]
        div[role="radiogroup"]
        > label *,

        div[data-testid="stRadio"]
        div[role="radiogroup"]
        > label p,

        div[data-testid="stRadio"]
        div[role="radiogroup"]
        > label span,

        div[data-testid="stRadio"]
        div[role="radiogroup"]
        > label div,

        div[data-testid="stRadio"]
        div[role="radiogroup"]
        > label [data-testid] {
            color: #12345b !important;
            -webkit-text-fill-color: #12345b !important;
        }

        /* Option hover */
        div[data-testid="stRadio"]
        div[role="radiogroup"]
        > label:hover {
            background: #f4fbfe !important;
            border-color: #2aa2d8 !important;

            box-shadow: 0 2px 8px rgba(18, 52, 91, 0.05);
        }

        /* Selected option */
        div[data-testid="stRadio"]
        div[role="radiogroup"]
        > label[data-checked="true"] {
            background: #e5f3fa !important;
            border-color: #017793 !important;
        }

        /* Radio circle */
        div[data-testid="stRadio"] input {
            accent-color: #017793 !important;
        }


        /* ================================================================
           BUTTONS
           ================================================================ */

        div.stButton > button {
            width: 100%;

            background: linear-gradient(
                90deg,
                #017793,
                #2aa2d8
            ) !important;

            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;

            font-weight: 700;
            font-size: 1rem;

            padding: 0.75rem 1rem;
            border-radius: 13px;
            border: none;

            box-shadow: 0 6px 18px rgba(0, 169, 214, 0.20);

            transition:
                transform 0.12s ease,
                box-shadow 0.12s ease;
        }

        div.stButton > button *,
        div.stButton > button p,
        div.stButton > button span {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        div.stButton > button:hover {
            transform: translateY(-1px);

            box-shadow:
                0 8px 22px rgba(0, 169, 214, 0.28);

            color: #ffffff !important;
        }

        div.stButton > button:disabled {
            background: #dbe7ed !important;

            color: #6f8492 !important;
            -webkit-text-fill-color: #6f8492 !important;

            box-shadow: none;
        }


        /* ================================================================
           CAPTIONS / SMALL TEXT
           ================================================================ */

        .welcome-note {
            text-align: center;

            color: #58718a !important;
            -webkit-text-fill-color: #58718a !important;

            font-size: 0.82rem;
            margin-top: 0.75rem;
        }

        div[data-testid="stCaptionContainer"],
        div[data-testid="stCaptionContainer"] * {
            color: #58718a !important;
            -webkit-text-fill-color: #58718a !important;
        }


        /* ================================================================
           ALERTS
           ================================================================ */

        .stAlert {
            border-radius: 12px;
        }


        /* ================================================================
           RESULT SCREEN
           ================================================================ */

        .score-big {
            font-size: 3.2rem;
            font-weight: 800;
            text-align: center;

            color: #12345b !important;
            -webkit-text-fill-color: #12345b !important;

            margin: 0.4rem 0 0 0;
        }

        .score-pct {
            text-align: center;

            color: #017793 !important;
            -webkit-text-fill-color: #017793 !important;

            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.6rem;
        }

        .score-msg {
            text-align: center;
            font-size: 1.15rem;
            font-weight: 700;

            color: #12345b !important;
            -webkit-text-fill-color: #12345b !important;

            margin: 0.6rem 0 1rem 0;
        }

        .score-footer {
            text-align: center;

            color: #58718a !important;
            -webkit-text-fill-color: #58718a !important;

            font-size: 0.95rem;
            line-height: 1.6;
        }


        /* ================================================================
           MOBILE
           ================================================================ */

        @media (max-width: 480px) {

            .block-container {
                padding-top: 1.25rem;
            }

            .claroda-logo img {
                max-height: 48px;
            }

            .chai-title {
                font-size: 1.7rem;
            }

            .chai-subtitle {
                font-size: 0.94rem;
            }

            .qtext {
                font-size: 1.15rem;
            }

            .score-big {
                font-size: 2.6rem;
            }

            .chai-card {
                padding: 1.15rem 1rem;
            }

            div[data-testid="stRadio"]
            div[role="radiogroup"]
            > label {
                font-size: 0.94rem !important;
                padding: 0.78rem 0.85rem !important;
            }
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
    Returns a gspread Worksheet handle.

    Authentication uses an OAuth user credential rather than a service-account
    key because some Google Cloud organizations disable service-account key
    creation.
    """
    if not GSPREAD_AVAILABLE:
        raise SheetsUnavailableError(
            "gspread/google-auth are not installed."
        )

    try:
        oauth_creds = st.secrets["gcp_oauth_credentials"]
    except Exception as exc:
        raise SheetsUnavailableError(
            "Google OAuth secrets are missing."
        ) from exc

    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        credentials = Credentials(
            token=None,
            refresh_token=oauth_creds["refresh_token"],
            token_uri=oauth_creds.get(
                "token_uri",
                "https://oauth2.googleapis.com/token",
            ),
            client_id=oauth_creds["client_id"],
            client_secret=oauth_creds["client_secret"],
            scopes=scopes,
        )

        credentials.refresh(Request())
        client = gspread.authorize(credentials)

    except Exception as exc:
        raise SheetsUnavailableError(
            "Could not authenticate with Google."
        ) from exc

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
            worksheet = spreadsheet.add_worksheet(
                title=WORKSHEET_NAME,
                rows=1000,
                cols=len(SHEET_HEADER),
            )

            worksheet.append_row(SHEET_HEADER)

        first_row = worksheet.row_values(1)

        if first_row != SHEET_HEADER:
            if not first_row:
                worksheet.append_row(SHEET_HEADER)

    except Exception as exc:
        raise SheetsUnavailableError(
            "Could not access the 'Responses' worksheet."
        ) from exc

    return worksheet


def email_already_submitted(worksheet, email: str) -> bool:
    """
    Return True only if the email was positively confirmed in the sheet.
    """
    try:
        email_col = worksheet.col_values(3)

    except Exception as exc:
        raise SheetsUnavailableError(
            "Could not verify prior submissions."
        ) from exc

    email_norm = email.strip().lower()

    existing = {
        e.strip().lower()
        for e in email_col[1:]
    }

    return email_norm in existing


def append_submission(
    worksheet,
    name: str,
    email: str,
    answer_labels: list,
    score: int,
    total: int,
):
    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        name.strip(),
        email.strip().lower(),
        *answer_labels,
        score,
        total,
    ]

    try:
        worksheet.append_row(
            row,
            value_input_option="USER_ENTERED",
        )

    except Exception as exc:
        raise SheetsUnavailableError(
            "Could not save your response."
        ) from exc


# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
def init_state():
    defaults = {
        "stage": "welcome",
        "name": "",
        "email": "",
        "q_index": 0,
        "answers": [None] * TOTAL_QUESTIONS,
        "score": 0,
        "submitted_to_sheets": False,
        "start_error": None,
        "quiz_questions": None,
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
def render_header():
    st.markdown(
        '<div class="claroda-logo">',
        unsafe_allow_html=True,
    )

    st.image(
        "assets/claroda_logo.png",
        width=170,
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="event-label">AI OVER CHAI</div>',
        unsafe_allow_html=True,
    )


def render_welcome():
    render_header()

    st.markdown(
        '<div class="chai-title">MCP Knowledge Quiz</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="chai-subtitle">'
        "Let's see what you remember from today's session.<br>"
        "7 quick questions based on the webinar."
        "</div>",
        unsafe_allow_html=True,
    )

    with st.container():

        st.markdown(
            '<div class="chai-card">',
            unsafe_allow_html=True,
        )

        name = st.text_input(
            "Your name",
            value=st.session_state.name,
            placeholder="e.g. Aditi Sharma",
        )

        email = st.text_input(
            "Work email",
            value=st.session_state.email,
            placeholder="e.g. aditi@claroda.com",
        )

        st.markdown(
            f'<div class="chai-pill-row">'
            f'<span class="chai-pill">{TOTAL_QUESTIONS} Questions</span>'
            f'<span class="chai-pill">Beginner Friendly</span>'
            f'<span class="chai-pill">Lucky Draw Entry</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

        start_clicked = st.button(
            "START QUIZ →",
            key="start_btn",
        )

        st.markdown(
            '<div class="welcome-note">'
            "One submission per email address."
            "</div>",
            unsafe_allow_html=True,
        )

    if st.session_state.start_error:
        st.error(st.session_state.start_error)

    if start_clicked:

        name_clean = name.strip()
        email_clean = email.strip().lower()

        if not name_clean:

            st.session_state.start_error = (
                "Please enter your name to continue."
            )

        elif not email_clean:

            st.session_state.start_error = (
                "Please enter your work email to continue."
            )

        elif not EMAIL_REGEX.match(email_clean):

            st.session_state.start_error = (
                "That email address doesn't look right. "
                "Please check it."
            )

        else:

            try:
                worksheet = get_worksheet()

                already_done = email_already_submitted(
                    worksheet,
                    email_clean,
                )

            except SheetsUnavailableError:

                st.session_state.start_error = (
                    "We couldn't verify your submission right now. "
                    "Please try again in a moment."
                )

            else:

                if already_done:

                    st.session_state.start_error = (
                        "This email has already submitted the quiz."
                    )

                else:

                    st.session_state.name = name_clean
                    st.session_state.email = email_clean
                    st.session_state.start_error = None
                    st.session_state.stage = "quiz"
                    st.session_state.q_index = 0
                    st.session_state.answers = [
                        None
                    ] * TOTAL_QUESTIONS

                    st.session_state.quiz_questions = (
                        build_shuffled_questions()
                    )

                    st.rerun()

        if st.session_state.start_error:
            st.rerun()


def render_quiz():

    idx = st.session_state.q_index

    if not st.session_state.quiz_questions:
        st.session_state.quiz_questions = (
            build_shuffled_questions()
        )

    question = st.session_state.quiz_questions[idx]

    # Show progress for the current question.
    # Q1 = approximately 14%, Q7 = 100%.
    progress_pct = int(
        ((idx + 1) / TOTAL_QUESTIONS) * 100
    )

    render_header()

    st.markdown(
        f'<div class="qcounter">'
        f"Question {idx + 1} of {TOTAL_QUESTIONS}"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="progress-track">'
        f'<div class="progress-fill" '
        f'style="width:{progress_pct}%;"></div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="chai-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="qtext">'
        f'{question["question"]}'
        f"</div>",
        unsafe_allow_html=True,
    )

    current_answer = st.session_state.answers[idx]

    selected = st.radio(
        label="options",
        options=list(
            range(len(question["options"]))
        ),
        format_func=lambda i: question["options"][i],
        index=(
            current_answer
            if current_answer is not None
            else None
        ),
        key=f"radio_q{idx}",
        label_visibility="collapsed",
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    st.session_state.answers[idx] = selected

    is_last = idx == TOTAL_QUESTIONS - 1

    button_label = (
        "SUBMIT QUIZ ✓"
        if is_last
        else "NEXT QUESTION →"
    )

    disabled = selected is None

    if st.button(
        button_label,
        key=f"next_btn_{idx}",
        disabled=disabled,
    ):

        if not is_last:

            st.session_state.q_index += 1
            st.rerun()

        else:

            finalize_quiz()
            st.rerun()

    if disabled:

        st.caption(
            "Select an answer to continue."
        )


def finalize_quiz():
    """Compute score and persist to Google Sheets exactly once."""

    score = 0
    answer_labels = []

    questions = (
        st.session_state.quiz_questions
        or QUESTIONS
    )

    for i, q in enumerate(questions):

        chosen = st.session_state.answers[i]

        if chosen == q["correct"]:
            score += 1

        answer_labels.append(
            q["options"][chosen]
            if chosen is not None
            else ""
        )

    st.session_state.score = score

    if not st.session_state.submitted_to_sheets:

        try:

            worksheet = get_worksheet()

            # Re-check duplicate immediately before writing.
            if not email_already_submitted(
                worksheet,
                st.session_state.email,
            ):

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
                "We couldn't save your response right now. "
                "Please screenshot your score and let the "
                "organizers know."
            )

    st.session_state.stage = "result"


def render_result():

    score = st.session_state.score

    pct = int(
        round(
            (score / TOTAL_QUESTIONS) * 100
        )
    )

    render_header()

    st.markdown(
        '<div class="chai-title">Quiz Complete!</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="chai-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="score-big">'
        f"{score} / {TOTAL_QUESTIONS}"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="score-pct">'
        f"{pct}%"
        f"</div>",
        unsafe_allow_html=True,
    )

    if pct == 100:

        message = (
            "Excellent work! You got all the questions right."
        )

    elif pct >= 70:

        message = (
            "Great job! You clearly understood the MCP basics."
        )

    elif pct >= 50:

        message = (
            "Nice attempt! You picked up the key ideas."
        )

    else:

        message = (
            "Thanks for playing along — MCP takes a little "
            "getting used to!"
        )

    st.markdown(
        f'<div class="score-msg">'
        f"{message}"
        f"</div>",
        unsafe_allow_html=True,
    )

    if st.session_state.get("save_error"):

        st.warning(
            st.session_state.save_error
        )

    else:

        st.markdown(
            '<div class="score-footer">'
            "Your response has been recorded.<br>"
            "Good luck in the lucky draw!"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


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
        st.error(
            "Something went wrong. "
            "Please refresh the page and try again."
        )


if __name__ == "__main__":
    main()

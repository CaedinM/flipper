import streamlit as st


def inject_theme():
    """
    Inject the Flipper dark terminal theme.
    Call once at the top of every page, after set_page_config.
    """
    st.markdown(
        """
        <style>
        /* =========================================================
           FLIPPER — DARK TERMINAL THEME
           Chartreuse × Forest Black
        ========================================================= */

        @import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap');

        /* --- Variables --- */
        :root {
            --bg:           #060D09;
            --surface:      #0B1510;
            --card:         #111D16;
            --card-hover:   #162419;
            --accent:       #C8FF00;
            --accent-dim:   #8AAE00;
            --accent-muted: #2A3A00;
            --text-1:       #E2EDD8;
            --text-2:       #5A8070;
            --text-3:       #2A4A35;
            --border:       #1A3020;
            --red:          #FF5555;
            --font-ui:      'Chakra Petch', monospace;
            --font-data:    'JetBrains Mono', monospace;
        }

        /* --- Global base --- */
        html, body, [class*="css"] {
            font-family: var(--font-ui) !important;
        }

        /* --- App background --- */
        .stApp,
        [data-testid="stAppViewContainer"] {
            background-color: var(--bg) !important;
        }

        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 5rem !important;
        }

        /* Hide top header bar entirely */
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {
            display: none !important;
        }

        /* --- Sidebar --- */
        [data-testid="stSidebar"] {
            background-color: var(--surface) !important;
            border-right: 1px solid var(--border) !important;
        }

        [data-testid="stSidebarNav"] {
            padding-top: 0.5rem;
        }

        /* Sidebar nav links */
        [data-testid="stSidebarNavLink"] {
            border-radius: 0 !important;
            padding: 0.55rem 1.2rem !important;
            margin: 0 !important;
            border-left: 2px solid transparent !important;
            transition: all 0.12s ease !important;
        }

        [data-testid="stSidebarNavLink"]:hover {
            background-color: var(--card) !important;
            border-left-color: var(--accent-dim) !important;
        }

        [data-testid="stSidebarNavLink"][aria-current="page"] {
            background-color: var(--card) !important;
            border-left-color: var(--accent) !important;
        }

        [data-testid="stSidebarNavLink"] span,
        [data-testid="stSidebarNavLink"] p {
            font-family: var(--font-ui) !important;
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.15em !important;
            text-transform: uppercase !important;
            color: var(--text-2) !important;
        }

        [data-testid="stSidebarNavLink"]:hover span,
        [data-testid="stSidebarNavLink"]:hover p,
        [data-testid="stSidebarNavLink"][aria-current="page"] span,
        [data-testid="stSidebarNavLink"][aria-current="page"] p {
            color: var(--accent) !important;
        }

        /* Sidebar image (logo) */
        [data-testid="stSidebar"] img {
            filter: brightness(0) invert(1);
            opacity: 0.85;
        }

        /* --- Typography --- */
        h1, .stMarkdown h1 {
            font-family: var(--font-ui) !important;
            font-weight: 700 !important;
            font-size: 2.2rem !important;
            letter-spacing: 0.06em !important;
            text-transform: uppercase !important;
            color: var(--text-1) !important;
            margin-bottom: 0.25rem !important;
        }

        h2, .stMarkdown h2 {
            font-family: var(--font-ui) !important;
            font-weight: 600 !important;
            font-size: 1.1rem !important;
            letter-spacing: 0.18em !important;
            text-transform: uppercase !important;
            color: var(--accent) !important;
            margin-top: 1.5rem !important;
        }

        h3, .stMarkdown h3 {
            font-family: var(--font-ui) !important;
            font-weight: 500 !important;
            font-size: 0.9rem !important;
            letter-spacing: 0.12em !important;
            text-transform: uppercase !important;
            color: var(--text-2) !important;
        }

        p, .stMarkdown p {
            font-family: var(--font-ui) !important;
            color: var(--text-2) !important;
            font-size: 0.88rem !important;
        }

        /* --- Metric cards --- */
        [data-testid="stMetric"] {
            background-color: var(--card) !important;
            border: 1px solid var(--border) !important;
            border-top: 2px solid var(--accent) !important;
            border-radius: 0 !important;
            padding: 1.1rem 1.4rem 1rem !important;
        }

        [data-testid="stMetricLabel"] p,
        [data-testid="stMetricLabel"] {
            font-family: var(--font-ui) !important;
            font-size: 0.6rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.22em !important;
            text-transform: uppercase !important;
            color: var(--text-2) !important;
        }

        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] > div,
        [data-testid="stMetricValue"] span {
            font-family: var(--font-data) !important;
            font-size: 1.85rem !important;
            font-weight: 500 !important;
            color: var(--text-1) !important;
            letter-spacing: -0.02em !important;
        }

        /* --- Buttons --- */
        .stButton > button {
            background: transparent !important;
            border: 1px solid var(--accent) !important;
            color: var(--accent) !important;
            font-family: var(--font-ui) !important;
            font-weight: 700 !important;
            font-size: 0.7rem !important;
            letter-spacing: 0.22em !important;
            text-transform: uppercase !important;
            border-radius: 0 !important;
            padding: 0.55rem 1.2rem !important;
            transition: background 0.1s ease, color 0.1s ease !important;
        }

        .stButton > button:hover {
            background: var(--accent) !important;
            color: var(--bg) !important;
            border-color: var(--accent) !important;
        }

        .stButton > button:active {
            transform: translateY(1px) !important;
        }

        /* Secondary (non-primary) buttons — e.g. Close Details */
        .stButton > button[kind="secondary"] {
            border-color: var(--border) !important;
            color: var(--text-2) !important;
        }

        .stButton > button[kind="secondary"]:hover {
            border-color: var(--text-2) !important;
            background: var(--card) !important;
            color: var(--text-1) !important;
        }

        /* --- Dataframes --- */
        [data-testid="stDataFrame"],
        [data-testid="stDataEditor"] {
            border: 1px solid var(--border) !important;
            border-radius: 0 !important;
        }

        /* --- Dividers --- */
        hr {
            border: none !important;
            border-top: 1px solid var(--border) !important;
            margin: 2rem 0 !important;
            opacity: 1 !important;
        }

        /* --- Expanders --- */
        .streamlit-expanderHeader,
        [data-testid="stExpander"] summary {
            background-color: var(--card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 0 !important;
            font-family: var(--font-ui) !important;
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.15em !important;
            text-transform: uppercase !important;
            color: var(--text-2) !important;
        }

        [data-testid="stExpander"] details[open] summary {
            border-bottom-color: var(--border) !important;
        }

        [data-testid="stExpanderDetails"] {
            background-color: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-top: none !important;
            border-radius: 0 !important;
        }

        /* --- Form inputs --- */
        [data-testid="stSelectbox"] > div > div,
        [data-testid="stMultiSelect"] > div > div {
            background-color: var(--card) !important;
            border-color: var(--border) !important;
            border-radius: 0 !important;
            font-family: var(--font-ui) !important;
            font-size: 0.85rem !important;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTimeInput"] input {
            background-color: var(--card) !important;
            border-color: var(--border) !important;
            border-radius: 0 !important;
            color: var(--text-1) !important;
            font-family: var(--font-data) !important;
            font-size: 0.9rem !important;
        }

        [data-testid="stTextInput"] input:focus,
        [data-testid="stNumberInput"] input:focus,
        [data-testid="stDateInput"] input:focus {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 1px var(--accent) !important;
        }

        /* Form labels */
        label,
        .stTextInput label,
        .stNumberInput label,
        .stDateInput label,
        .stSelectbox label,
        .stMultiSelect label {
            font-family: var(--font-ui) !important;
            font-size: 0.62rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.2em !important;
            text-transform: uppercase !important;
            color: var(--text-2) !important;
        }

        /* --- Captions --- */
        .stCaption,
        [data-testid="stCaptionContainer"] p {
            font-family: var(--font-data) !important;
            font-size: 0.62rem !important;
            color: var(--text-3) !important;
            letter-spacing: 0.04em !important;
        }

        /* --- Alerts --- */
        [data-testid="stAlert"] {
            border-radius: 0 !important;
            font-family: var(--font-ui) !important;
            font-size: 0.8rem !important;
        }

        /* --- Info / success boxes --- */
        [data-testid="stInfoMessage"],
        [data-testid="stSuccessMessage"] {
            border-radius: 0 !important;
        }

        /* --- Scrollbar --- */
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: var(--bg); }
        ::-webkit-scrollbar-thumb { background: var(--border); }
        ::-webkit-scrollbar-thumb:hover { background: var(--accent-dim); }

        /* --- Selectbox dropdown options --- */
        [data-baseweb="popover"],
        [data-baseweb="menu"] {
            background-color: var(--card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 0 !important;
        }

        /* --- Checkbox --- */
        [data-testid="stCheckbox"] label {
            font-family: var(--font-ui) !important;
            font-size: 0.78rem !important;
            letter-spacing: 0.1em !important;
        }

        /* === Accent line under page name in header === */
        [data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"]::before {
            content: '▶ ';
            color: var(--accent);
        }

        /* === Bordered containers (release cards) === */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: var(--card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 0 !important;
            transition: border-color 0.15s ease !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: var(--accent-dim) !important;
        }

        /* === Number input stepper buttons === */
        [data-testid="stNumberInput"] button {
            background: var(--card) !important;
            border-color: var(--border) !important;
            color: var(--text-2) !important;
            border-radius: 0 !important;
        }

        /* === Spinner === */
        [data-testid="stSpinner"] {
            font-family: var(--font-ui) !important;
            color: var(--accent) !important;
        }

        /* === Status indicator dot for subheaders on calendar pages === */
        [data-testid="stSubheader"] {
            border-left: 3px solid var(--accent) !important;
            padding-left: 0.75rem !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

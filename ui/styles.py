from __future__ import annotations

import streamlit as st


APP_CSS = """
<style>
:root {
    --tc-bg: #09090d;
    --tc-sidebar: #101017;

    --tc-panel: #181820;
    --tc-panel-soft: #20202a;
    --tc-panel-hover: #292936;
    --tc-popover: #15151d;

    --tc-border: rgba(255, 255, 255, 0.10);
    --tc-border-strong: rgba(255, 255, 255, 0.20);

    --tc-text: #f8f8fb;
    --tc-text-soft: #dedee9;
    --tc-muted: #a3a3b5;

    --tc-accent-a: #ff4f68;
    --tc-accent-b: #a855f7;
    --tc-accent-c: #5b8cff;

    --tc-gradient:
        linear-gradient(
            135deg,
            var(--tc-accent-a) 0%,
            var(--tc-accent-b) 52%,
            var(--tc-accent-c) 100%
        );
}


/* ==========================================================
   APPLICATION
   ========================================================== */

html,
body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
    background: var(--tc-bg) !important;
    color: var(--tc-text) !important;
}

[data-testid="stMainBlockContainer"] {
    max-width: 1180px;
    padding-top: 1rem;
    padding-bottom: 8rem;
}

#MainMenu,
footer,
div[data-testid="stDecoration"],
[data-testid="stStatusWidget"] {
    display: none !important;
}


/* ==========================================================
   HEADER AND SIDEBAR CONTROL
   ========================================================== */

header[data-testid="stHeader"] {
    display: block !important;
    visibility: visible !important;
    height: 3rem !important;
    min-height: 3rem !important;
    background: transparent !important;
}

div[data-testid="stToolbar"] {
    display: flex !important;
    visibility: visible !important;
    background: transparent !important;
}

button[data-testid="stSidebarCollapseButton"],
div[data-testid="stSidebarCollapsedControl"] button,
button[aria-label="Open sidebar"],
button[aria-label="Close sidebar"],
button[aria-label="Collapse sidebar"],
button[aria-label="Expand sidebar"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;

    position: fixed !important;
    top: 0.55rem !important;
    left: 0.65rem !important;
    z-index: 999999 !important;

    width: 2.5rem !important;
    min-width: 2.5rem !important;
    height: 2.5rem !important;
    min-height: 2.5rem !important;

    padding: 0 !important;

    border: 1px solid rgba(255, 255, 255, 0.24) !important;
    border-radius: 0.85rem !important;

    background: var(--tc-gradient) !important;
    color: white !important;

    box-shadow:
        0 10px 28px rgba(168, 85, 247, 0.30),
        0 5px 16px rgba(0, 0, 0, 0.45) !important;
}

button[data-testid="stSidebarCollapseButton"] svg,
div[data-testid="stSidebarCollapsedControl"] button svg,
button[aria-label="Open sidebar"] svg,
button[aria-label="Close sidebar"] svg,
button[aria-label="Collapse sidebar"] svg,
button[aria-label="Expand sidebar"] svg {
    color: white !important;
    fill: white !important;
    stroke: white !important;
}


/* ==========================================================
   SIDEBAR
   ========================================================== */

section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {
    background:
        linear-gradient(
            180deg,
            #111119 0%,
            #0d0d13 100%
        ) !important;

    color: var(--tc-text) !important;
}

section[data-testid="stSidebar"] {
    border-right: 1px solid var(--tc-border) !important;
}

section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span {
    color: var(--tc-text-soft);
}

section[data-testid="stSidebar"]
[data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] small {
    color: var(--tc-muted) !important;
    opacity: 1 !important;
}

section[data-testid="stSidebar"]
[data-baseweb="select"] > div,
section[data-testid="stSidebar"]
[data-testid="stTextInput"] input,
section[data-testid="stSidebar"]
[data-testid="stTextArea"] textarea {
    background: var(--tc-panel) !important;
    border-color: var(--tc-border) !important;
    color: var(--tc-text) !important;
}

section[data-testid="stSidebar"]
[data-baseweb="select"] span,
section[data-testid="stSidebar"]
[data-baseweb="select"] input {
    color: var(--tc-text) !important;
}

section[data-testid="stSidebar"]
[data-testid="stExpander"] {
    border: 1px solid var(--tc-border) !important;
    border-radius: 0.8rem !important;
    background: rgba(255, 255, 255, 0.02) !important;
}

section[data-testid="stSidebar"]
[data-testid="stExpander"] summary {
    color: var(--tc-text-soft) !important;
}


/* ==========================================================
   BRAND
   ========================================================== */

.tc-brand {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin: 0.35rem 0 1.2rem;
}

.tc-brand-logo {
    display: flex;
    width: 2.45rem;
    height: 2.45rem;
    flex: 0 0 2.45rem;
    align-items: center;
    justify-content: center;

    border: 1px solid rgba(255, 255, 255, 0.20);
    border-radius: 0.8rem;

    background: var(--tc-gradient);
    color: white;

    font-weight: 700;

    box-shadow:
        0 10px 26px rgba(168, 85, 247, 0.28);
}

.tc-brand-title {
    color: var(--tc-text);
    font-size: 1rem;
    font-weight: 750;
}

.tc-brand-subtitle {
    color: var(--tc-muted);
    font-size: 0.72rem;
    margin-top: 0.15rem;
}

.tc-section-label {
    color: #9999b1 !important;
    font-size: 0.68rem;
    font-weight: 750;
    letter-spacing: 0.13em;
    margin: 1.25rem 0 0.65rem;
    text-transform: uppercase;
}


/* ==========================================================
   PAGE AND EMPTY STATE
   ========================================================== */

.tc-page-title {
    color: var(--tc-text);
    font-size: clamp(2rem, 4vw, 2.8rem);
    line-height: 1.05;
    letter-spacing: -0.04em;
    margin: 0;
}

.tc-page-subtitle {
    color: var(--tc-muted);
    font-size: 0.96rem;
    margin-top: 0.55rem;
}

.tc-empty-state {
    max-width: 760px;
    margin: 2rem auto 1.2rem;
    padding: 2rem;

    text-align: center;

    border: 1px solid var(--tc-border);
    border-radius: 1.4rem;

    background:
        radial-gradient(
            circle at top,
            rgba(168, 85, 247, 0.14),
            transparent 48%
        ),
        var(--tc-panel);
}

.tc-empty-icon {
    display: flex;
    width: 3.3rem;
    height: 3.3rem;
    align-items: center;
    justify-content: center;
    margin: 0 auto 1rem;

    border-radius: 1rem;
    background: rgba(168, 85, 247, 0.18);

    color: white;
    font-size: 1.4rem;
}

.tc-empty-title {
    color: var(--tc-text);
    font-size: 1.45rem;
    margin: 0;
}

.tc-empty-subtitle {
    max-width: 600px;
    margin: 0.7rem auto 1.5rem;

    color: var(--tc-muted);
    line-height: 1.6;
}

.tc-feature-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.8rem;
}

.tc-feature-card {
    padding: 1rem;

    text-align: left;

    border: 1px solid var(--tc-border);
    border-radius: 1rem;

    background: rgba(255, 255, 255, 0.026);
}

.tc-feature-title {
    color: var(--tc-text);
    font-weight: 700;
}

.tc-feature-text {
    color: var(--tc-muted);
    font-size: 0.78rem;
    line-height: 1.5;
}


/* ==========================================================
   BADGES
   ========================================================== */

.tc-badge-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem;
    margin-bottom: 0.45rem;
}


.tc-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;

    padding: 0.35rem 0.75rem;
    margin-right: 0.35rem;
    margin-bottom: 0.35rem;

    border-radius: 999px;

    border: 1px solid var(--tc-border);

    background: rgba(255, 255, 255, 0.05);

    color: var(--tc-text-soft);

    font-size: 0.82rem;
    font-weight: 600;

    line-height: 1;
}

.tc-badge-dot {
    width: 0.45rem;
    height: 0.45rem;

    border-radius: 50%;

    background: var(--tc-muted);
}

.tc-badge-success .tc-badge-dot {
    background: #22c55e;
}

.tc-badge-warning .tc-badge-dot {
    background: #f59e0b;
}

.tc-badge-error .tc-badge-dot {
    background: #ef4444;
}

.tc-badge-info .tc-badge-dot {
    background: #5b8cff;
}


/* ==========================================================
   COMPOSER
   ========================================================== */

.st-key-tc_prompt_composer {
    position: relative !important;
    max-width: 100%;
    margin-top: 0.8rem;
}

.st-key-tc_prompt_composer
[data-testid="stPopover"] {
    position: absolute !important;
    left: 0.68rem !important;
    bottom: 0.62rem !important;
    z-index: 1000 !important;

    width: 2.6rem !important;
    margin: 0 !important;
}

.st-key-tc_prompt_composer
[data-testid="stPopover"] > button {
    width: 2.55rem !important;
    min-width: 2.55rem !important;
    height: 2.55rem !important;
    min-height: 2.55rem !important;

    padding: 0 !important;

    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    border-radius: 0.82rem !important;

    background: var(--tc-gradient) !important;
    color: white !important;

    font-size: 1.35rem !important;
    font-weight: 800 !important;

    box-shadow:
        0 9px 24px rgba(168, 85, 247, 0.32) !important;
}

.st-key-tc_prompt_composer
[data-testid="stPopover"] > button p,
.st-key-tc_prompt_composer
[data-testid="stPopover"] > button span,
.st-key-tc_prompt_composer
[data-testid="stPopover"] > button svg {
    color: white !important;
    fill: white !important;
    stroke: white !important;
}

[data-testid="stBottomBlockContainer"],
[data-testid="stBottom"],
[data-testid="stChatInput"] {
    background: transparent !important;
    border: 0 !important;
}

div[data-testid="stChatInput"] > div {
    min-height: 4rem !important;

    border: 1px solid var(--tc-border) !important;
    border-radius: 1.05rem !important;

    background:
        linear-gradient(
            180deg,
            #191921 0%,
            #15151d 100%
        ) !important;

    box-shadow:
        0 16px 46px rgba(0, 0, 0, 0.34) !important;
}

[data-testid="stChatInput"] textarea {
    min-height: 3.55rem !important;

    padding-left: 4rem !important;
    padding-right: 3.7rem !important;

    color: var(--tc-text) !important;
    caret-color: white !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #9292a5 !important;
    opacity: 1 !important;
}


/* ==========================================================
   ADD-TO-PROMPT POPOVER SURFACE
   ========================================================== */

/*
Streamlit may use either stPopoverBody or BaseWeb popover
depending on its version. Both are targeted.
*/

[data-testid="stPopoverBody"],
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] [role="dialog"] {
    background:
        linear-gradient(
            180deg,
            #1b1b25 0%,
            #13131b 100%
        ) !important;

    border: 1px solid var(--tc-border-strong) !important;
    border-radius: 1.1rem !important;

    color: var(--tc-text) !important;

    box-shadow:
        0 28px 80px rgba(0, 0, 0, 0.68) !important;
}

/*
Remove any white internal container inherited from Streamlit.
*/
[data-testid="stPopoverBody"]
[data-testid="stVerticalBlock"],
[data-testid="stPopoverBody"]
[data-testid="stElementContainer"],
[data-testid="stPopoverBody"]
[data-testid="stMarkdownContainer"],
div[data-baseweb="popover"]
[data-testid="stVerticalBlock"],
div[data-baseweb="popover"]
[data-testid="stElementContainer"] {
    background: transparent !important;
}


/* ==========================================================
   POPOVER TEXT
   ========================================================== */

[data-testid="stPopoverBody"] h1,
[data-testid="stPopoverBody"] h2,
[data-testid="stPopoverBody"] h3,
[data-testid="stPopoverBody"] h4,
[data-testid="stPopoverBody"] p,
[data-testid="stPopoverBody"] label,
[data-testid="stPopoverBody"] span,
[data-testid="stPopoverBody"]
[data-testid="stMarkdownContainer"],
div[data-baseweb="popover"] h1,
div[data-baseweb="popover"] h2,
div[data-baseweb="popover"] h3,
div[data-baseweb="popover"] h4,
div[data-baseweb="popover"] p,
div[data-baseweb="popover"] label,
div[data-baseweb="popover"] span {
    color: var(--tc-text-soft) !important;
}

[data-testid="stPopoverBody"]
[data-testid="stCaptionContainer"],
[data-testid="stPopoverBody"] small,
div[data-baseweb="popover"]
[data-testid="stCaptionContainer"],
div[data-baseweb="popover"] small {
    color: var(--tc-muted) !important;
}


/* ==========================================================
   FILE UPLOADER INSIDE PROMPT
   ========================================================== */

[data-testid="stPopoverBody"]
[data-testid="stFileUploader"],
div[data-baseweb="popover"]
[data-testid="stFileUploader"] {
    padding: 0.55rem !important;

    border: 1px solid var(--tc-border) !important;
    border-radius: 0.9rem !important;

    background: var(--tc-panel) !important;
}

[data-testid="stPopoverBody"]
[data-testid="stFileUploaderDropzone"],
div[data-baseweb="popover"]
[data-testid="stFileUploaderDropzone"] {
    min-height: 4.5rem !important;

    border: 1px dashed rgba(168, 85, 247, 0.62) !important;
    border-radius: 0.82rem !important;

    background:
        linear-gradient(
            135deg,
            rgba(255, 79, 104, 0.10),
            rgba(168, 85, 247, 0.15),
            rgba(91, 140, 255, 0.10)
        ) !important;
}

[data-testid="stPopoverBody"]
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stPopoverBody"]
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stPopoverBody"]
[data-testid="stFileUploaderDropzone"] small,
div[data-baseweb="popover"]
[data-testid="stFileUploaderDropzone"] p,
div[data-baseweb="popover"]
[data-testid="stFileUploaderDropzone"] span,
div[data-baseweb="popover"]
[data-testid="stFileUploaderDropzone"] small {
    color: var(--tc-text-soft) !important;
}

/*
Upload button.
*/
[data-testid="stPopoverBody"]
[data-testid="stFileUploaderDropzone"] button,
div[data-baseweb="popover"]
[data-testid="stFileUploaderDropzone"] button {
    min-height: 2.55rem !important;

    border: 1px solid rgba(255, 255, 255, 0.22) !important;
    border-radius: 0.72rem !important;

    background: var(--tc-gradient) !important;
    color: white !important;

    font-weight: 700 !important;

    box-shadow:
        0 8px 20px rgba(168, 85, 247, 0.26) !important;
}

[data-testid="stPopoverBody"]
[data-testid="stFileUploaderDropzone"] button p,
[data-testid="stPopoverBody"]
[data-testid="stFileUploaderDropzone"] button span,
[data-testid="stPopoverBody"]
[data-testid="stFileUploaderDropzone"] button svg,
div[data-baseweb="popover"]
[data-testid="stFileUploaderDropzone"] button p,
div[data-baseweb="popover"]
[data-testid="stFileUploaderDropzone"] button span,
div[data-baseweb="popover"]
[data-testid="stFileUploaderDropzone"] button svg {
    color: white !important;
    fill: white !important;
    stroke: white !important;
}


/* ==========================================================
   REASONING SELECTOR
   ========================================================== */

[data-testid="stPopoverBody"]
[data-baseweb="select"] > div,
div[data-baseweb="popover"]
[data-baseweb="select"] > div {
    min-height: 2.9rem !important;

    border: 1px solid rgba(168, 85, 247, 0.52) !important;
    border-radius: 0.78rem !important;

    background:
        linear-gradient(
            135deg,
            rgba(255, 79, 104, 0.10),
            rgba(168, 85, 247, 0.13),
            rgba(91, 140, 255, 0.08)
        ) !important;

    color: var(--tc-text) !important;

    box-shadow:
        inset 0 0 0 1px rgba(255, 255, 255, 0.025) !important;
}

[data-testid="stPopoverBody"]
[data-baseweb="select"] input,
[data-testid="stPopoverBody"]
[data-baseweb="select"] span,
[data-testid="stPopoverBody"]
[data-baseweb="select"] p,
div[data-baseweb="popover"]
[data-baseweb="select"] input,
div[data-baseweb="popover"]
[data-baseweb="select"] span,
div[data-baseweb="popover"]
[data-baseweb="select"] p {
    color: var(--tc-text) !important;
    opacity: 1 !important;
}

[data-testid="stPopoverBody"]
[data-baseweb="select"] svg,
div[data-baseweb="popover"]
[data-baseweb="select"] svg {
    color: var(--tc-text-soft) !important;
    fill: var(--tc-text-soft) !important;
}


/* ==========================================================
   REASONING DROPDOWN OPTIONS
   ========================================================== */

ul[role="listbox"] {
    border: 1px solid var(--tc-border-strong) !important;
    border-radius: 0.8rem !important;

    background: var(--tc-panel-soft) !important;
    color: var(--tc-text) !important;

    box-shadow:
        0 20px 50px rgba(0, 0, 0, 0.55) !important;
}

li[role="option"] {
    color: var(--tc-text) !important;
    background: transparent !important;
}

li[role="option"] span,
li[role="option"] p {
    color: var(--tc-text) !important;
}

li[role="option"]:hover,
li[role="option"][aria-selected="true"] {
    background: var(--tc-panel-hover) !important;
}


/* ==========================================================
   WEB AND DOCUMENT TOGGLES
   ========================================================== */

[data-testid="stPopoverBody"]
[data-testid="stToggle"] label,
[data-testid="stPopoverBody"]
[data-testid="stCheckbox"] label,
div[data-baseweb="popover"]
[data-testid="stToggle"] label,
div[data-baseweb="popover"]
[data-testid="stCheckbox"] label {
    color: var(--tc-text-soft) !important;
}

[data-testid="stPopoverBody"]
[data-testid="stToggle"] p,
[data-testid="stPopoverBody"]
[data-testid="stCheckbox"] p,
div[data-baseweb="popover"]
[data-testid="stToggle"] p,
div[data-baseweb="popover"]
[data-testid="stCheckbox"] p {
    color: var(--tc-text-soft) !important;
    opacity: 1 !important;
}


/* ==========================================================
   DEPLOY MODAL
   ========================================================== */

/*
Keep Streamlit's Deploy modal light and readable.
*/
div[role="dialog"]:not(
    [data-testid="stPopoverBody"]
):not(
    [data-baseweb="popover"]
) {
    background: #ffffff !important;
    color: #252936 !important;
}

div[role="dialog"]:not(
    [data-testid="stPopoverBody"]
):not(
    [data-baseweb="popover"]
) h1,
div[role="dialog"]:not(
    [data-testid="stPopoverBody"]
):not(
    [data-baseweb="popover"]
) h2,
div[role="dialog"]:not(
    [data-testid="stPopoverBody"]
):not(
    [data-baseweb="popover"]
) h3,
div[role="dialog"]:not(
    [data-testid="stPopoverBody"]
):not(
    [data-baseweb="popover"]
) p,
div[role="dialog"]:not(
    [data-testid="stPopoverBody"]
):not(
    [data-baseweb="popover"]
) span,
div[role="dialog"]:not(
    [data-testid="stPopoverBody"]
):not(
    [data-baseweb="popover"]
) label {
    color: #252936 !important;
}


/* ==========================================================
   RESPONSIVE
   ========================================================== */

@media (max-width: 850px) {
    .tc-feature-grid {
        grid-template-columns: 1fr;
    }

    .tc-empty-state {
        margin-top: 1rem;
        padding: 1.2rem;
    }
}

/* ==========================================================
   CHAT EXPERIENCE
   ========================================================== */

.tc-message {
    width: 100%;
    margin: 0.75rem 0;
    padding: 1rem 1.15rem;
    border-radius: 1rem;
    border: 1px solid var(--tc-border);
    background: var(--tc-panel);
    color: var(--tc-text);
    line-height: 1.65;
}

.tc-message-user {
    background:
        linear-gradient(
            135deg,
            rgba(255,79,104,0.18),
            rgba(168,85,247,0.18)
        );

    border-color:
        rgba(168,85,247,0.35);
}

.tc-message-assistant {
    background:
        rgba(255,255,255,0.04);
}


.tc-message-header {
    display:flex;
    align-items:center;
    gap:0.5rem;
    margin-bottom:0.45rem;

    font-size:0.82rem;
    color:var(--tc-muted);
}


.tc-message-body {
    color:var(--tc-text);
}


/* ==========================================================
   AGENT STATUS
   ========================================================== */

.tc-agent-status-card {
    padding:1rem;
    border-radius:1rem;

    background:
        linear-gradient(
            180deg,
            rgba(255,255,255,0.06),
            rgba(255,255,255,0.02)
        );

    border:1px solid var(--tc-border);
}


.tc-agent-step {
    display:flex;
    align-items:center;
    gap:0.65rem;

    padding:0.55rem 0;

    color:var(--tc-text-soft);
}


.tc-agent-step-dot {
    width:0.7rem;
    height:0.7rem;

    border-radius:50%;

    background:
        var(--tc-accent-b);
}


.tc-agent-step {
    transition: all 0.2s ease;
}

.tc-agent-step-completed {
    color: var(--tc-text);
}

.tc-agent-step-completed .tc-agent-step-dot {
    background: #22c55e;
    color: white;

    box-shadow:
        0 0 12px rgba(34, 197, 94, 0.45);
}

.tc-agent-step-active {
    color: white;

    font-weight: 700;
}

.tc-agent-step-active .tc-agent-step-dot {
    background:
        var(--tc-accent-a);

    color: white;

    box-shadow:
        0 0 14px rgba(168, 85, 247, 0.65);
}

.tc-agent-step-pending {
    color: var(--tc-muted);
}

.tc-agent-step-pending .tc-agent-step-dot {
    background:
        rgba(255,255,255,0.12);

    color:
        var(--tc-muted);
}


.tc-agent-step-active
.tc-agent-step-dot {
    background:
        var(--tc-accent-a);

    box-shadow:
        0 0 12px
        rgba(255,79,104,0.7);
}


/* ==========================================================
   CARDS
   ========================================================== */

.tc-card {
    padding:1rem;

    border-radius:1rem;

    background:
        var(--tc-panel);

    border:
        1px solid var(--tc-border);

    transition:
        transform .2s ease,
        border-color .2s ease;
}


.tc-card:hover {
    transform:
        translateY(-2px);

    border-color:
        var(--tc-border-strong);
}

</style>
"""


def apply_app_styles() -> None:
    st.markdown(
        APP_CSS,
        unsafe_allow_html=True,
    )

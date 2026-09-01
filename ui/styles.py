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


section[data-testid="stSidebar"] > div {
    padding-top: 1rem;
}


section[data-testid="stSidebar"] .stButton > button {
    min-height: 2.2rem;
    border-radius: 0.65rem;
    font-weight: 600;
}


section[data-testid="stSidebar"] .stMarkdown {
    margin-bottom: 0.35rem;
}


section[data-testid="stSidebar"] [data-testid="stExpander"] {
    margin-bottom: 0.6rem;
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



.tc-response-summary {

    margin-bottom: 1rem;

    padding: 0.9rem;

    border-radius: 0.85rem;

    border: 1px solid var(--tc-border);

    background:
        linear-gradient(
            180deg,
            rgba(255,255,255,0.05),
            rgba(255,255,255,0.02)
        );

}


.tc-response-summary-title {

    font-weight: 700;

    margin-bottom: 0.4rem;

}


.tc-response-summary-text {

    color: var(--tc-text-soft);

    line-height: 1.5;

}



.tc-response-card {

    display: flex;

    flex-direction: column;

    gap: 0.85rem;

}


.tc-response-section {

    padding: 1rem;

    border-radius: 0.9rem;

    border: 1px solid var(--tc-border);

    background:
        linear-gradient(
            180deg,
            rgba(255,255,255,0.04),
            rgba(255,255,255,0.02)
        );

}


.tc-response-title {

    font-weight: 700;

    font-size: 0.95rem;

    margin-bottom: 0.45rem;

    color: var(--tc-text);

}


.tc-response-text {

    white-space: pre-wrap;

    line-height: 1.6;

    color: var(--tc-text-soft);

    font-size: 0.92rem;

}



.tc-message {
    width: 100%;
    margin: 1rem 0;
    padding: 1.15rem 1.25rem;
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
    margin-bottom:0.65rem;

    font-size:0.85rem;
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


.tc-agent-panel {

    margin-top: 0.8rem;

    padding: 1rem;

    border-radius: 1rem;

    background:
        linear-gradient(
            180deg,
            #181823 0%,
            #11111a 100%
        );

    border: 1px solid var(--tc-border);

}


.tc-agent-row {

    display: flex;

    justify-content: space-between;

    align-items: center;

    gap: 0.75rem;

    padding: 0.45rem 0;

    border-bottom:
        1px solid var(--tc-border);

}


.tc-agent-row:last-child {

    border-bottom: none;

}


.tc-agent-label {

    color: var(--tc-muted);

    font-size: 0.82rem;

}


.tc-agent-value {

    color: var(--tc-text);

    font-weight: 600;

    text-align: right;

}


.tc-agent-status {

    margin-top: 0.85rem;

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


.tc-result-card {
    margin-top: 0.75rem;

    padding: 1rem;

    border-radius: 1rem;

    background:
        linear-gradient(
            180deg,
            #1b1b25 0%,
            #14141c 100%
        );

    border: 1px solid var(--tc-border);
}


.tc-result-body {
    display: flex;
    flex-direction: column;

    gap: 0.55rem;

    margin-top: 0.75rem;
}


.tc-result-row {
    display: flex;

    justify-content: space-between;

    color: var(--tc-text-soft);

    font-size: 0.9rem;
}


.tc-result-row strong {
    color: var(--tc-text);
}



.tc-source-panel {
    margin-top: 1rem;

    padding: 1rem;

    border-radius: 1rem;

    background:
        linear-gradient(
            180deg,
            #181823 0%,
            #11111a 100%
        );

    border: 1px solid var(--tc-border);
}


.tc-source-section {
    margin-top: 0.85rem;
}


.tc-source-label {
    margin-bottom: 0.45rem;

    font-size: 0.85rem;

    font-weight: 700;

    color: var(--tc-text-soft);
}


.tc-source-item {
    display: flex;

    justify-content: space-between;

    gap: 1rem;

    padding: 0.55rem 0;

    border-bottom:
        1px solid var(--tc-border);

    font-size: 0.9rem;
}


.tc-source-item:last-child {
    border-bottom: none;
}


.tc-source-item span {
    color: var(--tc-muted);
}



.tc-activity-panel {
    margin-top: 1rem;

    padding: 1rem;

    border-radius: 1rem;

    background:
        linear-gradient(
            180deg,
            #181823 0%,
            #11111a 100%
        );

    border: 1px solid var(--tc-border);
}


.tc-activity-complete {
    margin-bottom: 0.75rem;

    font-size: 0.85rem;

    font-weight: 600;

    color: var(--tc-text);

    opacity: 0.85;
}


.tc-activity-item {
    display: flex;

    align-items: center;

    gap: 0.65rem;

    margin-top: 0.75rem;

    color: var(--tc-text-soft);

    font-size: 0.9rem;
}


.tc-activity-dot {
    width: 0.65rem;

    height: 0.65rem;

    border-radius: 50%;

    background: var(--tc-muted);
}


.tc-active {
    background: #5b8cff;

    box-shadow:
        0 0 12px rgba(91,140,255,0.7);
}


.tc-success {
    background: #22c55e;
}


.tc-error {
    background: #ef4444;
}



.tc-learning-card {

    margin-top: 1rem;

    padding: 1rem;

    border-radius: 1rem;

    background:
        linear-gradient(
            180deg,
            #181823 0%,
            #11111a 100%
        );

    border: 1px solid var(--tc-border);
}


.tc-learning-body {

    margin-top: 0.75rem;
}


.tc-learning-row {

    display: flex;

    justify-content: space-between;

    align-items: center;

    padding: 0.45rem 0;

    border-bottom:
        1px solid var(--tc-border);

    color: var(--tc-text-soft);

}


.tc-learning-row:last-child {

    border-bottom: none;

}


.tc-learning-row strong {

    color: var(--tc-text);

}



.tc-memory-card {

    margin-top: 1rem;

    padding: 1rem;

    border-radius: 1rem;

    background:
        linear-gradient(
            180deg,
            #181823 0%,
            #11111a 100%
        );

    border: 1px solid var(--tc-border);
}


.tc-memory-body {

    margin-top: 0.75rem;

}


.tc-memory-row {

    display: flex;

    justify-content: space-between;

    align-items: center;

    padding: 0.45rem 0;

    border-bottom:
        1px solid var(--tc-border);

    color: var(--tc-text-soft);

}


.tc-memory-row:last-child {

    border-bottom: none;

}


.tc-memory-row strong {

    color: var(--tc-text);

}




.tc-dashboard-grid {

    display: grid;

    grid-template-columns:
        repeat(
            4,
            minmax(0, 1fr)
        );

    gap: 0.75rem;

    margin-bottom: 1rem;

}


.tc-dashboard-card {

    padding: 1rem;

    border-radius: 1rem;

    border: 1px solid var(--tc-border);

    background:
        linear-gradient(
            180deg,
            #181823 0%,
            #11111a 100%
        );

}


.tc-dashboard-title {

    font-size: 0.8rem;

    color: var(--tc-text-soft);

    margin-bottom: 0.35rem;

}


.tc-dashboard-value {

    font-size: 0.95rem;

    font-weight: 700;

    color: var(--tc-text);

    white-space: pre-line;

}


@media (max-width: 900px) {

    .tc-dashboard-grid {

        grid-template-columns:
            repeat(
                2,
                minmax(0, 1fr)
            );

    }

}


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

.tc-citation-badge {

    display: inline-flex;

    align-items: center;

    padding: 0.15rem 0.55rem;

    margin-left: 0.25rem;

    border-radius: 999px;

    border: 1px solid var(--tc-border);

    text-decoration: none;

    font-size: 0.8rem;

}


.tc-citation-badge:hover {

    opacity: 0.8;

}



.tc-response-actions {

    margin-top: 0.8rem;

    padding: 0.6rem;

    border-top: 1px solid var(--tc-border);

}


.tc-response-actions span {

    font-size: 0.75rem;

    opacity: 0.7;

    text-transform: uppercase;

    letter-spacing: 0.08em;

}

    /* Response quick actions */

    .tc-response-actions {
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        padding-top: 0.75rem;
        border-top: 1px solid var(--tc-border);
    }

    .tc-response-actions span {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        opacity: 0.65;
    }

    .tc-response-actions + div .stButton > button {
        min-height: 2.2rem;
        width: 100%;
        font-size: 0.85rem;
        font-weight: 600;
        padding: 0.35rem 0.75rem;
        border-radius: 10px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .tc-response-actions + div .stButton > button:hover {
        transform: translateY(-1px);
    }

    .tc-response-actions + div .stButton > button:focus {
        outline: none;
        box-shadow: none;
    }

/* ==========================================================
   LOGIN EXPERIENCE
   ========================================================== */

.tc-login-page {
    max-width: 950px;
    margin: 3rem auto 2rem auto;
}


.tc-login-brand {
    text-align: center;
    margin-bottom: 2rem;
}


.tc-login-brand h1 {
    font-size: 4rem;
    font-weight: 900;
    letter-spacing: -0.05em;

    background:
        linear-gradient(
            90deg,
            #ff4b4b,
            #a855f7
        );

    -webkit-background-clip: text;
    color: transparent;
}


.tc-login-brand p {
    color: var(--tc-text-soft);
    font-size: 1.15rem;
}


.tc-feature-grid {
    display: grid;

    grid-template-columns:
        repeat(
            3,
            1fr
        );

    gap: 1rem;

    margin-top: 2rem;
}


.tc-login-feature {

    padding: 1.3rem;

    min-height: 150px;

    border-radius: 1rem;

    background:
        linear-gradient(
            180deg,
            rgba(255,255,255,0.08),
            rgba(255,255,255,0.03)
        );

    border:
        1px solid var(--tc-border);
}


.tc-login-feature h3 {
    color: var(--tc-text);
    margin-bottom: 0.7rem;
}


.tc-login-feature p {
    color: var(--tc-text-soft);
    line-height: 1.5;
}




</style>
"""


def apply_app_styles() -> None:
    st.markdown(
        APP_CSS,
        unsafe_allow_html=True,
    )


import streamlit as st
from config import EXAMPLE_QUERIES, MODEL_CONFIGS, TOOL_REGISTRY
from agent import LLMInterface, TaskPilotAgent

st.set_page_config(page_title="TaskPilot AI", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")

st.html("""
<style>
.block-container { padding-top: 2rem; }
.stApp { background: #0f1117; color: #e1e4e8; }
.main-title { font-size: 2.4rem; font-weight: 800; background: linear-gradient(135deg, #58a6ff, #bc8cff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.15rem; }
.sub-title { font-size: 1rem; color: #8b949e; margin-bottom: 1.5rem; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 1.2rem 1.4rem; margin-bottom: 1rem; }
.card-response { background: #161b22; border-left: 4px solid #58a6ff; border-radius: 0 12px 12px 0; padding: 1.2rem 1.4rem; margin-bottom: 1rem; }
.pipeline-step { display: inline-flex; align-items: center; gap: 0.4rem; background: #21262d; border: 1px solid #30363d; border-radius: 8px; padding: 0.45rem 0.9rem; font-size: 0.85rem; margin: 0.25rem 0; }
.pipeline-step.success { border-color: #3fb950; }
.pipeline-step.error { border-color: #f85149; }
.pipeline-arrow { display: inline-block; color: #8b949e; margin: 0 0.35rem; font-size: 1.1rem; vertical-align: middle; }
.log-row { display: flex; gap: 0.6rem; padding: 0.35rem 0; border-bottom: 1px solid #21262d; font-size: 0.85rem; }
.log-label { color: #8b949e; min-width: 130px; flex-shrink: 0; }
.log-value { color: #e1e4e8; word-break: break-word; }
.stTextInput>div>div>input, .stTextArea>div>div>textarea { background: #161b22 !important; border-color: #30363d !important; color: #e1e4e8 !important; border-radius: 10px !important; }
div[data-baseweb="select"] { background: #161b22 !important; }
</style>
""")

if "agent" not in st.session_state: st.session_state.agent = None
if "logs" not in st.session_state: st.session_state.logs = []

with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    provider = st.selectbox("LLM Provider", ["groq", "openai", "gemini"], index=0)
    models = MODEL_CONFIGS[provider]["models"]
    selected_model = st.selectbox("Model", models, index=0)
    key_label = {"openai": "OpenAI API Key", "gemini": "Gemini API Key", "groq": "Groq API Key"}[provider]
    api_key = st.text_input(key_label, type="password", value="", help="Enter your API key")
    st.divider()
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.logs = []
        st.rerun()

agent_ready = False
if api_key.strip():
    try:
        llm = LLMInterface(provider, api_key.strip(), selected_model)
        st.session_state.agent = TaskPilotAgent(llm)
        agent_ready = True
    except Exception as e:
        st.error(f"LLM init failed: {e}")

st.markdown('<div class="main-title">🧠 TaskPilot AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Intelligent Workflow & Tool-Using Agent</div>', unsafe_allow_html=True)

if not agent_ready:
    st.info("👈 Enter your API key in the sidebar to start.")
    st.stop()

# --- BULLETPROOF EXAMPLE BUTTONS ---
def fill_example(text):
    st.session_state.chat_input = text

st.markdown("**Try an example:**")
cols = st.columns(3)
for i, ex in enumerate(EXAMPLE_QUERIES):
    with cols[i % 3]:
        st.button(ex["label"], key=f"ex_{i}", use_container_width=True, on_click=fill_example, args=(ex["text"],))

# --- FIX: Save text & clear BEFORE rendering the text area ---
def store_and_clear():
    st.session_state._submitted_text = st.session_state.get("chat_input", "")
    st.session_state.chat_input = ""

submitted = st.button("🚀 Run Agent", type="primary", use_container_width=True, on_click=store_and_clear)
user_input = st.text_area("Your query", height=100, placeholder="e.g. Summarize this text and extract tasks...", key="chat_input")

# Use saved text if button was clicked, otherwise use current text area
text_to_process = st.session_state.get("_submitted_text", "") if submitted else user_input

# --- SAFE EXECUTION ---
if submitted and text_to_process.strip():
    agent = st.session_state.agent
    error_occurred = False
    
    try:
        response, log = agent.process(text_to_process.strip())
    except Exception as e:
        error_occurred = True
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower() or "ResourceExhausted" in error_msg:
            st.error("⚠️ **Rate limit hit!** Wait 15 seconds, or switch to Groq in the sidebar (it has no daily limits).")
        else:
            st.error(f"❌ **Error:** {error_msg}")

    if not error_occurred:
        with st.status("🧠 Agent working...", expanded=True) as status:
            st.markdown("🔍 **Analyzing intent...**")
            st.markdown(f"🧭 **Intent:** {log.intent_description}")
            tool_labels = [f"{TOOL_REGISTRY.get(t,{}).get('icon','')} {TOOL_REGISTRY.get(t,{}).get('name', t)}" for t in log.selected_tools]
            st.markdown(f"🔧 **Tools:** {' → '.join(tool_labels)}")
            for step in log.tool_steps:
                m = TOOL_REGISTRY.get(step.tool_id, {})
                icon = "✅" if step.status == "success" else "❌"
                st.markdown(f"⚙️ **Step {step.order}:** {m.get('icon','')} {m.get('name', step.tool_id)} {icon} _({step.execution_time_sec:.2f}s)_")
            st.markdown(f"⏱️ **Total:** {log.total_time_sec:.2f}s")
            status.update(label="✅ Done!", state="complete")
        st.session_state.logs.append(log)

for log in reversed(st.session_state.logs):
    st.markdown(f'<div class="card"><div style="font-size:0.75rem;color:#8b949e;margin-bottom:0.3rem;">👤 YOU · {log.timestamp}</div><div>{log.user_input}</div></div>', unsafe_allow_html=True)
    if log.tool_steps:
        ph = '<div style="margin:0.6rem 0 1rem 0;">'
        for i, s in enumerate(log.tool_steps):
            m = TOOL_REGISTRY.get(s.tool_id, {})
            cls = "success" if s.status == "success" else "error"
            ph += f'<span class="pipeline-step {cls}">{m.get("icon","")} {m.get("name", s.tool_id)} <span style="color:#8b949e;font-size:0.75rem;">({s.execution_time_sec:.2f}s)</span></span>'
            if i < len(log.tool_steps) - 1:
                ph += '<span class="pipeline-arrow">→</span>'
        if log.is_multi_step:
            ph += '<span style="margin-left:0.5rem;font-size:0.75rem;color:#bc8cff;background:#21262d;padding:0.2rem 0.6rem;border-radius:10px;">Multi-Step</span>'
        ph += "</div>"
        st.markdown(ph, unsafe_allow_html=True)
    st.markdown(f'<div class="card-response"><div style="font-size:0.75rem;color:#58a6ff;margin-bottom:0.5rem;">🧠 TASKPILOT AI · {log.timestamp}</div>{log.final_response}</div>', unsafe_allow_html=True)
    with st.expander("📋 Execution Log", expanded=False):
        d = log.to_dict()
        st.markdown(f'<div class="log-row"><span class="log-label">Intent</span><span class="log-value">{d["intent"]["description"]}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="log-row"><span class="log-label">Reasoning</span><span class="log-value">{d["intent"]["reasoning"]}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="log-row"><span class="log-label">Tools</span><span class="log-value">{", ".join(d["selected_tools"])}</span></div>', unsafe_allow_html=True)
        for ts in d["tool_steps"]:
            st.markdown(f'<div class="log-row"><span class="log-label">Step {ts["order"]} - {ts["tool"]}</span><span class="log-value">{ts["status"]} · {ts["time_sec"]}s</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="log-row"><span class="log-label">Total Time</span><span class="log-value">{d["total_time_sec"]}s</span></div>', unsafe_allow_html=True)
    st.markdown("---")
import json, time
from dataclasses import dataclass, field
from datetime import datetime
from config import MODEL_CONFIGS, TOOL_REGISTRY
from tools import create_tools

class LLMInterface:
    def __init__(self, provider, api_key, model):
        self.provider, self.api_key, self.model = provider, api_key, model
        self._client = None
        self._init()

    def _init(self):
        if self.provider == "openai":
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        elif self.provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model)
        elif self.provider == "groq":
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url="https://api.groq.com/openai/v1")

    def generate(self, prompt, system_prompt=None, json_mode=False):
        if self.provider == "gemini":
            return self._gemini(prompt, system_prompt)
        return self._openai(prompt, system_prompt, json_mode)

    def _openai(self, prompt, sp, jm):
        cfg_key = "groq" if self.provider == "groq" else "openai"
        cfg = MODEL_CONFIGS[cfg_key]
        msgs = []
        if sp: msgs.append({"role": "system", "content": sp})
        msgs.append({"role": "user", "content": prompt})
        kw = dict(model=self.model, messages=msgs, max_tokens=cfg["max_tokens"], temperature=cfg["temperature"])
        if jm: kw["response_format"] = {"type": "json_object"}
        return self._client.chat.completions.create(**kw).choices[0].message.content.strip()

    def _gemini(self, prompt, sp):
        full = f"{sp}\n\n{prompt}" if sp else prompt
        return self._client.generate_content(full).text.strip()

@dataclass
class ToolStep:
    tool_id: str
    order: int
    input_text: str
    output_text: str
    execution_time_sec: float
    status: str

@dataclass
class AgentLog:
    timestamp: str = ""
    user_input: str = ""
    intent_description: str = ""
    intent_reasoning: str = ""
    selected_tools: list = field(default_factory=list)
    tool_steps: list = field(default_factory=list)
    final_response: str = ""
    total_time_sec: float = 0.0
    is_multi_step: bool = False
    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "user_input": self.user_input,
            "intent": {"description": self.intent_description, "reasoning": self.intent_reasoning},
            "selected_tools": self.selected_tools,
            "is_multi_step": self.is_multi_step,
            "tool_steps": [{"tool": s.tool_id, "order": s.order, "input": s.input_text, "output": s.output_text, "time_sec": round(s.execution_time_sec, 3), "status": s.status} for s in self.tool_steps],
            "final_response": self.final_response,
            "total_time_sec": round(self.total_time_sec, 3),
        }

ROUTING_PROMPT = """You are an intelligent router for an AI agent. Given a user query, decide which tool(s) to use and in what order.
Available tools:
- summarizer: Summarizes text into key points
- task_planner: Generates structured daily plans/routines from goals
- calculator: Performs arithmetic / math operations
- text_to_tasks: Extracts actionable tasks from text
- none: For greetings, chitchat, or direct LLM answers
Rules:
- Direct answer only -> ["none"]
- Multiple tools -> list in execution order
- "summarize and extract tasks" -> ["summarizer", "text_to_tasks"]
- "plan my day and break into tasks" -> ["task_planner", "text_to_tasks"]
Respond ONLY with valid JSON: {"intent": "desc", "reasoning": "why", "tools": ["id1","id2"], "is_multi_step": true/false}"""

SYNTH_PROMPT = "You are TaskPilot AI. Combine the tool outputs below into a clear Markdown response. If one tool, present with brief intro. If multiple, create clear sections."

class TaskPilotAgent:
    def __init__(self, llm):
        self.llm = llm
        self.tools = create_tools(llm)
        self.history = []

    def process(self, user_input):
        log = AgentLog(timestamp=datetime.now().isoformat(timespec="seconds"), user_input=user_input)
        t0 = time.time()
        tool_ids, idesc, ireas, multi = self._route(user_input)
        log.intent_description, log.intent_reasoning = idesc, ireas
        log.selected_tools, log.is_multi_step = tool_ids, multi
        if tool_ids == ["none"]:
            log.final_response = self._direct(user_input)
            log.total_time_sec = time.time() - t0
            self.history.append(log)
            return log.final_response, log
        chain = user_input
        for i, tid in enumerate(tool_ids):
            tool = self.tools.get(tid)
            if not tool:
                log.tool_steps.append(ToolStep(tid, i+1, chain, f"Unknown tool: {tid}", 0, "error"))
                continue
            ts = time.time()
            try:
                out = tool.execute(chain)
                log.tool_steps.append(ToolStep(tid, i+1, chain, out, time.time()-ts, "success"))
                chain = out
            except Exception as e:
                log.tool_steps.append(ToolStep(tid, i+1, chain, f"Error: {e}", time.time()-ts, "error"))
        log.final_response = self._synthesize(user_input, log.tool_steps)
        log.total_time_sec = time.time() - t0
        self.history.append(log)
        return log.final_response, log

    def _route(self, text):
        try:
            raw = self.llm.generate(text, system_prompt=ROUTING_PROMPT, json_mode=(self.llm.provider != "gemini"))
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            d = json.loads(raw)
            valid = set(self.tools.keys()) | {"none"}
            tools = [t for t in d.get("tools", ["none"]) if t in valid] or ["none"]
            return tools, d.get("intent", ""), d.get("reasoning", ""), d.get("is_multi_step", len(tools) > 1)
        except:
            return self._kw_route(text)

    def _kw_route(self, t):
        t = t.lower()
        if any(k in t for k in ["calculate", "compute", "math", "+", "*"]):
            return (["calculator"], "Arithmetic", "Keyword", False)
        if any(k in t for k in ["summarize", "summary", "key points"]):
            if any(k in t for k in ["task", "action"]):
                return (["summarizer", "text_to_tasks"], "Summarize+Tasks", "Keyword", True)
            return (["summarizer"], "Summarize", "Keyword", False)
        if any(k in t for k in ["plan", "schedule", "routine"]):
            if any(k in t for k in ["task", "break down"]):
                return (["task_planner", "text_to_tasks"], "Plan+Tasks", "Keyword", True)
            return (["task_planner"], "Plan", "Keyword", False)
        if any(k in t for k in ["task", "to-do", "todo"]):
            return (["text_to_tasks"], "Tasks", "Keyword", False)
        return (["none"], "Direct", "Keyword", False)

    def _synthesize(self, user_input, steps):
        if len(steps) == 1 and steps[0].status == "success":
            return steps[0].output_text
        parts = []
        for s in steps:
            m = TOOL_REGISTRY.get(s.tool_id, {})
            tag = "OK" if s.status == "success" else "FAIL"
            parts.append(f"### {m.get('icon', '')} {m.get('name', s.tool_id)} [{tag}]\n\n{s.output_text}")
        combined = "\n\n---\n\n".join(parts)
        return self.llm.generate(f"User query: {user_input}\n\nTool outputs:\n\n{combined}\n\nCombine into coherent response.", system_prompt=SYNTH_PROMPT)

    def _direct(self, text):
        return self.llm.generate(text, system_prompt="You are TaskPilot AI, a helpful concise assistant.")
import ast, operator, re
from abc import ABC, abstractmethod

class _SafeMathEvaluator:
    _OPS = {
        ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
    }
    def evaluate(self, expr):
        tree = ast.parse(expr.strip(), mode="eval")
        return float(self._walk(tree.body))
    def _walk(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Num):
            return node.n
        if isinstance(node, ast.BinOp):
            l, r = self._walk(node.left), self._walk(node.right)
            t = type(node.op)
            if t not in self._OPS:
                raise ValueError(f"Unsupported: {t.__name__}")
            return self._OPS[t](l, r)
        if isinstance(node, ast.UnaryOp):
            o = self._walk(node.operand)
            if isinstance(node.op, ast.USub): return -o
            if isinstance(node.op, ast.UAdd): return +o
        raise ValueError(f"Unsupported: {type(node).__name__}")

_safe_eval = _SafeMathEvaluator()

class BaseTool(ABC):
    @property
    @abstractmethod
    def tool_id(self): ...
    @property
    @abstractmethod
    def description(self): ...
    @abstractmethod
    def execute(self, input_text, **kwargs): ...

class SummarizerTool(BaseTool):
    def __init__(self, llm): self.llm = llm
    @property
    def tool_id(self): return "summarizer"
    @property
    def description(self): return "Summarizes text into key points."
    def execute(self, input_text, **kwargs):
        s = "Summarize the text into 4-7 bullet points. Focus on facts and action items. Do NOT add info not in the source."
        return self.llm.generate(f"Text to summarize:\n\n{input_text}", system_prompt=s)

class TaskPlannerTool(BaseTool):
    def __init__(self, llm): self.llm = llm
    @property
    def tool_id(self): return "task_planner"
    @property
    def description(self): return "Generates structured daily plans."
    def execute(self, input_text, **kwargs):
        s = "Create a structured daily schedule with time blocks, priority levels (High/Medium/Low), specific actionable items, and short breaks. Use Markdown."
        return self.llm.generate(f"Goals:\n\n{input_text}", system_prompt=s)

class CalculatorTool(BaseTool):
    def __init__(self, llm=None): self.llm = llm
    @property
    def tool_id(self): return "calculator"
    @property
    def description(self): return "Performs arithmetic operations."
    def execute(self, input_text, **kwargs):
        expr = self._extract(input_text)
        try:
            result = _safe_eval.evaluate(expr)
            if result == int(result): result = int(result)
            return f"**Expression:** `{expr}`\n\n**Result:** `{result}`"
        except Exception as e:
            return f"Could not evaluate: `{e}`"
    def _extract(self, text):
        text = re.sub(r"(?i)^(calculate|what is|compute|eval|solve)\s*[:\-]?\s*", "", text).strip()
        try:
            _safe_eval.evaluate(text)
            return text
        except:
            pass
        for c in re.findall(r"[\d\s\+\-\*\/\.\(\)\^%]+", text):
            c = c.strip()
            if len(c) >= 3:
                try:
                    _safe_eval.evaluate(c)
                    return c
                except:
                    continue
        if self.llm:
            try:
                r = self.llm.generate(f"Convert to Python arithmetic expr (+ - * / ** % //). Return ONLY the expression:\n{text}")
                r = re.sub(r"^```.*?\n?", "", r.strip())
                r = re.sub(r"\n?```$", "", r).strip()
                _safe_eval.evaluate(r)
                return r
            except:
                pass
        raise ValueError(f"No math expression found in: {text!r}")

class TextToTasksTool(BaseTool):
    def __init__(self, llm): self.llm = llm
    @property
    def tool_id(self): return "text_to_tasks"
    @property
    def description(self): return "Converts text into actionable tasks."
    def execute(self, input_text, **kwargs):
        s = "Extract all actionable tasks. For each provide: Task (verb-first), Priority (High/Medium/Low), Effort (Quick/Moderate/Extended). Numbered Markdown list. Do NOT invent tasks."
        return self.llm.generate(f"Text:\n\n{input_text}", system_prompt=s)

def create_tools(llm):
    return {
        "summarizer": SummarizerTool(llm),
        "task_planner": TaskPlannerTool(llm),
        "calculator": CalculatorTool(llm),
        "text_to_tasks": TextToTasksTool(llm),
    }
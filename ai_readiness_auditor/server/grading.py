"""Deterministic grading engine for AI-Readiness Auditor.

Grades project files using ast + re only. No external dependencies.
Returns GradeResult with score (0.0-1.0), breakdown, and feedback.
"""
import ast
import re
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class GradeResult:
    score: float
    breakdown: Dict[str, float]
    feedback: List[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _file_exists(files: Dict[str, str], name: str) -> bool:
    """Check if a file exists (case-insensitive key match)."""
    name_lower = name.lower()
    return any(k.lower() == name_lower for k in files)


def _get_file(files: Dict[str, str], name: str) -> str:
    """Get file content by name (case-insensitive). Returns '' if missing."""
    name_lower = name.lower()
    for k, v in files.items():
        if k.lower() == name_lower:
            return v
    return ""


def _has_heading(content: str, patterns: List[str]) -> bool:
    """Check if markdown content has a heading matching any pattern."""
    for pattern in patterns:
        if re.search(r'#+\s*' + pattern, content, re.IGNORECASE):
            return True
    return False


def _extract_code_blocks(content: str) -> List[str]:
    """Extract fenced code blocks from markdown."""
    return re.findall(r'```(?:python)?\s*\n(.*?)```', content, re.DOTALL)


def _is_valid_python(source: str) -> bool:
    """Check if source string is valid Python."""
    try:
        ast.parse(source)
        return True
    except SyntaxError:
        return False


def _get_python_files(files: Dict[str, str]) -> Dict[str, str]:
    """Get all .py source files (excluding __init__.py, setup.py, tests)."""
    result = {}
    for path, content in files.items():
        if not path.endswith('.py'):
            continue
        basename = path.split('/')[-1]
        if basename in ('__init__.py', 'setup.py'):
            continue
        if 'test' in path.lower() or 'example' in path.lower():
            continue
        result[path] = content
    return result


def _get_init_file(files: Dict[str, str]) -> str:
    """Get __init__.py content."""
    for path, content in files.items():
        if path.endswith('__init__.py'):
            return content
    return ""


# ---------------------------------------------------------------------------
# Task 1 (Easy): README + llms.txt
# ---------------------------------------------------------------------------

def _grade_readme(files: Dict[str, str]) -> tuple[Dict[str, float], List[str]]:
    """Grade README.md quality. Returns (checks, feedback)."""
    checks = {}
    feedback = []

    content = _get_file(files, "README.md")
    if not content:
        # Also check common variations
        content = _get_file(files, "readme.md")

    # 1. README exists
    exists = len(content) > 0
    checks["readme_exists"] = 1.0 if exists else 0.0
    if not exists:
        feedback.append("Missing README.md — create one with project documentation")
        return checks, feedback

    # 2. Installation section
    has_install = _has_heading(content, [r"install", r"getting\s*started", r"setup"])
    checks["readme_installation"] = 1.0 if has_install else 0.0
    if not has_install:
        feedback.append("README missing Installation/Setup section")

    # 3. Usage / Quickstart section
    has_usage = _has_heading(content, [r"usage", r"quick\s*start", r"getting\s*started", r"how\s*to\s*use"])
    checks["readme_usage"] = 1.0 if has_usage else 0.0
    if not has_usage:
        feedback.append("README missing Usage/Quickstart section")

    # 4. API reference section
    has_api = _has_heading(content, [r"api", r"reference", r"functions", r"methods", r"modules"])
    checks["readme_api"] = 1.0 if has_api else 0.0
    if not has_api:
        feedback.append("README missing API Reference section")

    # 5. Has code blocks
    code_blocks = _extract_code_blocks(content)
    checks["readme_code_blocks"] = 1.0 if len(code_blocks) > 0 else 0.0
    if not code_blocks:
        feedback.append("README has no code examples (add ```python blocks)")

    # 6. Code blocks are valid Python
    if code_blocks:
        valid = sum(1 for b in code_blocks if _is_valid_python(b))
        checks["readme_valid_code"] = valid / len(code_blocks)
        if valid < len(code_blocks):
            feedback.append(f"README has {len(code_blocks) - valid}/{len(code_blocks)} invalid Python code blocks")
    else:
        checks["readme_valid_code"] = 0.0

    # 7. Sufficient word count (>= 200 words)
    word_count = len(content.split())
    checks["readme_word_count"] = min(word_count / 200, 1.0)
    if word_count < 200:
        feedback.append(f"README too short ({word_count} words, aim for 200+)")

    return checks, feedback


def _grade_llms_txt(files: Dict[str, str]) -> tuple[Dict[str, float], List[str]]:
    """Grade llms.txt quality."""
    checks = {}
    feedback = []

    content = _get_file(files, "llms.txt")

    # 1. llms.txt exists
    exists = len(content) > 0
    checks["llms_txt_exists"] = 1.0 if exists else 0.0
    if not exists:
        feedback.append("Missing llms.txt — create one following llmstxt.org format")
        return checks, feedback

    # 2. Has structure (headings with #)
    has_headings = bool(re.search(r'^#\s+', content, re.MULTILINE))
    checks["llms_txt_structure"] = 1.0 if has_headings else 0.0
    if not has_headings:
        feedback.append("llms.txt lacks structure — add # headings")

    # 3. Has links or references
    has_links = bool(re.search(r'https?://|>\s*\[', content))
    checks["llms_txt_links"] = 1.0 if has_links else 0.0
    if not has_links:
        feedback.append("llms.txt has no links or references")

    return checks, feedback


def grade_easy(files: Dict[str, str]) -> GradeResult:
    """Grade Task 1: README + llms.txt."""
    readme_checks, readme_fb = _grade_readme(files)
    llms_checks, llms_fb = _grade_llms_txt(files)

    all_checks = {**readme_checks, **llms_checks}
    all_feedback = readme_fb + llms_fb

    # Weighted average — all checks equal weight
    score = sum(all_checks.values()) / len(all_checks) if all_checks else 0.0

    return GradeResult(score=round(score, 4), breakdown=all_checks, feedback=all_feedback)


# ---------------------------------------------------------------------------
# Task 2 (Medium): AI instruction files + project structure
# ---------------------------------------------------------------------------

def _grade_claude_md(files: Dict[str, str]) -> tuple[Dict[str, float], List[str]]:
    """Grade CLAUDE.md quality."""
    checks = {}
    feedback = []

    content = _get_file(files, "CLAUDE.md")

    checks["claude_md_exists"] = 1.0 if content else 0.0
    if not content:
        feedback.append("Missing CLAUDE.md — create one with project instructions for Claude")
        return checks, feedback

    has_overview = _has_heading(content, [r"overview", r"about", r"description", r"project"])
    checks["claude_md_overview"] = 1.0 if has_overview else 0.0
    if not has_overview:
        feedback.append("CLAUDE.md missing project overview section")

    has_commands = _has_heading(content, [r"command", r"build", r"run", r"develop", r"script"])
    checks["claude_md_commands"] = 1.0 if has_commands else 0.0
    if not has_commands:
        feedback.append("CLAUDE.md missing commands/build section")

    has_structure = _has_heading(content, [r"structure", r"directory", r"layout", r"architect"])
    checks["claude_md_structure"] = 1.0 if has_structure else 0.0
    if not has_structure:
        feedback.append("CLAUDE.md missing project structure section")

    return checks, feedback


def _grade_agents_md(files: Dict[str, str]) -> tuple[Dict[str, float], List[str]]:
    """Grade AGENTS.md quality."""
    checks = {}
    feedback = []

    content = _get_file(files, "AGENTS.md")
    if not content:
        content = _get_file(files, "agents.md")

    exists = len(content) > 0
    checks["agents_md_exists"] = 1.0 if exists else 0.0
    if not exists:
        feedback.append("Missing AGENTS.md — create one with AI agent instructions")
        return checks, feedback

    word_count = len(content.split())
    checks["agents_md_content"] = 1.0 if word_count >= 50 else min(word_count / 50, 1.0)
    if word_count < 50:
        feedback.append(f"AGENTS.md too short ({word_count} words, aim for 50+)")

    return checks, feedback


def _grade_structure(files: Dict[str, str]) -> tuple[Dict[str, float], List[str]]:
    """Grade project structure: .env.example, examples/, __init__.py __all__, py.typed."""
    checks = {}
    feedback = []

    # .env.example exists
    env_content = _get_file(files, ".env.example")
    checks["env_example_exists"] = 1.0 if env_content else 0.0
    if not env_content:
        feedback.append("Missing .env.example — list required environment variables")
    else:
        has_vars = bool(re.search(r'^[A-Z_]+=', env_content, re.MULTILINE))
        checks["env_example_vars"] = 1.0 if has_vars else 0.0
        if not has_vars:
            feedback.append(".env.example has no KEY=value entries")

    if not env_content:
        checks["env_example_vars"] = 0.0

    # examples/ folder has files
    has_examples = any(
        k.startswith("examples/") and k.endswith(".py") for k in files
    )
    checks["examples_exist"] = 1.0 if has_examples else 0.0
    if not has_examples:
        feedback.append("Missing examples/ folder with Python example files")

    # Examples are valid Python
    example_files = {k: v for k, v in files.items()
                     if k.startswith("examples/") and k.endswith(".py")}
    if example_files:
        valid = sum(1 for v in example_files.values() if _is_valid_python(v))
        checks["examples_valid"] = valid / len(example_files)
        if valid < len(example_files):
            feedback.append(f"{len(example_files) - valid}/{len(example_files)} example files have syntax errors")
    else:
        checks["examples_valid"] = 0.0

    # __init__.py has __all__
    init_content = _get_init_file(files)
    has_all = False
    if init_content:
        try:
            tree = ast.parse(init_content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == '__all__':
                            has_all = True
        except SyntaxError:
            pass
    checks["init_has_all"] = 1.0 if has_all else 0.0
    if not has_all:
        feedback.append("__init__.py missing __all__ — add explicit public API exports")

    # py.typed exists
    has_py_typed = _file_exists(files, "py.typed") or any(
        k.endswith("py.typed") for k in files
    )
    checks["py_typed_exists"] = 1.0 if has_py_typed else 0.0
    if not has_py_typed:
        feedback.append("Missing py.typed marker file (PEP 561)")

    # CONTRIBUTING.md exists with content
    contrib_content = _get_file(files, "CONTRIBUTING.md")
    checks["contributing_md_exists"] = 1.0 if contrib_content else 0.0
    if not contrib_content:
        feedback.append("Missing CONTRIBUTING.md — add contribution guidelines for developers and AI agents")
    else:
        contrib_words = len(contrib_content.split())
        checks["contributing_md_content"] = 1.0 if contrib_words >= 50 else min(contrib_words / 50, 1.0)
        if contrib_words < 50:
            feedback.append(f"CONTRIBUTING.md too short ({contrib_words} words, aim for 50+)")

    if not contrib_content:
        checks["contributing_md_content"] = 0.0

    # .pre-commit-config.yaml exists
    precommit_content = _get_file(files, ".pre-commit-config.yaml")
    checks["precommit_config_exists"] = 1.0 if precommit_content else 0.0
    if not precommit_content:
        feedback.append("Missing .pre-commit-config.yaml — add pre-commit hooks for fast feedback")

    return checks, feedback


def grade_medium(files: Dict[str, str]) -> GradeResult:
    """Grade Task 2: AI instruction files + project structure."""
    claude_checks, claude_fb = _grade_claude_md(files)
    agents_checks, agents_fb = _grade_agents_md(files)
    struct_checks, struct_fb = _grade_structure(files)

    all_checks = {**claude_checks, **agents_checks, **struct_checks}
    all_feedback = claude_fb + agents_fb + struct_fb

    score = sum(all_checks.values()) / len(all_checks) if all_checks else 0.0

    return GradeResult(score=round(score, 4), breakdown=all_checks, feedback=all_feedback)


# ---------------------------------------------------------------------------
# Task 3 (Hard): Everything + Python code quality
# ---------------------------------------------------------------------------

def _grade_type_hints(files: Dict[str, str]) -> tuple[float, List[str]]:
    """Grade type hint coverage across Python source files."""
    py_files = _get_python_files(files)
    if not py_files:
        return 0.0, ["No Python source files found"]

    total_funcs = 0
    annotated_funcs = 0

    for path, content in py_files.items():
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_funcs += 1
                args = node.args
                all_annotated = True
                for arg in args.args:
                    if arg.arg == 'self':
                        continue
                    if arg.annotation is None:
                        all_annotated = False
                        break
                if node.returns is None:
                    all_annotated = False
                if all_annotated:
                    annotated_funcs += 1

    if total_funcs == 0:
        return 1.0, []

    score = annotated_funcs / total_funcs
    feedback = []
    if score < 1.0:
        feedback.append(f"Type hints: {annotated_funcs}/{total_funcs} functions fully annotated ({score:.0%})")
    return score, feedback


def _grade_docstrings(files: Dict[str, str]) -> tuple[float, List[str]]:
    """Grade docstring coverage across Python source files."""
    py_files = _get_python_files(files)
    if not py_files:
        return 0.0, ["No Python source files found"]

    total_funcs = 0
    docstringed = 0

    for path, content in py_files.items():
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_funcs += 1
                if (node.body
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)):
                    docstringed += 1

    if total_funcs == 0:
        return 1.0, []

    score = docstringed / total_funcs
    feedback = []
    if score < 1.0:
        feedback.append(f"Docstrings: {docstringed}/{total_funcs} functions have docstrings ({score:.0%})")
    return score, feedback


def _grade_naming(files: Dict[str, str]) -> tuple[float, List[str]]:
    """Grade PEP 8 naming convention compliance."""
    py_files = _get_python_files(files)
    if not py_files:
        return 0.0, ["No Python source files found"]

    total_funcs = 0
    compliant = 0
    bad_names = []

    for path, content in py_files.items():
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_funcs += 1
                # PEP 8: lowercase_with_underscores, private can start with _
                if re.match(r'^_?[a-z][a-z0-9_]*$', node.name) and len(node.name) > 2:
                    compliant += 1
                else:
                    bad_names.append(node.name)

    if total_funcs == 0:
        return 1.0, []

    score = compliant / total_funcs
    feedback = []
    if bad_names:
        shown = bad_names[:5]
        extra = f" (+{len(bad_names) - 5} more)" if len(bad_names) > 5 else ""
        feedback.append(f"Naming: {len(bad_names)} functions don't follow PEP 8: {shown}{extra}")
    return score, feedback


def _grade_error_messages(files: Dict[str, str]) -> tuple[float, List[str]]:
    """Grade error message quality — exceptions should have descriptive messages."""
    py_files = _get_python_files(files)
    if not py_files:
        return 0.0, ["No Python source files found"]

    total_raises = 0
    descriptive = 0

    for path, content in py_files.items():
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise) and node.exc is not None:
                if isinstance(node.exc, ast.Call) and node.exc.args:
                    total_raises += 1
                    arg = node.exc.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        # Descriptive = more than 10 chars and not just "error" or "bad"
                        msg = arg.value.strip().lower()
                        if len(msg) > 10 and msg not in ('error', 'bad', 'invalid', 'failed'):
                            descriptive += 1
                    elif isinstance(arg, ast.JoinedStr):
                        # f-string — likely descriptive
                        descriptive += 1
                elif isinstance(node.exc, ast.Call) and not node.exc.args:
                    # raise Exception() with no message
                    total_raises += 1

    if total_raises == 0:
        return 1.0, []

    score = descriptive / total_raises
    feedback = []
    if score < 1.0:
        feedback.append(f"Error messages: {descriptive}/{total_raises} raises have descriptive messages ({score:.0%})")
    return score, feedback


def grade_hard(files: Dict[str, str]) -> GradeResult:
    """Grade Task 3: Everything (easy + medium + code quality)."""
    # Easy checks (25%)
    easy_result = grade_easy(files)
    # Medium checks (25%)
    medium_result = grade_medium(files)

    # Code quality checks (50%)
    type_score, type_fb = _grade_type_hints(files)
    doc_score, doc_fb = _grade_docstrings(files)
    naming_score, naming_fb = _grade_naming(files)
    error_score, error_fb = _grade_error_messages(files)

    code_score = (type_score + doc_score + naming_score + error_score) / 4

    # Composite score
    score = easy_result.score * 0.25 + medium_result.score * 0.25 + code_score * 0.50

    breakdown = {}
    # Prefix easy/medium checks
    for k, v in easy_result.breakdown.items():
        breakdown[f"easy_{k}"] = v
    for k, v in medium_result.breakdown.items():
        breakdown[f"medium_{k}"] = v
    # Code quality checks
    breakdown["code_type_hints"] = round(type_score, 4)
    breakdown["code_docstrings"] = round(doc_score, 4)
    breakdown["code_naming"] = round(naming_score, 4)
    breakdown["code_error_messages"] = round(error_score, 4)

    all_feedback = easy_result.feedback + medium_result.feedback + type_fb + doc_fb + naming_fb + error_fb

    return GradeResult(score=round(score, 4), breakdown=breakdown, feedback=all_feedback)


# ---------------------------------------------------------------------------
# Master grading function
# ---------------------------------------------------------------------------

def grade_project(project_files: Dict[str, str], task_id: str) -> GradeResult:
    """Grade a project based on the specified task."""
    if task_id == "easy":
        return grade_easy(project_files)
    elif task_id == "medium":
        return grade_medium(project_files)
    elif task_id == "hard":
        return grade_hard(project_files)
    else:
        return GradeResult(score=0.0, breakdown={}, feedback=[f"Unknown task: {task_id}"])

#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["questionary>=2.0"]
# ///

import json
import os
import subprocess
import sys
from pathlib import Path

import questionary
from questionary import Choice, Style


def get_myclaude_home():
    return Path(os.getenv("MYCLAUDE_HOME", None) or "~/.myclaude").expanduser()


def get_skills_path():
    return get_myclaude_home() / "skills"


def get_mcps_path():
    return get_myclaude_home() / "mcps.json"


PALETTE = {
    "teal_100": "#D8EDEB",
    "teal_200": "#B9DFDD",
    "teal_300": "#8CCBC7",
    "teal_400": "#4FAEA9",
    "teal_500": "#088177",
    "teal_600": "#06736A",
    "teal_700": "#066B63",
    "teal_800": "#05534D",
    "teal_900": "#033A35",
    "petrol_100": "#E9EEF2",
    "petrol_200": "#D2DEE6",
    "petrol_300": "#B4C9D4",
    "petrol_400": "#7FA4B1",
    "petrol_500": "#2B697A",
    "petrol_600": "#215A6A",
    "petrol_700": "#185161",
    "petrol_800": "#123D4A",
    "petrol_900": "#0C2A34",
    "wheat_100": "#F2ECE1",
    "wheat_200": "#EADBC4",
    "wheat_300": "#E1C5A1",
    "wheat_400": "#D7B27F",
    "wheat_500": "#C89D58",
    "wheat_600": "#A97E3C",
    "wheat_700": "#805B20",
    "wheat_800": "#5C3F14",
    "wheat_900": "#3A260C",
    "rhubarb_100": "#F5E1E3",
    "rhubarb_200": "#E9C5C9",
    "rhubarb_300": "#D9A3A9",
    "rhubarb_400": "#C77C84",
    "rhubarb_500": "#B55B64",
    "rhubarb_600": "#A14852",
    "rhubarb_700": "#99424B",
    "rhubarb_800": "#6F2E35",
    "rhubarb_900": "#4A1D22",
    "neutral_100": "#F2F2F2",
    "neutral_200": "#E9E9E9",
    "neutral_300": "#D9D9D9",
    "neutral_400": "#B6B6B6",
    "neutral_500": "#969696",
    "neutral_600": "#6D6D6D",
    "neutral_700": "#5A5A5A",
    "neutral_800": "#3B3B3B",
    "neutral_900": "#1B1B1B",
}

PRIMARY_TEXT = PALETTE["neutral_300"]
SECONDARY_TEXT = PALETTE["neutral_700"]
COLOR_USER = PALETTE["rhubarb_400"]
COLOR_REPO = PALETTE["wheat_400"]
COLOR_HIGHLIGHTED = PALETTE["neutral_400"]
COLOR_SELECTED = PALETTE["teal_400"]

CUSTOM_STYLE = Style(
    [
        ("question", f"fg:{PRIMARY_TEXT}"),
        ("pointer", f"fg:{COLOR_HIGHLIGHTED}"),
        ("highlighted", f"fg:{COLOR_HIGHLIGHTED}"),
        ("selected", f"noinherit fg:{COLOR_SELECTED}"),
        ("instruction", f"fg:{SECONDARY_TEXT} italic"),
        ("text", f"fg:{SECONDARY_TEXT}"),
    ]
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def ansi_fg(
    hex_color: str, bold: bool = False, dim: bool = False, italic: bool = False
) -> str:
    rgb = hex_color.lstrip("#")
    parts = []
    if bold:
        parts.append("1")
    if dim:
        parts.append("2")
    if italic:
        parts.append("3")
    parts.append(f"38;2;{int(rgb[0:2], 16)};{int(rgb[2:4], 16)};{int(rgb[4:6], 16)}")
    return "\x1b[" + ";".join(parts) + "m"


def colored(
    text: str,
    hex_color: str,
    *,
    bold: bool = False,
    dim: bool = False,
    italic: bool = False,
) -> str:
    return f"{ansi_fg(hex_color, bold=bold, dim=dim, italic=italic)}{text}\x1b[0m"


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def repo_root() -> Path:
    out = run(["git", "rev-parse", "--show-toplevel"])
    if not out:
        die("Not inside a git repository.")
    return Path(out)


def print_summary(primary: str, secondary: str, items: set[str], color: str) -> None:
    print(
        colored(" " + primary, color),
        colored(secondary, color, italic=True, dim=True),
        end="",
    )
    if items:
        content = " · ".join(
            sorted([colored(text, color, bold=True) for text in items])
        )
    else:
        content = colored("none", SECONDARY_TEXT, bold=True, italic=True)
    print(" " + content)


# ---------------------------------------------------------------------------
# MCP helpers (from mymcps.py)
# ---------------------------------------------------------------------------


def read_mcp_servers(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("mcpServers", {})
    except json.JSONDecodeError as e:
        die(f"Invalid JSON in {path}: {e}")
    return {}


def write_mcp_json(path: Path, servers: dict) -> None:
    path.write_text(json.dumps({"mcpServers": servers}, indent=2) + "\n")


def ensure_excluded(exclude_file: Path, entry: str) -> None:
    lines = exclude_file.read_text().splitlines() if exclude_file.exists() else []
    if entry not in lines:
        with exclude_file.open("a") as f:
            f.write(entry + "\n")


def get_mcps(root: Path) -> tuple[set[str], set[str]]:
    mcps_available = get_mcps_path()
    global_path = Path.home() / ".claude.json"
    local_path = root / ".mcp.json"

    available = read_mcp_servers(mcps_available)
    global_servers = read_mcp_servers(global_path)
    local_servers = read_mcp_servers(local_path)

    global_names = set(global_servers)
    available_names = {n for n in available if n not in global_servers}
    local_active = {n for n in available_names if n in local_servers}
    return global_names, local_active


def modify_mcps(root: Path) -> set[str]:
    mcps_available = get_mcps_path()
    global_path = Path.home() / ".claude.json"
    local_path = root / ".mcp.json"
    exclude_file = root / ".git" / "info" / "exclude"

    available = read_mcp_servers(mcps_available)
    if not available:
        print(f"  No available MCPs found in {mcps_available}.")
        return set()

    global_servers = read_mcp_servers(global_path)
    local_servers = read_mcp_servers(local_path)

    global_names = sorted(global_servers)
    available_names = sorted(n for n in available if n not in global_servers)
    active_local = {n for n in available_names if n in local_servers}

    if not available_names:
        print(f"  No additional MCPs available in {mcps_available}.")
        return set(global_names)

    choices = [
        Choice(title=name, value=name, checked=(name in active_local))
        for name in available_names
    ]

    question = questionary.checkbox(
        "Your local MCPs",
        choices=choices,
        style=CUSTOM_STYLE,
        qmark="",
        use_jk_keys=False,
        instruction="(space toggle, enter confirm, esc/q exit)",
        erase_when_done=True,
    )

    _bind_cancel_keys(question)
    selected = question.ask()

    if selected is None:
        want_active = active_local
    else:
        want_active = {n for n in selected if n in available_names}
        new_servers = {
            name: available[name] for name in available_names if name in want_active
        }
        write_mcp_json(local_path, new_servers)
        ensure_excluded(exclude_file, "mcp.json")

    return set(global_names) | want_active


# ---------------------------------------------------------------------------
# Skills helpers (from myskills.py)
# ---------------------------------------------------------------------------


def get_dir_names(dirpath: Path) -> set[str]:
    if not dirpath.exists():
        return set()
    return {p.name for p in dirpath.iterdir() if p.is_dir()}


def get_tracked_skills(root: Path, skills_dir_rel: str) -> set[str]:
    if not run(["git", "-C", str(root), "rev-parse", "--verify", "HEAD"]):
        return set()
    out = run(
        ["git", "-C", str(root), "ls-tree", "--name-only", f"HEAD:{skills_dir_rel}"]
    )
    if not out:
        return set()
    return {line for line in out.splitlines() if line}


def is_local_linked(local_skills_dir: Path, name: str) -> bool:
    return (local_skills_dir / name).exists()


def apply_skill(
    name: str,
    want_active: bool,
    skills_available: Path,
    local_skills_dir: Path,
    exclude_file: Path,
    skills_dir_rel: str,
) -> None:
    linked = is_local_linked(local_skills_dir, name)
    entry = f"{skills_dir_rel}/{name}"
    dest = local_skills_dir / name

    if want_active and not linked:
        local_skills_dir.mkdir(parents=True, exist_ok=True)
        dest.symlink_to(skills_available / name)
        lines = exclude_file.read_text().splitlines() if exclude_file.exists() else []
        if entry not in lines:
            with exclude_file.open("a") as f:
                f.write(entry + "\n")
    elif not want_active and linked:
        dest.unlink(missing_ok=True)
        if exclude_file.exists():
            lines = exclude_file.read_text().splitlines()
            lines = [ln for ln in lines if ln != entry]
            exclude_file.write_text("\n".join(lines) + ("\n" if lines else ""))


def get_active_skills(root: Path) -> set[str]:
    skills_dir_rel = ".claude/skills"
    skills_installed = Path.home() / skills_dir_rel
    skills_available = get_skills_path()
    local_skills_dir = root / skills_dir_rel

    installed = get_dir_names(skills_installed)
    available = get_dir_names(skills_available)
    tracked = get_tracked_skills(root, skills_dir_rel)

    eligible = {n for n in available if n not in tracked}
    active_local = {n for n in eligible if is_local_linked(local_skills_dir, n)}

    return installed | tracked | active_local


def get_skills_status(root: Path) -> tuple[set[str], set[str], set[str]]:
    skills_dir_rel = ".claude/skills"
    skills_installed = Path.home() / skills_dir_rel
    skills_available = get_skills_path()
    local_skills_dir = root / skills_dir_rel

    installed = get_dir_names(skills_installed)
    available = get_dir_names(skills_available)
    tracked = get_tracked_skills(root, skills_dir_rel)
    eligible = {n for n in available if n not in tracked}
    local_active = {n for n in eligible if is_local_linked(local_skills_dir, n)}

    return installed, tracked, local_active


def modify_skills(root: Path) -> set[str]:
    skills_dir_rel = ".claude/skills"
    skills_installed = Path.home() / skills_dir_rel
    skills_available = get_skills_path()
    local_skills_dir = root / skills_dir_rel
    exclude_file = root / ".git/info/exclude"

    installed = get_dir_names(skills_installed)
    available = get_dir_names(skills_available)
    tracked = get_tracked_skills(root, skills_dir_rel)

    eligible_skills = [n for n in available if n not in tracked]
    if not eligible_skills:
        print(f"  No local skills available in {skills_available}.")
        return installed | tracked

    active_skills = {n for n in eligible_skills if is_local_linked(local_skills_dir, n)}

    choices = [
        Choice(title=name, value=name, checked=(name in active_skills))
        for name in sorted(eligible_skills)
    ]

    question = questionary.checkbox(
        "Your skills",
        choices=choices,
        style=CUSTOM_STYLE,
        qmark="",
        use_jk_keys=False,
        instruction="(↑↓ navigate, space toggle, enter confirm, esc/q exit)",
        erase_when_done=True,
    )

    _bind_cancel_keys(question)
    selected = question.ask()

    if selected is None:
        want_active_names = active_skills
    else:
        want_active_names = set(selected)
        for name in eligible_skills:
            apply_skill(
                name,
                name in want_active_names,
                skills_available,
                local_skills_dir,
                exclude_file,
                skills_dir_rel,
            )

    return installed | tracked | want_active_names


# ---------------------------------------------------------------------------
# Shared key-binding helper
# ---------------------------------------------------------------------------


def _bind_cancel_keys(question) -> None:
    @question.application.key_bindings.add("q", eager=True)
    def _cancel_q(event) -> None:
        event.app.exit(result=None)

    @question.application.key_bindings.add("c-c", eager=True)
    def _cancel_ctrl_c(event) -> None:
        event.app.exit(result=None)

    @question.application.key_bindings.add("escape", eager=True)
    def _cancel_esc(event) -> None:
        event.app.exit(result=None)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

ACCEPT = "accept"
MODIFY_MCPS = "mcps"
MODIFY_SKILLS = "skills"
QUIT = "quit"


def print_status(root: Path) -> None:
    global_mcps, local_mcps = get_mcps(root)
    user_skills, repo_skills, local_skills = get_skills_status(root)

    print_summary(
        "User MCPs",
        "(always active, installed in ~/.claude.json):",
        global_mcps,
        COLOR_USER,
    )
    print_summary(
        "User skills",
        "(always active, installed in ~/.claude/skills):",
        user_skills,
        COLOR_USER,
    )

    print_summary(
        "Repository skills",
        "(always active, git committed in <git_root>/.claude/skills):",
        repo_skills,
        COLOR_REPO,
    )

    print_summary(
        "Your local MCPs",
        "(use myclaude to add/remove, git ignored in <git_root>/mcp.json):",
        local_mcps,
        COLOR_SELECTED,
    )
    print_summary(
        "Your local skills",
        "(use myclaude to add/remove, git ignored in <git_root>/.claude/skills):",
        local_skills,
        COLOR_SELECTED,
    )


def prompt_action() -> str:
    choices = [
        Choice(title="Launch claude", value=ACCEPT),
        Choice(title="Modify MCPs", value=MODIFY_MCPS),
        Choice(title="Modify skills", value=MODIFY_SKILLS),
        Choice(title="Quit", value=QUIT),
    ]

    question = questionary.select(
        "What would you like to do?",
        choices=choices,
        style=CUSTOM_STYLE,
        qmark="",
        instruction="(↑↓ navigate, enter confirm, esc/q exit)",
        use_shortcuts=False,
        erase_when_done=True,
    )

    _bind_cancel_keys(question)
    return question.ask() or QUIT


def main() -> None:
    root = repo_root()

    _printed = False

    def _print_status():
        nonlocal _printed
        if _printed:
            print("\033[F\033[K" * 6, end="")
        print_status(root)
        print()
        _printed = True

    while True:
        _print_status()

        action = prompt_action()

        if action == QUIT:
            _print_status()
            exit(22)
        if action == ACCEPT:
            _print_status()
            break
        elif action == MODIFY_MCPS:
            modify_mcps(root)
        elif action == MODIFY_SKILLS:
            modify_skills(root)


def _print_palette() -> None:
    groups: dict[str, list[tuple[str, str]]] = {}
    for key, hex_color in PALETTE.items():
        prefix = key.rsplit("_", 1)[0]
        groups.setdefault(prefix, []).append((key, hex_color))
    for prefix, swatches in groups.items():
        row = ""
        for key, hex_color in swatches:
            label = key.split("_")[-1]
            row += colored(f" {label} ", hex_color, bold=True)
            row += colored(f" {hex_color} ", hex_color)
            row += "  "
        print(f"{colored(f'{prefix:<10}', PALETTE['neutral_400'], italic=True)}  {row}")


if __name__ == "__main__":
    # _print_palette()
    main()

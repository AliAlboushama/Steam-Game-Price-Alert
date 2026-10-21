"""
Terminal look: one place for colours, the title bar, tables and prompts.
Colours follow the Steam store (navy background, blue accent, green discount badge).
"""
import sys
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

VERSION = "2.0.1"

THEME = Theme({
    "accent": "bold #66c0f4",     # Steam blue
    "muted": "#8f98a0",
    "title": "bold #ffffff on #1b2838",
    "price": "bold #beee11",      # Steam sale green
    "old": "strike #8f98a0",
    "badge": "bold #beee11 on #4c6b22",
    "good": "bold #a1cd44",
    "warn": "bold #e5c07b",
    "bad": "bold #e06c75",
    "gold": "bold #ffd166",
    "name": "bold #ffffff",
})

# Logs (systemd, Docker) aren't terminals: no colours, and a fixed width so tables don't squash
console = Console(theme=THEME, highlight=False,
                  width=None if sys.stdout is not None and sys.stdout.isatty() else 110)

def clear():
    """Clear the screen (only when it's a real terminal)."""
    if console.is_terminal:
        console.clear()

def header(section, info=""):
    """Full-width title bar: 'STEAM PRICE ALERT  /  Section ........ info'."""
    clear()
    width = console.width
    left = Text(" STEAM PRICE ALERT ", style="bold #ffffff on #1b2838")
    left.append(f" {section} ", style="bold #66c0f4 on #1b2838")
    right = Text(f" {info}  v{VERSION} " if info else f" v{VERSION} ", style="#8f98a0 on #1b2838")
    pad = max(0, width - left.cell_len - right.cell_len)
    console.print(Text.assemble(left, Text(" " * pad, style="on #1b2838"), right))
    console.print()

def table(*columns, **kwargs):
    """A table in the house style: no outer box, a thin line under the header."""
    t = Table(box=box.SIMPLE_HEAD, header_style="muted", pad_edge=False, show_edge=False, **kwargs)
    for col in columns:
        if isinstance(col, tuple):
            t.add_column(col[0], **col[1])
        else:
            t.add_column(col)
    return t

def discount_badge(percent):
    """Steam-style ' -70% ' badge, or empty text when there's no discount."""
    return Text(f" -{percent}% ", style="badge") if percent else Text("")

def price_text(info):
    """'17,99€' in green with the old price struck through, or a plain status."""
    if not info or info.get('final') is None:
        if info and info.get('is_free'):
            return Text("Free to play", style="good")
        if info and info.get('coming_soon'):
            return Text("Coming soon", style="muted")
        return Text("Not sold right now", style="muted")
    text = Text()
    if info.get('discount_percent', 0) > 0 and info.get('initial_formatted'):
        text.append(info['initial_formatted'], style="old")
        text.append("  ")
        text.append(info['final_formatted'], style="price")
    else:
        text.append(info['final_formatted'], style="name")
    return text

def menu(options):
    """Two-column menu. options = [(key, label), ...]."""
    grid = Table.grid(padding=(0, 4))
    grid.add_column(); grid.add_column()
    half = (len(options) + 1) // 2
    left, right = options[:half], options[half:]
    key_width = max(len(key) for key, _ in options)
    for i in range(half):
        cells = []
        for column in (left, right):
            if i < len(column):
                key, label = column[i]
                cells.append(Text.assemble((f" {key.rjust(key_width)} ", "accent"), f" {label}"))
            else:
                cells.append(Text(""))
        grid.add_row(*cells)
    console.print(grid)
    console.print()

def ask(prompt):
    """Prompt with the accent arrow and return the stripped answer."""
    return console.input(f"[accent]›[/] {prompt}").strip()

def pause(message="Press Enter to go back"):
    console.input(f"\n[muted]{message}[/]")

def ok(message):
    console.print(f"[good]✓[/] {message}")

def warn(message):
    console.print(f"[warn]![/] {message}")

def error(message):
    console.print(f"[bad]✗[/] {message}")

def note(message):
    console.print(f"[muted]{message}[/]")

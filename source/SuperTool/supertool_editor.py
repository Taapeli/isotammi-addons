#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2026          Kari Kujansuu
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

"""
PythonCodeView: a Gtk.TextView subclass suitable for editing Python code.

Features:
  - Tab key inserts spaces (default: 4) instead of a literal tab character.
  - Shift+Tab dedents the current line (or all selected lines).
  - Tab on a multi-line selection indents every selected line.
  - Enter/Return auto-indents the new line to match the previous line's
    indentation, and adds one extra indent level if the previous line
    ends with ':' (start of a block).
  - Backspace at the start of the indentation "outdents" by one tab-width
    instead of deleting a single space, when the cursor is only preceded
    by whitespace on the current line.
  - Syntax highlighting (keywords, builtins, strings, comments, numbers,
    decorators, and def/class names), driven by the stdlib `tokenize`
    module and refreshed on a short debounce after each edit.

Requires: PyGObject (python3-gi), GTK 3.

Author: Kari Kujansuu with Claude AI
"""

import builtins
import io
import keyword
import tokenize

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango, GLib


class PythonCodeView(Gtk.TextView):
    def __init__(self, tab_width=4, **kwargs):
        super().__init__(**kwargs)

        self.tab_width = tab_width

        # Editor niceties.
        self.set_monospace(True)
        self.set_wrap_mode(Gtk.WrapMode.NONE)
        self.set_left_margin(6)
        self.set_right_margin(6)

        # Tell GTK the tab stop width (purely visual; we never actually
        # insert real tab characters ourselves).
        self.set_tab_width(self.tab_width)

        self.connect("key-press-event", self._on_key_press)

        # -- syntax highlighting setup --
        self._builtin_names = set(dir(builtins))
        self._keyword_names = set(keyword.kwlist) | set(getattr(keyword, "softkwlist", []))
        self._highlight_source_id = None
        self._setup_highlight_tags(self.get_buffer())
        self.get_buffer().connect("changed", self._schedule_highlight)
        # Highlight whatever is already in the buffer (e.g. set via set_text
        # before this signal was connected, or text loaded programmatically).
        GLib.idle_add(self._do_highlight)

    # -- syntax highlighting ------------------------------------------

    def _setup_highlight_tags(self, buf):
        table = buf.get_tag_table()
        specs = {
            "py-keyword": {"foreground": "#0000AA", "weight": Pango.Weight.BOLD},
            "py-builtin": {"foreground": "#007070"},
            "py-string": {"foreground": "#008000"},
            "py-comment": {"foreground": "#888888", "style": Pango.Style.ITALIC},
            "py-number": {"foreground": "#AA00AA"},
            "py-decorator": {"foreground": "#AA5500"},
            "py-defname": {"foreground": "#aa0000", "weight": Pango.Weight.BOLD},
            "py-self": {"foreground": "#AA5500", "style": Pango.Style.ITALIC},
        }
        self._tag_names = list(specs.keys())
        for name, props in specs.items():
            if table.lookup(name) is not None:
                continue
            buf.create_tag(name, **props)

    def _schedule_highlight(self, *_args):
        if self._highlight_source_id is not None:
            GLib.source_remove(self._highlight_source_id)
        self._highlight_source_id = GLib.timeout_add(150, self._do_highlight)

    def _do_highlight(self):
        self._highlight_source_id = None
        buf = self.get_buffer()
        start, end = buf.get_bounds()
        text = buf.get_text(start, end, True)

        for name in self._tag_names:
            buf.remove_tag_by_name(name, start, end)

        line_count = buf.get_line_count()

        def iter_at(row, col):
            # tokenize rows are 1-based; clamp defensively since partially
            # typed code (e.g. an unterminated string) can yield positions
            # past the buffer's current bounds.
            line = max(0, min(row - 1, line_count - 1))
            it = buf.get_iter_at_line(line)
            line_len = it.copy()
            if not line_len.ends_line():
                line_len.forward_to_line_end()
            max_col = line_len.get_line_offset()
            it.set_line_offset(min(col, max_col))
            return it

        def tag_range(name, start_rc, end_rc):
            s = iter_at(*start_rc)
            e = iter_at(*end_rc)
            buf.apply_tag_by_name(name, s, e)

        prev_tok = None  # (toktype, string) of the previous significant token
        try:
            for tok in tokenize.generate_tokens(io.StringIO(text).readline):
                toktype, tokstr, start_rc, end_rc, _line = tok

                if toktype == tokenize.COMMENT:
                    tag_range("py-comment", start_rc, end_rc)
                elif toktype == tokenize.STRING:
                    tag_range("py-string", start_rc, end_rc)
                elif toktype == tokenize.NUMBER:
                    tag_range("py-number", start_rc, end_rc)
                elif toktype == tokenize.OP and tokstr == "@":
                    tag_range("py-decorator", start_rc, end_rc)
                elif toktype == tokenize.NAME:
                    if prev_tok and prev_tok[0] == tokenize.OP and prev_tok[1] == "@":
                        tag_range("py-decorator", start_rc, end_rc)
                    elif tokstr in ("self", "cls"):
                        tag_range("py-self", start_rc, end_rc)
                    elif tokstr in self._keyword_names:
                        tag_range("py-keyword", start_rc, end_rc)
                        if tokstr in ("def", "class"):
                            prev_tok = (toktype, tokstr)
                            continue
                    elif prev_tok and prev_tok[0] == tokenize.NAME and prev_tok[1] in ("def", "class"):
                        tag_range("py-defname", start_rc, end_rc)
                    elif tokstr in self._builtin_names:
                        tag_range("py-builtin", start_rc, end_rc)

                if toktype not in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT):
                    prev_tok = (toktype, tokstr)
        except (tokenize.TokenError, IndentationError, SyntaxError):
            # Typical while mid-edit (e.g. an unterminated string or an
            # unbalanced bracket) -- just keep whatever we managed to tag.
            pass
        except Exception:
            # Never let a highlighting glitch break editing.
            pass

        return False

    # -- helpers ----------------------------------------------------

    def set_tab_width(self, width):
        self.tab_width = width
        font_desc = Pango.FontDescription("Monospace")
        layout = self.create_pango_layout(" " * width)
        layout.set_font_description(font_desc)
        char_width = layout.get_pixel_size()[0]
        tabs = Pango.TabArray.new(1, True)
        tabs.set_tab(0, Pango.TabAlign.LEFT, char_width)
        self.set_tabs(tabs)

    def _get_indent_str(self):
        return " " * self.tab_width

    def _line_bounds(self, buf, it):
        """Return (line_start_iter, line_end_iter) for the line containing it."""
        start = it.copy()
        start.set_line(it.get_line())
        end = start.copy()
        if not end.ends_line():
            end.forward_to_line_end()
        return start, end

    def _line_text(self, buf, it):
        start, end = self._line_bounds(buf, it)
        return buf.get_text(start, end, False)

    def _leading_whitespace(self, text):
        i = 0
        while i < len(text) and text[i] in (" ", "\t"):
            i += 1
        return text[:i]

    def _strip_trailing_comment(self, line):
        """Return line with a trailing '# ...' comment removed, ignoring
        '#' characters that appear inside string literals. This is a
        best-effort, single-line heuristic (it doesn't track whether we're
        already inside a triple-quoted string from a previous line)."""
        in_str = False
        quote = ""
        i = 0
        n = len(line)
        while i < n:
            c = line[i]
            if in_str:
                if c == "\\":
                    i += 2
                    continue
                if c == quote:
                    in_str = False
                i += 1
                continue
            if c in ("'", '"'):
                in_str = True
                quote = c
                i += 1
                continue
            if c == "#":
                return line[:i]
            i += 1
        return line

    # -- indent / dedent on selections -------------------------------

    def _indent_selection(self, buf, shrink=False):
        bounds = buf.get_selection_bounds()
        indent = self._get_indent_str()

        if not bounds:
            it = buf.get_iter_at_mark(buf.get_insert())
            start_line = end_line = it.get_line()
        else:
            start_it, end_it = bounds
            start_line = start_it.get_line()
            end_line = end_it.get_line()
            # If selection ends exactly at column 0 of a line, don't
            # include that trailing line (matches typical editor behavior).
            if end_it.get_line_offset() == 0 and end_line > start_line:
                end_line -= 1

        buf.begin_user_action()
        for line in range(start_line, end_line + 1):
            it = buf.get_iter_at_line(line)
            if shrink:
                text = self._line_text(buf, it)
                remove = 0
                while remove < self.tab_width and remove < len(text) and text[remove] == " ":
                    remove += 1
                if remove == 0 and text[:1] == "\t":
                    remove = 1
                if remove:
                    end = it.copy()
                    end.forward_chars(remove)
                    buf.delete(it, end)
            else:
                buf.insert(it, indent)
        buf.end_user_action()
        return True

    # -- key handling -------------------------------------------------

    def _on_key_press(self, widget, event):
        buf = self.get_buffer()
        keyval = event.keyval
        state = event.state

        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)

        # Tab / Shift+Tab
        if keyval in (Gdk.KEY_Tab, Gdk.KEY_KP_Tab, Gdk.KEY_ISO_Left_Tab):
            has_selection = buf.get_has_selection()
            if keyval == Gdk.KEY_ISO_Left_Tab or shift:
                return self._indent_selection(buf, shrink=True)
            if has_selection:
                return self._indent_selection(buf, shrink=False)
            # No selection: just insert spaces at the cursor.
            buf.begin_user_action()
            buf.delete_selection(True, True)
            buf.insert_at_cursor(self._get_indent_str())
            buf.end_user_action()
            return True

        # Enter / Return: auto-indent
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            it = buf.get_iter_at_mark(buf.get_insert())
            current_line = self._line_text(buf, it)
            # Only consider text up to the cursor for the ":" check /
            # for constructing the new indent (in case cursor is mid-line).
            cursor_col = it.get_line_offset()
            text_before_cursor = current_line[:cursor_col]

            indent = self._leading_whitespace(current_line)
            stripped = self._strip_trailing_comment(text_before_cursor).strip()

            extra = ""
            if stripped.endswith(":"):
                extra = self._get_indent_str()

            # Dedent automatically after certain keywords that typically
            # close a block early (optional nicety, comment out if unwanted).
            dedent_keywords = ("return", "pass", "break", "continue", "raise")
            if stripped in dedent_keywords or any(
                stripped == kw or stripped.startswith(kw + " ") or stripped.startswith(kw + "(")
                for kw in dedent_keywords
            ):
                pass  # keep same indent; only ':' increases it

            buf.begin_user_action()
            buf.delete_selection(True, True)
            buf.insert_at_cursor("\n" + indent + extra)
            buf.end_user_action()
            return True

        # Backspace: outdent when only whitespace precedes cursor on the line
        if keyval == Gdk.KEY_BackSpace and not buf.get_has_selection():
            it = buf.get_iter_at_mark(buf.get_insert())
            line_start = it.copy()
            line_start.set_line(it.get_line())
            text_before = buf.get_text(line_start, it, False)

            if text_before and text_before == " " * len(text_before):
                remove = len(text_before) % self.tab_width or self.tab_width
                remove = min(remove, len(text_before))
                start = it.copy()
                start.backward_chars(remove)
                buf.begin_user_action()
                buf.delete(start, it)
                buf.end_user_action()
                return True

        return False


# ---------------------------------------------------------------------
# Simple demo / smoke test
# ---------------------------------------------------------------------
if __name__ == "__main__":
    win = Gtk.Window(title="PythonCodeView demo")
    win.set_default_size(700, 500)
    win.connect("destroy", Gtk.main_quit)

    scroller = Gtk.ScrolledWindow()
    view = PythonCodeView(tab_width=4)
    buf = view.get_buffer()
    buf.set_text(
        "def example(x):\n"
        "    if x > 0:\n"
        "        return x\n"
        "    else:\n"
        "        return -x\n"
    )

    scroller.add(view)
    win.add(scroller)
    win.show_all()
    Gtk.main()
    

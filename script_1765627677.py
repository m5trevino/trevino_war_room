# 1. CLEANUP: Remove the system-wide one I pushed earlier (if it exists)
sudo rm -f /usr/local/bin/merger

# 2. OVERWRITE: Update your local binary
cat << 'EOF' > /home/flintx/.local/bin/merge
#!/usr/bin/env python3
import curses
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# ─── CONFIGURATION ───
# IGNORE LIST (The Filter)
BLACKLIST_DIRS = {".venv", "venv", "env", ".git", "__pycache__", "node_modules", "dist", "build", ".idea", ".vscode", "dropzone_storage", ".mypy_cache", "target", "bin", "obj", "__pypackages__", "site-packages"}
BLACKLIST_EXT = {".pyc", ".o", ".exe", ".dll", ".so", ".bin", ".db", ".sqlite", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip", ".tar", ".gz", ".pdf", ".svg", ".ttf", ".woff", ".woff2"}

CONFIG_PATH = Path.home() / ".config" / "merge_master" / "config.json"
DEFAULT_OUT = Path.home() / "merged"
BANNER = [
    "░▒▓██████████████▓▒░░▒▓████████▓▒░▒▓███████▓▒░ ░▒▓██████▓▒░░▒▓████████▓▒░▒▓███████▓▒░",
    "░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░",
    "░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░",
    "░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓██████▓▒░ ░▒▓███████▓▒░░▒▓█▓▒▒▓███▓▒░▒▓██████▓▒░ ░▒▓█▓▒░░▒▓█▓▒░",
    "░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░",
    "░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░",
    "░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░░▒▓████████▓▒░▒▓███████▓▒░"
]

class FileObj:
    def __init__(self, path):
        self.path = path
        self.rel_path = path
        self.ext = path.suffix.lower() if path.suffix else "no_ext"
        self.size = path.stat().st_size
        self.included = False

def load_config():
    if not CONFIG_PATH.exists():
        return {"presets": {}, "ignore": []}
    try: return json.loads(CONFIG_PATH.read_text())
    except: return {"presets": {}, "ignore": []}

def scan_files(root_dir, config):
    ignore_patterns = config.get("ignore", [])
    # Merge config ignores with hardcoded blacklist
    active_blacklist = BLACKLIST_DIRS.union(set(ignore_patterns))
    
    files = []
    root_path = Path(root_dir).resolve()
    
    for p in root_path.rglob("*"):
        if not p.is_file(): continue
        
        # 1. Check path parts against blacklist dirs
        if any(part in active_blacklist for part in p.parts): continue
        
        # 2. Check extension against blacklist ext
        if p.suffix.lower() in BLACKLIST_EXT: continue
        
        # 3. Check hidden files (optional, usually good to ignore .DS_Store etc)
        if p.name.startswith("."): continue
        
        f_obj = FileObj(p)
        try: f_obj.rel_path = p.relative_to(root_path)
        except: f_obj.rel_path = p
        files.append(f_obj)
    
    files.sort(key=lambda x: str(x.rel_path))
    return files, root_path

def get_tree_diagram(files):
    lines = ["# PROJECT MAP:"]
    for f in files:
        lines.append(f"# ├── {f.rel_path}")
    return "\n".join(lines) + "\n"

# ─── UI ENGINE ───
class App:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.config = load_config()
        self.root = Path.cwd()
        self.files, self.abs_root = scan_files(self.root, self.config)
        self.presets = self.config.get("presets", {})
        
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_CYAN, -1)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(4, curses.COLOR_MAGENTA, -1)
        curses.init_pair(5, curses.COLOR_YELLOW, -1)
        
        self.run_main_menu()

    def run_main_menu(self):
        opts = ["PRESET: DEV CORE (Code Only)", "PRESET: ALL TEXT", "CUSTOM: Select Extensions", "EXIT"]
        cur = 0
        while True:
            self.stdscr.clear()
            h, w = self.stdscr.getmaxyx()
            
            # Banner Logic
            if h > 20 and w > 90:
                for i, line in enumerate(BANNER):
                    self.stdscr.addstr(1 + i, (w - len(line)) // 2, line, curses.color_pair(1) | curses.A_BOLD)
                offset = 10
            else:
                self.stdscr.addstr(1, 2, "MERGE MASTER V3.0", curses.color_pair(1) | curses.A_BOLD)
                offset = 3

            for i, opt in enumerate(opts):
                style = curses.color_pair(3) if i == cur else curses.color_pair(1)
                self.stdscr.addstr(offset + i, 4, f" {opt} ", style)
            
            key = self.stdscr.getch()
            if key == curses.KEY_UP: cur = (cur - 1) % len(opts)
            elif key == curses.KEY_DOWN: cur = (cur + 1) % len(opts)
            elif key == 10:
                if cur == 0: self.apply_preset("dev_core"); break
                if cur == 1: self.apply_preset("all"); break
                if cur == 2: self.run_ext_menu(); break
                if cur == 3: sys.exit(0)

    def apply_preset(self, name):
        if name == "all":
            for f in self.files: f.included = True
        elif name == "dev_core":
            code_exts = {".py", ".js", ".html", ".css", ".sh", ".c", ".cpp", ".rs", ".go", ".java", ".md", ".json", ".yaml", ".toml", ".sql"}
            for f in self.files:
                if f.ext in code_exts: f.included = True
        else:
            patterns = self.presets.get(name, [])
            for f in self.files:
                if any(f.path.match(p) for p in patterns): f.included = True
        self.run_staging()

    def run_ext_menu(self):
        ext_map = {}
        for f in self.files: ext_map.setdefault(f.ext, []).append(f)
        exts = sorted(ext_map.keys())
        selection = {e: False for e in exts}
        cur = 0
        while True:
            self.stdscr.clear()
            h, w = self.stdscr.getmaxyx()
            self.draw_box(0, 0, h-1, w//2 - 1, "EXTENSIONS (Space: Toggle)")
            for i, e in enumerate(exts):
                if i >= h-4: break
                mark = "[x]" if selection[e] else "[ ]"
                style = curses.color_pair(3) if i == cur else curses.color_pair(1)
                self.stdscr.addstr(1+i, 2, f"{mark} {e} ({len(ext_map[e])})", style)
            self.draw_box(0, w//2, h-1, w-1, "PREVIEW")
            if exts:
                curr_ext = exts[cur]
                for i, f in enumerate(ext_map[curr_ext]):
                    if i >= h-4: break
                    self.stdscr.addstr(1+i, w//2 + 2, str(f.rel_path)[:w//2-4], curses.color_pair(5))
            self.stdscr.addstr(h-1, 2, "ENTER: Confirm | q: Back", curses.color_pair(2))
            key = self.stdscr.getch()
            if key == curses.KEY_UP: cur = max(0, cur - 1)
            elif key == curses.KEY_DOWN: cur = min(len(exts) - 1, cur + 1)
            elif key == ord(' '): selection[exts[cur]] = not selection[exts[cur]]
            elif key == ord('q'): self.run_main_menu(); return
            elif key == 10:
                for e, sel in selection.items():
                    if sel: 
                        for f in ext_map[e]: f.included = True
                self.run_staging()
                return

    def run_staging(self):
        active_pane = 0; cur_inc = 0; cur_exc = 0
        while True:
            self.stdscr.clear()
            h, w = self.stdscr.getmaxyx()
            mid = w // 2
            inc_files = [f for f in self.files if f.included]
            exc_files = [f for f in self.files if not f.included]
            size_str = f"{sum(f.size for f in inc_files)/1024:.1f}KB"
            
            style_inc = curses.color_pair(2) | curses.A_BOLD if active_pane == 0 else curses.color_pair(2)
            style_exc = curses.color_pair(2) | curses.A_BOLD if active_pane == 1 else curses.color_pair(2)
            
            self.draw_box(0, 0, h-3, mid-1, f"INCLUDED ({len(inc_files)})", style_inc)
            self.draw_box(0, mid, h-3, w-1, f"EXCLUDED ({len(exc_files)})", style_exc)
            
            for i, f in enumerate(inc_files):
                if i >= h-6: break
                style = curses.color_pair(3) if (active_pane == 0 and i == cur_inc) else curses.color_pair(1)
                self.stdscr.addstr(1+i, 2, str(f.rel_path)[:mid-4], style)
            for i, f in enumerate(exc_files):
                if i >= h-6: break
                style = curses.color_pair(3) if (active_pane == 1 and i == cur_exc) else curses.color_pair(4)
                self.stdscr.addstr(1+i, mid+2, str(f.rel_path)[:mid-4], style)
                
            status = f" FILES: {len(inc_files)} | SIZE: {size_str} "
            self.stdscr.addstr(h-2, (w-len(status))//2, status, curses.color_pair(3))
            self.stdscr.addstr(h-1, 2, "[TAB] Switch [SPACE] Toggle [ENTER] GENERATE", curses.color_pair(5))
            
            key = self.stdscr.getch()
            if key == 9: active_pane = 1 - active_pane
            elif key == curses.KEY_UP:
                if active_pane == 0: cur_inc = max(0, cur_inc - 1)
                else: cur_exc = max(0, cur_exc - 1)
            elif key == curses.KEY_DOWN:
                if active_pane == 0: cur_inc = min(len(inc_files)-1, cur_inc + 1)
                else: cur_exc = min(len(exc_files)-1, cur_exc + 1)
            elif key == ord(' '):
                if active_pane == 0 and inc_files:
                    inc_files[cur_inc].included = False
                    cur_inc = max(0, cur_inc - 1)
                elif active_pane == 1 and exc_files:
                    exc_files[cur_exc].included = True
                    cur_exc = max(0, cur_exc - 1)
            elif key == 10:
                if not inc_files: continue
                self.run_finalize(inc_files)
                return

    def run_finalize(self, final_files):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        def_name = f"merged_payload_{ts}.txt"
        
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        
        # Draw Box
        box_h, box_w = 8, 50
        y, x = (h - box_h)//2, (w - box_w)//2
        self.draw_box(y, x, y+box_h, x+box_w, "GENERATING PAYLOAD", curses.color_pair(2) | curses.A_BOLD)
        
        # Generation Logic
        sep = "=" * 60
        tree = get_tree_diagram(final_files)
        
        full_content = []
        full_content.append(f"# {sep}")
        full_content.append(f"# MERGED PAYLOAD - {datetime.now()}")
        full_content.append(f"# SOURCE: {self.abs_root}")
        full_content.append(f"# {sep}\n")
        full_content.append(tree)
        full_content.append("\n")
        
        for f in final_files:
            try:
                try: text = f.path.read_text(encoding='utf-8')
                except: text = f.path.read_bytes().decode('latin-1', errors='replace')
                
                delimiter = "EOF"
                if "EOF" in text: delimiter = "LIMIT"
                
                full_content.append(f"# {sep}")
                full_content.append(f"# FILE: {f.rel_path}")
                full_content.append(f"# {sep}")
                
                dir_name = f.rel_path.parent
                if str(dir_name) != ".":
                    full_content.append(f"mkdir -p \"{dir_name}\"")
                
                full_content.append(f"cat << '{delimiter}' > \"{f.rel_path}\"")
                full_content.append(text)
                full_content.append(f"{delimiter}\n")
            except Exception as e:
                full_content.append(f"# ERROR: {e}\n")
        
        final_str = "\n".join(full_content)
        
        # Save
        DEFAULT_OUT.mkdir(parents=True, exist_ok=True)
        final_file = DEFAULT_OUT / def_name
        final_file.write_text(final_str, encoding='utf-8')
        
        # Clipboard
        msg = f"SAVED: {final_file.name}"
        try:
            p = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
            p.communicate(input=final_str.encode('utf-8'))
            msg += " | COPIED TO CLIPBOARD"
        except:
            msg += " | NO CLIPBOARD (install xclip)"
            
        self.stdscr.addstr(y+3, x+3, msg[:box_w-6], curses.color_pair(5))
        self.stdscr.addstr(y+5, x+3, "PRESS ANY KEY TO EXIT", curses.color_pair(1))
        self.stdscr.getch()
        sys.exit(0)

    def draw_box(self, y1, x1, y2, x2, title, color=None):
        if color is None: color = curses.color_pair(2)
        try:
            self.stdscr.vline(y1+1, x1, curses.ACS_VLINE, y2-y1-1, color)
            self.stdscr.vline(y1+1, x2, curses.ACS_VLINE, y2-y1-1, color)
            self.stdscr.hline(y1, x1+1, curses.ACS_HLINE, x2-x1-1, color)
            self.stdscr.hline(y2, x1+1, curses.ACS_HLINE, x2-x1-1, color)
            self.stdscr.addch(y1, x1, curses.ACS_ULCORNER, color)
            self.stdscr.addch(y1, x2, curses.ACS_URCORNER, color)
            self.stdscr.addch(y2, x1, curses.ACS_LLCORNER, color)
            self.stdscr.addch(y2, x2, curses.ACS_LRCORNER, color)
            if title: self.stdscr.addstr(y1, x1+2, f" {title} ", color | curses.A_BOLD)
        except: pass

def main(stdscr):
    curses.curs_set(0)
    App(stdscr)

if __name__ == "__main__":
    curses.wrapper(main)
EOF
chmod +x /home/flintx/.local/bin/merge
⚡ DROP

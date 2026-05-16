"""
Desktop Pet - 桌面宠物小黄鸡
基于 Python tkinter 实现
集成 Ollama AI 对话功能
"""
import sys
import tkinter as tk
import tkinter.messagebox as messagebox
import random
import os
import json
import urllib.request
import urllib.parse
import threading
import subprocess
import shutil
from pathlib import Path


def _app_dir():
    """程序所在目录（源码运行或 PyInstaller 打包后均为 exe 同级目录）"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _local_data_dir():
    """用户数据与缓存：local-only/desktop-pet/"""
    import pony_local

    start = Path(__file__).resolve().parent
    pony_local.ensure_repo_on_path(start)
    pony_local.configure_pycache("desktop-pet", start=start)
    return str(pony_local.project_local_dir("desktop-pet", start=start))


def _migrate_data_file(filename: str, app_dir: str, data_dir: str) -> str:
    """从源码目录迁移到 local-only（若目标不存在）。"""
    os.makedirs(data_dir, exist_ok=True)
    dst = os.path.join(data_dir, filename)
    src = os.path.join(app_dir, filename)
    if os.path.isfile(src) and not os.path.isfile(dst):
        shutil.copy2(src, dst)
    return dst


def _plan_task_desktop_folder():
    """桌面「桌面宠物」文件夹（cmd / PS 等可配合此处放置快捷方式）"""
    return os.path.join(os.path.expanduser("~"), "Desktop", "桌面宠物")


def _try_launch_from_desktop_pet(folder, filenames):
    """若桌面「桌面宠物」下存在给定快捷方式/脚本则优先启动"""
    if not folder or not os.path.isdir(folder):
        return False
    for name in filenames:
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            if sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.Popen([path])
            return True
    return False


def _find_cursor_exe():
    """PATH 中的 cursor；否则 CURSOR_EXTRA_INSTALL_DIRS；再常见安装位置（%LOCALAPPDATA%\\Programs\\cursor 等）。"""
    w = shutil.which("cursor")
    if w:
        return w
    for root in CURSOR_EXTRA_INSTALL_DIRS:
        p = os.path.join(root, "Cursor.exe")
        if os.path.isfile(p):
            return p
    local = os.environ.get("LOCALAPPDATA", "")
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    for p in (
        os.path.join(local, "Programs", "cursor", "Cursor.exe"),
        os.path.join(local, "Programs", "Cursor", "Cursor.exe"),
        os.path.join(pf, "cursor", "Cursor.exe"),
        os.path.join(pf, "Cursor", "Cursor.exe"),
    ):
        if os.path.isfile(p):
            return p
    return None


def _find_opencode_exe():
    """OpenCode CLI：OPENCODE_EXE → OPENCODE_EXTRA_EXES → PATH 中 opencode / opencode.cmd"""
    envp = os.environ.get("OPENCODE_EXE", "").strip()
    if envp and os.path.isfile(envp):
        return envp
    for p in OPENCODE_EXTRA_EXES:
        if p and os.path.isfile(p):
            return p
    for name in ("opencode", "opencode.cmd"):
        w = shutil.which(name)
        if w:
            return w
    return None


def _find_gemini_cli_exe():
    """Gemini CLI：GEMINI_CLI_EXE → GEMINI_EXTRA_EXES → PATH 中 gemini / gemini.cmd"""
    envp = os.environ.get("GEMINI_CLI_EXE", "").strip()
    if envp and os.path.isfile(envp):
        return envp
    for p in GEMINI_EXTRA_EXES:
        if p and os.path.isfile(p):
            return p
    for name in ("gemini", "gemini.cmd"):
        w = shutil.which(name)
        if w:
            return w
    ap = os.environ.get("APPDATA", "")
    for fname in ("gemini.cmd", "gemini"):
        p = os.path.join(ap, "npm", fname)
        if os.path.isfile(p):
            return p
    return None


def _launch_cli_in_powershell_maximized(exe, home):
    """在全屏 PowerShell 中从用户主目录启动 CLI（路径含空格时安全转义）。"""
    exe = os.path.normpath(exe)
    exe_esc = exe.replace("'", "''")
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoExit",
            "-WindowStyle",
            "Maximized",
            "-Command",
            f"Set-Location $HOME; & '{exe_esc}'",
        ],
        cwd=home,
    )


def _find_ollama_launch():
    """返回 ("gui", path) 或 ("cli", path) 或 (None, None)。
    官方默认目录：%LOCALAPPDATA%\\Programs\\Ollama（优先 GUI：ollama app.exe）。"""
    local = os.environ.get("LOCALAPPDATA", "")
    ollama_dir = os.path.join(local, "Programs", "Ollama")
    if os.path.isdir(ollama_dir):
        for name in ("ollama app.exe", "Ollama.exe", "ollama.exe"):
            p = os.path.join(ollama_dir, name)
            if os.path.isfile(p):
                return ("gui", p)
    w = shutil.which("ollama")
    if w:
        return ("cli", w)
    return (None, None)


def _popen_user_program(exe, cwd):
    """启动外部程序；Windows 下 .cmd/.bat 需 shell=True"""
    exe = os.path.normpath(exe)
    if sys.platform == "win32" and exe.lower().endswith((".cmd", ".bat")):
        subprocess.Popen(exe, cwd=cwd, shell=True)
    else:
        subprocess.Popen([exe], cwd=cwd)


def _clamp_int(v, lo, hi, fallback):
    try:
        i = int(float(v))
    except (TypeError, ValueError):
        return fallback
    return max(lo, min(hi, i))


DEFAULT_PET_SETTINGS = {
    "ollama_model": "gemma3:4b",
    "ollama_base_url": "http://localhost:11434",
    "pet_scale": 2.0,
    "show_pet_on_start": False,
    "plan_task_targets": ["cursor"],
    "plan_ready_text": "I'm ready",
    "plan_ready_x": 12,
    "plan_ready_y": 12,
    "plan_ready_w": 240,
    "plan_ready_h": 44,
    "plan_ready_font_pt": 12,
    "plan_ready_duration_ms": 2600,
}
PET_SCALE_MIN = 1.0
PET_SCALE_MAX = 3.5
MODEL_PRESETS = ("gemma3:4b", "gemma3:1b")

# 计划任务：设置里选择的目标（与托盘「开始计划」联动，具体启动逻辑见 open_start_plan）
# 「CLI」同时尝试启动 OpenCode CLI 与 Gemini CLI（各自若找到则各开一个全屏 PowerShell）
PLAN_TASK_OPTIONS = (
    ("cursor", "Cursor"),
    ("cli", "CLI"),
    ("ollama", "Ollama"),
    ("cmd", "cmd"),
    ("powershell", "PS"),
)
PLAN_TASK_IDS = frozenset(k for k, _ in PLAN_TASK_OPTIONS)


def _plan_task_label(tid):
    for k, lab in PLAN_TASK_OPTIONS:
        if k == tid:
            return lab
    return tid


# 自定义/便携版 Cursor 安装目录（其下需有 Cursor.exe），在 PATH 与 %LOCALAPPDATA% 默认路径之间探测
CURSOR_EXTRA_INSTALL_DIRS = (r"D:\Pony\Cursor",)

def _opencode_install_dir():
    """OpenCode 官方安装目录（%LOCALAPPDATA%\\OpenCode，与 C:\\Users\\Administrator\\AppData\\Local\\OpenCode 一致）。"""
    local = (os.environ.get("LOCALAPPDATA") or "").strip()
    if not local:
        local = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(local, "OpenCode")


# 计划任务「CLI」OpenCode：优先 opencode-cli.exe，其次 opencode.exe / OpenCode.exe
OPENCODE_EXTRA_EXES = (
    os.path.join(_opencode_install_dir(), "opencode-cli.exe"),
    os.path.join(_opencode_install_dir(), "opencode.exe"),
    os.path.join(_opencode_install_dir(), "OpenCode.exe"),
)

# 计划任务「Gemini CLI」：按需填写本机 gemini 可执行文件；也可用环境变量 GEMINI_CLI_EXE
GEMINI_EXTRA_EXES = ()

MAIN_WINDOW_TITLE = "桌面宠物"
SELF_WINDOW_TITLES = frozenset({
    "Desktop Pet",
    MAIN_WINDOW_TITLE,
    "设置与召唤",
    "和 小鸡仔 聊天",
    "快捷翻译",
})


def _win32_enable_crisp_ui():
    """高 DPI 下减轻 Tk 文字发虚（须在创建任何 Tk 窗口前调用）"""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def _win32_ensure_single_instance():
    """已有实例时激活其主窗口并终止当前进程；返回 True 表示可继续启动。"""
    if sys.platform != "win32":
        return True
    import ctypes
    kernel32 = ctypes.windll.kernel32
    ERROR_ALREADY_EXISTS = 183
    kernel32.SetLastError(0)
    kernel32.CreateMutexW(None, False, "Global\\DesktopPetChickenSingle_v1")
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, MAIN_WINDOW_TITLE)
        if hwnd:
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)
        return False
    return True


class OllamaChat:
    """Ollama API 聊天类"""
    
    def __init__(self, model="gemma3:4b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.chat_url = f"{base_url}/api/chat"
        self.conversation_history = []
        # 系统提示
        self.system_prompt = """你是一个可爱的桌面宠物小黄鸡。
你的名字叫"小鸡仔"。
你很喜欢和主人聊天。
回答要简短、有趣、可爱。
偶尔会用emoji。
如果主人问你你 会什么，你可以回答：陪聊天、讲笑话、回答问题。"""
        self.conversation_history.append({
            "role": "system",
            "content": self.system_prompt
        })
    
    def chat(self, message, callback=None):
        """发送消息到 Ollama"""
        # 添加用户消息到历史
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # 在后台线程中请求
        def request_thread():
            try:
                response = self._send_request()
                
                if callback:
                    if response.get('message'):
                        answer = response['message'].get('content', '')
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": answer
                        })
                        callback(answer)
                    else:
                        callback("抱歉，我暂时无法回答...")
            except Exception as e:
                if callback:
                    callback(f"连接失败: {str(e)}")
        
        thread = threading.Thread(target=request_thread, daemon=True)
        thread.start()
    
    def _send_request(self):
        """发送 HTTP 请求到 Ollama（消息体来自 conversation_history）"""
        payload = {
            "model": self.model,
            "messages": self.conversation_history[-10:],  # 只保留最近10条
            "stream": False
        }
        
        data = json.dumps(payload).encode('utf-8')
        
        req = urllib.request.Request(
            self.chat_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result


class DesktopPet:
    """桌面宠物类"""
    
    # 宠物状态
    STATE_IDLE = "idle"
    STATE_SLEEPING = "sleeping"
    STATE_HAPPY = "happy"
    STATE_EATING = "eating"
    
    def __init__(self):
        if not _win32_ensure_single_instance():
            sys.exit(0)
        _win32_enable_crisp_ui()
        
        self.state = self.STATE_IDLE
        self.state_timer = None
        self.anim_timer = None
        self.move_timer = None
        self.frame = 0
        self.direction = 1
        self.x = 100
        self.y = 100
        self.transparent_color = '#FF00FF'
        self.tray_icon = None
        self._main_fullscreen = False
        
        self._app_dir = _app_dir()
        self._data_dir = _local_data_dir()
        self._settings_path = _migrate_data_file(
            "pet_settings.json", self._app_dir, self._data_dir
        )
        self.software_modes_file = _migrate_data_file(
            "software_modes.txt", self._app_dir, self._data_dir
        )
        self.current_software = ""
        self.current_mode = "工作模式"
        
        _s = self.load_settings()
        self.ai = OllamaChat(model=_s["ollama_model"], base_url=_s["ollama_base_url"])
        
        self.setup_global_keyboard_hook()
        
        self.main = tk.Tk()
        self.main.title(MAIN_WINDOW_TITLE)
        self.main.minsize(640, 480)
        self._build_main_dashboard()
        self.main.protocol("WM_DELETE_WINDOW", self.hide_main_window)
        try:
            self.main.state("zoomed")
        except tk.TclError:
            pass
        
        self.pet_scale = float(_s.get("pet_scale", DEFAULT_PET_SETTINGS["pet_scale"]))
        self.pet_scale = max(PET_SCALE_MIN, min(PET_SCALE_MAX, self.pet_scale))
        self.pet_dim = int(round(144 * self.pet_scale))
        self.pet_cx = self.pet_dim // 2
        
        self.pet_win = tk.Toplevel(self.main)
        self.pet_win.title("Desktop Pet")
        self.pet_win.geometry(f'{self.pet_dim}x{self.pet_dim}+{self.x}+{self.y}')
        self.setup_pet_window()
        
        self.canvas = tk.Canvas(
            self.pet_win,
            width=self.pet_dim,
            height=self.pet_dim,
            bg=self.transparent_color,
            highlightthickness=0,
        )
        self.canvas.pack()
        
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<Button-3>', self.on_right_click)
        
        self.pet_win.attributes('-topmost', True)
        if bool(_s.get("show_pet_on_start", False)):
            self.pet_win.deiconify()
            self.pet_win.focus_force()
        else:
            self.pet_win.withdraw()
        self.main.lift()
        self.main.focus_force()
        
        self.create_context_menu()
        self.start_anim()
        
        self.last_active_software = "Unknown"
        self.update_active_software()
        
        software, mode = self.get_current_software_mode()
        if mode == "非工作模式":
            self.schedule_random_move()
        
        self.setup_system_tray()
        
        self.main.mainloop()
    
    def update_active_software(self):
        """后台定时更新当前活动软件（排除本程序各窗口标题）"""
        try:
            software, _ = self.get_current_software()
            if software and software != "Unknown":
                self.last_active_software = software
        except Exception:
            pass
        self.main.after(10000, self.update_active_software)
    
    @staticmethod
    def _is_own_window_title(title):
        if not title or not str(title).strip():
            return True
        t = str(title).strip()
        if t in SELF_WINDOW_TITLES:
            return True
        if t.startswith("和 小鸡仔"):
            return True
        if "聊天" in t and ("小鸡仔" in t or "小鸡" in t):
            return True
        return False
    
    def get_current_software(self):
        """获取当前活动窗口的软件名（前台为本程序任意窗口含聊天时返回 Unknown）"""
        try:
            import ctypes
            
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            
            if hwnd == 0:
                return "Unknown", "Unknown"
            
            if sys.platform == "win32":
                pid = ctypes.c_ulong(0)
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value == os.getpid():
                    return "Unknown", "Unknown"
            
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            title = "Unknown"
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value
            
            if self._is_own_window_title(title):
                return "Unknown", "Unknown"
            return title, title
            
        except Exception as e:
            print(f"获取软件失败: {e}")
        return "Unknown", "Unknown"
    
    def load_software_modes(self):
        """从文件加载软件模式配置"""
        modes = {}
        try:
            if os.path.exists(self.software_modes_file):
                with open(self.software_modes_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line:
                            software, mode = line.split('=', 1)
                            modes[software.strip()] = mode.strip()
        except:
            pass
        return modes
    
    def save_software_mode(self, software, mode):
        """保存单个软件的模式"""
        modes = self.load_software_modes()
        modes[software] = mode
        
        try:
            with open(self.software_modes_file, 'w', encoding='utf-8') as f:
                for sw, m in modes.items():
                    f.write(f"{sw}={m}\n")
        except Exception as e:
            print(f"保存失败: {e}")
    
    def get_current_software_mode(self):
        """获取当前软件的模式"""
        # 使用后台记录的最近活动软件
        software_name = getattr(self, 'last_active_software', 'Unknown')
        
        # 如果没有记录，使用当前窗口
        if not software_name or software_name == 'Unknown':
            software_name, _ = self.get_current_software()
        
        self.current_software = software_name
        
        modes = self.load_software_modes()
        self.current_mode = modes.get(software_name, "非工作模式")  # 默认非工作模式
        
        return software_name, self.current_mode
    
    def set_current_software_mode(self, mode, software_name=None):
        """设置当前软件的模式"""
        # 如果没有传入软件名，使用菜单创建时的软件名
        if not software_name:
            software_name = getattr(self, 'current_menu_software', None)
        
        # 如果还是没有，使用当前的
        if not software_name or software_name == "Unknown":
            software_name, _ = self.get_current_software()
        
        self.save_software_mode(software_name, mode)
        self.current_mode = mode
        
        # 根据模式控制随机移动
        if mode == "工作模式":
            self.show_bubble(f"已设为工作模式 🔒")
            if self.move_timer:
                self.pet_win.after_cancel(self.move_timer)
                self.move_timer = None
        else:
            self.show_bubble(f"已设为非工作模式 🎮")
            self.schedule_random_move()
        
        # 刷新右键菜单
        self.create_context_menu()
    
    def load_settings(self):
        out = dict(DEFAULT_PET_SETTINGS)
        try:
            if os.path.isfile(self._settings_path):
                with open(self._settings_path, 'r', encoding='utf-8') as f:
                    merged = json.load(f)
                for k in DEFAULT_PET_SETTINGS:
                    if k not in merged:
                        continue
                    v = merged[k]
                    if k == "pet_scale":
                        try:
                            s = float(v)
                            out[k] = max(PET_SCALE_MIN, min(PET_SCALE_MAX, s))
                        except (TypeError, ValueError):
                            pass
                    elif k == "show_pet_on_start":
                        out[k] = bool(v)
                    elif k in ("ollama_model", "ollama_base_url"):
                        if str(v).strip():
                            out[k] = str(v).strip()
                    elif k == "plan_task_targets":
                        if isinstance(v, list):
                            seen = []
                            for x in v:
                                tid = str(x).strip()
                                if tid in ("opencode", "opencode_cli", "gemini_cli"):
                                    tid = "cli"
                                if tid in PLAN_TASK_IDS and tid not in seen:
                                    seen.append(tid)
                            if seen:
                                out[k] = seen
                    elif k == "plan_ready_text":
                        t = str(v).strip() if v is not None else ""
                        if t:
                            out[k] = t[:200]
                    elif k == "plan_ready_x":
                        out[k] = _clamp_int(v, 0, 10000, out[k])
                    elif k == "plan_ready_y":
                        out[k] = _clamp_int(v, 0, 10000, out[k])
                    elif k == "plan_ready_w":
                        out[k] = _clamp_int(v, 80, 1200, out[k])
                    elif k == "plan_ready_h":
                        out[k] = _clamp_int(v, 20, 400, out[k])
                    elif k == "plan_ready_font_pt":
                        out[k] = _clamp_int(v, 8, 48, out[k])
                    elif k == "plan_ready_duration_ms":
                        out[k] = _clamp_int(v, 300, 20000, out[k])
                if "plan_task_targets" not in merged and isinstance(
                    merged.get("plan_task_target"), str
                ):
                    tid = merged["plan_task_target"].strip()
                    if tid in ("opencode", "opencode_cli", "gemini_cli"):
                        tid = "cli"
                    if tid in PLAN_TASK_IDS:
                        out["plan_task_targets"] = [tid]
        except Exception:
            pass
        return out
    
    def save_settings(self, updates):
        data = self.load_settings()
        for k, v in updates.items():
            if k == "pet_scale":
                try:
                    data[k] = max(PET_SCALE_MIN, min(PET_SCALE_MAX, float(v)))
                except (TypeError, ValueError):
                    continue
            elif k == "show_pet_on_start":
                data[k] = bool(v)
            elif k == "plan_task_targets":
                if isinstance(v, list):
                    seen = []
                    for x in v:
                        tid = str(x).strip()
                        if tid in ("opencode", "opencode_cli", "gemini_cli"):
                            tid = "cli"
                        if tid in PLAN_TASK_IDS and tid not in seen:
                            seen.append(tid)
                    if seen:
                        data[k] = seen
                        data.pop("plan_task_target", None)
            elif k == "plan_ready_text":
                t = str(v).strip() if v is not None else ""
                if t:
                    data[k] = t[:200]
            elif k == "plan_ready_x":
                data[k] = _clamp_int(v, 0, 10000, DEFAULT_PET_SETTINGS["plan_ready_x"])
            elif k == "plan_ready_y":
                data[k] = _clamp_int(v, 0, 10000, DEFAULT_PET_SETTINGS["plan_ready_y"])
            elif k == "plan_ready_w":
                data[k] = _clamp_int(v, 80, 1200, DEFAULT_PET_SETTINGS["plan_ready_w"])
            elif k == "plan_ready_h":
                data[k] = _clamp_int(v, 20, 400, DEFAULT_PET_SETTINGS["plan_ready_h"])
            elif k == "plan_ready_font_pt":
                data[k] = _clamp_int(v, 8, 48, DEFAULT_PET_SETTINGS["plan_ready_font_pt"])
            elif k == "plan_ready_duration_ms":
                data[k] = _clamp_int(v, 300, 20000, DEFAULT_PET_SETTINGS["plan_ready_duration_ms"])
            else:
                data[k] = v
        with open(self._settings_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def apply_pet_scale(self, new_scale):
        """立即调整小鸡窗口与画布尺寸（不写入文件，由调用方先 save 或单独保存）"""
        new_scale = max(PET_SCALE_MIN, min(PET_SCALE_MAX, float(new_scale)))
        self.pet_scale = new_scale
        self.pet_dim = int(round(144 * self.pet_scale))
        self.pet_cx = self.pet_dim // 2
        self.canvas.config(width=self.pet_dim, height=self.pet_dim)
        x = self.pet_win.winfo_x()
        y = self.pet_win.winfo_y()
        self.pet_win.geometry(f"{self.pet_dim}x{self.pet_dim}+{x}+{y}")
    
    def rebuild_ai(self):
        s = self.load_settings()
        self.ai = OllamaChat(model=s["ollama_model"], base_url=s["ollama_base_url"])
    
    def setup_pet_window(self):
        """宠物小窗：无边框、透明、置顶"""
        self.pet_win.overrideredirect(True)
        self.pet_win.attributes('-transparentcolor', self.transparent_color)
        self.pet_win.configure(bg=self.transparent_color)
        self.pet_win.attributes('-topmost', True)
        try:
            import ctypes
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            hwnd = self.pet_win.winfo_id()
            exstyle = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle | WS_EX_TOOLWINDOW)
        except Exception:
            pass
    
    def _build_main_dashboard(self):
        """双击启动的主界面：可全屏，内含召唤与设置"""
        bg = "#F8F5F0"
        bar = "#5D2E46"
        self.main.configure(bg=bg)
        top = tk.Frame(self.main, bg=bar, height=52)
        top.pack(fill=tk.X)
        tk.Label(
            top,
            text=MAIN_WINDOW_TITLE,
            font=("Microsoft YaHei UI", 17),
            fg="white",
            bg=bar,
        ).pack(side=tk.LEFT, padx=18, pady=10)
        
        body = tk.Frame(self.main, bg=bg)
        body.pack(fill=tk.BOTH, expand=True, padx=36, pady=28)
        tk.Label(
            body,
            text="在此控制小黄鸡与聊天模型（全局仅允许运行一只鸡）",
            font=("Microsoft YaHei UI", 11),
            bg=bg,
            fg="#333",
        ).pack(anchor=tk.W, pady=(0, 6))
        tk.Label(
            body,
            text="默认不自动显示小鸡：请点「召唤 / 隐藏」或按 Ctrl+Shift+P；大小在「设置与召唤」里可调。",
            font=("Microsoft YaHei UI", 9),
            bg=bg,
            fg="#666",
        ).pack(anchor=tk.W, pady=(0, 14))
        
        row1 = tk.Frame(body, bg=bg)
        row1.pack(anchor=tk.W, pady=8)
        tk.Button(
            row1,
            text="召唤 / 隐藏小黄鸡",
            font=("Microsoft YaHei UI", 11),
            width=18,
            command=self.summon_pet,
        ).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(
            row1,
            text="设置与模型",
            font=("Microsoft YaHei UI", 11),
            width=14,
            command=self.open_settings_panel,
        ).pack(side=tk.LEFT, padx=6)
        tk.Button(
            row1,
            text="和我聊天",
            font=("Microsoft YaHei UI", 11),
            width=12,
            command=self.open_chat,
        ).pack(side=tk.LEFT, padx=6)
        tk.Button(
            row1,
            text="快捷翻译",
            font=("Microsoft YaHei UI", 11),
            width=12,
            command=self.open_quick_translate,
        ).pack(side=tk.LEFT, padx=6)
        
        row2 = tk.Frame(body, bg=bg)
        row2.pack(anchor=tk.W, pady=8)
        tk.Button(
            row2,
            text="全屏 / 退出全屏",
            font=("Microsoft YaHei UI", 10),
            width=16,
            command=self.toggle_main_fullscreen,
        ).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(
            row2,
            text="隐藏本面板（托盘与小鸡仍可用）",
            font=("Microsoft YaHei UI", 10),
            width=28,
            command=self.hide_main_window,
        ).pack(side=tk.LEFT, padx=6)
        
        tk.Label(
            body,
            text="快捷键：Ctrl+Shift+P 召唤/隐藏小鸡  ·  Ctrl+Shift+T 快捷翻译",
            font=("Microsoft YaHei UI", 10),
            bg=bg,
            fg="#666",
        ).pack(anchor=tk.W, pady=(24, 6))
        tk.Label(
            body,
            text="关闭本窗口不会退出程序；在托盘菜单中选「退出」可彻底关闭。",
            font=("Microsoft YaHei UI", 9),
            bg=bg,
            fg="#888",
        ).pack(anchor=tk.W)
    
    def hide_main_window(self):
        self.main.withdraw()
    
    def toggle_main_fullscreen(self):
        self._main_fullscreen = not self._main_fullscreen
        self.main.attributes("-fullscreen", self._main_fullscreen)
    
    def setup_global_keyboard_hook(self):
        """设置全局键盘钩子 - 使用 keyboard 模块"""
        import keyboard
        
        keyboard.add_hotkey("ctrl+shift+p", self.summon_pet)
        keyboard.add_hotkey("ctrl+shift+t", self.open_quick_translate)
        print("全局热键: Ctrl+Shift+P 召唤/隐藏小鸡 | Ctrl+Shift+T 快捷翻译")
    
    @staticmethod
    def _build_tray_icon_image():
        """小黄鸡风格 64x64 托盘图标（RGBA）"""
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((10, 22, 54, 52), fill=(255, 217, 61, 255), outline=(230, 184, 0, 255), width=2)
        d.ellipse((32, 18, 44, 26), fill=(255, 217, 61, 255), outline=(230, 184, 0, 255), width=1)
        d.polygon([(28, 38), (36, 38), (32, 46)], fill=(255, 140, 0, 255))
        d.ellipse((18, 28, 26, 36), fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=1)
        d.ellipse((38, 28, 46, 36), fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=1)
        d.ellipse((20, 30, 24, 34), fill=(0, 0, 0, 255))
        d.ellipse((40, 30, 44, 34), fill=(0, 0, 0, 255))
        d.ellipse((14, 36, 20, 42), fill=(255, 182, 193, 200))
        d.ellipse((44, 36, 50, 42), fill=(255, 182, 193, 200))
        d.ellipse((22, 50, 30, 56), fill=(255, 140, 0, 255))
        d.ellipse((34, 50, 42, 56), fill=(255, 140, 0, 255))
        return img
    
    def setup_system_tray(self):
        """Windows 系统托盘（需 pip install pystray pillow）"""
        if sys.platform != "win32":
            return
        try:
            import pystray
        except ImportError:
            print("提示: 系统托盘需安装 pystray、Pillow：pip install pystray pillow")
            return
        
        image = self._build_tray_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("打开主面板", self._tray_main),
            pystray.MenuItem("显示 / 隐藏小鸡", self._tray_toggle, default=True),
            pystray.MenuItem("快捷翻译", self._tray_translate),
            pystray.MenuItem("设置与召唤", self._tray_settings),
            pystray.MenuItem("打开启动器", self._tray_open_launcher),
            pystray.MenuItem("开始计划", self._tray_start_plan),
            pystray.MenuItem("退出", self._tray_quit),
        )
        self.tray_icon = pystray.Icon(
            "desktop_pet_chicken",
            image,
            "桌面宠物",
            menu,
        )
        
        def run_tray():
            self.tray_icon.run()
        
        threading.Thread(target=run_tray, daemon=True).start()
    
    def _tray_main(self, icon, item):
        self.main.after(0, self.show_main_window)
    
    def _tray_toggle(self, icon, item):
        self.main.after(0, self.summon_pet)
    
    def _tray_settings(self, icon, item):
        self.main.after(0, self.open_settings_panel)
    
    def _tray_translate(self, icon, item):
        self.main.after(0, self.open_quick_translate)
    
    def _tray_open_launcher(self, icon, item):
        self.main.after(0, self.open_launcher)
    
    def _tray_start_plan(self, icon, item):
        self.main.after(0, self.open_start_plan)
    
    def _launch_one_plan_task(self, tid, home, pet_dir, new_console):
        """启动单项计划任务；成功返回 None，失败返回错误说明字符串。"""
        if tid == "cursor":
            exe = _find_cursor_exe()
            if not exe:
                return "未找到 Cursor，请安装或将 cursor 加入 PATH。"
            _popen_user_program(exe, home)
            return None
        if tid == "cli":
            oc = _find_opencode_exe()
            gm = _find_gemini_cli_exe()
            if not oc and not gm:
                return (
                    "未找到 CLI：请至少安装 OpenCode CLI 或 Gemini CLI 之一；"
                    "可设置 OPENCODE_EXE / OPENCODE_EXTRA_EXES 与 GEMINI_CLI_EXE / GEMINI_EXTRA_EXES。"
                )
            if oc:
                _launch_cli_in_powershell_maximized(oc, home)
            if gm:
                _launch_cli_in_powershell_maximized(gm, home)
            return None
        if tid == "ollama":
            mode, path = _find_ollama_launch()
            if mode == "gui":
                subprocess.Popen([path], cwd=home)
                return None
            if mode == "cli":
                subprocess.Popen([path, "serve"], cwd=home, creationflags=new_console)
                return None
            return "未找到 Ollama，请安装桌面版或将 ollama 加入 PATH。"
        if tid == "cmd":
            if _try_launch_from_desktop_pet(
                pet_dir, ("cmd.lnk", "CMD.lnk", "cmd.bat", "Cmd.bat")
            ):
                return None
            cmd_exe = os.environ.get("COMSPEC") or "cmd.exe"
            subprocess.Popen([cmd_exe], cwd=home, creationflags=new_console)
            return None
        if tid == "powershell":
            if _try_launch_from_desktop_pet(
                pet_dir,
                ("PS.lnk", "ps.lnk", "powershell.lnk", "PowerShell.lnk", "ps.bat"),
            ):
                return None
            ps_exe = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
            if not ps_exe:
                cand = os.path.join(
                    os.environ.get("SystemRoot", r"C:\Windows"),
                    "System32",
                    "WindowsPowerShell",
                    "v1.0",
                    "powershell.exe",
                )
                ps_exe = cand if os.path.isfile(cand) else None
            if not ps_exe:
                return "未找到 PowerShell。"
            subprocess.Popen([ps_exe, "-NoLogo"], cwd=home, creationflags=new_console)
            return None
        return f"未知目标: {tid}"
    
    def open_start_plan(self):
        """按设置中的「计划任务」多选依次启动"""
        s = self.load_settings()
        raw = s.get("plan_task_targets")
        if not isinstance(raw, list):
            raw = []
        targets = []
        for t in raw:
            tid = str(t).strip()
            if tid in ("opencode", "opencode_cli", "gemini_cli"):
                tid = "cli"
            if tid in PLAN_TASK_IDS and tid not in targets:
                targets.append(tid)
        if not targets:
            messagebox.showerror(
                "开始计划",
                "未选择任何任务。请在「设置与召唤」→ 计划任务中勾选至少一项。",
                parent=self.main,
            )
            return
        self.show_plan_ready_corner()
        home = os.path.expanduser("~")
        pet_dir = _plan_task_desktop_folder()
        new_console = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        errs = []
        for tid in targets:
            try:
                err = self._launch_one_plan_task(tid, home, pet_dir, new_console)
                if err:
                    errs.append(f"{_plan_task_label(tid)}：{err}")
            except Exception as e:
                errs.append(f"{_plan_task_label(tid)}：{e}")
        if errs:
            messagebox.showerror("开始计划", "\n".join(errs), parent=self.main)
    
    def _tray_quit(self, icon, item):
        self.main.after(0, self.quit)
    
    def show_main_window(self):
        self.main.deiconify()
        self.main.lift()
        self.main.focus_force()
    
    def create_context_menu(self):
        """创建右键菜单"""
        raw = getattr(self, "last_active_software", "Unknown")
        if not raw or raw == "Unknown":
            t, _ = self.get_current_software()
            raw = t if t != "Unknown" else "Unknown"
        self.current_menu_software = raw
        display_sw = raw if raw != "Unknown" else "（无）请先切到其他软件窗口"
        
        modes = self.load_software_modes()
        mode = modes.get(raw, "非工作模式")
        
        self.context_menu = tk.Menu(self.pet_win, tearoff=0)
        
        self.context_menu.add_command(label=f"📱 当前软件: {display_sw}", state=tk.DISABLED)
        self.context_menu.add_command(label=f"📊 当前模式: {mode}", state=tk.DISABLED)
        self.context_menu.add_separator()
        
        if mode == "工作模式":
            # 工作模式：只能打开启动器 + 设为非工作模式
            self.context_menu.add_command(label="🚀 打开启动器", command=self.open_launcher)
            self.context_menu.add_command(label="🌐 快捷翻译", command=self.open_quick_translate)
            self.context_menu.add_command(label="⚙ 设置与召唤", command=self.open_settings_panel)
            self.context_menu.add_separator()
            self.context_menu.add_command(
                label="🎮 设为非工作模式",
                command=lambda s=raw: self.set_current_software_mode("非工作模式", s),
            )
        else:
            self.context_menu.add_command(label="🍕 喂食", command=self.feed)
            self.context_menu.add_command(label="😴 睡觉", command=self.sleep)
            self.context_menu.add_command(label="💬 和我聊天", command=self.open_chat)
            self.context_menu.add_command(label="🌐 快捷翻译", command=self.open_quick_translate)
            self.context_menu.add_command(label="⚙ 设置与召唤", command=self.open_settings_panel)
            self.context_menu.add_command(label="🚀 打开启动器", command=self.open_launcher)
            self.context_menu.add_separator()
            self.context_menu.add_command(
                label="🔒 设为工作模式",
                command=lambda s=raw: self.set_current_software_mode("工作模式", s),
            )
        
        self.context_menu.add_separator()
        self.context_menu.add_command(label="💬 关于", command=self.about)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="❌ 退出", command=self.quit)
    
    def open_launcher(self):
        """打开启动器 bat：同目录 > 上一级目录 > 原 Pony 固定路径"""
        candidates = [
            os.path.join(self._app_dir, "open_programs.bat"),
            os.path.join(os.path.dirname(self._app_dir), "open_programs.bat"),
        ]
        for p in candidates:
            if os.path.isfile(p):
                bat = os.path.normpath(p)
                subprocess.Popen(f'start cmd /c "{bat}"', shell=True)
                return
        self.show_bubble("未找到 open_programs.bat\n请放在程序同目录")
    
    @staticmethod
    def _guess_translate_direction(text):
        if not text or not text.strip():
            return "en_zh"
        cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        return "zh_en" if cjk > max(3, len(text) * 0.15) else "en_zh"
    
    def _ollama_generate_translate(self, text, mode):
        s = self.load_settings()
        base = s["ollama_base_url"].rstrip("/")
        model = s["ollama_model"]
        if mode == "auto":
            prompt = (
                "判断以下文字的主要语言。若以中文为主则译为英文；否则译为简体中文。\n"
                "只输出译文，不要引号、不要标题、不要解释。\n\n" + text.strip()
            )
        elif mode == "zh_en":
            prompt = (
                "将下列文字翻译成自然流畅的英文。\n"
                "只输出译文，不要引号、不要前缀、不要解释。\n\n" + text.strip()
            )
        else:
            prompt = (
                "Translate the following into natural Simplified Chinese.\n"
                "Output only the translation, no quotes or notes.\n\n" + text.strip()
            )
        n = min(8192, max(256, len(text) * 2 + 400))
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.15, "num_predict": n},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{base}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        return (out.get("response") or "").strip()
    
    @staticmethod
    def _mymemory_translate(text, langpair):
        t = text[:480]
        q = urllib.parse.quote(t, safe="")
        url = f"https://api.mymemory.translated.net/get?q={q}&langpair={langpair}"
        req = urllib.request.Request(url, headers={"User-Agent": "DesktopPet/1.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            j = json.loads(resp.read().decode("utf-8"))
        td = j.get("responseData") or {}
        tr = (td.get("translatedText") or "").strip()
        if not tr or "MYMEMORY WARNING" in tr.upper():
            return ""
        return tr
    
    def _translate_run_backend(self, text, mode):
        try:
            r = self._ollama_generate_translate(text, mode)
            if r:
                return r
        except Exception:
            pass
        eff = self._guess_translate_direction(text) if mode == "auto" else mode
        lp = "zh-CHS|en" if eff == "zh_en" else "en|zh-CHS"
        try:
            r2 = self._mymemory_translate(text, lp)
            if r2:
                return r2
        except Exception:
            pass
        return ""
    
    def open_quick_translate(self):
        """中英快捷翻译：优先本机 Ollama，失败时用 MyMemory 在线接口（有长度与频次限制）"""
        import tkinter.scrolledtext as scrolledtext
        
        try:
            if self.main.state() == "withdrawn":
                self.show_main_window()
        except tk.TclError:
            pass
        
        win = tk.Toplevel(self.main)
        win.title("快捷翻译")
        win.geometry("600x560")
        win.minsize(480, 420)
        win.attributes("-topmost", True)
        bg = "#f5f5f5"
        win.configure(bg=bg)
        
        tk.Label(
            win,
            text="快捷翻译（Ctrl+Shift+T）",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=bg,
        ).pack(anchor=tk.W, padx=12, pady=(10, 4))
        tk.Label(
            win,
            text="优先使用设置里的 Ollama；失败时尝试 MyMemory（长文本可能被截断）。",
            font=("Microsoft YaHei UI", 9),
            fg="#555",
            bg=bg,
        ).pack(anchor=tk.W, padx=12)
        
        mode_var = tk.StringVar(value="auto")
        mf = tk.Frame(win, bg=bg)
        mf.pack(anchor=tk.W, padx=12, pady=8)
        for lab, val in (
            ("自动（中英互判）", "auto"),
            ("中文 → 英文", "zh_en"),
            ("英文 → 中文", "en_zh"),
        ):
            tk.Radiobutton(mf, text=lab, variable=mode_var, value=val, bg=bg).pack(side=tk.LEFT, padx=(0, 12))
        
        tk.Label(win, text="原文", font=("Microsoft YaHei UI", 9), bg=bg).pack(anchor=tk.W, padx=12)
        inp = scrolledtext.ScrolledText(
            win,
            height=8,
            font=("Microsoft YaHei UI", 11),
            wrap=tk.WORD,
            fg="#141414",
            bg="#ffffff",
        )
        inp.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)
        
        tk.Label(win, text="译文", font=("Microsoft YaHei UI", 9), bg=bg).pack(anchor=tk.W, padx=12)
        out = scrolledtext.ScrolledText(
            win,
            height=8,
            font=("Microsoft YaHei UI", 11),
            wrap=tk.WORD,
            fg="#141414",
            bg="#f9f9f9",
            state=tk.DISABLED,
        )
        out.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)
        
        status = tk.Label(win, text="", font=("Microsoft YaHei UI", 9), fg="#666", bg=bg)
        status.pack(anchor=tk.W, padx=12, pady=2)
        
        bf = tk.Frame(win, bg=bg)
        bf.pack(fill=tk.X, padx=12, pady=10)
        
        def paste_clip():
            try:
                clip = self.main.clipboard_get()
                inp.delete("1.0", tk.END)
                inp.insert("1.0", clip)
            except tk.TclError:
                status.config(text="剪贴板为空或无法读取")
        
        def copy_out():
            t = out.get("1.0", tk.END).strip()
            if not t:
                status.config(text="没有可复制的译文")
                return
            self.main.clipboard_clear()
            self.main.clipboard_append(t)
            status.config(text="已复制译文到剪贴板")
        
        def run_tr():
            text = inp.get("1.0", tk.END).strip()
            if not text:
                status.config(text="请先输入或粘贴要翻译的文字")
                return
            status.config(text="正在翻译…")
            btn_tr.config(state=tk.DISABLED)
            m = mode_var.get()
            
            def work():
                res = self._translate_run_backend(text, m)
                
                def done():
                    btn_tr.config(state=tk.NORMAL)
                    out.config(state=tk.NORMAL)
                    out.delete("1.0", tk.END)
                    if res:
                        out.insert("1.0", res)
                        status.config(text="完成")
                    else:
                        status.config(text="翻译失败：请确认 Ollama 已运行且模型可用，或检查网络")
                    out.config(state=tk.DISABLED)
                
                self.main.after(0, done)
            
            threading.Thread(target=work, daemon=True).start()
        
        btn_tr = tk.Button(bf, text="翻译", font=("Microsoft YaHei UI", 10), width=10, command=run_tr)
        btn_tr.pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(bf, text="从剪贴板粘贴", font=("Microsoft YaHei UI", 10), command=paste_clip).pack(
            side=tk.LEFT, padx=4
        )
        tk.Button(bf, text="复制译文", font=("Microsoft YaHei UI", 10), command=copy_out).pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text="关闭", font=("Microsoft YaHei UI", 10), command=win.destroy).pack(side=tk.RIGHT)
        
        win.bind("<Control-Return>", lambda e: run_tr())
    
    def open_settings_panel(self):
        """设置：Ollama 模型/地址 + 宠物大小与启动选项 + 召唤说明"""
        win = tk.Toplevel(self.main)
        win.title("设置与召唤")
        win.geometry("500x980")
        win.minsize(480, 920)
        win.attributes("-topmost", True)
        
        data = self.load_settings()
        url_var = tk.StringVar(value=data["ollama_base_url"])
        choice = tk.StringVar()
        custom_var = tk.StringVar()
        if data["ollama_model"] in MODEL_PRESETS:
            choice.set(data["ollama_model"])
            custom_var.set("")
        else:
            choice.set("custom")
            custom_var.set(data["ollama_model"])
        
        tk.Label(win, text="Ollama 聊天", font=("Microsoft YaHei UI", 10, "bold")).pack(
            anchor=tk.W, padx=14, pady=(12, 4)
        )
        f_url = tk.Frame(win)
        f_url.pack(fill=tk.X, padx=14, pady=2)
        tk.Label(f_url, text="服务地址").pack(side=tk.LEFT)
        tk.Entry(f_url, textvariable=url_var, width=42).pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        
        tk.Label(win, text="聊天模型", anchor=tk.W).pack(fill=tk.X, padx=14, pady=(10, 4))
        fm = tk.Frame(win)
        fm.pack(fill=tk.X, padx=14)
        tk.Radiobutton(
            fm, text="gemma3:4b（推荐）", variable=choice, value="gemma3:4b"
        ).pack(anchor=tk.W)
        tk.Radiobutton(
            fm, text="gemma3:1b（更快、更省显存）", variable=choice, value="gemma3:1b"
        ).pack(anchor=tk.W)
        f_c = tk.Frame(fm)
        f_c.pack(anchor=tk.W, fill=tk.X, pady=2)
        tk.Radiobutton(f_c, text="自定义模型名", variable=choice, value="custom").pack(side=tk.LEFT)
        custom_ent = tk.Entry(f_c, textvariable=custom_var, width=24)
        custom_ent.pack(side=tk.LEFT, padx=6)
        
        def sync_custom_entry(*_):
            st = tk.NORMAL if choice.get() == "custom" else tk.DISABLED
            custom_ent.config(state=st)
        
        choice.trace_add("write", lambda *_: sync_custom_entry())
        sync_custom_entry()
        
        def do_save():
            url = url_var.get().strip()
            if not url:
                messagebox.showerror("提示", "请填写 Ollama 服务地址。", parent=win)
                return
            if choice.get() == "custom":
                m = custom_var.get().strip()
                if not m:
                    messagebox.showerror("提示", "请填写自定义模型名，或改选上方预设。", parent=win)
                    return
            else:
                m = choice.get()
            try:
                self.save_settings({"ollama_model": m, "ollama_base_url": url})
                self.rebuild_ai()
            except Exception as e:
                messagebox.showerror("保存失败", str(e), parent=win)
                return
            messagebox.showinfo(
                "已保存",
                "设置已写入 local-only/desktop-pet/pet_settings.json。\n对话记录已按新模型重置。",
                parent=win,
            )
        
        tk.Button(win, text="保存聊天设置", command=do_save, width=18).pack(pady=10)
        
        tk.Label(win, text="计划任务（可多选）", font=("Microsoft YaHei UI", 10, "bold")).pack(
            anchor=tk.W, padx=14, pady=(16, 4)
        )
        _pt_loaded = data.get("plan_task_targets")
        if not isinstance(_pt_loaded, list):
            _pt_loaded = []
        _pt_set = {str(x).strip() for x in _pt_loaded if str(x).strip() in PLAN_TASK_IDS}
        plan_vars = {key: tk.BooleanVar(value=(key in _pt_set)) for key, _ in PLAN_TASK_OPTIONS}
        plan_f = tk.Frame(win)
        plan_f.pack(fill=tk.X, padx=14, pady=2)
        for key, label in PLAN_TASK_OPTIONS:
            tk.Checkbutton(
                plan_f,
                text=label,
                variable=plan_vars[key],
                font=("Microsoft YaHei UI", 9),
            ).pack(anchor=tk.W)
        plan_hint = (
            "说明：「开始计划」将按上列勾选项依次打开（顺序为列表自上而下）。"
            "「CLI」会尝试启动本机已安装的 OpenCode CLI 与 Gemini CLI（找到几个开几个全屏 PowerShell）。"
            " 选 cmd / PS 时，工作目录为当前用户主目录。"
            f" 可在桌面「桌面宠物」文件夹（{_plan_task_desktop_folder()}）中放置快捷方式，"
            "界面中仍只显示为 cmd 或 PS。"
        )
        tk.Label(
            win,
            text=plan_hint,
            justify=tk.LEFT,
            wraplength=420,
            font=("Microsoft YaHei UI", 8),
            fg="#555",
        ).pack(anchor=tk.W, padx=14, pady=(4, 2))
        
        def do_save_plan_task():
            selected = [key for key, _ in PLAN_TASK_OPTIONS if plan_vars[key].get()]
            if not selected:
                messagebox.showerror("提示", "请至少勾选一项计划任务。", parent=win)
                return
            try:
                self.save_settings({"plan_task_targets": selected})
            except Exception as e:
                messagebox.showerror("保存失败", str(e), parent=win)
                return
            try:
                os.makedirs(_plan_task_desktop_folder(), exist_ok=True)
            except OSError:
                pass
            messagebox.showinfo("已保存", "计划任务（多选）已写入 pet_settings.json。", parent=win)
        
        tk.Button(win, text="保存计划任务", command=do_save_plan_task, width=18).pack(pady=(4, 6))
        
        tk.Label(win, text="开始计划时提示框", font=("Microsoft YaHei UI", 10, "bold")).pack(
            anchor=tk.W, padx=14, pady=(14, 4)
        )
        ready_txt_var = tk.StringVar(value=str(data.get("plan_ready_text", "I'm ready"))[:200])
        tk.Label(win, text="文字", font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W, padx=14, pady=(0, 2))
        tk.Entry(win, textvariable=ready_txt_var, width=52, font=("Microsoft YaHei UI", 9)).pack(
            padx=14, fill=tk.X, pady=(0, 6)
        )
        rxf = tk.Frame(win)
        rxf.pack(fill=tk.X, padx=14, pady=2)
        ready_x_var = tk.StringVar(value=str(int(data.get("plan_ready_x", 12))))
        ready_y_var = tk.StringVar(value=str(int(data.get("plan_ready_y", 12))))
        ready_w_var = tk.StringVar(value=str(int(data.get("plan_ready_w", 240))))
        ready_h_var = tk.StringVar(value=str(int(data.get("plan_ready_h", 44))))
        ready_font_var = tk.StringVar(value=str(int(data.get("plan_ready_font_pt", 12))))
        ready_ms_var = tk.StringVar(value=str(int(data.get("plan_ready_duration_ms", 2600))))
        for lab, var, wid in (
            ("左边距 X", ready_x_var, 8),
            ("上边距 Y", ready_y_var, 8),
            ("宽度 W", ready_w_var, 8),
            ("高度 H", ready_h_var, 8),
            ("字号", ready_font_var, 8),
            ("显示毫秒", ready_ms_var, 10),
        ):
            tk.Label(rxf, text=lab, font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=(0, 4))
            tk.Entry(rxf, textvariable=var, width=wid, font=("Microsoft YaHei UI", 9)).pack(
                side=tk.LEFT, padx=(0, 10)
            )
        tk.Label(
            win,
            text="坐标相对屏幕左上角；可先调数字再点「预览」查看效果，满意后点「保存提示框」写入配置。",
            justify=tk.LEFT,
            wraplength=430,
            font=("Microsoft YaHei UI", 8),
            fg="#555",
        ).pack(anchor=tk.W, padx=14, pady=(4, 4))
        
        def _parse_ready_prefs_from_form():
            return {
                "plan_ready_text": str(ready_txt_var.get()).strip()[:200],
                "plan_ready_x": _clamp_int(ready_x_var.get(), 0, 10000, 12),
                "plan_ready_y": _clamp_int(ready_y_var.get(), 0, 10000, 12),
                "plan_ready_w": _clamp_int(ready_w_var.get(), 80, 1200, 240),
                "plan_ready_h": _clamp_int(ready_h_var.get(), 20, 400, 44),
                "plan_ready_font_pt": _clamp_int(ready_font_var.get(), 8, 48, 12),
                "plan_ready_duration_ms": _clamp_int(ready_ms_var.get(), 300, 20000, 2600),
            }
        
        def do_preview_ready():
            try:
                self.show_plan_ready_corner(**_parse_ready_prefs_from_form())
            except Exception as e:
                messagebox.showerror("预览失败", str(e), parent=win)
        
        def do_save_ready_box():
            prefs = _parse_ready_prefs_from_form()
            if not str(prefs["plan_ready_text"]).strip():
                messagebox.showerror("提示", "提示文字不能为空。", parent=win)
                return
            try:
                self.save_settings(prefs)
            except Exception as e:
                messagebox.showerror("保存失败", str(e), parent=win)
                return
            messagebox.showinfo("已保存", "开始计划提示框参数已写入 pet_settings.json。", parent=win)
        
        rbf = tk.Frame(win)
        rbf.pack(fill=tk.X, padx=14, pady=(2, 8))
        tk.Button(rbf, text="预览", command=do_preview_ready, width=10).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(rbf, text="保存提示框", command=do_save_ready_box, width=14).pack(side=tk.LEFT)
        
        tk.Label(win, text="宠物大小与启动", font=("Microsoft YaHei UI", 10, "bold")).pack(
            anchor=tk.W, padx=14, pady=(16, 4)
        )
        scale_var = tk.DoubleVar(value=float(data.get("pet_scale", 2.0)))
        show_start_var = tk.BooleanVar(value=bool(data.get("show_pet_on_start", False)))
        
        def update_dim_hint(*_):
            sc = max(PET_SCALE_MIN, min(PET_SCALE_MAX, float(scale_var.get())))
            d = int(round(144 * sc))
            dim_hint.config(text=f"窗口约 {d}×{d} 像素（相对基准 144 缩放 {sc:.2f} 倍）")
        
        dim_hint = tk.Label(win, text="", font=("Microsoft YaHei UI", 9), fg="#555")
        dim_hint.pack(anchor=tk.W, padx=14, pady=(0, 4))
        scale_var.trace_add("write", lambda *_: update_dim_hint())
        update_dim_hint()
        
        sf = tk.Frame(win)
        sf.pack(fill=tk.X, padx=14, pady=4)
        tk.Label(sf, text="缩放").pack(side=tk.LEFT)
        tk.Scale(
            sf,
            variable=scale_var,
            from_=PET_SCALE_MIN,
            to=PET_SCALE_MAX,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            length=320,
            showvalue=1,
        ).pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)
        
        tk.Checkbutton(
            win,
            text="启动时自动显示小鸡（快捷方式打开后立刻出现）",
            variable=show_start_var,
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor=tk.W, padx=14, pady=(8, 4))
        
        def do_save_appearance():
            try:
                sc = float(scale_var.get())
            except (tk.TclError, ValueError, TypeError):
                sc = 2.0
            sc = max(PET_SCALE_MIN, min(PET_SCALE_MAX, sc))
            show_on = bool(show_start_var.get())
            try:
                self.save_settings({"pet_scale": sc, "show_pet_on_start": show_on})
                self.apply_pet_scale(sc)
            except Exception as e:
                messagebox.showerror("保存失败", str(e), parent=win)
                return
            messagebox.showinfo(
                "已保存",
                "外观与启动选项已写入 pet_settings.json。\n"
                "「启动时显示」将在下次打开程序时生效。",
                parent=win,
            )
        
        tk.Button(win, text="应用并保存大小 / 启动选项", command=do_save_appearance, width=26).pack(
            pady=(6, 4)
        )
        
        tk.Label(win, text="宠物召唤", font=("Microsoft YaHei UI", 10, "bold")).pack(
            anchor=tk.W, padx=14, pady=(14, 4)
        )
        summon_txt = (
            "• 主面板「桌面宠物」上的「召唤 / 隐藏小黄鸡」按钮\n"
            "• 全局快捷键 Ctrl+Shift+P：显示 / 隐藏宠物\n"
            "• Ctrl+Shift+T：快捷翻译（主面板、托盘、右键菜单也可打开）\n"
            "• 托盘：默认项为显示/隐藏小鸡；「打开主面板」可找回大窗口\n"
            "• 右键点击宠物：打开功能菜单"
        )
        tk.Label(win, text=summon_txt, justify=tk.LEFT, wraplength=420).pack(anchor=tk.W, padx=14)
        tk.Button(win, text="立即 显示 / 隐藏 宠物", command=self.summon_pet, width=22).pack(pady=12)
        
        tk.Button(win, text="关闭", command=win.destroy, width=10).pack(pady=(4, 12))
    
    def _pet_px(self, v):
        """将 144 设计坐标系映射到当前宠物缩放"""
        return int(round(float(v) * self.pet_scale))
    
    def _pet_w(self, w):
        """线宽/描边随缩放略增"""
        return max(1, int(round(w * self.pet_scale)))
    
    def draw_chicken(self):
        """绘制小黄鸡"""
        self.canvas.delete('all')
        
        if self.state == self.STATE_SLEEPING:
            self.draw_sleeping()
        elif self.state == self.STATE_HAPPY:
            self.draw_happy()
        elif self.state == self.STATE_EATING:
            self.draw_eating()
        else:
            self.draw_idle()
    
    def draw_idle(self):
        """绘制待机状态"""
        p, w = self._pet_px, self._pet_w
        body_color = '#FFD93D'
        offset = 2 if self.frame % 20 < 10 else -2
        
        self.canvas.create_oval(
            p(45), p(60 + offset), p(115), p(130 + offset),
            fill=body_color, outline='#E6B800', width=w(2),
        )
        
        wing_offset = 6 if self.frame % 30 < 15 else 0
        self.canvas.create_oval(
            p(38), p(80 + offset + wing_offset), p(55), p(105 + offset + wing_offset),
            fill='#FFCC00', outline='#E6B800', width=w(1),
        )
        self.canvas.create_oval(
            p(105), p(80 + offset + wing_offset), p(122), p(105 + offset + wing_offset),
            fill='#FFCC00', outline='#E6B800', width=w(1),
        )
        
        eye_offset = 2 if self.frame % 40 < 20 else 0
        self.canvas.create_oval(
            p(60), p(75 + offset + eye_offset), p(70), p(85 + offset + eye_offset),
            fill='white', outline='black', width=w(1),
        )
        self.canvas.create_oval(
            p(90), p(75 + offset + eye_offset), p(100), p(85 + offset + eye_offset),
            fill='white', outline='black', width=w(1),
        )
        
        self.canvas.create_oval(p(62), p(77 + offset + eye_offset), p(68), p(83 + offset + eye_offset), fill='black')
        self.canvas.create_oval(p(92), p(77 + offset + eye_offset), p(98), p(83 + offset + eye_offset), fill='black')
        
        self.canvas.create_polygon(
            p(75), p(95 + offset), p(85), p(95 + offset), p(80), p(105 + offset),
            fill='#FF8C00', outline='#CC7000',
        )
        
        self.canvas.create_oval(p(42), p(90 + offset), p(52), p(100 + offset), fill='#FFB6C1', outline='')
        self.canvas.create_oval(p(108), p(90 + offset), p(118), p(100 + offset), fill='#FFB6C1', outline='')
        
        self.canvas.create_oval(p(60), p(125 + offset), p(70), p(135 + offset), fill='#FF8C00', outline='')
        self.canvas.create_oval(p(90), p(125 + offset), p(100), p(135 + offset), fill='#FF8C00', outline='')
        
        self.canvas.create_line(p(80), p(60 + offset), p(80), p(48 + offset), fill='#FFD93D', width=w(5))
        self.canvas.create_line(p(72), p(62 + offset), p(64), p(50 + offset), fill='#FFD93D', width=w(4))
        self.canvas.create_line(p(88), p(62 + offset), p(96), p(50 + offset), fill='#FFD93D', width=w(4))
    
    def draw_happy(self):
        """绘制开心状态"""
        p, w = self._pet_px, self._pet_w
        offset = -12 if self.frame % 10 < 5 else 0
        
        self.canvas.create_oval(
            p(42), p(48 + offset), p(102), p(120 + offset),
            fill='#FFD93D', outline='#E6B800', width=w(2),
        )
        
        self.canvas.create_oval(
            p(28), p(68 + offset), p(45), p(90 + offset),
            fill='#FFCC00', outline='#E6B800', width=w(1),
        )
        self.canvas.create_oval(
            p(99), p(68 + offset), p(116), p(90 + offset),
            fill='#FFCC00', outline='#E6B800', width=w(1),
        )
        
        self.canvas.create_arc(
            p(56), p(76 + offset), p(68), p(88 + offset), start=0, extent=180, fill='black',
        )
        self.canvas.create_arc(
            p(76), p(76 + offset), p(88), p(88 + offset), start=0, extent=180, fill='black',
        )
        
        self.canvas.create_arc(
            p(64), p(88 + offset), p(80), p(102 + offset), start=0, extent=-180,
            fill='#FF8C00', outline='#CC7000', width=w(1),
        )
        
        self.canvas.create_oval(p(36), p(82 + offset), p(46), p(92 + offset), fill='#FFB6C1', outline='')
        self.canvas.create_oval(p(98), p(82 + offset), p(108), p(92 + offset), fill='#FFB6C1', outline='')
        
        self.canvas.create_oval(p(52), p(115 + offset), p(62), p(125 + offset), fill='#FF8C00', outline='')
        self.canvas.create_oval(p(82), p(115 + offset), p(92), p(125 + offset), fill='#FF8C00', outline='')
        
        self.canvas.create_line(p(72), p(48 + offset), p(72), p(36 + offset), fill='#FFD93D', width=w(5))
        self.canvas.create_line(p(64), p(50 + offset), p(56), p(38 + offset), fill='#FFD93D', width=w(4))
        self.canvas.create_line(p(80), p(50 + offset), p(88), p(38 + offset), fill='#FFD93D', width=w(4))
    
    def draw_sleeping(self):
        """绘制睡觉状态"""
        p, w = self._pet_px, self._pet_w
        z_offset = (self.frame // 10) % 3
        fz = max(10, int(round(8 * self.pet_scale)))
        fz2 = max(8, int(round(6 * self.pet_scale)))
        fz3 = max(7, int(round(5 * self.pet_scale)))
        
        self.canvas.create_oval(p(42), p(78), p(102), p(138), fill='#FFD93D', outline='#E6B800', width=w(2))
        
        self.canvas.create_oval(p(38), p(84), p(50), p(104), fill='#FFCC00', outline='#E6B800', width=w(1))
        self.canvas.create_oval(p(94), p(84), p(106), p(104), fill='#FFCC00', outline='#E6B800', width=w(1))
        
        self.canvas.create_line(p(56), p(82), p(68), p(82), fill='black', width=w(2))
        self.canvas.create_line(p(76), p(82), p(88), p(82), fill='black', width=w(2))
        
        self.canvas.create_oval(p(68), p(94), p(76), p(102), fill='#FF8C00', outline='')
        
        self.canvas.create_oval(p(36), p(88), p(46), p(98), fill='#FFB6C1', outline='')
        self.canvas.create_oval(p(98), p(88), p(108), p(98), fill='#FFB6C1', outline='')
        
        self.canvas.create_oval(p(52), p(132), p(62), p(142), fill='#FF8C00', outline='')
        self.canvas.create_oval(p(82), p(132), p(92), p(142), fill='#FF8C00', outline='')
        
        self.canvas.create_line(p(72), p(78), p(72), p(66), fill='#FFD93D', width=w(5))
        self.canvas.create_line(p(64), p(80), p(56), p(68), fill='#FFD93D', width=w(4))
        self.canvas.create_line(p(80), p(80), p(88), p(68), fill='#FFD93D', width=w(4))
        
        self.canvas.create_text(p(90), p(30), text='Z', fill='blue', font=('Arial', fz))
        self.canvas.create_text(p(100), p(22), text='z', fill='blue', font=('Arial', fz2))
        if z_offset > 0:
            self.canvas.create_text(p(106), p(14), text='z', fill='blue', font=('Arial', fz3))
    
    def draw_eating(self):
        """绘制吃东西状态"""
        p, w = self._pet_px, self._pet_w
        offset = 4
        emoji_pt = max(16, int(round(14 * self.pet_scale)))
        
        self.canvas.create_oval(
            p(42), p(56 + offset), p(102), p(124 + offset),
            fill='#FFD93D', outline='#E6B800', width=w(2),
        )
        
        self.canvas.create_oval(
            p(32), p(76 + offset), p(48), p(98 + offset),
            fill='#FFCC00', outline='#E6B800', width=w(1),
        )
        self.canvas.create_oval(
            p(96), p(76 + offset), p(112), p(98 + offset),
            fill='#FFCC00', outline='#E6B800', width=w(1),
        )
        
        self.canvas.create_oval(
            p(56), p(70 + offset), p(66), p(80 + offset),
            fill='white', outline='black', width=w(1),
        )
        self.canvas.create_oval(
            p(78), p(70 + offset), p(88), p(80 + offset),
            fill='white', outline='black', width=w(1),
        )
        self.canvas.create_oval(p(58), p(72 + offset), p(64), p(78 + offset), fill='black')
        self.canvas.create_oval(p(80), p(72 + offset), p(86), p(78 + offset), fill='black')
        
        self.canvas.create_oval(p(65), p(92), p(79), p(106), fill='#FF8C00', outline='')
        
        self.canvas.create_oval(p(36), p(82 + offset), p(46), p(92 + offset), fill='#FFB6C1', outline='')
        self.canvas.create_oval(p(98), p(82 + offset), p(108), p(92 + offset), fill='#FFB6C1', outline='')
        
        self.canvas.create_oval(p(52), p(118 + offset), p(62), p(128 + offset), fill='#FF8C00', outline='')
        self.canvas.create_oval(p(82), p(118 + offset), p(92), p(128 + offset), fill='#FF8C00', outline='')
        
        self.canvas.create_line(p(72), p(56 + offset), p(72), p(44 + offset), fill='#FFD93D', width=w(5))
        
        foods = ['🍕', '🍎', '🍪', '🍰', '🍩']
        self.canvas.create_text(
            p(72), p(115), text=foods[self.frame % len(foods)], font=('Segoe UI', emoji_pt),
        )
        
    def start_anim(self):
        """开始动画循环"""
        self.frame += 1
        self.draw_chicken()
        self.anim_timer = self.pet_win.after(100, self.start_anim)
    
    def set_state(self, new_state):
        """设置宠物状态"""
        if self.state_timer:
            self.pet_win.after_cancel(self.state_timer)
        
        self.state = new_state
        
        if new_state in [self.STATE_HAPPY, self.STATE_EATING]:
            self.state_timer = self.pet_win.after(2000, lambda: self.set_state(self.STATE_IDLE))
    
    def on_click(self, event):
        """左键点击 - 工作模式时只能拖动"""
        # 获取当前软件模式
        software = getattr(self, 'last_active_software', 'Unknown')
        modes = self.load_software_modes()
        mode = modes.get(software, "非工作模式")
        
        # 工作模式时无法互动，只能拖动
        if mode == "工作模式":
            return
        
        if self.state == self.STATE_SLEEPING:
            self.wakeup()
        else:
            self.set_state(self.STATE_HAPPY)
            self.show_bubble("你好呀! 🐣")
    
    def on_drag(self, event):
        """拖拽移动"""
        deltax = event.x - self.pet_cx
        deltay = event.y - self.pet_cx
        
        x = self.pet_win.winfo_x()
        y = self.pet_win.winfo_y()
        
        new_x = x + deltax
        new_y = y + deltay
        
        self.pet_win.geometry(f'{self.pet_dim}x{self.pet_dim}+{new_x}+{new_y}')
        
        # 更新保存的坐标
        self.x = new_x
        self.y = new_y
    
    def on_right_click(self, event):
        """右键点击 - 显示菜单（软件名由后台定时更新）"""
        self.create_context_menu()
        self.context_menu.post(event.x_root, event.y_root)
    
    def summon_pet(self):
        """召唤/隐藏小黄鸡 - 切换显示状态"""
        if self.pet_win.winfo_viewable():
            # 如果显示中，则隐藏
            self.pet_win.withdraw()
        else:
            # 如果隐藏中，则显示
            # 获取屏幕尺寸
            screen_width = self.pet_win.winfo_screenwidth()
            screen_height = self.pet_win.winfo_screenheight()
            
            # 计算屏幕中央位置
            x = (screen_width - self.pet_dim) // 2
            y = (screen_height - self.pet_dim) // 2
            
            # 显示并移动到屏幕中央
            self.pet_win.deiconify()
            self.pet_win.geometry(f'{self.pet_dim}x{self.pet_dim}+{x}+{y}')
            self.pet_win.attributes('-topmost', True)
            
            # 强制获取焦点
            self.pet_win.focus_force()
            
            self.show_bubble("我来了! 🐥")
    
    def feed(self):
        """喂食"""
        if self.state != self.STATE_SLEEPING:
            self.set_state(self.STATE_EATING)
            foods = ['🍕', '🍎', '🍪', '🍰', '🍩']
            food = random.choice(foods)
            self.show_bubble(f"谢谢! {food}")
    
    def sleep(self):
        """睡觉"""
        if self.state != self.STATE_SLEEPING:
            self.set_state(self.STATE_SLEEPING)
            self.show_bubble("晚安... 💤")
    
    def wakeup(self):
        """唤醒"""
        self.set_state(self.STATE_IDLE)
        self.show_bubble("早安! ☀️")
    
    def about(self):
        """关于"""
        self.show_bubble("桌面宠物 v1.0\n小黄鸡 🐣")
    
    def open_chat(self):
        """打开聊天窗口（高对比字体 + 略大尺寸，减轻发糊）"""
        chat_font = ("Microsoft YaHei UI", 11)
        chat_win = tk.Toplevel(self.main)
        chat_win.title("和 小鸡仔 聊天")
        chat_win.geometry("480x620")
        chat_win.minsize(400, 480)
        chat_win.configure(bg="#f0f0f0")
        
        s = self.load_settings()
        top_bar = tk.Frame(chat_win, bg="#f0f0f0")
        top_bar.pack(fill=tk.X, padx=12, pady=(10, 6))
        tk.Label(
            top_bar,
            text=f"模型: {s['ollama_model']}",
            font=("Microsoft YaHei UI", 10),
            fg="#222",
            bg="#f0f0f0",
        ).pack(side=tk.LEFT)
        tk.Button(
            top_bar,
            text="模型与召唤设置…",
            font=("Microsoft YaHei UI", 10),
            command=self.open_settings_panel,
        ).pack(side=tk.RIGHT)
        
        chat_frame = tk.Frame(chat_win, bg="#f0f0f0")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        
        scrollbar = tk.Scrollbar(chat_frame, width=14)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.chat_text = tk.Text(
            chat_frame,
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD,
            font=chat_font,
            fg="#141414",
            bg="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=10,
            spacing1=2,
            spacing2=2,
            spacing3=4,
            insertbackground="#141414",
            selectbackground="#b8d4f0",
            selectforeground="#000000",
            highlightthickness=1,
            highlightbackground="#cccccc",
            highlightcolor="#6b9bd1",
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.chat_text.yview)
        
        self.chat_text.insert(tk.END, "🐣 小鸡仔: 你好呀！我是小鸡仔，有什么想和我聊的吗？\n\n")
        self.chat_text.config(state=tk.DISABLED)
        
        input_frame = tk.Frame(chat_win, bg="#f0f0f0")
        input_frame.pack(fill=tk.X, padx=12, pady=(0, 12))
        
        self.chat_entry = tk.Entry(
            input_frame,
            font=chat_font,
            fg="#141414",
            bg="#ffffff",
            relief=tk.SOLID,
            highlightthickness=1,
            highlightbackground="#aaaaaa",
        )
        self.chat_entry.pack(fill=tk.X, side=tk.LEFT, expand=True, ipady=4)
        self.chat_entry.bind("<Return>", lambda e: self.send_message(chat_win))
        
        send_btn = tk.Button(
            input_frame,
            text="发送",
            font=("Microsoft YaHei UI", 10),
            command=lambda: self.send_message(chat_win),
        )
        send_btn.pack(side=tk.RIGHT, padx=(8, 0))
        
        self.chat_status = tk.Label(
            chat_win,
            text="",
            fg="#555555",
            bg="#f0f0f0",
            font=("Microsoft YaHei UI", 9),
        )
        self.chat_status.pack(pady=(0, 8))
    
    def send_message(self, chat_win):
        """发送消息"""
        message = self.chat_entry.get().strip()
        if not message:
            return
        
        # 清空输入框
        self.chat_entry.delete(0, tk.END)
        
        # 显示用户消息
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"👤 你: {message}\n\n")
        self.chat_text.see(tk.END)
        
        # 显示思考中
        self.chat_text.insert(tk.END, "🐣 小鸡仔: 正在思考...\n")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)
        
        # 更新状态
        self.chat_status.config(text="AI 正在回复...")
        
        # 发送消息到 Ollama
        self.ai.chat(message, lambda response: self.on_ai_response(response, chat_win))
    
    def on_ai_response(self, response, chat_win):
        """AI 回复回调"""
        # 在主线程中更新 UI
        def update_ui():
            self.chat_text.config(state=tk.NORMAL)
            needle = "🐣 小鸡仔: 正在思考"
            pos, last_hit = "1.0", None
            while True:
                hit = self.chat_text.search(needle, pos, tk.END)
                if not hit:
                    break
                last_hit = hit
                pos = self.chat_text.index(f"{hit}+1c")
            if last_hit:
                self.chat_text.delete(
                    self.chat_text.index(f"{last_hit} linestart"),
                    self.chat_text.index(f"{last_hit} lineend + 1c"),
                )
            
            # 显示 AI 回复
            self.chat_text.insert(tk.END, f"🐣 小鸡仔: {response}\n\n")
            self.chat_text.see(tk.END)
            self.chat_text.config(state=tk.DISABLED)
            
            # 重置状态
            self.chat_status.config(text="")
        
        # 调度到主线程
        chat_win.after(0, update_ui)
    
    def show_plan_ready_corner(self, **overrides):
        """「开始计划」提示框；尺寸与位置来自 pet_settings（可传 overrides 供预览）。"""
        s = self.load_settings()
        text = overrides.get("plan_ready_text", s.get("plan_ready_text", "I'm ready"))
        text = str(text).strip()[:200] or "I'm ready"
        x = _clamp_int(overrides.get("plan_ready_x", s.get("plan_ready_x")), 0, 10000, 12)
        y = _clamp_int(overrides.get("plan_ready_y", s.get("plan_ready_y")), 0, 10000, 12)
        w = _clamp_int(overrides.get("plan_ready_w", s.get("plan_ready_w")), 80, 1200, 240)
        h = _clamp_int(overrides.get("plan_ready_h", s.get("plan_ready_h")), 20, 400, 44)
        font_pt = _clamp_int(overrides.get("plan_ready_font_pt", s.get("plan_ready_font_pt")), 8, 48, 12)
        duration_ms = _clamp_int(
            overrides.get("plan_ready_duration_ms", s.get("plan_ready_duration_ms")),
            300,
            20000,
            2600,
        )
        ov = tk.Toplevel(self.main)
        ov.overrideredirect(True)
        ov.attributes("-topmost", True)
        ov.resizable(False, False)
        bg = "#333333"
        ov.configure(bg=bg)
        inner_w = max(10, w - 20)
        inner_h = max(10, h - 16)
        lbl = tk.Label(
            ov,
            text=text,
            fg="#e8e8e8",
            bg=bg,
            font=("Segoe UI", font_pt),
            anchor="nw",
            justify="left",
            wraplength=max(12, w - 24),
        )
        lbl.place(x=10, y=8, width=inner_w, height=inner_h)
        ov.geometry(f"{w}x{h}+{x}+{y}")

        def dismiss(_=None):
            try:
                ov.destroy()
            except tk.TclError:
                pass

        ov.bind("<Button-1>", dismiss)
        ov.bind("<Escape>", dismiss)
        ov.after(duration_ms, dismiss)
    
    def show_bubble(self, text):
        """显示气泡消息"""
        bubble = tk.Toplevel(self.pet_win)
        bubble.overrideredirect(True)
        bubble.attributes('-topmost', True)
        bubble.configure(bg='white')
        
        label = tk.Label(bubble, text=text, bg='white', font=('Arial', 10), padx=10, pady=5)
        label.pack()
        
        x = self.pet_win.winfo_x() + max(0, self.pet_cx - 40)
        y = self.pet_win.winfo_y() - 36
        bubble.geometry(f'+{x}+{y}')
        
        bubble.after(2000, bubble.destroy)
    
    def schedule_random_move(self):
        """定时随机移动"""
        if self.state == self.STATE_IDLE:
            if random.random() < 0.3:
                self.do_random_move()
        
        delay = random.randint(3000, 8000)
        self.move_timer = self.pet_win.after(delay, self.schedule_random_move)
    
    def do_random_move(self):
        """执行随机移动"""
        x = self.pet_win.winfo_x()
        y = self.pet_win.winfo_y()
        
        dx = random.randint(-50, 50)
        dy = random.randint(-30, 30)
        
        screen_width = self.pet_win.winfo_screenwidth()
        screen_height = self.pet_win.winfo_screenheight()
        
        new_x = max(0, min(x + dx, screen_width - self.pet_dim))
        new_y = max(0, min(y + dy, screen_height - self.pet_dim))
        
        self.pet_win.geometry(f'{self.pet_dim}x{self.pet_dim}+{new_x}+{new_y}')
    
    def quit(self):
        """退出程序"""
        if self.anim_timer:
            self.pet_win.after_cancel(self.anim_timer)
        if self.state_timer:
            self.pet_win.after_cancel(self.state_timer)
        if self.move_timer:
            self.pet_win.after_cancel(self.move_timer)
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
        self.main.destroy()


if __name__ == '__main__':
    try:
        DesktopPet()
    except Exception as e:
        print(f"错误: {e}")
        input("按回车退出...")
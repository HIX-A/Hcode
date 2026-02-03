import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import io
import traceback
from keyword import iskeyword  # 用于Python关键字判断（语法高亮）

# 仿VSCode深色主题配色（全平台兼容，微调更贴合原版）
COLOR_BG_MAIN = "#1E1E1E"    # 主背景
COLOR_BG_SIDEBAR = "#252526" # 侧边栏/行号背景
COLOR_BG_EDITOR = "#1E1E1E"  # 编辑区背景
COLOR_BG_CONSOLE = "#000000" # 控制台背景（纯黑，仿终端）
COLOR_BG_STATUS = "#007ACC"  # 状态栏背景
COLOR_FG_TEXT = "#D4D4D4"    # 编辑区默认文本色
COLOR_FG_CONSOLE = "#00FF00" # 控制台普通文本色（绿色）
COLOR_FG_WHITE = "#FFFFFF"   # 白色标题/按钮文字
COLOR_FG_ERROR = "#FF4444"   # 错误文本色（红色）
COLOR_FG_KEYWORD = "#569CD6"# 关键字色（VSCode原版蓝）
COLOR_FG_STRING = "#CE9178"  # 字符串色（VSCode原版橙红）
COLOR_FG_COMMENT = "#6A9955"# 注释色（VSCode原版绿）
COLOR_FG_NUMBER = "#B5CEA8" # 数字色（VSCode原版浅绿）
COLOR_SELECT = "#007ACC"     # 选中背景色
COLOR_BTN = "#007ACC"        # 按钮背景色
COLOR_CURSOR = "#FFFFFF"     # 编辑区光标色

class HCodeEditorWithRun:
    def __init__(self, root):
        self.root = root
        self.root.title("Hcode - 未命名文件 [Python编辑器]")
        self.root.geometry("1200x800")  # 适配宽屏，操作更舒适
        self.root.configure(bg=COLOR_BG_MAIN)
        self.root.resizable(True, True)

        # 核心状态变量
        self.current_file = None  # 当前文件路径
        self.is_modified = False  # 文件是否未保存

        # 初始化界面、事件、控制台、语法高亮
        self._init_ui()
        self._init_highlight_tags()  # 新增：初始化语法高亮标签
        self._bind_events()
        self._update_line_numbers()
        self._init_console()

    def _init_ui(self):
        """初始化所有界面：菜单栏+侧边栏+编辑区+控制台+状态栏+运行按钮"""
        # ========== 1. 顶部菜单栏 ==========
        menu_bar = tk.Menu(self.root, bg=COLOR_BG_SIDEBAR, fg=COLOR_FG_TEXT, tearoff=0)
        # 文件菜单
        file_menu = tk.Menu(menu_bar, bg=COLOR_BG_SIDEBAR, fg=COLOR_FG_TEXT, tearoff=0)
        file_menu.add_command(label="新建", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="打开", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="保存", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="另存为", command=self.save_as_file, accelerator="Ctrl+Shift+S")
        menu_bar.add_cascade(label="文件", menu=file_menu)
        # 编辑菜单
        edit_menu = tk.Menu(menu_bar, bg=COLOR_BG_SIDEBAR, fg=COLOR_FG_TEXT, tearoff=0)
        edit_menu.add_command(label="撤销", command=lambda: self.editor.edit_undo(), accelerator="Ctrl+Z")
        edit_menu.add_command(label="重做", command=lambda: self.editor.edit_redo(), accelerator="Ctrl+Y")
        edit_menu.add_command(label="全选", command=lambda: self.editor.event_generate("<<SelectAll>>"), accelerator="Ctrl+A")
        menu_bar.add_cascade(label="编辑", menu=edit_menu)
        # 运行菜单
        run_menu = tk.Menu(menu_bar, bg=COLOR_BG_SIDEBAR, fg=COLOR_FG_TEXT, tearoff=0)
        run_menu.add_command(label="运行代码", command=self.run_code, accelerator="F5")
        run_menu.add_command(label="清空控制台", command=self.clear_console, accelerator="Ctrl+L")
        menu_bar.add_cascade(label="运行", menu=run_menu)
        self.root.config(menu=menu_bar)

        # ========== 2. 主容器（侧边栏 + 右侧编辑/控制台区） ==========
        main_frame = tk.Frame(self.root, bg=COLOR_BG_MAIN)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # ---------- 左侧侧边栏（180px） ----------
        sidebar = tk.Frame(main_frame, bg=COLOR_BG_SIDEBAR, width=180)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="资源管理器", bg=COLOR_BG_SIDEBAR, fg=COLOR_FG_WHITE, font=("Arial",10)).pack(pady=10, padx=15, anchor=tk.W)
        self.file_list = tk.Listbox(sidebar, bg=COLOR_BG_SIDEBAR, fg=COLOR_FG_TEXT, bd=0, highlightthickness=0,
                                    selectbackground=COLOR_SELECT, selectforeground=COLOR_FG_WHITE)
        self.file_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ---------- 右侧主区（编辑区 + 控制台区，垂直排列） ----------
        right_frame = tk.Frame(main_frame, bg=COLOR_BG_MAIN)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 编辑区顶部：功能按钮（运行+清空控制台）
        btn_frame = tk.Frame(right_frame, bg=COLOR_BG_EDITOR)
        btn_frame.pack(fill=tk.X, padx=5, pady=3)
        # 运行代码按钮
        self.run_btn = tk.Button(btn_frame, text="运行代码 (F5)", command=self.run_code, bg=COLOR_BTN,
                                 fg=COLOR_FG_WHITE, bd=0, padx=15, pady=2, font=("Arial",9,"bold"))
        self.run_btn.pack(side=tk.LEFT, padx=5)
        # 清空控制台按钮
        self.clear_console_btn = tk.Button(btn_frame, text="清空控制台 (Ctrl+L)", command=self.clear_console,
                                           bg=COLOR_BG_SIDEBAR, fg=COLOR_FG_TEXT, bd=0, padx=15, pady=2, font=("Arial",9))
        self.clear_console_btn.pack(side=tk.LEFT, padx=5)

        # 编辑区（行号 + 编辑框 + 滚动条）
        edit_container = tk.Frame(right_frame, bg=COLOR_BG_EDITOR)
        edit_container.pack(fill=tk.BOTH, expand=True, pady=(0,3))
        # 编辑区滚动条
        self.edit_scroll = tk.Scrollbar(edit_container, bg=COLOR_BG_SIDEBAR, troughcolor=COLOR_BG_MAIN, bd=0)
        self.edit_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        # 行号框（优化：固定字体，与编辑区一致）
        self.line_numbers = tk.Text(edit_container, width=4, bg=COLOR_BG_SIDEBAR, fg=COLOR_FG_TEXT, bd=0,
                                    highlightthickness=0, state=tk.DISABLED, wrap=tk.NONE, font=("Consolas",12))
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        # 核心代码编辑框（优化：新增光标色、固定等宽字体）
        self.editor = tk.Text(edit_container, bg=COLOR_BG_EDITOR, fg=COLOR_FG_TEXT, bd=0, highlightthickness=0,
                              wrap=tk.NONE, undo=True, maxundo=-1, font=("Consolas",12),
                              insertbackground=COLOR_CURSOR,  # 新增：白色光标，更醒目
                              yscrollcommand=self._sync_edit_scroll)
        self.editor.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.edit_scroll.config(command=self._sync_edit_scroll)

        # 控制台输出区（仿VSCode终端，纯黑背景+绿色文字）
        console_frame = tk.Frame(right_frame, bg=COLOR_BG_CONSOLE, height=200)
        console_frame.pack(fill=tk.BOTH, expand=False)
        console_frame.pack_propagate(False)  # 固定高度
        # 控制台标题
        tk.Label(console_frame, text="▶ 控制台输出（运行结果/错误信息）", bg=COLOR_BG_SIDEBAR,
                 fg=COLOR_FG_WHITE, anchor=tk.W, font=("Arial",9)).pack(fill=tk.X)
        # 控制台滚动条
        self.console_scroll = tk.Scrollbar(console_frame, bg=COLOR_BG_SIDEBAR, troughcolor=COLOR_BG_CONSOLE, bd=0)
        self.console_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        # 控制台文本框（只读，绿色文字，优化：提前配置错误标签）
        self.console = tk.Text(console_frame, bg=COLOR_BG_CONSOLE, fg=COLOR_FG_CONSOLE, bd=0, highlightthickness=0,
                               wrap=tk.WORD, state=tk.DISABLED, font=("Consolas",11),
                               yscrollcommand=self.console_scroll.set)
        self.console.tag_configure("error", foreground=COLOR_FG_ERROR)  # 提前配置错误标签，避免重复创建
        self.console.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.console_scroll.config(command=self.console.yview)

        # ========== 3. 底部状态栏 ==========
        self.status_bar = tk.Label(self.root, text="未命名文件 | 已保存 | 按F5运行代码 | Ctrl+L清空控制台",
                                   bg=COLOR_BG_STATUS, fg=COLOR_FG_WHITE, anchor=tk.W, padx=10, font=("Arial",9))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _init_highlight_tags(self):
        """新增：初始化Python语法高亮标签（VSCode原版配色）"""
        self.editor.tag_configure("keyword", foreground=COLOR_FG_KEYWORD, font=("Consolas",12,"bold"))
        self.editor.tag_configure("string", foreground=COLOR_FG_STRING)
        self.editor.tag_configure("comment", foreground=COLOR_FG_COMMENT, font=("Consolas",12,"italic"))
        self.editor.tag_configure("number", foreground=COLOR_FG_NUMBER)
        # 保证选中内容优先级高于高亮标签，避免选中时被高亮覆盖
        self.editor.tag_raise("sel")

    def _bind_events(self):
        """绑定所有快捷键和事件（新增：自动缩进、语法高亮触发）"""
        # 编辑区事件：修改标记+更新行号+语法高亮（新增）
        self.editor.bind("<KeyRelease>", lambda e: (self._mark_modified(), self._update_line_numbers(), self._syntax_highlight()))
        self.editor.bind("<MouseWheel>", lambda e: self._update_line_numbers())
        self.editor.bind("<ButtonRelease-1>", lambda e: self._update_line_numbers())
        # 新增：回车自动缩进（核心功能）
        self.editor.bind("<Return>", self._auto_indent)
        # 文件操作快捷键
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-S>", lambda e: self.save_as_file())
        # 编辑快捷键
        self.root.bind("<Control-z>", lambda e: self.editor.edit_undo())
        self.root.bind("<Control-y>", lambda e: self.editor.edit_redo())
        self.root.bind("<Control-a>", lambda e: self.editor.event_generate("<<SelectAll>>"))
        # 运行/控制台快捷键
        self.root.bind("<F5>", lambda e: self.run_code())
        self.root.bind("<Control-l>", lambda e: self.clear_console())
        # 关闭窗口检查
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _init_console(self):
        """初始化控制台：修复重定向逻辑，避免冗余buffer"""
        # 直接重定向，无需额外StringIO缓冲，减少冗余
        sys.stdout = self
        sys.stderr = self

    def write(self, text):
        """重定向write方法：优化性能，避免重复配置标签"""
        self.console.config(state=tk.NORMAL)
        # 错误信息标红（优化：更全面的错误关键词匹配）
        error_keywords = ["Error", "Traceback", "SyntaxError", "NameError", "TypeError", "IndexError", "KeyError"]
        if any(keyword in text for keyword in error_keywords):
            self.console.insert(tk.END, text, "error")
        else:
            self.console.insert(tk.END, text)
        self.console.config(state=tk.DISABLED)
        self.console.yview(tk.END)  # 自动滚动到最后一行

    def flush(self):
        """重定向flush方法：兼容标准输出协议"""
        pass

    def _sync_edit_scroll(self, *args):
        """编辑区滚动同步：行号+编辑框+滚动条（优化：更稳定的同步逻辑）"""
        self.editor.yview(*args)
        self.line_numbers.yview(*args)
        self.edit_scroll.set(*args)

    def _update_line_numbers(self):
        """更新编辑区行号（优化：容错性更强，避免空内容报错）"""
        try:
            content = self.editor.get("1.0", tk.END)
            line_count = max(content.count("\n"), 1)  # 至少显示1行
            line_text = "\n".join(str(i) for i in range(1, line_count))
            self.line_numbers.config(state=tk.NORMAL)
            self.line_numbers.delete("1.0", tk.END)
            self.line_numbers.insert("1.0", line_text)
            self.line_numbers.config(state=tk.DISABLED)
            # 行号与编辑区滚动位置完全同步
            self.line_numbers.yview_moveto(self.editor.yview()[0])
        except Exception:
            pass

    def _auto_indent(self, event):
        """新增：智能自动缩进（仿VSCode，Python开发必备）"""
        # 获取当前光标所在行号
        current_line = self.editor.index(tk.INSERT).split(".")[0]
        # 获取上一行完整内容
        prev_line_content = self.editor.get(f"{current_line}.0", f"{current_line}.end")
        # 计算上一行的缩进空格数（仅统计开头的空格/制表符）
        indent_space = len(prev_line_content) - len(prev_line_content.lstrip())
        # 特殊场景：上一行以:结尾（if/for/def/while等），额外增加4个空格
        if prev_line_content.rstrip().endswith(":"):
            indent_space += 4
        # 插入回车+对应缩进，替代默认回车行为
        self.editor.insert(tk.INSERT, "\n" + " " * indent_space)
        # 阻止默认回车，避免重复换行
        return "break"

    def _syntax_highlight(self):
        """新增：Python实时语法高亮（关键字/字符串/注释/数字）"""
        # 先清除所有现有高亮标签，避免叠加
        for tag in ["keyword", "string", "comment", "number"]:
            self.editor.tag_remove(tag, "1.0", tk.END)

        # 获取编辑区所有内容，按行处理
        all_content = self.editor.get("1.0", tk.END)
        lines = all_content.split("\n")
        current_line = 1

        for line in lines:
            if not line:
                current_line += 1
                continue

            # 1. 注释高亮（# 开头，行内注释均支持）
            comment_index = line.find("#")
            if comment_index != -1:
                self.editor.tag_add(
                    "comment",
                    f"{current_line}.{comment_index}",
                    f"{current_line}.end"
                )
                # 注释后的内容不参与其他高亮，截断处理
                line = line[:comment_index]

            # 2. 字符串高亮（单引号/双引号，支持单行）
            for quote in ["'", '"']:
                start_idx = 0
                while True:
                    # 查找字符串开始位置
                    s_pos = line.find(quote, start_idx)
                    if s_pos == -1:
                        break
                    # 查找字符串结束位置
                    e_pos = line.find(quote, s_pos + 1)
                    if e_pos == -1:
                        break
                    # 添加字符串高亮标签
                    self.editor.tag_add(
                        "string",
                        f"{current_line}.{s_pos}",
                        f"{current_line}.{e_pos + 1}"
                    )
                    start_idx = e_pos + 1

            # 3. 关键字和数字高亮（按空格分割token）
            tokens = line.split()
            for token in tokens:
                # 清理token中的标点（如 if: → if，print() → print）
                clean_token = ''.join(c for c in token if c.isalnum() or c == "_")
                # 查找token在当前行的起始位置
                token_start = line.find(token)
                if token_start == -1:
                    continue
                token_end = token_start + len(token)

                # 关键字高亮（使用Python内置keyword模块，准确无遗漏）
                if iskeyword(clean_token):
                    self.editor.tag_add(
                        "keyword",
                        f"{current_line}.{token_start}",
                        f"{current_line}.{token_end}"
                    )
                # 数字高亮（支持整数/浮点数，如 123、3.14、0.5）
                elif clean_token.replace(".", "", 1).isdigit():
                    self.editor.tag_add(
                        "number",
                        f"{current_line}.{token_start}",
                        f"{current_line}.{token_end}"
                    )

            current_line += 1

    def _mark_modified(self):
        """标记文件未保存（优化：标题格式统一）"""
        if not self.is_modified:
            self.is_modified = True
            file_name = os.path.basename(self.current_file) if self.current_file else "未命名文件"
            self.root.title(f"Hcode - {file_name} * [Python编辑器]")
            self.status_bar.config(text=f"{file_name} | 未保存 | 按F5运行代码 | Ctrl+L清空控制台")

    def _mark_saved(self):
        """标记文件已保存（优化：标题格式统一）"""
        self.is_modified = False
        file_name = os.path.basename(self.current_file) if self.current_file else "未命名文件"
        self.root.title(f"Hcode - {file_name} [Python编辑器]")
        self.status_bar.config(text=f"{file_name} | 已保存 | 按F5运行代码 | Ctrl+L清空控制台")

    def _check_unsaved(self):
        """检查未保存内容（保持原有逻辑）"""
        if self.is_modified:
            result = messagebox.askyesnocancel("未保存的更改", "当前文件有未保存内容，是否放弃更改？")
            return result if result is not None else False
        return True

    # ========== 基础文件操作（保持原有逻辑，优化中文路径兼容） ==========
    def new_file(self):
        if self._check_unsaved():
            self.current_file = None
            self.editor.delete("1.0", tk.END)
            self.file_list.delete(0, tk.END)
            self._mark_saved()
            self._update_line_numbers()

    def open_file(self):
        if self._check_unsaved():
            file_path = filedialog.askopenfilename(
                title="打开文件",
                filetypes=[("Python文件", "*.py"), ("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            if file_path:
                try:
                    # 强制UTF-8编码，确保中文内容/路径无乱码
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.editor.delete("1.0", tk.END)
                    self.editor.insert("1.0", content)
                    self.current_file = file_path
                    self.file_list.delete(0, tk.END)
                    self.file_list.insert(0, os.path.basename(file_path))
                    self._mark_saved()
                    self._update_line_numbers()
                    self._syntax_highlight()  # 打开文件后立即高亮
                except Exception as e:
                    messagebox.showerror("打开失败", f"错误：{str(e)}")

    def save_file(self):
        if self.current_file:
            try:
                content = self.editor.get("1.0", tk.END)
                # 强制UTF-8编码，保存中文无乱码
                with open(self.current_file, "w", encoding="utf-8") as f:
                    f.write(content)
                self._mark_saved()
                messagebox.showinfo("保存成功", f"已保存至：\n{self.current_file}")
            except Exception as e:
                messagebox.showerror("保存失败", f"错误：{str(e)}")
        else:
            self.save_as_file()

    def save_as_file(self):
        file_path = filedialog.asksaveasfilename(
            title="另存为",
            defaultextension=".py",
            filetypes=[("Python文件", "*.py"), ("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                content = self.editor.get("1.0", tk.END)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.current_file = file_path
                self.file_list.delete(0, tk.END)
                self.file_list.insert(0, os.path.basename(file_path))
                self._mark_saved()
                messagebox.showinfo("另存为成功", f"已保存至：\n{self.current_file}")
            except Exception as e:
                messagebox.showerror("保存失败", f"错误：{str(e)}")

    # ========== 核心功能：运行代码 + 控制台操作（保持原有逻辑） ==========
    def run_code(self):
        """运行编辑区的Python代码，结果/错误输出到控制台"""
        self.console_insert(f"\n{'='*50}\n【运行开始】{os.path.basename(self.current_file) if self.current_file else '未命名文件'}\n{'='*50}\n")
        try:
            code = self.editor.get("1.0", tk.END).strip()
            if not code:
                self.console_insert("⚠️  错误：编辑区无代码可运行！\n", is_error=True)
                return
            local_namespace = {}
            exec(code, globals(), local_namespace)
            self.console_insert(f"\n✅ 运行成功！无报错信息\n")
        except SyntaxError as e:
            error_info = f"❌ 语法错误 - 第{e.lineno}行：{e.msg}\n错误代码：{e.text or '未知'}\n"
            self.console_insert(error_info, is_error=True)
        except Exception as e:
            error_info = f"❌ 运行时错误：{type(e).__name__} - {str(e)}\n"
            error_info += traceback.format_exc()
            self.console_insert(error_info, is_error=True)
        finally:
            self.console_insert(f"{'='*50}\n【运行结束】\n{'='*50}\n")

    def clear_console(self):
        """清空控制台所有内容"""
        self.console.config(state=tk.NORMAL)
        self.console.delete("1.0", tk.END)
        self.console.config(state=tk.DISABLED)
        self.console_insert("✅ 控制台已清空\n")

    def console_insert(self, text, is_error=False):
        """控制台插入文本：普通绿色，错误红色，自动滚动"""
        self.console.config(state=tk.NORMAL)
        if is_error:
            self.console.insert(tk.END, text, "error")
        else:
            self.console.insert(tk.END, text)
        self.console.config(state=tk.DISABLED)
        self.console.yview(tk.END)

    def _on_close(self):
        """关闭窗口：恢复标准输出，防止Python环境异常（保持原有逻辑）"""
        if self._check_unsaved():
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            self.root.destroy()

# 程序入口：全局异常捕获，确保100%能启动
if __name__ == "__main__":
    try:
        root = tk.Tk()
        # 新增：跨平台中文兼容，解决Tkinter中文显示乱码问题
        if sys.platform == "win32":
            root.option_add("*Font", "SimHei 10")  # Windows中文
        else:
            root.option_add("*Font", "WenQuanYi Zen Hei 10")  # Linux/Mac中文
        app = HCodeEditorWithRun(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("启动失败", f"编辑器启动出错：\n{str(e)}\n\n错误详情：\n{traceback.format_exc()}")
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        print(f"启动错误：{e}\n{traceback.format_exc()}")

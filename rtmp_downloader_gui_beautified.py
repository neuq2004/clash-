import subprocess
import datetime
import os
import sys
import requests
import re
import threading
import unicodedata
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QListWidget, QMenu, QAction, QMessageBox, QDesktopWidget,
    QScrollArea, QSizePolicy, QDialog, QListWidgetItem, QInputDialog, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QFontDatabase, QPalette, QColor
import time
import winsound
from plyer import notification
from collections import deque

# --- 配置项 ---
OUTPUT_DIR = r"D:\RTMP_Downloads"  # 输出目录：保存下载的视频文件
MIN_FILE_SIZE_MB = 50  # 最小文件大小（MB）：低于此大小的文件将被删除
SERVER_CHAN_SENDKEY = "sctp8915tireevunye59gauvucheojo"  # Server酱通知的SendKey
SUCCESS_SOUND = r"C:\Windows\Media\Windows Notify System Generic.wav"  # 成功提示音
WARNING_SOUND = r"C:\Windows\Media\Windows Notify System Generic.wav"  # 警告提示音
ERROR_SOUND = r"C:\Windows\Media\Windows Foreground.wav"  # 错误提示音
LOG_FOLDER_NAME = "logs"  # 日志文件夹名称
LOG_BASE_PATH = os.path.join(OUTPUT_DIR, LOG_FOLDER_NAME)  # 日志基础路径
LOG_BASE_NAME = "download_log"  # 日志文件基础名称
LOG_FILE_EXTENSION = ".txt"  # 日志文件扩展名
ANCHORS_FILE = "anchors.txt"  # 主播列表文件
FFMPEG_PATH = r"F:\Program\ffmpeg-2025-06-08-git-5fea5e3e11-full_build\bin\ffmpeg.exe"  # FFmpeg 路径
YT_DLP_PATH = r"F:\Program\ffmpeg-2025-06-08-git-5fea5e3e11-full_build\bin\yt-dlp.exe"  # yt-dlp 路径
DEFAULT_FONT_FAMILY = "Microsoft YaHei UI"  # 默认字体家族
DEFAULT_FONT_SIZE = 10  # 默认字体大小
LOG_FONT_SIZE = 9  # 日志字体大小
ANCHOR_LIST_FONT_FAMILY = "Microsoft YaHei UI"  # 主播列表字体
ANCHOR_LIST_FONT_SIZE = 12  # 主播列表字体大小
MAX_ANCHORS_PER_COLUMN = 52  # 每列最大主播数
ANCHOR_DROPDOWN_WIDTH = 1200 # 主播下拉菜单宽度
ANCHOR_DROPDOWN_HEIGHT = 1100 # 主播下拉菜单高度
UPDATE_INTERVAL_MS = 50  # 更新间隔（毫秒）
DOWNLOAD_TIMEOUT_SECONDS = 120  # 下载超时时间（秒）
STARTUP_TIMEOUT_SECONDS = 60  # 启动超时时间（秒）
TASKS_FRAME_HEIGHT = 600 # 任务栏高度（像素）
TASKS_FONT_SIZE = 11 # 任务栏字体大小
ICON_PATH = r"F:\Program\ffmpeg-2025-06-08-git-5fea5e3e11-full_build\icon" # 图标路径

# --- 现代化样式定义 ---
MODERN_STYLE = """
QMainWindow {
    background-color: #f8f9fa;
    color: #333;
}

QWidget {
    background-color: #ffffff;
    color: #333;
    font-family: 'Microsoft YaHei UI', sans-serif;
}

QPushButton {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: bold;
    font-size: 11px;
    min-width: 80px;
    min-height: 32px;
}

QPushButton:hover {
    background-color: #0056b3;
    transform: translateY(-1px);
}

QPushButton:pressed {
    background-color: #004085;
    transform: translateY(0px);
}

QPushButton:disabled {
    background-color: #e9ecef;
    color: #6c757d;
}

QPushButton#dangerButton {
    background-color: #dc3545;
}

QPushButton#dangerButton:hover {
    background-color: #c82333;
}

QPushButton#successButton {
    background-color: #28a745;
}

QPushButton#successButton:hover {
    background-color: #218838;
}

QPushButton#warningButton {
    background-color: #ffc107;
    color: #212529;
}

QPushButton#warningButton:hover {
    background-color: #e0a800;
}

QLineEdit {
    border: 2px solid #dee2e6;
    border-radius: 6px;
    padding: 10px 12px;
    font-size: 11px;
    background-color: white;
    selection-background-color: #007bff;
}

QLineEdit:focus {
    border-color: #007bff;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

QTextEdit {
    border: 2px solid #dee2e6;
    border-radius: 6px;
    padding: 8px;
    font-size: 10px;
    background-color: white;
    selection-background-color: #007bff;
}

QTextEdit:focus {
    border-color: #007bff;
}

QListWidget {
    border: 2px solid #dee2e6;
    border-radius: 6px;
    background-color: white;
    selection-background-color: #007bff;
    outline: none;
}

QListWidget::item {
    padding: 8px 12px;
    border-bottom: 1px solid #f8f9fa;
    border-radius: 4px;
    margin: 2px;
}

QListWidget::item:selected {
    background-color: #007bff;
    color: white;
}

QListWidget::item:hover {
    background-color: #f8f9fa;
}

QLabel {
    color: #333;
    font-size: 11px;
}

QLabel#titleLabel {
    font-size: 16px;
    font-weight: bold;
    color: #007bff;
    margin: 8px 0;
}

QLabel#sectionLabel {
    font-size: 12px;
    font-weight: bold;
    color: #495057;
    margin: 5px 0;
}

QFrame {
    background-color: white;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    margin: 4px;
}

QFrame#taskFrame {
    background-color: white;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    margin: 2px;
    padding: 6px;
}

QFrame#taskFrame:hover {
    border-color: #007bff;
    box-shadow: 0 2px 8px rgba(0, 123, 255, 0.15);
}

QScrollArea {
    border: none;
    background-color: #f8f9fa;
}

QScrollBar:vertical {
    background: #f8f9fa;
    width: 12px;
    border-radius: 6px;
    border: none;
}

QScrollBar::handle:vertical {
    background: #ced4da;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #adb5bd;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QMenu {
    background-color: white;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 16px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #007bff;
    color: white;
}
"""

# --- 深色主题样式 ---
DARK_THEME_STYLE = """
QMainWindow {
    background-color: #2b2b2b;
    color: #ffffff;
}

QWidget {
    background-color: #353535;
    color: #ffffff;
    font-family: 'Microsoft YaHei UI', sans-serif;
}

QPushButton {
    background-color: #0d7377;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: bold;
    font-size: 11px;
    min-width: 80px;
    min-height: 32px;
}

QPushButton:hover {
    background-color: #14a085;
}

QPushButton:pressed {
    background-color: #0a5d61;
}

QPushButton:disabled {
    background-color: #555555;
    color: #888888;
}

QPushButton#dangerButton {
    background-color: #dc3545;
}

QPushButton#dangerButton:hover {
    background-color: #c82333;
}

QPushButton#successButton {
    background-color: #28a745;
}

QPushButton#successButton:hover {
    background-color: #218838;
}

QLineEdit {
    border: 2px solid #555555;
    border-radius: 6px;
    padding: 10px 12px;
    font-size: 11px;
    background-color: #404040;
    color: white;
    selection-background-color: #0d7377;
}

QLineEdit:focus {
    border-color: #0d7377;
}

QTextEdit {
    border: 2px solid #555555;
    border-radius: 6px;
    padding: 8px;
    font-size: 10px;
    background-color: #404040;
    color: white;
    selection-background-color: #0d7377;
}

QListWidget {
    border: 2px solid #555555;
    border-radius: 6px;
    background-color: #404040;
    color: white;
    selection-background-color: #0d7377;
}

QListWidget::item {
    padding: 8px 12px;
    border-bottom: 1px solid #505050;
    border-radius: 4px;
    margin: 2px;
}

QListWidget::item:selected {
    background-color: #0d7377;
    color: white;
}

QListWidget::item:hover {
    background-color: #505050;
}

QLabel {
    color: #ffffff;
    font-size: 11px;
}

QLabel#titleLabel {
    font-size: 16px;
    font-weight: bold;
    color: #14a085;
    margin: 8px 0;
}

QFrame {
    background-color: #404040;
    border: 1px solid #555555;
    border-radius: 8px;
    margin: 4px;
}

QFrame#taskFrame {
    background-color: #404040;
    border: 1px solid #555555;
    border-radius: 6px;
    margin: 2px;
    padding: 6px;
}

QFrame#taskFrame:hover {
    border-color: #0d7377;
}

QScrollArea {
    border: none;
    background-color: #2b2b2b;
}

QScrollBar:vertical {
    background: #404040;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #606060;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #707070;
}
"""

# --- 辅助函数：计算字符串显示宽度 ---
def get_display_width(text):
    width = 0
    for char in text:
        if unicodedata.east_asian_width(char) in ('W', 'F', 'A'):
            width += 2
        else:
            width += 1
    return width

# --- 辅助函数：清理文件名 ---
def sanitize_filename(name):
    if not name:
        return "unnamed"
    invalid_chars = '<>:"/\\|?*'
    valid_chars_pattern = r'[\u4e00-\u9fa5a-zA-Z0-9\-_\.()\s]'
    sanitized = ''.join(c if re.match(valid_chars_pattern, c) and c not in invalid_chars else '_' for c in name)
    sanitized = sanitized.strip('_')
    return sanitized if sanitized else "unnamed"

# --- 辅助函数：截取 RTMP 变量 ---
def get_short_rtmp_var(rtmp_var):
    return rtmp_var.split('?')[0] + '?' if '?' in rtmp_var else rtmp_var

# --- 辅助函数：加载主播列表 ---
def load_anchors_from_file():
    anchors = {}
    if not os.path.exists(ANCHORS_FILE):
        return anchors
    try:
        with open(ANCHORS_FILE, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                anchor_name = line.strip()
                if anchor_name:
                    anchors[str(i)] = anchor_name 
        return anchors
    except Exception as e:
        print(f"加载主播列表失败: {e}")
        return anchors

# --- 辅助函数：保存主播列表 ---
def save_anchors_to_file(anchors):
    try:
        with open(ANCHORS_FILE, 'w', encoding='utf-8') as f:
            sorted_anchor_names = [name for _, name in sorted(anchors.items(), key=lambda item: int(item[0]))]
            for anchor_name in sorted_anchor_names:
                f.write(f"{anchor_name}\n")
    except Exception as e:
        print(f"保存主播列表失败: {e}")

# --- 辅助函数：获取当前日志文件路径 ---
def get_current_log_file_path():
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    log_filename = f"{LOG_BASE_NAME}_{today_str}{LOG_FILE_EXTENSION}"
    return os.path.join(LOG_BASE_PATH, log_filename)

# --- 辅助函数：写入日志 ---
def write_log(message, lock):
    if "下载开始: RTMP地址=" in message or "下载结束: 文件=" in message:
        current_log_file = get_current_log_file_path()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        with lock:
            try:
                os.makedirs(os.path.dirname(current_log_file), exist_ok=True)
                with open(current_log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
            except Exception as e:
                print(f"写入日志失败: {e}")

# --- 辅助函数：获取当天主播下载次数 ---
def get_today_download_count(anchor_name, lock):
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    sanitized_anchor_name = sanitize_filename(anchor_name)
    with lock:
        if not os.path.exists(OUTPUT_DIR):
            return 1
        existing_files = [f for f in os.listdir(OUTPUT_DIR) if os.path.isfile(os.path.join(OUTPUT_DIR, f))]
        pattern = re.compile(rf"^{re.escape(sanitized_anchor_name)}_{today_str}_(\d+)\.flv$", re.IGNORECASE)
        max_x = 0
        for filename in existing_files:
            match = pattern.match(filename)
            if match:
                try:
                    x_val = int(match.group(1))
                    if x_val > max_x:
                        max_x = x_val
                except ValueError:
                    continue
        return max_x + 1

# --- 辅助函数：播放声音 ---
def play_custom_sound(sound_file):
    if sound_file and os.path.exists(sound_file):
        try:
            winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as e:
            pass

# --- 辅助函数：发送Server酱通知 ---
def send_server_chan_notification(title, desp, log_lock):
    if SERVER_CHAN_SENDKEY == "XX" or not SERVER_CHAN_SENDKEY.strip():
        return
    url = f"https://sctapi.ftqq.com/{SERVER_CHAN_SENDKEY}.send"
    data = {"title": title, "desp": desp}
    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get('code') == 0:
            pass
        else:
            pass
    except requests.exceptions.RequestException as e:
        pass
    except Exception as e:
        pass

# --- 下载线程类 ---
class DownloadThread(QThread):
    log_signal = pyqtSignal(int, str)
    status_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(int, int, str)

    def __init__(self, task_id, variable_part, anchor_name, output_dir, min_file_size_mb, file_access_lock, log_lock):
        super().__init__()
        self.task_id = task_id
        self.variable_part = variable_part
        self.anchor_name = anchor_name
        self.output_dir = output_dir
        self.min_file_size_mb = min_file_size_mb
        self.file_access_lock = file_access_lock
        self.log_lock = log_lock
        self.process = None
        self._is_stopped = False
        self.sanitized_anchor_name = sanitize_filename(self.anchor_name)

    def run(self):
        start_time_dt = datetime.datetime.now()
        now = datetime.datetime.now()
        date_part = now.strftime("%Y%m%d")
        download_count = get_today_download_count(self.sanitized_anchor_name, self.file_access_lock)
        output_file_name = f"{self.sanitized_anchor_name}_{date_part}_{download_count}.flv"
        output_path = os.path.join(self.output_dir, output_file_name)
        full_rtmp_url = f"rtmp://hlive.whzhiyou.top/record/{self.variable_part}"
        
        self.log_signal.emit(self.task_id, f"任务{self.task_id} 目标 RTMP 地址: {full_rtmp_url}")
        self.log_signal.emit(self.task_id, f"任务{self.task_id} 将保存到: {output_path}")
        self.log_signal.emit(self.task_id, f"任务{self.task_id} 正在启动 YT-DLP 下载...")
        write_log(f"下载开始: RTMP地址='{full_rtmp_url}', 文件='{output_file_name}'", self.log_lock)

        with self.file_access_lock:
            if os.path.exists(output_path):
                self.log_signal.emit(self.task_id, f"任务{self.task_id} 错误: 文件 {output_path} 已存在")
                self.status_signal.emit(self.task_id, "文件已存在")
                self.finished_signal.emit(self.task_id, -1, "文件已存在")
                return

        if not self.variable_part or '?' not in self.variable_part:
            self.log_signal.emit(self.task_id, f"任务{self.task_id} 错误: RTMP 变量格式无效")
            self.status_signal.emit(self.task_id, "RTMP 变量无效")
            self.finished_signal.emit(self.task_id, -1, "RTMP 变量无效")
            return

        try:
            yt_dlp_cmd = [YT_DLP_PATH, "--version"] if os.path.exists(YT_DLP_PATH) else ["yt-dlp", "--version"]
            yt_dlp_version = subprocess.run(
                yt_dlp_cmd, 
                capture_output=True, 
                text=True, 
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.log_signal.emit(self.task_id, f"任务{self.task_id} 错误: 未找到 yt-dlp - {str(e)}")
            self.status_signal.emit(self.task_id, f"工具未找到: {str(e)}")
            self.finished_signal.emit(self.task_id, -1, f"工具未找到: {str(e)}")
            return

        try:
            ffmpeg_cmd = [FFMPEG_PATH, "-version"] if os.path.exists(FFMPEG_PATH) else ["ffmpeg", "-version"]
            ffmpeg_version = subprocess.run(
                ffmpeg_cmd, 
                capture_output=True, 
                text=True, 
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.log_signal.emit(self.task_id, f"任务{self.task_id} 警告: 未找到 ffmpeg - {str(e)}。yt-dlp可能无法下载部分格式。")

        try:
            yt_dlp_cmd = [YT_DLP_PATH, "--get-url", full_rtmp_url] if os.path.exists(YT_DLP_PATH) else ["yt-dlp", "--get-url", full_rtmp_url]
            response = subprocess.run(
                yt_dlp_cmd, 
                capture_output=True, 
                text=True, 
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except subprocess.CalledProcessError as e:
            self.log_signal.emit(self.task_id, f"任务{self.task_id} 错误: RTMP 地址无效或不可访问 - {e.stderr.strip()}")
            self.status_signal.emit(self.task_id, f"RTMP 地址无效: {e.stderr.strip()}")
            self.finished_signal.emit(self.task_id, -1, f"RTMP 地址无效: {e.stderr.strip()}")
            return

        exit_code = -1
        final_file_size_bytes = 0
        final_file_size_mb = 0.0
        duration_delta = datetime.timedelta(seconds=0)
        video_duration_str = "00:00:00"
        log_result_message = "结果: 未知错误或下载未完成。"
        server_chan_title = f"{os.path.basename(output_path)} - 下载出错"
        server_chan_desp = ""
        desktop_notification_title = "RTMP 下载通知"
        desktop_notification_message = ""
        sound_to_play = ERROR_SOUND

        try:
            command = [YT_DLP_PATH, "-o", output_path, full_rtmp_url]
            start_time = time.time()
            try:
                self.process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except (FileNotFoundError, subprocess.SubprocessError) as e:
                self.log_signal.emit(self.task_id, f"任务{self.task_id} 错误: 无法启动 yt-dlp - {str(e)}")
                self.status_signal.emit(self.task_id, f"启动失败: {str(e)}")
                self.finished_signal.emit(self.task_id, -1, f"启动失败: {str(e)}")
                return

            last_update = time.time()
            download_started_indicator = False

            while True:
                if self._is_stopped:
                    self.log_signal.emit(self.task_id, f"任务{self.task_id} 收到终止请求，正在停止...")
                    self.status_signal.emit(self.task_id, "已终止")
                    if self.process:
                        self.process.terminate()
                        try:
                            self.process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            self.process.kill()
                    exit_code = -2
                    log_result_message = "结果: 任务被用户终止。"
                    break

                returncode = self.process.poll()
                if returncode is not None:
                    exit_code = returncode
                    break

                try:
                    line = self.process.stdout.readline().strip()
                    if line:
                        self.process_yt_dlp_output(line)
                        last_update = time.time()
                        if "[download]" in line and ("%" in line or "ETA" in line or "MiB/s" in line or "KiB/s" in line or "B/s" in line or "Downloaded" in line):
                            download_started_indicator = True
                except Exception as e:
                    self.log_signal.emit(self.task_id, f"任务{self.task_id} 读取输出失败: {str(e)}")

                if not download_started_indicator and time.time() - start_time > STARTUP_TIMEOUT_SECONDS:
                    self.log_signal.emit(self.task_id, f"任务{self.task_id} 启动超时，未检测到下载进度")
                    self.status_signal.emit(self.task_id, "启动超时")
                    if self.process:
                        self.process.terminate()
                        try:
                            self.process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            self.process.kill()
                    exit_code = -1
                    log_result_message = "结果: 启动超时，未检测到下载进度。"
                    break

                if download_started_indicator and time.time() - last_update > DOWNLOAD_TIMEOUT_SECONDS:
                    self.log_signal.emit(self.task_id, f"任务{self.task_id} 下载超时，未检测到进度更新")
                    self.status_signal.emit(self.task_id, "下载超时")
                    if self.process:
                        self.process.terminate()
                        try:
                            self.process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            self.process.kill()
                    exit_code = -1
                    log_result_message = "结果: 下载超时，未检测到进度更新。"
                    break

                self.msleep(UPDATE_INTERVAL_MS)

            try:
                stdout_remaining, _ = self.process.communicate(timeout=1)
                if stdout_remaining:
                    for line in stdout_remaining.splitlines():
                        if line.strip():
                            self.process_yt_dlp_output(line.strip())
            except subprocess.TimeoutExpired:
                pass
            except Exception as e:
                pass

            end_time_dt = datetime.datetime.now()
            duration_delta = end_time_dt - start_time_dt
            total_seconds = int(duration_delta.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            video_duration_str = f"{hours:02}:{minutes:02}:{seconds:02}"

            if not self._is_stopped:
                with self.file_access_lock:
                    if os.path.exists(output_path):
                        final_file_size_bytes = os.path.getsize(output_path)
                        final_file_size_mb = final_file_size_bytes / (1024 * 1024)
                        if final_file_size_bytes == 0:
                            self.log_signal.emit(self.task_id, f"任务{self.task_id} 错误: 文件 {output_file_name} 已创建但为空")
                            self.status_signal.emit(self.task_id, "文件为空")
                            try:
                                os.remove(output_path)
                                self.log_signal.emit(self.task_id, f"任务{self.task_id} 文件 {output_file_name} 已删除")
                            except Exception as e:
                                self.log_signal.emit(self.task_id, f"任务{self.task_id} 删除空文件失败: {e}")
                            exit_code = -1
                            log_result_message = "结果: 文件为空已删除。"
                            return

                base_file_name_for_notify = os.path.basename(output_path)
                min_size_bytes = self.min_file_size_mb * 1024 * 1024

                if exit_code == 0 and os.path.exists(output_path) and final_file_size_bytes > 0:
                    if final_file_size_bytes < min_size_bytes:
                        self.log_signal.emit(self.task_id, f"任务{self.task_id} 下载完成，但文件大小 ({final_file_size_mb:.2f}MB) 低于 {self.min_file_size_mb}MB，将自动删除。")
                        with self.file_access_lock:
                            try:
                                os.remove(output_path)
                            except Exception as e:
                                self.log_signal.emit(self.task_id, f"任务{self.task_id} 删除文件失败: {e}")
                        self.status_signal.emit(self.task_id, f"文件太小 ({final_file_size_mb:.2f}MB)")
                        log_result_message = f"结果: 文件太小({final_file_size_mb:.2f}MB，少于{self.min_file_size_mb}MB)已删除。"
                        server_chan_title = f"{base_file_name_for_notify} ({int(final_file_size_mb)}MB) - 文件太小已删除"
                        server_chan_desp = (
                            f"**文件名:** {base_file_name_for_notify}\n\n"
                            f"**大小:** {final_file_size_mb:.2f}MB\n\n"
                            f"**时长:** {video_duration_str}\n\n"
                            f"**开始时间:** {start_time_dt.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"**结束时间:** {end_time_dt.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"**状态:** 下载完成但文件太小已删除！\n\n"
                            f"**原始RTMP地址:** {full_rtmp_url}"
                        )
                        desktop_notification_title = "RTMP 下载提醒"
                        desktop_notification_message = f"{base_file_name_for_notify} ({final_file_size_mb:.2f}MB, {video_duration_str}) - 文件太小已删除"
                        sound_to_play = WARNING_SOUND
                    else:
                        self.log_signal.emit(self.task_id, f"任务{self.task_id} 下载成功！视频已保存为: {output_path} (大小: {final_file_size_mb:.2f}MB, 时长: {video_duration_str})")
                        self.status_signal.emit(self.task_id, f"下载成功！({final_file_size_mb:.2f}MB)")
                        log_result_message = f"结果: 成功。文件大小: {final_file_size_mb:.2f}MB, 时长: {video_duration_str}。"
                        server_chan_title = f"{base_file_name_for_notify} ({int(final_file_size_mb)}MB) ✅"
                        server_chan_desp = (
                            f"**时长:** {video_duration_str}\n\n"
                            f"**开始时间:** {start_time_dt.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"**结束时间:** {end_time_dt.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"**状态:** ✅下载成功！\n\n"
                            f"**原始RTMP地址:** {full_rtmp_url}"
                        )
                        desktop_notification_title = "RTMP 下载成功"
                        desktop_notification_message = f"{base_file_name_for_notify} ({final_file_size_mb:.2f}MB, {video_duration_str}) - 下载成功"
                        sound_to_play = SUCCESS_SOUND
                else:
                    self.log_signal.emit(self.task_id, f"任务{self.task_id} 下载失败！YT-DLP 退出码: {exit_code}，文件不存在或为空。")
                    self.log_signal.emit(self.task_id, "请检查 RTMP 地址、YT-DLP/FFmpeg 安装或网络连接。")
                    self.status_signal.emit(self.task_id, f"下载失败: YT-DLP 退出码 {exit_code}")
                    log_result_message = f"结果: 失败。YT-DLP退出码={exit_code}, 文件存在={os.path.exists(output_path)}, 文件大小={final_file_size_bytes}字节。"
                    server_chan_title = f"{base_file_name_for_notify} - 下载失败"
                    server_chan_desp = (
                        f"**文件名:** {base_file_name_for_notify}\n\n"
                        f"**大小:** {final_file_size_mb:.2f}MB\n\n"
                        f"**时长:** {video_duration_str}\n\n"
                        f"**开始时间:** {start_time_dt.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"**结束时间:** {end_time_dt.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"**状态:** ❌下载失败！\n\n"
                        f"**错误码:** {exit_code}\n\n"
                        f"**原始RTMP地址:** {full_rtmp_url}\n\n"
                        f"请检查日志中的错误信息。"
                    )
                    desktop_notification_title = "RTMP 下载失败"
                    desktop_notification_message = f"{base_file_name_for_notify} ({final_file_size_mb:.2f}MB, {video_duration_str}) - 下载失败"
                    sound_to_play = ERROR_SOUND
            else:
                server_chan_title = f"{os.path.basename(output_path)} - 下载已终止"
                server_chan_desp = (
                    f"**文件名:** {os.path.basename(output_path)}\n\n"
                    f"**状态:** 任务已被用户终止。\n\n"
                    f"**原始RTMP地址:** {full_rtmp_url}"
                )
                desktop_notification_title = "RTMP 下载已终止"
                desktop_notification_message = f"{os.path.basename(output_path)} - 任务已终止"
                sound_to_play = WARNING_SOUND
        except Exception as e:
            self.log_signal.emit(self.task_id, f"任务{self.task_id} 下载时发生意外错误: {str(e)}")
            self.log_signal.emit(self.task_id, "请检查日志中的详细信息。")
            self.status_signal.emit(self.task_id, f"意外错误: {str(e)}")
            log_result_message = f"结果: 失败。发生意外错误: {str(e)}"
            server_chan_title = f"{os.path.basename(output_path)} - 意外错误"
            server_chan_desp = (
                f"发生意外错误: {str(e)}\n\n"
                f"**文件名:** {os.path.basename(output_path)}\n\n"
                f"**原始RTMP地址:** {full_rtmp_url}\n\n"
                f"请检查日志中的详细信息。"
            )
            desktop_notification_title = "RTMP 下载错误"
            desktop_notification_message = f"发生意外错误: {str(e)}"
            sound_to_play = ERROR_SOUND
        finally:
            self.process = None
            write_log(f"下载结束: 文件='{output_file_name}', 文件大小={final_file_size_mb:.2f}MB, 耗时={duration_delta}, 时长={video_duration_str}, {log_result_message}", self.log_lock)
            send_server_chan_notification(server_chan_title, server_chan_desp, self.log_lock)
            try:
                if notification:
                    notification.notify(
                        title=desktop_notification_title,
                        message=desktop_notification_message,
                        timeout=5
                    )
            except Exception as e:
                pass
            play_custom_sound(sound_to_play)
            self.finished_signal.emit(self.task_id, exit_code, log_result_message)

    def stop(self):
        self._is_stopped = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                pass

    def process_yt_dlp_output(self, line):
        if not line.strip():
            return
        
        line = line.strip()
        
        if "[download]" in line and ("%" in line or "ETA" in line or "MiB/s" in line or "KiB/s" in line or "B/s" in line):
            status_line = line.replace("[download]", "").strip()
            if "%" in status_line:
                parts = status_line.split()
                for part in parts:
                    if "%" in part:
                        try:
                            percentage = part.replace("%", "").strip()
                            if percentage.replace(".", "").isdigit():
                                self.status_signal.emit(self.task_id, f"下载中: {percentage}%")
                                break
                        except:
                            pass
            else:
                self.status_signal.emit(self.task_id, f"下载中: {status_line}")
        elif "[download]" in line and "Downloading" in line:
            self.status_signal.emit(self.task_id, "正在下载...")
        elif "[download]" in line and "has already been downloaded" in line:
            self.status_signal.emit(self.task_id, "文件已存在")
        elif "[download]" in line and "100%" in line:
            self.status_signal.emit(self.task_id, "下载完成")
        elif "[ffmpeg]" in line and "Merging" in line:
            self.status_signal.emit(self.task_id, "正在合并文件...")
        elif "[ffmpeg]" in line and "Converting" in line:
            self.status_signal.emit(self.task_id, "正在转换格式...")
        elif "ERROR" in line:
            self.status_signal.emit(self.task_id, "下载出错")
        elif "WARNING" in line:
            self.status_signal.emit(self.task_id, "警告")
        
        self.log_signal.emit(self.task_id, line)

# --- 主播编辑器对话框 ---
class AnchorEditorDialog(QDialog):
    anchors_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("主播列表编辑器")
        self.setModal(True)
        self.resize(700, 600)
        
        # 居中显示
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)
        
        self.current_anchors = {}
        self.load_current_anchors()
        self.init_ui()
        self.populate_anchor_list()

    def load_current_anchors(self):
        self.current_anchors = load_anchors_from_file()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 标题
        title_label = QLabel("主播列表管理")
        title_label.setObjectName("titleLabel")
        layout.addWidget(title_label)

        # 主播列表
        list_frame = QFrame()
        list_frame.setFrameStyle(QFrame.Box)
        list_layout = QVBoxLayout(list_frame)
        
        self.anchor_list = QListWidget()
        self.anchor_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                background-color: white;
                selection-background-color: #007bff;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #f8f9fa;
                border-radius: 4px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background-color: #007bff;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
            }
        """)
        list_layout.addWidget(self.anchor_list)
        layout.addWidget(list_frame)

        # 按钮区域
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        
        self.add_button = QPushButton("添加主播")
        self.add_button.setObjectName("successButton")
        self.add_button.clicked.connect(self.add_anchor)
        
        self.edit_button = QPushButton("编辑主播")
        self.edit_button.clicked.connect(self.edit_anchor)
        
        self.delete_button = QPushButton("删除主播")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self.delete_anchor)
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        
        layout.addWidget(button_frame)

        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        self.save_button = QPushButton("保存并关闭")
        self.save_button.setObjectName("successButton")
        self.save_button.clicked.connect(self.save_and_close)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setObjectName("dangerButton")
        self.cancel_button.clicked.connect(self.reject)
        
        bottom_layout.addWidget(self.save_button)
        bottom_layout.addWidget(self.cancel_button)
        layout.addLayout(bottom_layout)

    def populate_anchor_list(self):
        self.anchor_list.clear()
        if not self.current_anchors:
            return
        
        sorted_anchors = sorted(self.current_anchors.items(), key=lambda item: int(item[0]))
        for num, name in sorted_anchors:
            formatted_num = f"{int(num):03d}"
            item_text = f"{formatted_num}. {name}"
            self.anchor_list.addItem(item_text)

    def add_anchor(self):
        name, ok = QInputDialog.getText(self, "添加主播", "请输入主播名称:")
        if ok and name.strip():
            name = name.strip()
            if name:
                next_num = max([int(k) for k in self.current_anchors.keys()], default=0) + 1
                self.current_anchors[str(next_num)] = name
                self.populate_anchor_list()
                
                # 选中新添加的项
                for i in range(self.anchor_list.count()):
                    if name in self.anchor_list.item(i).text():
                        self.anchor_list.setCurrentRow(i)
                        break

    def delete_anchor(self):
        current_row = self.anchor_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请选择要删除的主播。")
            return
        
        current_item = self.anchor_list.item(current_row)
        if not current_item:
            return
        
        item_text = current_item.text()
        anchor_name = item_text.split('. ', 1)[1] if '. ' in item_text else item_text
        
        reply = QMessageBox.question(self, "确认删除", f"确定要删除主播 '{anchor_name}' 吗？", 
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # 找到要删除的键
            key_to_delete = None
            for key, value in self.current_anchors.items():
                if value == anchor_name:
                    key_to_delete = key
                    break
            
            if key_to_delete:
                del self.current_anchors[key_to_delete]
                # 重新编号
                self.renumber_anchors()
                self.populate_anchor_list()

    def edit_anchor(self):
        current_row = self.anchor_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请选择要编辑的主播。")
            return
        
        current_item = self.anchor_list.item(current_row)
        if not current_item:
            return
        
        item_text = current_item.text()
        old_name = item_text.split('. ', 1)[1] if '. ' in item_text else item_text
        
        new_name, ok = QInputDialog.getText(self, "编辑主播", "请输入新的主播名称:", text=old_name)
        if ok and new_name.strip():
            new_name = new_name.strip()
            if new_name != old_name:
                # 找到要修改的键
                key_to_update = None
                for key, value in self.current_anchors.items():
                    if value == old_name:
                        key_to_update = key
                        break
                
                if key_to_update:
                    self.current_anchors[key_to_update] = new_name
                    self.populate_anchor_list()
                    
                    # 选中修改后的项
                    for i in range(self.anchor_list.count()):
                        if new_name in self.anchor_list.item(i).text():
                            self.anchor_list.setCurrentRow(i)
                            break

    def renumber_anchors(self):
        """重新编号主播列表，确保连续"""
        if not self.current_anchors:
            return
        
        sorted_anchors = sorted(self.current_anchors.items(), key=lambda item: int(item[0]))
        self.current_anchors = {}
        
        for i, (_, name) in enumerate(sorted_anchors, 1):
            self.current_anchors[str(i)] = name

    def save_and_close(self):
        save_anchors_to_file(self.current_anchors)
        self.anchors_updated.emit()
        self.accept()

# --- 主应用程序类 ---
class RTMPDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RTMP 流下载器 - 美化版")
        self.setGeometry(100, 100, 1200, 800)
        
        # 居中显示
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)
        
        # 设置应用图标
        if os.path.exists(ICON_PATH):
            icon_file = os.path.join(ICON_PATH, "app.png")
            if os.path.exists(icon_file):
                self.setWindowIcon(QIcon(icon_file))
        
        # 数据结构
        self.anchors = {}
        self.found_anchors_list = []
        self.selected_anchor_name = ""
        self.selected_anchor_original_num = ""
        self.download_tasks = {}
        self.download_queue = deque()
        self.task_id_counter = 0
        self.task_id_lock = threading.Lock()
        self.file_access_lock = threading.Lock()
        self.log_lock = threading.Lock()
        self.max_anchor_name_display_width = 0
        self.max_rtmp_var_display_width = 0
        self.is_dark_theme = False
        
        # 字体设置
        self.default_font = QFont(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE)
        self.log_font = QFont(DEFAULT_FONT_FAMILY, LOG_FONT_SIZE)
        self.tasks_font = QFont(DEFAULT_FONT_FAMILY, TASKS_FONT_SIZE)
        self.anchor_list_font = QFont(ANCHOR_LIST_FONT_FAMILY, ANCHOR_LIST_FONT_SIZE)
        
        # 应用样式
        self.apply_modern_style()
        
        # 初始化界面
        self.init_ui()
        
        # 加载主播列表
        self.load_anchors()
        
        # 启动时检查输出目录
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
        if not os.path.exists(LOG_BASE_PATH):
            os.makedirs(LOG_BASE_PATH)

    def apply_modern_style(self):
        """应用现代化样式"""
        if self.is_dark_theme:
            self.setStyleSheet(DARK_THEME_STYLE)
        else:
            self.setStyleSheet(MODERN_STYLE)

    def toggle_theme(self):
        """切换主题"""
        self.is_dark_theme = not self.is_dark_theme
        self.apply_modern_style()

    def init_ui(self):
        # 主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 主布局
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # 标题区域
        title_layout = QHBoxLayout()
        title_label = QLabel("🎬 RTMP 流下载器")
        title_label.setObjectName("titleLabel")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # 主题切换按钮
        theme_button = QPushButton("🌙 深色主题")
        theme_button.setObjectName("warningButton")
        theme_button.clicked.connect(self.toggle_theme_with_text)
        title_layout.addWidget(theme_button)
        
        main_layout.addLayout(title_layout)
        
        # 输入区域
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_layout = QVBoxLayout(input_frame)
        input_layout.setSpacing(12)
        
        # RTMP 输入
        rtmp_layout = QVBoxLayout()
        rtmp_label = QLabel("📡 RTMP 地址变量:")
        rtmp_label.setObjectName("sectionLabel")
        rtmp_layout.addWidget(rtmp_label)
        
        rtmp_input_layout = QHBoxLayout()
        self.rtmp_entry = QLineEdit()
        self.rtmp_entry.setPlaceholderText("请输入 RTMP 变量部分，例如：room_id=12345?auth=xxx")
        self.rtmp_entry.textChanged.connect(self.check_download_button_state)
        self.rtmp_entry.setContextMenuPolicy(Qt.CustomContextMenu)
        self.rtmp_entry.customContextMenuRequested.connect(self.show_rtmp_menu)
        rtmp_input_layout.addWidget(self.rtmp_entry)
        
        self.paste_button = QPushButton("📋")
        self.paste_button.setToolTip("粘贴剪贴板内容")
        self.paste_button.clicked.connect(self.paste_to_rtmp_entry)
        self.paste_button.setMaximumWidth(40)
        rtmp_input_layout.addWidget(self.paste_button)
        
        rtmp_layout.addLayout(rtmp_input_layout)
        input_layout.addLayout(rtmp_layout)
        
        # 主播选择区域
        anchor_layout = QVBoxLayout()
        anchor_label = QLabel("👤 主播选择:")
        anchor_label.setObjectName("sectionLabel")
        anchor_layout.addWidget(anchor_label)
        
        anchor_select_layout = QHBoxLayout()
        
        # 搜索框
        search_layout = QVBoxLayout()
        search_label = QLabel("🔍 搜索主播:")
        search_layout.addWidget(search_label)
        
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("输入主播名称搜索...")
        self.search_entry.textChanged.connect(self.perform_search)
        search_layout.addWidget(self.search_entry)
        
        self.search_button = QPushButton("🔍 搜索")
        self.search_button.clicked.connect(self.perform_search)
        search_layout.addWidget(self.search_button)
        
        anchor_select_layout.addLayout(search_layout)
        
        # 主播选择
        select_layout = QVBoxLayout()
        select_label = QLabel("选择主播:")
        select_layout.addWidget(select_label)
        
        self.anchor_combo = QLineEdit()
        self.anchor_combo.setPlaceholderText("请选择主播")
        self.anchor_combo.setReadOnly(True)
        self.anchor_combo.textChanged.connect(self.check_download_button_state)
        self.anchor_combo.mousePressEvent = lambda event: self.show_anchor_dropdown()
        select_layout.addWidget(self.anchor_combo)
        
        anchor_buttons_layout = QHBoxLayout()
        
        self.edit_anchors_button = QPushButton("✏️ 编辑主播")
        self.edit_anchors_button.clicked.connect(self.open_anchor_editor)
        anchor_buttons_layout.addWidget(self.edit_anchors_button)
        
        self.refresh_anchors_button = QPushButton("🔄 刷新列表")
        self.refresh_anchors_button.clicked.connect(self.refresh_anchors_list)
        anchor_buttons_layout.addWidget(self.refresh_anchors_button)
        
        select_layout.addLayout(anchor_buttons_layout)
        
        anchor_select_layout.addLayout(select_layout)
        
        anchor_layout.addLayout(anchor_select_layout)
        input_layout.addLayout(anchor_layout)
        
        # 操作按钮
        buttons_layout = QHBoxLayout()
        
        self.add_to_queue_button = QPushButton("➕ 添加到队列")
        self.add_to_queue_button.clicked.connect(self.add_to_download_queue)
        buttons_layout.addWidget(self.add_to_queue_button)
        
        self.download_button = QPushButton("⬇️ 立即下载")
        self.download_button.setObjectName("successButton")
        self.download_button.clicked.connect(self.start_download_thread)
        buttons_layout.addWidget(self.download_button)
        
        self.start_queue_button = QPushButton("▶️ 开始队列下载")
        self.start_queue_button.clicked.connect(self.start_queue_downloads)
        buttons_layout.addWidget(self.start_queue_button)
        
        buttons_layout.addStretch()
        input_layout.addLayout(buttons_layout)
        
        main_layout.addWidget(input_frame)
        
        # 任务显示区域
        tasks_frame = QFrame()
        tasks_frame.setObjectName("tasksFrame")
        tasks_layout = QVBoxLayout(tasks_frame)
        
        tasks_title = QLabel("📋 下载任务")
        tasks_title.setObjectName("sectionLabel")
        tasks_layout.addWidget(tasks_title)
        
        # 任务滚动区域
        self.tasks_scroll = QScrollArea()
        self.tasks_scroll.setWidgetResizable(True)
        self.tasks_scroll.setMinimumHeight(400)
        self.tasks_scroll.setMaximumHeight(500)
        
        self.tasks_container = QWidget()
        self.tasks_container_layout = QVBoxLayout(self.tasks_container)
        self.tasks_container_layout.setSpacing(4)  # 紧凑间距
        self.tasks_container_layout.setContentsMargins(4, 4, 4, 4)  # 紧凑边距
        self.tasks_container_layout.addStretch(1)
        self.tasks_scroll.setWidget(self.tasks_container)
        
        tasks_layout.addWidget(self.tasks_scroll)
        main_layout.addWidget(tasks_frame)
        
        # 日志区域
        log_frame = QFrame()
        log_frame.setObjectName("logFrame")
        log_layout = QVBoxLayout(log_frame)
        
        log_title = QLabel("📄 运行日志")
        log_title.setObjectName("sectionLabel")
        log_layout.addWidget(log_title)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(self.log_font)
        self.log_text.setMinimumHeight(150)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        main_layout.addWidget(log_frame)
        
        # 初始状态
        self.check_download_button_state()

    def toggle_theme_with_text(self):
        """切换主题并更新按钮文本"""
        self.toggle_theme()
        # 更新按钮文本
        for button in self.findChildren(QPushButton):
            if "深色主题" in button.text():
                button.setText("☀️ 浅色主题" if self.is_dark_theme else "🌙 深色主题")
                break

    def closeEvent(self, event):
        """关闭应用时的清理工作"""
        running_tasks = []
        for task_id, task_info in self.download_tasks.items():
            thread = task_info.get('thread')
            if thread and thread.isRunning():
                running_tasks.append(task_id)
        
        if running_tasks:
            reply = QMessageBox.question(self, "确认退出", 
                                       f"还有 {len(running_tasks)} 个下载任务正在运行，确定要退出吗？",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            # 停止所有运行中的任务
            for task_id in running_tasks:
                self.stop_download_task(task_id)
        
        event.accept()

    def show_rtmp_menu(self, pos):
        """显示RTMP输入框右键菜单"""
        menu = QMenu(self)
        paste_action = QAction("粘贴", self)
        paste_action.triggered.connect(self.paste_to_rtmp_entry)
        menu.addAction(paste_action)
        menu.exec_(self.rtmp_entry.mapToGlobal(pos))

    def paste_to_rtmp_entry(self):
        """粘贴剪贴板内容到RTMP输入框"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.rtmp_entry.setText(text)
            self.write_to_log_ui(f"已粘贴内容: {text[:50]}{'...' if len(text) > 50 else ''}")

    def write_to_log_ui(self, message):
        """写入UI日志"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.log_text.append(formatted_message)
        
        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # 限制日志行数，防止内存占用过大
        if self.log_text.document().blockCount() > 1000:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.Down, cursor.KeepAnchor, 100)
            cursor.removeSelectedText()

    def write_to_log_file(self, message):
        """写入文件日志"""
        write_log(message, self.log_lock)

    def update_task_status_gui(self, task_id, status):
        """更新任务状态GUI"""
        if not isinstance(task_id, int):
            return
        if task_id not in self.download_tasks:
            return
        
        task_info = self.download_tasks.get(task_id)
        if not task_info or not task_info.get('task_label'):
            return
        
        self.download_tasks[task_id]['status'] = status
        task_id_str = str(task_id)
        anchor_name = task_info['anchor_name']
        short_rtmp_var = task_info['short_rtmp_var']
        
        current_anchor_comma_width = get_display_width(f"{anchor_name}, ")
        max_anchor_and_comma_width = self.max_anchor_name_display_width + get_display_width(",")
        max_rtmp_var_width = self.max_rtmp_var_display_width + get_display_width("变量: ,")
        padding_after_comma = " " * max(0, max_anchor_and_comma_width - current_anchor_comma_width)
        
        if status == "等待下载..." or "正在准备下载..." in status:
            current_rtmp_var_width = get_display_width(f"变量: {short_rtmp_var}, ")
            padding_after_rtmp_var = " " * max(0, max_rtmp_var_width - current_rtmp_var_width)
            full_task_display_text = f"[任务{task_id_str}] 主播: {anchor_name},{padding_after_comma} 变量: {short_rtmp_var},{padding_after_rtmp_var} 状态: {status}"
        else:
            full_task_display_text = f"[任务{task_id_str}] 主播: {anchor_name},{padding_after_comma} 状态: {status}"
        
        try:
            task_info['task_label'].setText(full_task_display_text)
            task_info['task_label'].update()
        except RuntimeError:
            pass

    def stop_download_task(self, task_id):
        """停止下载任务"""
        if not isinstance(task_id, int):
            return
        if task_id not in self.download_tasks:
            return
        
        thread = self.download_tasks[task_id].get('thread')
        if thread and thread.isRunning():
            self.write_to_log_ui(f"请求终止任务{task_id}...")
            thread.stop()
        else:
            self.write_to_log_ui(f"任务{task_id} 不在运行中或已终止。")
        self.remove_task_from_gui(task_id)

    def remove_task_from_gui(self, task_id):
        """从GUI移除任务"""
        if not isinstance(task_id, int):
            return
        if task_id not in self.download_tasks:
            return
        
        task_info = self.download_tasks.get(task_id)
        if task_info and task_info.get('task_widget'):
            task_widget_to_remove = task_info['task_widget']
            self.tasks_container_layout.removeWidget(task_widget_to_remove)
            task_widget_to_remove.deleteLater()
        
        try:
            del self.download_tasks[task_id]
        except KeyError:
            pass
        
        # 清理额外的拉伸项
        while self.tasks_container_layout.count() > 0 and self.tasks_container_layout.itemAt(self.tasks_container_layout.count() - 1).spacerItem():
            item = self.tasks_container_layout.takeAt(self.tasks_container_layout.count() - 1)
            del item
        
        # 如果还有项目，添加一个拉伸
        if self.tasks_container_layout.count() > 0:
            self.tasks_container_layout.addStretch(1)
        
        self.check_download_button_state()

    def check_download_button_state(self):
        """检查下载按钮状态"""
        enable = bool(self.rtmp_entry.text().strip() and self.anchor_combo.text() != "请选择主播" and self.anchor_combo.text() != "无主播")
        self.add_to_queue_button.setEnabled(enable)
        self.download_button.setEnabled(enable)
        self.start_queue_button.setEnabled(len(self.download_queue) > 0)

    def load_anchors(self):
        """加载主播列表"""
        old_anchors_count = len(self.anchors)
        self.anchors = load_anchors_from_file()
        self.max_anchor_name_display_width = 0
        
        for anchor_name in self.anchors.values():
            self.max_anchor_name_display_width = max(self.max_anchor_name_display_width, get_display_width(anchor_name))
        
        if self.max_anchor_name_display_width == 0:
            self.max_anchor_name_display_width = get_display_width("一个默认主播名占位符")
        
        if not self.anchors and not os.path.exists(ANCHORS_FILE):
            QMessageBox.warning(self, "警告", f"未找到主播配置文件 '{ANCHORS_FILE}'。\n请确保该文件存在且每行输入一个主播名称。")
            self.disable_operational_controls()
            self.anchor_combo.setText("无主播")
            self.anchor_combo.setEnabled(False)
            self.refresh_anchors_button.setEnabled(True)
            self.edit_anchors_button.setEnabled(True)
        elif not self.anchors:
            QMessageBox.warning(self, "警告", f"主播配置文件 '{ANCHORS_FILE}' 为空。\n请在文件中添加主播名称。")
            self.disable_operational_controls()
            self.anchor_combo.setText("无主播")
            self.anchor_combo.setEnabled(False)
            self.refresh_anchors_button.setEnabled(True)
            self.edit_anchors_button.setEnabled(True)
        else:
            self.found_anchors_list = list(self.anchors.items())
            self.found_anchors_list = sorted(self.found_anchors_list, key=lambda item: int(item[0]))
            
            if len(self.anchors) > old_anchors_count:
                self.write_to_log_ui(f"主播列表加载完成，新增 {len(self.anchors) - old_anchors_count} 位主播。")
            else:
                self.write_to_log_ui("主播列表加载完成。")
            
            self.rtmp_entry.setEnabled(True)
            self.search_entry.setEnabled(True)
            self.anchor_combo.setEnabled(True)
            self.search_button.setEnabled(True)
            self.refresh_anchors_button.setEnabled(True)
            self.edit_anchors_button.setEnabled(True)
            self.check_download_button_state()
            self.anchor_combo.setText("请选择主播")
            self.selected_anchor_name = ""
            self.selected_anchor_original_num = ""
            self.search_entry.clear()
            self.perform_search()

    def refresh_anchors_list(self):
        """刷新主播列表"""
        self.write_to_log_ui("正在刷新主播列表...")
        self.load_anchors()

    def disable_operational_controls(self):
        """禁用操作控件"""
        self.rtmp_entry.setEnabled(False)
        self.search_entry.setEnabled(False)
        self.add_to_queue_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.anchor_combo.setEnabled(False)
        self.search_button.setEnabled(False)
        self.paste_button.setEnabled(False)
        self.start_queue_button.setEnabled(False)

    def open_anchor_editor(self):
        """打开主播编辑器"""
        editor = AnchorEditorDialog(self)
        editor.anchors_updated.connect(self.load_anchors)
        editor.exec_()

    def show_anchor_dropdown(self):
        """显示主播下拉选择"""
        if not self.found_anchors_list:
            QMessageBox.information(self, "提示", "主播列表为空，请先刷新或检查 anchors.txt 文件。")
            return
        
        dropdown = QMainWindow(self)
        dropdown.setWindowTitle("选择主播")
        # 计算实际需要的高度
        actual_height = anchors_per_column * 28 + 100  # 加上窗口边框和标题栏
        dropdown.setFixedSize(ANCHOR_DROPDOWN_WIDTH, min(actual_height, 800))  # 最大不超过800px
        
        # 居中显示
        screen = QDesktopWidget().screenGeometry()
        size = dropdown.geometry()
        dropdown.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)
        
        central_widget = QWidget()
        dropdown.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        layout.setSpacing(10)
        
        total_anchors = len(self.found_anchors_list)
        num_columns = max(1, (total_anchors + MAX_ANCHORS_PER_COLUMN - 1) // MAX_ANCHORS_PER_COLUMN)
        anchors_per_column = (total_anchors + num_columns - 1) // num_columns
        
        max_name_lengths = [0] * num_columns
        anchor_indices = [[] for _ in range(num_columns)]
        current_idx = 0
        
        for c in range(num_columns):
            for _ in range(anchors_per_column):
                if current_idx < total_anchors:
                    original_num, anchor_name = self.found_anchors_list[current_idx]
                    max_name_lengths[c] = max(max_name_lengths[c], get_display_width(anchor_name))
                    anchor_indices[c].append(current_idx)
                    current_idx += 1
            
            list_widget = QListWidget()
            list_widget.setFont(self.anchor_list_font)
            calculated_width = (3 + max_name_lengths[c] + 5) * 10
            list_widget.setFixedWidth(max(calculated_width, 200))
            list_widget.setFixedHeight(anchors_per_column * 28 + 10)  # 完全展示所有项目
            list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 禁用滚动条
            
            for idx in anchor_indices[c]:
                original_num, anchor_name = self.found_anchors_list[idx]
                formatted_num = f"{int(original_num):03d}"
                item_text = f"{formatted_num}. {anchor_name}"
                list_widget.addItem(item_text)
                list_widget.item(list_widget.count() - 1).setData(Qt.UserRole, idx)
            
            list_widget.itemClicked.connect(lambda item, lw=list_widget: self.select_anchor(lw, dropdown))
            layout.addWidget(list_widget)
        
        dropdown.show()

    def select_anchor(self, list_widget, dropdown):
        """选择主播"""
        selected_item = list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "错误", "未选中主播，请重试。")
            return
        
        anchor_idx_in_found_list = selected_item.data(Qt.UserRole)
        if anchor_idx_in_found_list is None or not (0 <= anchor_idx_in_found_list < len(self.found_anchors_list)):
            QMessageBox.warning(self, "错误", "主播选择失败，请重试。")
            return
        
        original_num, anchor_name = self.found_anchors_list[anchor_idx_in_found_list]
        self.anchor_combo.setText(anchor_name)
        self.selected_anchor_name = anchor_name
        self.selected_anchor_original_num = original_num
        self.check_download_button_state()
        dropdown.close()

    def perform_search(self):
        """执行搜索"""
        query = self.search_entry.text().strip().lower()
        if not query:
            self.found_anchors_list = sorted(self.anchors.items(), key=lambda item: int(item[0]))
            self.anchor_combo.setText("请选择主播")
            self.selected_anchor_name = ""
            self.selected_anchor_original_num = ""
            return
        
        found = sorted([(num, name) for num, name in self.anchors.items() if query in name.lower()], key=lambda item: int(item[0]))
        self.found_anchors_list = found
        self.anchor_combo.setText("请选择主播")
        self.selected_anchor_name = ""
        self.selected_anchor_original_num = ""
        self.check_download_button_state()

    def check_duplicate_task(self, rtmp_var):
        """检查重复任务"""
        short_rtmp_var_to_check = get_short_rtmp_var(rtmp_var)
        
        # 检查正在进行的任务
        for task_id, task_info in self.download_tasks.items():
            if task_info['thread'] and task_info['thread'].isRunning():
                if get_short_rtmp_var(task_info['rtmp_var']) == short_rtmp_var_to_check:
                    return True, f"任务 {task_id} (主播: {task_info['anchor_name']}) 正在运行，RTMP 变量相同。"
        
        # 检查队列中的任务
        for task_id, _, _ in self.download_queue:
            task_info = self.download_tasks.get(task_id)
            if task_info and get_short_rtmp_var(task_info['rtmp_var']) == short_rtmp_var_to_check:
                return True, f"任务 {task_id} (主播: {task_info['anchor_name']}) 已在队列中，RTMP 变量相同。"
        
        return False, ""

    def add_to_download_queue(self):
        """添加到下载队列"""
        rtmp_var = self.rtmp_entry.text().strip()
        anchor_name = self.selected_anchor_name
        
        if not rtmp_var:
            QMessageBox.warning(self, "输入错误", "请输入 RTMP 变量部分。")
            return
        if not anchor_name:
            QMessageBox.warning(self, "错误", "主播名称为空，请重新选择。")
            return
        
        is_duplicate, duplicate_msg = self.check_duplicate_task(rtmp_var)
        if is_duplicate:
            reply = QMessageBox.question(self, "重复任务检测", 
                                       f"检测到重复任务：\n{duplicate_msg}\n\n是否仍然添加到队列？",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            self.write_to_log_ui(f"重复任务检测：'{rtmp_var}' - {duplicate_msg}. 用户选择: {'是' if reply == QMessageBox.Yes else '否'}")
            if reply == QMessageBox.No:
                return

        short_rtmp_var = get_short_rtmp_var(rtmp_var)
        with self.task_id_lock:
            self.task_id_counter += 1
            task_id = self.task_id_counter
        
        self.download_queue.append((task_id, rtmp_var, anchor_name))
        
        # 创建任务卡片
        task_info_widget = QFrame()
        task_info_widget.setObjectName("taskFrame")
        task_hbox_layout = QHBoxLayout(task_info_widget)
        task_hbox_layout.setContentsMargins(6, 4, 6, 4)
        task_hbox_layout.setSpacing(8)
        
        task_label = QLabel(f"[任务{task_id}] 主播: {anchor_name}, 变量: {short_rtmp_var}, 状态: 等待下载...")
        task_label.setFont(self.tasks_font)
        task_label.setObjectName("taskLabel")
        task_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        task_label.setMinimumWidth(700)
        task_hbox_layout.addWidget(task_label)
        
        stop_button = QPushButton("🗑️ 移除")
        stop_button.setObjectName("dangerButton")
        stop_button.setFont(self.default_font)
        stop_button.setFixedSize(70, 26)
        stop_button.clicked.connect(lambda _, tid=task_id: self.remove_from_queue(tid))
        task_hbox_layout.addWidget(stop_button, 0, Qt.AlignCenter)
        
        self.download_tasks[task_id] = {
            'anchor_name': anchor_name,
            'rtmp_var': rtmp_var,
            'short_rtmp_var': short_rtmp_var,
            'status': '等待下载...',
            'thread': None,
            'task_widget': task_info_widget,
            'task_label': task_label,
            'stop_button': stop_button
        }
        
        self.max_rtmp_var_display_width = max(self.max_rtmp_var_display_width, get_display_width(short_rtmp_var))
        
        # 移除现有的拉伸项
        while self.tasks_container_layout.count() > 0 and self.tasks_container_layout.itemAt(self.tasks_container_layout.count() - 1).spacerItem():
            item = self.tasks_container_layout.takeAt(self.tasks_container_layout.count() - 1)
            del item
        
        self.tasks_container_layout.addWidget(task_info_widget)
        self.tasks_container_layout.addStretch(1)
        
        self.write_to_log_ui(f"任务{task_id} 已添加到下载队列：RTMP变量='{rtmp_var}', 主播='{anchor_name}'")
        
        # 清空输入
        self.rtmp_entry.clear()
        self.anchor_combo.setText("请选择主播")
        self.selected_anchor_name = ""
        self.selected_anchor_original_num = ""
        self.check_download_button_state()

    def remove_from_queue(self, task_id):
        """从队列移除任务"""
        if not isinstance(task_id, int):
            return
        if task_id not in self.download_tasks:
            return
        
        # 检查任务是否已经在队列中
        queue_before = len(self.download_queue)
        self.download_queue = deque([(tid, rtmp, anchor) for tid, rtmp, anchor in self.download_queue if tid != task_id])
        queue_after = len(self.download_queue)

        if queue_before > queue_after:
            self.write_to_log_ui(f"任务{task_id} 从下载队列移除。")

        self.remove_task_from_gui(task_id)
        self.check_download_button_state()

    def start_queue_downloads(self):
        """开始队列下载"""
        if not self.download_queue:
            QMessageBox.information(self, "提示", "下载队列为空。")
            return
        
        self.write_to_log_ui("开始处理下载队列...")
        
        # 同时开始所有队列中的下载
        while self.download_queue:
            task_id, rtmp_var, anchor_name = self.download_queue.popleft()
            self.start_download_thread(task_id, rtmp_var, anchor_name)
        
        self.check_download_button_state()

    def start_download_thread(self, task_id=None, rtmp_var=None, anchor_name=None):
        """开始下载线程"""
        if task_id is None:  # 直接下载请求
            rtmp_var = self.rtmp_entry.text().strip()
            anchor_name = self.selected_anchor_name
            
            if not rtmp_var:
                QMessageBox.warning(self, "输入错误", "请输入 RTMP 变量部分。")
                return
            if not anchor_name:
                QMessageBox.warning(self, "错误", "主播名称为空，请重新选择。")
                return
            
            is_duplicate, duplicate_msg = self.check_duplicate_task(rtmp_var)
            if is_duplicate:
                reply = QMessageBox.question(self, "重复任务检测", 
                                           f"检测到重复任务：\n{duplicate_msg}\n\n是否仍然开始下载？",
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                self.write_to_log_ui(f"重复任务检测：'{rtmp_var}' - {duplicate_msg}. 用户选择: {'是' if reply == QMessageBox.Yes else '否'}")
                if reply == QMessageBox.No:
                    return

            with self.task_id_lock:
                self.task_id_counter += 1
                task_id = self.task_id_counter
            
            short_rtmp_var = get_short_rtmp_var(rtmp_var)
            
                         # 创建任务卡片
             task_info_widget = QFrame()
             task_info_widget.setObjectName("taskFrame")
             task_hbox_layout = QHBoxLayout(task_info_widget)
             task_hbox_layout.setContentsMargins(6, 4, 6, 4)
             task_hbox_layout.setSpacing(8)
             
             task_label = QLabel(f"[任务{task_id}] 主播: {anchor_name}, 变量: {short_rtmp_var}, 状态: 正在准备下载...")
             task_label.setFont(self.tasks_font)
             task_label.setObjectName("taskLabel")
             task_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
             task_label.setMinimumWidth(700)
             task_hbox_layout.addWidget(task_label)
             
             stop_button = QPushButton("⏹️ 终止")
             stop_button.setObjectName("dangerButton")
             stop_button.setFont(self.default_font)
             stop_button.setFixedSize(70, 26)
             stop_button.clicked.connect(lambda _, tid=task_id: self.stop_download_task(tid))
             task_hbox_layout.addWidget(stop_button, 0, Qt.AlignCenter)
            
            self.download_tasks[task_id] = {
                'anchor_name': anchor_name,
                'rtmp_var': rtmp_var,
                'short_rtmp_var': short_rtmp_var,
                'status': '正在准备下载...',
                'thread': None,
                'task_widget': task_info_widget,
                'task_label': task_label,
                'stop_button': stop_button
            }
            
            self.max_rtmp_var_display_width = max(self.max_rtmp_var_display_width, get_display_width(short_rtmp_var))
            
            # 移除现有的拉伸项
            while self.tasks_container_layout.count() > 0 and self.tasks_container_layout.itemAt(self.tasks_container_layout.count() - 1).spacerItem():
                item = self.tasks_container_layout.takeAt(self.tasks_container_layout.count() - 1)
                del item
            
            self.tasks_container_layout.addWidget(task_info_widget)
            self.tasks_container_layout.addStretch(1)
        else:  # 队列下载请求
            if not isinstance(task_id, int):
                return
            if task_id not in self.download_tasks:
                return
            
                         self.download_tasks[task_id]['status'] = '正在准备下载...'
             self.download_tasks[task_id]['stop_button'].setText("⏹️ 终止")
             self.download_tasks[task_id]['stop_button'].setFixedSize(70, 26)
             self.update_task_status_gui(task_id, "正在准备下载...")

        # 创建并启动下载线程
        thread = DownloadThread(task_id, rtmp_var, anchor_name, OUTPUT_DIR, MIN_FILE_SIZE_MB, self.file_access_lock, self.log_lock)
        self.download_tasks[task_id]['thread'] = thread
        
        thread.log_signal.connect(lambda tid, msg, t=task_id: self.write_to_log_ui(f"任务{t}: {msg}"))
        thread.status_signal.connect(lambda tid, msg, t=task_id: self.update_task_status_gui(t, msg))
        thread.finished_signal.connect(lambda tid, code, msg, t=task_id: self.download_finished_callback(t, code, msg))
        
        thread.start()
        
        # 清空输入字段 - 直接下载时总是清空，队列下载时不清空
        if rtmp_var == self.rtmp_entry.text().strip():  # 直接下载
            self.rtmp_entry.clear()
            self.anchor_combo.setText("请选择主播")
            self.selected_anchor_name = ""
            self.selected_anchor_original_num = ""
        
        self.check_download_button_state()

    def download_finished_callback(self, task_id, exit_code, error_msg):
        """下载完成回调"""
        if not isinstance(task_id, int):
            return
        if task_id not in self.download_tasks:
            return
        
        thread = self.download_tasks[task_id].get('thread')
        if thread and thread.isRunning():
            thread.wait(10000)
        
        if exit_code == 0:
            self.update_task_status_gui(task_id, "下载完成！")
        elif exit_code == -2:
            self.update_task_status_gui(task_id, "任务已终止")
        else:
            error_text = error_msg or "下载失败或取消。"
            self.update_task_status_gui(task_id, f"下载失败: {error_text}")
            QMessageBox.critical(self, "下载失败", f"任务{task_id} 失败或发生错误：{error_text}。请查看日志区域了解详情。")
        
        self.remove_task_from_gui(task_id)

# --- 主程序入口 ---
if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        print(f"正在创建视频下载目录: {OUTPUT_DIR}...")
        os.makedirs(OUTPUT_DIR)
    if not os.path.exists(LOG_BASE_PATH):
        print(f"正在创建日志目录: {LOG_BASE_PATH}...")
        os.makedirs(LOG_BASE_PATH)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用现代样式
    
    window = RTMPDownloaderApp()
    window.show()
    window.activateWindow()
    window.raise_()
    
    sys.exit(app.exec_())
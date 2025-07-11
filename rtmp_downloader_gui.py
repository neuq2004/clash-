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
    QScrollArea, QSizePolicy, QDialog, QListWidgetItem, QInputDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QFontDatabase
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
                    # 使用当前行号作为键，以维护文件中的原始顺序
                    anchors[str(i)] = anchor_name 
        return anchors
    except Exception as e:
        print(f"加载主播列表失败: {e}")
        return anchors

# --- 辅助函数：保存主播列表 ---
def save_anchors_to_file(anchors):
    try:
        with open(ANCHORS_FILE, 'w', encoding='utf-8') as f:
            # 获取所有主播名称并按其在字典中的原始键（编号）排序
            # sorted(anchors.items(), key=lambda item: int(item[0])) ensures numerical sort of string keys
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
    # 只记录特定的下载开始和结束信息
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
    # 过滤掉其他日志，不写入文件

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
            # write_log(f"播放声音失败: {e}", threading.Lock()) # 根据要求过滤掉此日志
            pass

# --- 辅助函数：发送Server酱通知 ---
def send_server_chan_notification(title, desp, log_lock):
    if SERVER_CHAN_SENDKEY == "XX" or not SERVER_CHAN_SENDKEY.strip():
        # write_log("Server酱 SendKey 未配置或为空，跳过通知发送。", log_lock) # 根据要求过滤掉此日志
        return
    url = f"https://sctapi.ftqq.com/{SERVER_CHAN_SENDKEY}.send"
    data = {"title": title, "desp": desp}
    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get('code') == 0:
            # write_log("Server酱通知发送成功！", log_lock) # 根据要求过滤掉此日志
            pass
        else:
            # write_log(f"Server酱通知发送失败：代码={result.get('code')}, 消息={result.get('message', '未知错误')}", log_lock) # 根据要求过滤掉此日志
            pass
    except requests.exceptions.RequestException as e:
        # write_log(f"发送Server酱通知时发生网络错误或超时：{e}", log_lock) # 根据要求过滤掉此日志
        pass
    except Exception as e:
        # write_log(f"发送Server酱通知时发生未知错误：{e}", log_lock) # 根据要求过滤掉此日志
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
        # write_log(f"DownloadThread 启动, task_id={self.task_id}", self.log_lock) # 根据要求过滤掉此日志
        start_time_dt = datetime.datetime.now()
        now = datetime.datetime.now()
        date_part = now.strftime("%Y%m%d")
        download_count = get_today_download_count(self.sanitized_anchor_name, self.file_access_lock)
        output_file_name = f"{self.sanitized_anchor_name}_{date_part}_{download_count}.flv"
        output_path = os.path.join(self.output_dir, output_file_name)
        full_rtmp_url = f"rtmp://hlive.whzhiyou.top/record/{self.variable_part}"
        # self.log_signal.emit(self.task_id, f"--- 任务{self.task_id} 处理下载 ---") # 根据要求过滤掉此日志
        # self.log_signal.emit(self.task_id, f"任务{self.task_id} 主播名称: {self.anchor_name}") # 根据要求过滤掉此日志
        # self.log_signal.emit(self.task_id, f"任务{self.task_id} 清理后文件名: {self.sanitized_anchor_name}") # 根据要求过滤掉此日志
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
            # self.log_signal.emit(self.task_id, f"任务{self.task_id} yt-dlp 版本: {yt_dlp_version.stdout.strip()}") # 根据要求过滤掉此日志
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
            # self.log_signal.emit(self.task_id, f"任务{self.task_id} ffmpeg 版本: {ffmpeg_version.stdout.strip()}") # 根据要求过滤掉此日志
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
            # self.log_signal.emit(self.task_id, f"任务{self.task_id} RTMP 地址验证成功: {response.stdout.strip()}") # 根据要求过滤掉此日志
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
            # self.log_signal.emit(self.task_id, f"任务{self.task_id} 执行命令: {' '.join(command)}") # 根据要求过滤掉此日志
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
                # self.log_signal.emit(self.task_id, f"任务{self.task_id} 读取剩余输出超时，进程可能未完全关闭。") # 根据要求过滤掉此日志
                pass
            except Exception as e:
                # self.log_signal.emit(self.task_id, f"任务{self.task_id} 读取剩余输出失败: {str(e)}") # 根据要求过滤掉此日志
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
                                # self.log_signal.emit(self.task_id, f"任务{self.task_id} 文件 {output_file_name} 已删除") # 根据要求过滤掉此日志
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
                        app_name="RTMP 下载工具",
                        timeout=10
                    )
                else:
                    # self.log_signal.emit(self.task_id, "警告: 'plyer' 库未导入或不可用，桌面通知功能无法使用。") # 根据要求过滤掉此日志
                    pass
            except Exception as e:
                # self.log_signal.emit(self.task_id, f"任务{self.task_id} 桌面通知发送失败: {e}") # 根据要求过滤掉此日志
                pass
            play_custom_sound(sound_to_play)
            self.finished_signal.emit(self.task_id, exit_code, log_result_message)

    def stop(self):
        self._is_stopped = True
        if self.process is not None and self.process.poll() is None:
            self.log_signal.emit(self.task_id, f"任务{self.task_id} 正在终止进程...")
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
                # self.log_signal.emit(self.task_id, f"任务{self.task_id} 进程已正常终止") # 根据要求过滤掉此日志
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.log_signal.emit(self.task_id, f"任务{self.task_id} 进程强制终止 (超时)")
            except Exception as e:
                self.log_signal.emit(self.task_id, f"任务{self.task_id} 关闭进程时发生错误: {e}")

    def process_yt_dlp_output(self, line):
        line = line.strip()
        # self.log_signal.emit(self.task_id, f"任务{self.task_id} [YT-DLP 输出]: {line}") # 根据要求过滤掉此日志
        # if "ETA" in line:
            # self.log_signal.emit(self.task_id, f"任务{self.task_id} 检测到 ETA: {line}") # 根据要求过滤掉此日志
        status_content = ""
        if "[download]" in line:
            match_full_progress = re.search(
                r"\[download\]\s+"
                r"(?:([\d.]+\%)\s+of\s+~?([\d.]+[KMG]?iB))?"
                r"\s*"
                r"(?:([\d.]+[KMG]?iB)\s+at\s+([\d.]+[KMG]?iB/s))?"
                r"\s*(?:\((\d{2}:\d{2}:\d{2})\)|ETA\s+(\d{2}:\d{2}(?::\d{2})?))?"
                r".*",
                line
            )
            if match_full_progress:
                percent, total_size, current_size, speed, eta_paren, eta_str = match_full_progress.groups()
                parts = []
                if percent:
                    parts.append(f"{percent}")
                    if total_size:
                        parts.append(f"of {total_size}")
                elif current_size:
                    parts.append(f"{current_size}")
                if speed:
                    parts.append(f"at {speed}")
                final_eta = eta_paren or eta_str or ""
                if final_eta:
                    parts.append(f"ETA {final_eta}")
                status_content = f"[下载中] {' '.join(parts)}" if parts else f"[下载中] {line.replace('[download]', '').strip()}"
                # if final_eta:
                    # self.log_signal.emit(self.task_id, f"任务{self.task_id} 匹配到 ETA: {final_eta}") # 根据要求过滤掉此日志
            elif re.search(r"\[download\] Downloaded ([\d.]+[KMG]?iB)", line):
                downloaded_size = re.search(r"\[download\] Downloaded ([\d.]+[KMG]?iB)", line).group(1)
                status_content = f"[下载中] 已下载 {downloaded_size}"
            elif re.search(r"\[download\] Destination:\s*(.*)", line):
                filename_full_path = re.search(r"\[download\] Destination:\s*(.*)", line).group(1).strip()
                display_filename = os.path.basename(filename_full_path)
                status_content = f"[下载中] 正在保存到: {display_filename}"
            else:
                status_content = f"[下载中] {line.replace('[download]', '').strip()}"
            self.status_signal.emit(self.task_id, status_content)
        elif "downloading" in line.lower() and ("http" in line.lower() or "rtmp" in line.lower()):
            self.status_signal.emit(self.task_id, f"[开始下载] {line.strip()}")
        elif "merging" in line.lower():
            self.status_signal.emit(self.task_id, "[处理中] 正在合并视频...")
        elif "postprocessing" in line.lower():
            self.status_signal.emit(self.task_id, "[处理中] 后期处理...")
        elif any(err in line.lower() for err in ["错误", "失败", "无法", "不能", "连接拒绝", "无法打开", "连接重置", "退出代码"]):
            self.status_signal.emit(self.task_id, f"下载错误: {line.strip()}")
            self.log_signal.emit(self.task_id, f"任务{self.task_id} 错误: {line.strip()}")
        # if "ETA" in line and not status_content:
            # self.log_signal.emit(self.task_id, f"任务{self.task_id} ETA 未匹配，正则可能需要调整: {line}") # 根据要求过滤掉此日志

# --- 主播编辑器 GUI 类 ---
class AnchorEditorDialog(QDialog):
    anchors_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("主播编辑器")
        self.setWindowIcon(QIcon(os.path.join(ICON_PATH, "edit_anchor.png")))
        self.setGeometry(200, 200, 400, 600)
        
        # 让弹窗居中显示
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        self.current_anchors = {}
        self.load_current_anchors()
        self.init_ui()

    def load_current_anchors(self):
        self.current_anchors = load_anchors_from_file()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 主播列表
        self.anchor_list_widget = QListWidget()
        self.anchor_list_widget.setFont(QFont(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE))
        self.populate_anchor_list()
        main_layout.addWidget(self.anchor_list_widget)

        # 添加主播
        add_layout = QHBoxLayout()
        self.new_anchor_entry = QLineEdit()
        self.new_anchor_entry.setPlaceholderText("输入新主播名称")
        self.new_anchor_entry.setFont(QFont(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE))
        add_button = QPushButton("添加主播")
        add_button.setFont(QFont(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE))
        add_button.setIcon(QIcon(os.path.join(ICON_PATH, "add.png")))
        add_button.clicked.connect(self.add_anchor)
        add_layout.addWidget(self.new_anchor_entry)
        add_layout.addWidget(add_button)
        main_layout.addLayout(add_layout)

        # 删除选中主播
        delete_button = QPushButton("删除选中主播")
        delete_button.setFont(QFont(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE))
        delete_button.setIcon(QIcon(os.path.join(ICON_PATH, "delete.png")))
        delete_button.clicked.connect(self.delete_anchor)
        main_layout.addWidget(delete_button)

        # 编辑选中主播 (可选，提供更好的用户体验)
        edit_button = QPushButton("编辑选中主播")
        edit_button.setFont(QFont(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE))
        edit_button.setIcon(QIcon(os.path.join(ICON_PATH, "edit.png")))
        edit_button.clicked.connect(self.edit_anchor)
        main_layout.addWidget(edit_button)

        # 保存并关闭
        save_button = QPushButton("保存并关闭")
        save_button.setFont(QFont(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, QFont.Bold))
        save_button.setIcon(QIcon(os.path.join(ICON_PATH, "save.png")))
        save_button.clicked.connect(self.save_and_close)
        main_layout.addWidget(save_button)

    def populate_anchor_list(self):
        self.anchor_list_widget.clear()
        # 将字典转换为按编号排序的列表
        sorted_anchors = sorted(self.current_anchors.items(), key=lambda item: int(item[0]))
        for num, name in sorted_anchors:
            # 格式化为三位数字
            formatted_num = f"{int(num):03d}"
            item = QListWidgetItem(f"{formatted_num}. {name}")
            item.setData(Qt.UserRole, (num, name)) # 存储原始编号和主播名
            self.anchor_list_widget.addItem(item)

    def add_anchor(self):
        new_name = self.new_anchor_entry.text().strip()
        if not new_name:
            QMessageBox.warning(self, "警告", "主播名称不能为空。")
            return
        if new_name in self.current_anchors.values():
            QMessageBox.warning(self, "警告", "该主播名称已存在。")
            return
        
        selected_item = self.anchor_list_widget.currentItem()
        
        # 获取当前主播名称的有序列表，保留它们的原始顺序
        current_ordered_names = [name for _, name in sorted(self.current_anchors.items(), key=lambda item: int(item[0]))]
        
        new_ordered_names = []

        if selected_item:
            # 获取选中项在 QListWidget 中的索引
            selected_row = self.anchor_list_widget.row(selected_item)
            
            # 在选中项的下一行插入新主播
            for i, name in enumerate(current_ordered_names):
                new_ordered_names.append(name)
                if i == selected_row: # QListWidget的row是0-based，与列表索引对应
                    new_ordered_names.append(new_name)
        else: # 未选中任何项，默认在最下方添加
            new_ordered_names = current_ordered_names + [new_name]

        # 重新构建 current_anchors 字典并重新编号
        reordered_anchors = {}
        for i, name in enumerate(new_ordered_names, 1):
            reordered_anchors[str(i)] = name
        self.current_anchors = reordered_anchors
            
        self.populate_anchor_list()
        self.new_anchor_entry.clear()
        QMessageBox.information(self, "成功", f"主播 '{new_name}' 已添加。")


    def delete_anchor(self):
        selected_item = self.anchor_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "警告", "请选择要删除的主播。")
            return

        original_num_to_delete, anchor_name_to_delete = selected_item.data(Qt.UserRole)
        reply = QMessageBox.question(self, "确认删除", f"确定要删除主播 '{anchor_name_to_delete}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # 获取当前所有主播名称的有序列表
            current_ordered_names = [name for _, name in sorted(self.current_anchors.items(), key=lambda item: int(item[0]))]
            
            # 从列表中移除要删除的主播
            if anchor_name_to_delete in current_ordered_names:
                current_ordered_names.remove(anchor_name_to_delete)
            
            # 重新构建 current_anchors 字典并重新编号
            new_anchors = {}
            for i, name in enumerate(current_ordered_names, 1):
                new_anchors[str(i)] = name
            self.current_anchors = new_anchors

            self.populate_anchor_list()
            QMessageBox.information(self, "成功", f"主播 '{anchor_name_to_delete}' 已删除。")

    def edit_anchor(self):
        selected_item = self.anchor_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "警告", "请选择要编辑的主播。")
            return
        
        old_anchor_num, old_anchor_name = selected_item.data(Qt.UserRole)
        new_anchor_name, ok = QInputDialog.getText(self, "编辑主播", f"编辑主播名称 '{old_anchor_name}':",
                                                   QLineEdit.Normal, old_anchor_name)
        if ok and new_anchor_name.strip():
            new_anchor_name = new_anchor_name.strip()
            if new_anchor_name == old_anchor_name:
                return # 名称未改变
            # 检查新名称是否与其他现有主播名称重复（不包括当前正在编辑的）
            for key, value in self.current_anchors.items():
                if value == new_anchor_name and key != old_anchor_num: # 确保不是自己
                    QMessageBox.warning(self, "警告", "新主播名称已存在。")
                    return
            
            # 更新字典中的主播名
            self.current_anchors[old_anchor_num] = new_anchor_name
            
            self.populate_anchor_list()
            QMessageBox.information(self, "成功", f"主播名称已从 '{old_anchor_name}' 更新为 '{new_anchor_name}'。")


    def save_and_close(self):
        # 将当前的 current_anchors 字典保存到文件
        # load_anchors_from_file 会按照文件行号重新加载编号，所以这里只需要保存有序的名称列表即可
        # populate_anchor_list 已经确保 current_anchors 内部是按数字键排序的
        # 这里的 self.current_anchors 已经包含了最新的顺序和连续编号
        save_anchors_to_file(self.current_anchors) # 直接保存 current_anchors，因为内部编号已整理好
        self.anchors_updated.emit() # 发出信号通知主窗口更新
        self.accept()

# --- RTMP 下载器GUI类 ---
class RTMPDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RTMP 下载工具")
        self.setFixedSize(1200, 1000)
        self.setWindowIcon(QIcon(os.path.join(ICON_PATH, "app_icon.png")))
        self.default_font = QFont(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE)
        self.log_font = QFont("Consolas", LOG_FONT_SIZE)
        font_db = QFontDatabase()
        if ANCHOR_LIST_FONT_FAMILY in font_db.families():
            self.anchor_list_font = QFont(ANCHOR_LIST_FONT_FAMILY, ANCHOR_LIST_FONT_SIZE)
            print(f"字体 '{ANCHOR_LIST_FONT_FAMILY}' 已加载。")
        else:
            print(f"警告: 字体 '{ANCHOR_LIST_FONT_FAMILY}' 不可用，使用 'Arial' 替代。")
            self.anchor_list_font = QFont("Arial", ANCHOR_LIST_FONT_SIZE)
        self.tasks_font = QFont(DEFAULT_FONT_FAMILY, TASKS_FONT_SIZE, QFont.Bold)
        self.anchors = {}
        self.found_anchors_list = []
        self.download_tasks = {}
        self.download_queue = deque()
        self.task_id_counter = 0
        self.task_id_lock = threading.Lock()  # 新增：保护 task_id_counter
        self.file_access_lock = threading.Lock()
        self.log_lock = threading.Lock()
        self.max_anchor_name_display_width = 0
        self.max_rtmp_var_display_width = 0
        self.selected_anchor_name = ""
        self.selected_anchor_original_num = ""
        self.init_ui()
        self.load_anchors()
        self.setStyleSheet("""
            QWidget {
                font-family: 'Microsoft YaHei UI';
                font-size: 10pt;
                background-color: #f0f2f5;
                color: #333333;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #dcdcdc;
                border-radius: 5px;
                padding: 5px;
                background-color: #ffffff;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #0078d4;
                background-color: #f9f9f9;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:pressed {
                background-color: #003087;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QScrollArea {
                border: 1px solid #dcdcdc;
                border-radius: 5px;
                background-color: #ffffff;
            }
            QLabel {
                color: #333333;
            }
            QLabel#taskLabel {
                font-family: 'Microsoft YaHei UI', 'Consolas';
                font-size: """ + str(TASKS_FONT_SIZE) + """pt;
                padding: 5px;
                font-weight: bold;
            }
            QTextEdit {
                background-color: #fafafa;
            }
            QListWidget {
                border: 1px solid #dcdcdc;
                border-radius: 5px;
                background-color: #ffffff;
                font-family: '""" + ANCHOR_LIST_FONT_FAMILY + """';
                font-size: """ + str(ANCHOR_LIST_FONT_SIZE) + """pt;
                padding: 10px;
            }
            QListWidget:focus {
                border: 1px solid #0078d4;
            }
            QPushButton#stopButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px;
                text-align: center;
                min-width: 90px;
                min-height: 26px;
                font-family: 'Microsoft YaHei UI', 'Segoe UI', 'SimSun';
                font-size: 10pt;
            }
            QPushButton#stopButton:hover {
                background-color: #c82333;
            }
            QPushButton#stopButton:pressed {
                background-color: #bd2130;
            }
            QPushButton#pasteButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton#pasteButton:hover {
                background-color: #218838;
            }
            QPushButton#pasteButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton#queueButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton#queueButton:hover {
                background-color: #138496;
            }
            QPushButton#queueButton:pressed {
                background-color: #117a8b;
            }
            QPushButton#queueButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QPushButton#editAnchorButton { /* Added style for new button */
                background-color: #ffc107;
                color: #333333;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton#editAnchorButton:hover { /* Added style for new button */
                background-color: #e0a800;
            }
            QPushButton#editAnchorButton:pressed { /* Added style for new button */
                background-color: #c69500;
            }
        """)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        # RTMP 输入区域
        rtmp_frame = QWidget()
        rtmp_layout = QHBoxLayout(rtmp_frame)
        rtmp_label = QLabel("变量部分：")
        rtmp_label.setFont(self.default_font)
        self.rtmp_entry = QLineEdit()
        self.rtmp_entry.setFont(self.default_font)
        self.rtmp_entry.setMinimumWidth(400)
        self.paste_button = QPushButton("粘贴")
        self.paste_button.setFont(self.default_font)
        self.paste_button.setObjectName("pasteButton")
        self.paste_button.setIcon(QIcon(os.path.join(ICON_PATH, "paste.png")))
        self.paste_button.clicked.connect(self.paste_to_rtmp_entry)
        rtmp_layout.addWidget(rtmp_label)
        rtmp_layout.addWidget(self.rtmp_entry)
        rtmp_layout.addWidget(self.paste_button)
        main_layout.addWidget(rtmp_frame)

        # 右键菜单
        self.rtmp_entry.setContextMenuPolicy(Qt.CustomContextMenu)
        self.rtmp_entry.customContextMenuRequested.connect(self.show_rtmp_menu)

        # 主播选择区域
        anchor_frame = QWidget()
        anchor_layout = QVBoxLayout(anchor_frame)
        search_refresh_frame = QWidget()
        search_refresh_layout = QHBoxLayout(search_refresh_frame)
        search_label = QLabel("搜索：")
        search_label.setFont(self.default_font)
        self.search_entry = QLineEdit()
        self.search_entry.setFont(self.default_font)
        self.search_entry.returnPressed.connect(self.perform_search)
        self.search_button = QPushButton("搜索")
        self.search_button.setFont(self.default_font)
        self.search_button.setIcon(QIcon(os.path.join(ICON_PATH, "search.png")))
        self.search_button.clicked.connect(self.perform_search)
        self.refresh_anchors_button = QPushButton("刷新主播列表")
        self.refresh_anchors_button.setFont(self.default_font)
        self.refresh_anchors_button.setIcon(QIcon(os.path.join(ICON_PATH, "refresh.png")))
        self.refresh_anchors_button.clicked.connect(self.refresh_anchors_list)
        self.edit_anchors_button = QPushButton("编辑主播") # 新增按钮
        self.edit_anchors_button.setFont(self.default_font)
        self.edit_anchors_button.setObjectName("editAnchorButton")
        self.edit_anchors_button.setIcon(QIcon(os.path.join(ICON_PATH, "edit_anchor.png")))
        self.edit_anchors_button.clicked.connect(self.open_anchor_editor) # 连接到新方法
        search_refresh_layout.addWidget(search_label)
        search_refresh_layout.addWidget(self.search_entry)
        search_refresh_layout.addWidget(self.search_button)
        search_refresh_layout.addWidget(self.refresh_anchors_button)
        search_refresh_layout.addWidget(self.edit_anchors_button) # 添加新按钮
        anchor_layout.addWidget(search_refresh_frame)
        anchor_label = QLabel("选择主播：")
        anchor_label.setFont(self.default_font)
        self.anchor_combo = QPushButton("请选择主播")
        self.anchor_combo.setFont(self.default_font)
        self.anchor_combo.setIcon(QIcon(os.path.join(ICON_PATH, "anchor.png")))
        self.anchor_combo.clicked.connect(self.show_anchor_dropdown)
        anchor_layout.addWidget(anchor_label)
        anchor_layout.addWidget(self.anchor_combo)
        main_layout.addWidget(anchor_frame)

        # 下载控制区域
        control_frame = QWidget()
        control_layout = QHBoxLayout(control_frame)
        self.add_to_queue_button = QPushButton("添加到队列")
        self.add_to_queue_button.setFont(self.default_font)
        self.add_to_queue_button.setIcon(QIcon(os.path.join(ICON_PATH, "queue.png")))
        self.add_to_queue_button.clicked.connect(self.add_to_download_queue)
        self.add_to_queue_button.setEnabled(False)
        self.start_queue_button = QPushButton("开始队列")
        self.start_queue_button.setFont(self.default_font)
        self.start_queue_button.setObjectName("queueButton")
        self.start_queue_button.setIcon(QIcon(os.path.join(ICON_PATH, "start_queue.png")))
        self.start_queue_button.clicked.connect(self.start_queue_downloads)
        self.start_queue_button.setEnabled(False)
        self.download_button = QPushButton("直接下载")
        self.download_button.setFont(self.default_font)
        self.download_button.setIcon(QIcon(os.path.join(ICON_PATH, "download.png")))
        # 修正：直接下载按钮的连接，不传递参数
        self.download_button.clicked.connect(lambda: self.start_download_thread())
        self.download_button.setEnabled(False)
        control_layout.addWidget(self.add_to_queue_button)
        control_layout.addWidget(self.start_queue_button)
        control_layout.addStretch()
        control_layout.addWidget(self.download_button)
        main_layout.addWidget(control_frame)

        # 任务状态区域
        tasks_frame = QWidget()
        tasks_layout = QVBoxLayout(tasks_frame)
        tasks_label = QLabel("正在进行的下载任务")
        tasks_label.setFont(QFont(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, QFont.Bold))
        tasks_layout.addWidget(tasks_label)
        self.tasks_scroll_area = QScrollArea()
        self.tasks_scroll_area.setWidgetResizable(True)
        self.tasks_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tasks_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tasks_scroll_area.setFixedHeight(TASKS_FRAME_HEIGHT)
        self.tasks_content_widget = QWidget()
        self.tasks_container_layout = QVBoxLayout(self.tasks_content_widget)
        self.tasks_container_layout.setAlignment(Qt.AlignTop)
        self.tasks_scroll_area.setWidget(self.tasks_content_widget)
        tasks_layout.addWidget(self.tasks_scroll_area)
        tasks_layout.setStretchFactor(self.tasks_scroll_area, 1)
        main_layout.addWidget(tasks_frame)
        main_layout.setStretchFactor(tasks_frame, 1)

        # 日志区域
        log_frame = QWidget()
        log_layout = QVBoxLayout(log_frame)
        log_label = QLabel("下载日志")
        log_label.setFont(QFont(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, QFont.Bold))
        self.log_text = QTextEdit()
        self.log_text.setFont(self.log_font)
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(100)
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_frame)

        self.rtmp_entry.textChanged.connect(self.check_download_button_state)

    def closeEvent(self, event):
        if self.download_tasks or self.download_queue:
            reply = QMessageBox.question(
                self, "确认退出", "有正在进行的下载任务或队列中的任务，是否终止并退出？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                for task_id in list(self.download_tasks.keys()):
                    self.stop_download_task(task_id)
                for task_id, task_info in list(self.download_tasks.items()):
                    if task_info['thread'] and task_info['thread'].isRunning():
                        task_info['thread'].wait(5000)
                self.download_queue.clear()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def show_rtmp_menu(self, pos):
        menu = QMenu(self.rtmp_entry)
        paste_action = QAction("粘贴", self)
        paste_action.setIcon(QIcon(os.path.join(ICON_PATH, "paste.png")))
        paste_action.triggered.connect(self.paste_to_rtmp_entry)
        menu.addAction(paste_action)
        menu.exec_(self.rtmp_entry.mapToGlobal(pos))

    def paste_to_rtmp_entry(self):
        try:
            clipboard = QApplication.clipboard()
            self.rtmp_entry.setText(clipboard.text())
            # self.write_to_log_ui("已粘贴剪贴板内容到 RTMP 变量输入框。") # 根据要求过滤掉此日志
        except Exception as e:
            # self.write_to_log_ui(f"剪贴板为空或无法访问: {e}") # 根据要求过滤掉此日志
            QMessageBox.warning(self, "警告", "剪贴板为空或无法访问。")

    def write_to_log_ui(self, message):
        if not isinstance(message, str):
            # self.write_to_log_file(f"警告: 尝试写入非字符串日志: {type(message)}") # 根据要求过滤掉此日志
            return
        try:
            # 过滤UI日志，只保留特定内容
            # 任务或队列开始，任务RTMP地址，下载成功，刷新主播提示
            if (("任务" in message and ("目标 RTMP 地址:" in message or "正在启动 YT-DLP 下载..." in message)) or
                "下载成功！视频已保存为:" in message or
                "已添加到下载队列：" in message or
                "开始处理下载队列..." in message or
                "主播列表加载完成" in message or
                "重复任务检测" in message or # 新增：重复任务检测的日志
                "正在刷新主播列表..." in message): # 新增：刷新主播列表的日志
                self.log_text.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")
                QTimer.singleShot(0, lambda: self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum()))
            # self.write_to_log_file(f"检测到False: {message}") # 根据要求过滤掉此日志
        except Exception as e:
            # self.write_to_log_file(f"写入日志到界面失败: {e}") # 根据要求过滤掉此日志
            pass

    def write_to_log_file(self, message):
        """辅助方法：确保所有日志写入文件"""
        write_log(message, self.log_lock)

    def update_task_status_gui(self, task_id, status):
        if not isinstance(task_id, int):
            # self.write_to_log_ui(f"错误: 无效的任务ID类型 {type(task_id)}，值: {task_id}") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"错误: update_task_status_gui 收到无效task_id: {task_id}") # 根据要求过滤掉此日志
            return
        if task_id not in self.download_tasks:
            # self.write_to_log_ui(f"错误: 任务{task_id} 未在 download_tasks 中找到") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"错误: 任务{task_id} 未在 download_tasks 中找到") # 根据要求过滤掉此日志
            return
        task_info = self.download_tasks.get(task_id)
        if not task_info or not task_info.get('task_label'):
            # self.write_to_log_ui(f"错误: 任务{task_id} 未在 download_tasks 中找到或控件已删除") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"错误: 任务{task_id} 未在 download_tasks 中找到或控件已删除") # 根据要求过滤掉此日志
            return
        self.download_tasks[task_id]['status'] = status
        task_id_str = str(task_id)
        anchor_name = task_info['anchor_name']
        short_rtmp_var = task_info['short_rtmp_var']
        current_anchor_comma_width = get_display_width(f"{anchor_name}, ")
        # max_task_id_width = len(str(self.task_id_counter)) # This might fluctuate, better to use a fixed or calculated max
        max_anchor_and_comma_width = self.max_anchor_name_display_width + get_display_width(",")
        max_rtmp_var_width = self.max_rtmp_var_display_width + get_display_width("变量: ,")
        padding_after_comma = " " * max(0, max_anchor_and_comma_width - current_anchor_comma_width)
        if status == "等待下载..." or "正在准备下载..." in status: # Adjust for initial states
            current_rtmp_var_width = get_display_width(f"变量: {short_rtmp_var}, ")
            padding_after_rtmp_var = " " * max(0, max_rtmp_var_width - current_rtmp_var_width)
            full_task_display_text = f"[任务{task_id_str}] 主播: {anchor_name},{padding_after_comma} 变量: {short_rtmp_var},{padding_after_rtmp_var} 状态: {status}"
        else:
            full_task_display_text = f"[任务{task_id_str}] 主播: {anchor_name},{padding_after_comma} 状态: {status}"
        try:
            task_info['task_label'].setText(full_task_display_text)
            task_info['task_label'].update()
            # self.write_to_log_file(f"任务{task_id} 状态更新: {status}") # 根据要求过滤掉此日志
        except RuntimeError:
            # self.write_to_log_ui(f"任务{task_id} 更新状态失败：控件已被删除") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"任务{task_id} 更新状态失败：控件已被删除") # 根据要求过滤掉此日志
            pass

    def stop_download_task(self, task_id):
        if not isinstance(task_id, int):
            # self.write_to_log_ui(f"错误: 无效的任务ID类型 {type(task_id)}，值: {task_id}") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"错误: stop_download_task 收到无效task_id: {task_id}") # 根据要求过滤掉此日志
            return
        if task_id not in self.download_tasks:
            # self.write_to_log_ui(f"错误: 任务{task_id} 未在 download_tasks 中找到") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"错误: 任务{task_id} 未在 download_tasks 中找到") # 根据要求过滤掉此日志
            return
        thread = self.download_tasks[task_id].get('thread')
        if thread and thread.isRunning():
            self.write_to_log_ui(f"请求终止任务{task_id}...")
            thread.stop()
        else:
            self.write_to_log_ui(f"任务{task_id} 不在运行中或已终止。")
        self.remove_task_from_gui(task_id)

    def remove_task_from_gui(self, task_id):
        if not isinstance(task_id, int):
            # self.write_to_log_ui(f"错误: 无效的任务ID类型 {type(task_id)}，值: {task_id}") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"错误: remove_task_from_gui 收到无效task_id: {task_id}") # 根据要求过滤掉此日志
            return
        if task_id not in self.download_tasks:
            # self.write_to_log_ui(f"错误: 任务{task_id} 未在 download_tasks 中找到") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"错误: 任务{task_id} 未在 download_tasks 中找到") # 根据要求过滤掉此日志
            return
        # self.write_to_log_ui(f"任务{task_id} 从GUI移除。") # 根据要求过滤掉此日志
        task_info = self.download_tasks.get(task_id)
        if task_info and task_info.get('task_widget'):
            task_widget_to_remove = task_info['task_widget']
            self.tasks_container_layout.removeWidget(task_widget_to_remove)
            task_widget_to_remove.deleteLater()
        try:
            del self.download_tasks[task_id]
        except KeyError:
            # self.write_to_log_ui(f"错误: 任务{task_id} 在移除时未找到") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"错误: 任务{task_id} 在移除时未找到") # 根据要求过滤掉此日志
            pass
        # Clear extra stretch items
        while self.tasks_container_layout.count() > 0 and self.tasks_container_layout.itemAt(self.tasks_container_layout.count() - 1).spacerItem():
            item = self.tasks_container_layout.takeAt(self.tasks_container_layout.count() - 1)
            del item
        # Add a single stretch at the end if there are still items
        if self.tasks_container_layout.count() > 0:
            self.tasks_container_layout.addStretch(1)
        self.check_download_button_state()

    def check_download_button_state(self):
        enable = bool(self.rtmp_entry.text().strip() and self.anchor_combo.text() != "请选择主播" and self.anchor_combo.text() != "无主播")
        self.add_to_queue_button.setEnabled(enable)
        self.download_button.setEnabled(enable)
        self.start_queue_button.setEnabled(len(self.download_queue) > 0)

    def load_anchors(self):
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
            self.edit_anchors_button.setEnabled(True) # 编辑主播按钮应该始终可用，即使文件不存在，方便创建
        elif not self.anchors:
            QMessageBox.warning(self, "警告", f"主播配置文件 '{ANCHORS_FILE}' 为空。\n请在文件中添加主播名称。")
            self.disable_operational_controls()
            self.anchor_combo.setText("无主播")
            self.anchor_combo.setEnabled(False)
            self.refresh_anchors_button.setEnabled(True)
            self.edit_anchors_button.setEnabled(True)
        else:
            self.found_anchors_list = list(self.anchors.items())
            # Ensure found_anchors_list is sorted by original number for consistent display
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
        self.write_to_log_ui("正在刷新主播列表...")
        self.load_anchors()

    def disable_operational_controls(self):
        self.rtmp_entry.setEnabled(False)
        self.search_entry.setEnabled(False)
        self.add_to_queue_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.anchor_combo.setEnabled(False)
        self.search_button.setEnabled(False)
        self.paste_button.setEnabled(False)
        self.start_queue_button.setEnabled(False)

    def open_anchor_editor(self):
        editor = AnchorEditorDialog(self)
        editor.anchors_updated.connect(self.load_anchors) # 连接信号，编辑器关闭后刷新主播列表
        editor.exec_()

    def show_anchor_dropdown(self):
        if not self.found_anchors_list:
            QMessageBox.information(self, "提示", "主播列表为空，请先刷新或检查 anchors.txt 文件。")
            return
        dropdown = QMainWindow(self)
        dropdown.setWindowTitle("选择主播")
        dropdown.setFixedSize(ANCHOR_DROPDOWN_WIDTH, ANCHOR_DROPDOWN_HEIGHT)
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
        # 这里不需要获取max_original_num_len，因为我们直接格式化为001
        # max_original_num_len = max(len(num) for num in self.anchors.keys()) if self.anchors else 0
        max_name_lengths = [0] * num_columns
        anchor_indices = [[] for _ in range(num_columns)]
        current_idx = 0
        for c in range(num_columns):
            start_idx = current_idx
            for _ in range(anchors_per_column):
                if current_idx < total_anchors:
                    # 使用 self.found_anchors_list 中的 (num, name) 对
                    original_num, anchor_name = self.found_anchors_list[current_idx]
                    max_name_lengths[c] = max(max_name_lengths[c], get_display_width(anchor_name))
                    anchor_indices[c].append(current_idx)
                    current_idx += 1
            list_widget = QListWidget()
            list_widget.setFont(self.anchor_list_font)
            # 假定编号固定为3位，因此宽度计算固定
            calculated_width = (3 + max_name_lengths[c] + 5) * 10 
            list_widget.setFixedWidth(max(calculated_width, 200))
            list_widget.setFixedHeight(min(anchors_per_column * 24, ANCHOR_DROPDOWN_HEIGHT - 50))
            list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            for idx in anchor_indices[c]:
                original_num, anchor_name = self.found_anchors_list[idx]
                # 格式化为三位数字
                formatted_num = f"{int(original_num):03d}"
                item_text = f"{formatted_num}. {anchor_name}"
                list_widget.addItem(item_text)
                list_widget.item(list_widget.count() - 1).setData(Qt.UserRole, idx) # 存储的是 self.found_anchors_list 的索引
            list_widget.itemClicked.connect(lambda item, lw=list_widget: self.select_anchor(lw, dropdown))
            layout.addWidget(list_widget)
            # self.write_to_log_ui(f"列 {c+1}: 添加 {len(anchor_indices[c])} 个主播，索引范围 {start_idx}-{current_idx-1}") # 根据要求过滤掉此日志
        dropdown.show()

    def select_anchor(self, list_widget, dropdown):
        selected_item = list_widget.currentItem()
        if not selected_item:
            # self.write_to_log_ui(f"主播选择失败：未选中任何项") # 根据要求过滤掉此日志
            QMessageBox.warning(self, "错误", "未选中主播，请重试。")
            return
        anchor_idx_in_found_list = selected_item.data(Qt.UserRole)
        if anchor_idx_in_found_list is None or not (0 <= anchor_idx_in_found_list < len(self.found_anchors_list)):
            # self.write_to_log_ui(f"主播选择失败：无效的索引 {anchor_idx}") # 根据要求过滤掉此日志
            QMessageBox.warning(self, "错误", "主播选择失败，请重试。")
            return
        original_num, anchor_name = self.found_anchors_list[anchor_idx_in_found_list]
        self.anchor_combo.setText(anchor_name)
        self.selected_anchor_name = anchor_name
        self.selected_anchor_original_num = original_num
        # self.write_to_log_ui(f"选择了主播: {anchor_name} (原始编号: {original_num}, 索引: {anchor_idx_in_found_list})") # 根据要求过滤掉此日志
        self.check_download_button_state()
        dropdown.close()

    def perform_search(self):
        query = self.search_entry.text().strip().lower()
        if not query:
            # 保持原始排序
            self.found_anchors_list = sorted(self.anchors.items(), key=lambda item: int(item[0]))
            # self.write_to_log_ui("搜索关键词为空，显示所有主播。") # 根据要求过滤掉此日志
            self.anchor_combo.setText("请选择主播")
            self.selected_anchor_name = ""
            self.selected_anchor_original_num = ""
            return
        # 搜索结果按原始编号排序
        found = sorted([(num, name) for num, name in self.anchors.items() if query in name.lower()], key=lambda item: int(item[0]))
        self.found_anchors_list = found
        # self.write_to_log_ui(f"搜索 '{query}'，找到 {len(found)} 位主播。") # 根据要求过滤掉此日志
        self.anchor_combo.setText("请选择主播")
        self.selected_anchor_name = ""
        self.selected_anchor_original_num = ""
        self.check_download_button_state()

    def check_duplicate_task(self, rtmp_var):
        short_rtmp_var_to_check = get_short_rtmp_var(rtmp_var)
        
        # 检查正在进行的任务
        for task_id, task_info in self.download_tasks.items():
            if task_info['thread'] and task_info['thread'].isRunning():
                if get_short_rtmp_var(task_info['rtmp_var']) == short_rtmp_var_to_check:
                    return True, f"任务 {task_id} (主播: {task_info['anchor_name']}) 正在运行，RTMP 变量相同。"
        
        # 检查队列中的任务
        for task_id, _, _ in self.download_queue:
            task_info = self.download_tasks.get(task_id) # 队列中的任务也会在 download_tasks 中
            if task_info and get_short_rtmp_var(task_info['rtmp_var']) == short_rtmp_var_to_check:
                return True, f"任务 {task_id} (主播: {task_info['anchor_name']}) 已在队列中，RTMP 变量相同。"
        
        return False, ""

    def add_to_download_queue(self):
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
        task_info_widget = QWidget()
        task_hbox_layout = QHBoxLayout(task_info_widget)
        task_hbox_layout.setContentsMargins(5, 2, 5, 2)
        task_hbox_layout.setSpacing(8)
        task_label = QLabel(f"[任务{task_id}] 主播: {anchor_name}, 变量: {short_rtmp_var}, 状态: 等待下载...")
        task_label.setFont(self.tasks_font)
        task_label.setObjectName("taskLabel")
        task_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        task_label.setMinimumWidth(700)
        task_hbox_layout.addWidget(task_label)
        stop_button = QPushButton("移除")
        stop_button.setFont(self.default_font)
        stop_button.setObjectName("stopButton")
        stop_button.setIcon(QIcon(os.path.join(ICON_PATH, "stop.png")))
        stop_button.setFixedSize(90, 26)
        stop_button.clicked.connect(lambda _, tid=task_id: self.remove_from_queue(tid))
        task_hbox_layout.addWidget(stop_button)
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
        # Remove any existing stretch to ensure new widget is added correctly
        while self.tasks_container_layout.count() > 0 and self.tasks_container_layout.itemAt(self.tasks_container_layout.count() - 1).spacerItem():
            item = self.tasks_container_layout.takeAt(self.tasks_container_layout.count() - 1)
            del item
        self.tasks_container_layout.addWidget(task_info_widget)
        self.tasks_container_layout.addStretch(1) # Add stretch after the new widget
        self.write_to_log_ui(f"任务{task_id} 已添加到下载队列：RTMP变量='{rtmp_var}', 主播='{anchor_name}'")
        # self.write_to_log_file(f"任务{task_id} 添加到队列，download_tasks={list(self.download_tasks.keys())}, download_queue={[t[0] for t in self.download_queue]}") # 根据要求过滤掉此日志
        self.rtmp_entry.clear()
        self.anchor_combo.setText("请选择主播")
        self.selected_anchor_name = ""
        self.selected_anchor_original_num = ""
        self.check_download_button_state()

    def remove_from_queue(self, task_id):
        if not isinstance(task_id, int):
            # self.write_to_log_ui(f"错误: 无效的任务ID类型 {type(task_id)}，值: {task_id}") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"错误: remove_from_queue 收到无效task_id: {task_id}") # 根据要求过滤掉此日志
            return
        if task_id not in self.download_tasks:
            # self.write_to_log_ui(f"错误: 任务{task_id} 未在 download_tasks 中找到") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"错误: 任务{task_id} 未在 download_tasks 中找到") # 根据要求过滤掉此日志
            return
        
        # 检查任务是否已经在队列中
        queue_before = len(self.download_queue)
        self.download_queue = deque([(tid, rtmp, anchor) for tid, rtmp, anchor in self.download_queue if tid != task_id])
        queue_after = len(self.download_queue)

        if queue_before > queue_after: # Successfully removed from queue
            self.write_to_log_ui(f"任务{task_id} 从下载队列移除。")
            # self.write_to_log_file(f"任务{task_id} 从队列移除，剩余队列={[t[0] for t in self.download_queue]}") # 根据要求过滤掉此日志
        else: # Task was not in queue, might be a running task or already completed
            pass # No log needed, as stop_download_task handles running tasks

        self.remove_task_from_gui(task_id)
        self.check_download_button_state()

    def start_queue_downloads(self):
        if not self.download_queue:
            QMessageBox.information(self, "提示", "下载队列为空。")
            return
        self.write_to_log_ui("开始处理下载队列...")
        # Start all downloads in the queue simultaneously
        while self.download_queue:
            task_id, rtmp_var, anchor_name = self.download_queue.popleft()
            self.start_download_thread(task_id, rtmp_var, anchor_name)
        self.check_download_button_state()


    def start_download_thread(self, task_id=None, rtmp_var=None, anchor_name=None):
        # self.write_to_log_ui(f"启动下载线程，传入参数: task_id={task_id}, rtmp_var={rtmp_var}, anchor_name={anchor_name}") # 根据要求过滤掉此日志
        # self.write_to_log_file(f"start_download_thread 调用，task_id={task_id}, rtmp_var={rtmp_var}, anchor_name={anchor_name}") # 根据要求过滤掉此日志
        if task_id is None: # This is a direct download request
            rtmp_var = self.rtmp_entry.text().strip()
            anchor_name = self.selected_anchor_name
            if not rtmp_var:
                # self.write_to_log_ui("错误: RTMP 变量为空") # 根据要求过滤掉此日志
                # self.write_to_log_file("错误: RTMP 变量为空") # 根据要求过滤掉此日志
                QMessageBox.warning(self, "输入错误", "请输入 RTMP 变量部分。")
                return
            if not anchor_name:
                # self.write_to_log_ui("错误: 主播名称为空") # 根据要求过滤掉此日志
                # self.write_to_log_file("错误: 主播名称为空") # 根据要求过滤掉此日志
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
            # self.write_to_log_ui(f"分配新任务ID: {task_id} for 直接下载") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"分配新任务ID: {task_id} for 直接下载, rtmp_var={rtmp_var}, anchor_name={anchor_name}") # 根据要求过滤掉此日志
            task_info_widget = QWidget()
            task_hbox_layout = QHBoxLayout(task_info_widget)
            task_hbox_layout.setContentsMargins(5, 2, 5, 2)
            task_hbox_layout.setSpacing(8)
            task_label = QLabel(f"[任务{task_id}] 主播: {anchor_name}, 变量: {short_rtmp_var}, 状态: 正在准备下载...")
            task_label.setFont(self.tasks_font)
            task_label.setObjectName("taskLabel")
            task_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            task_label.setMinimumWidth(700)
            task_hbox_layout.addWidget(task_label)
            stop_button = QPushButton("终止")
            stop_button.setFont(self.default_font)
            stop_button.setObjectName("stopButton")
            stop_button.setIcon(QIcon(os.path.join(ICON_PATH, "stop.png")))
            stop_button.setFixedSize(90, 26)
            stop_button.clicked.connect(lambda _, tid=task_id: self.stop_download_task(tid))
            task_hbox_layout.addWidget(stop_button)
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
            # self.write_to_log_ui(f"任务{task_id} 控件已创建，主播: {anchor_name}, RTMP变量: {rtmp_var}") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"任务{task_id} 控件已创建，download_tasks={list(self.download_tasks.keys())}") # 根据要求过滤掉此日志
            while self.tasks_container_layout.count() > 0 and self.tasks_container_layout.itemAt(self.tasks_container_layout.count() - 1).spacerItem():
                item = self.tasks_container_layout.takeAt(self.tasks_container_layout.count() - 1)
                del item
            self.tasks_container_layout.addWidget(task_info_widget)
            self.tasks_container_layout.addStretch(1)
            # self.write_to_log_ui(f"任务{task_id} 已添加到任务栏") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"任务{task_id} 已添加到任务栏，download_tasks={list(self.download_tasks.keys())}") # 根据要求过滤掉此日志
        else: # This is a queue download request
            if not isinstance(task_id, int):
                # self.write_to_log_ui(f"错误: 无效的任务ID类型 {type(task_id)}，值: {task_id}") # 根据要求过滤掉此日志
                # self.write_to_log_file(f"错误: 队列下载收到无效task_id: {task_id}") # 根据要求过滤掉此日志
                return
            if task_id not in self.download_tasks:
                # self.write_to_log_ui(f"错误: 任务{task_id} 未在 download_tasks 中找到") # 根据要求过滤掉此日志
                # self.write_to_log_file(f"错误: 任务{task_id} 未在 download_tasks 中找到") # 根据要求过滤掉此日志
                return
            self.download_tasks[task_id]['status'] = '正在准备下载...'
            self.download_tasks[task_id]['stop_button'].setText("终止")
            self.update_task_status_gui(task_id, "正在准备下载...")
            # self.write_to_log_file(f"任务{task_id} 从队列启动，更新按钮为'终止'，download_tasks={list(self.download_tasks.keys())}") # 根据要求过滤掉此日志

        thread = DownloadThread(task_id, rtmp_var, anchor_name, OUTPUT_DIR, MIN_FILE_SIZE_MB, self.file_access_lock, self.log_lock)
        self.download_tasks[task_id]['thread'] = thread
        thread.log_signal.connect(lambda tid, msg, t=task_id: self.write_to_log_ui(f"任务{t}: {msg}"))
        thread.status_signal.connect(lambda tid, msg, t=task_id: self.update_task_status_gui(t, msg))
        thread.finished_signal.connect(lambda tid, code, msg, t=task_id: self.download_finished_callback(t, code, msg))
        # self.write_to_log_file(f"任务{task_id} 信号连接完成，thread={id(thread)}") # 根据要求过滤掉此日志
        thread.start()
        # self.write_to_log_ui(f"任务{task_id} 下载线程已启动") # 根据要求过滤掉此日志
        # self.write_to_log_file(f"任务{task_id} 下载线程已启动，download_tasks={list(self.download_tasks.keys())}") # 根据要求过滤掉此日志
        
        # Only clear input fields if it's a direct download or if queue is empty after starting a queue task
        if task_id not in [tid for tid, _, _ in self.download_queue]:
            self.rtmp_entry.clear()
            self.anchor_combo.setText("请选择主播")
            self.selected_anchor_name = ""
            self.selected_anchor_original_num = ""
        self.check_download_button_state()

    def download_finished_callback(self, task_id, exit_code, error_msg):
        if not isinstance(task_id, int):
            # self.write_to_log_ui(f"错误: 无效的任务ID类型 {type(task_id)}，值: {task_id}") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"错误: download_finished_callback 收到无效task_id: {task_id}") # 根据要求过滤掉此日志
            return
        if task_id not in self.download_tasks:
            # self.write_to_log_ui(f"错误: 任务{task_id} 未在 download_tasks 中找到") # 根据要求过滤掉此日志
            # self.write_to_log_file(f"错误: 任务{task_id} 未在 download_tasks 中找到") # 根据要求过滤掉此日志
            return
        # self.write_to_log_ui(f"任务{task_id} 下载完成回调，退出码: {exit_code}, 信息: {error_msg}") # 根据要求过滤掉此日志
        # self.write_to_log_file(f"任务{task_id} 下载完成回调，退出码: {exit_code}, 信息: {error_msg}, download_tasks={list(self.download_tasks.keys())}") # 根据要求过滤掉此日志
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

        # After a task finishes, if there are items in the queue, start the next one
        # This line is removed to allow multiple simultaneous downloads.
        # if self.download_queue:
        #     QTimer.singleShot(1000, self.start_queue_downloads) # Add a small delay

if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        print(f"正在创建视频下载目录: {OUTPUT_DIR}...")
        os.makedirs(OUTPUT_DIR)
    if not os.path.exists(LOG_BASE_PATH):
        print(f"正在创建日志目录: {LOG_BASE_PATH}...")
        os.makedirs(LOG_BASE_PATH)
    app = QApplication(sys.argv)
    window = RTMPDownloaderApp()
    window.show()
    window.activateWindow()
    window.raise_()
    sys.exit(app.exec_())
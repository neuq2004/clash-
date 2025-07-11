from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import subprocess
import time
import os
import json
import hashlib

class EnhancedDownloadThread(QThread):
    """增强的下载线程"""
    
    # 信号定义
    progress_signal = pyqtSignal(int, int, int)  # task_id, progress, speed
    log_signal = pyqtSignal(int, str)
    status_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(int, int, str)
    thumbnail_signal = pyqtSignal(int, str)  # task_id, thumbnail_path
    
    def __init__(self, task_id, rtmp_url, anchor_name, config_manager):
        super().__init__()
        self.task_id = task_id
        self.rtmp_url = rtmp_url
        self.anchor_name = anchor_name
        self.config = config_manager
        self.process = None
        self._is_stopped = False
        self._is_paused = False
        self.retry_count = 0
        self.max_retries = self.config.get('download.retry_count', 3)
        self.resume_info = None
        
    def run(self):
        """主下载逻辑"""
        while self.retry_count <= self.max_retries:
            try:
                self._download_stream()
                break
            except Exception as e:
                self.retry_count += 1
                if self.retry_count <= self.max_retries:
                    self.log_signal.emit(
                        self.task_id, 
                        f"下载失败，{5}秒后重试 ({self.retry_count}/{self.max_retries}): {str(e)}"
                    )
                    time.sleep(5)
                else:
                    self.finished_signal.emit(self.task_id, -1, f"重试次数已达上限: {str(e)}")
                    return
    
    def _download_stream(self):
        """执行下载"""
        output_path = self._get_output_path()
        
        # 检查断点续传
        if self._should_resume(output_path):
            self.log_signal.emit(self.task_id, "检测到未完成的下载，继续下载...")
            self.status_signal.emit(self.task_id, "断点续传中...")
        else:
            self.status_signal.emit(self.task_id, "开始下载...")
        
        # 构建下载命令
        command = self._build_download_command(output_path)
        
        # 启动下载进程
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            universal_newlines=True
        )
        
        # 监控下载进度
        self._monitor_download_progress()
        
        # 检查下载结果
        self._check_download_result(output_path)
    
    def _build_download_command(self, output_path):
        """构建下载命令"""
        yt_dlp_path = self.config.get('paths.yt_dlp_path', 'yt-dlp')
        
        command = [
            yt_dlp_path,
            '--no-playlist',
            '--write-thumbnail',
            '--write-info-json',
            '--output', output_path,
            self.rtmp_url
        ]
        
        # 添加断点续传支持
        if self._should_resume(output_path):
            command.extend(['--continue', '--no-overwrites'])
        
        # 添加速度限制
        speed_limit = self.config.get('download.speed_limit')
        if speed_limit:
            command.extend(['--limit-rate', f'{speed_limit}K'])
        
        return command
    
    def _monitor_download_progress(self):
        """监控下载进度"""
        last_progress_time = time.time()
        
        while True:
            if self._is_stopped:
                self._terminate_process()
                return
            
            if self._is_paused:
                time.sleep(1)
                continue
            
            if self.process.poll() is not None:
                break
            
            try:
                line = self.process.stdout.readline()
                if line:
                    self._process_output_line(line.strip())
                    last_progress_time = time.time()
                elif time.time() - last_progress_time > 120:  # 2分钟无输出
                    self.log_signal.emit(self.task_id, "下载超时，正在重试...")
                    self._terminate_process()
                    raise TimeoutError("下载超时")
            except Exception as e:
                self.log_signal.emit(self.task_id, f"监控进度时出错: {str(e)}")
                break
            
            time.sleep(0.1)
    
    def _process_output_line(self, line):
        """处理输出行"""
        if "[download]" in line:
            # 解析下载进度
            progress_info = self._parse_progress(line)
            if progress_info:
                progress, speed = progress_info
                self.progress_signal.emit(self.task_id, progress, speed)
                self.status_signal.emit(self.task_id, f"下载中... {progress}%")
        
        elif "ERROR" in line:
            self.log_signal.emit(self.task_id, f"下载错误: {line}")
        
        elif "WARNING" in line:
            self.log_signal.emit(self.task_id, f"下载警告: {line}")
        
        # 发送详细日志
        self.log_signal.emit(self.task_id, line)
    
    def _parse_progress(self, line):
        """解析下载进度"""
        try:
            # 解析 yt-dlp 的进度输出
            if "%" in line and "ETA" in line:
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        progress = int(float(part.replace("%", "")))
                        # 查找速度信息
                        speed = 0
                        for i, p in enumerate(parts):
                            if "iB/s" in p and i > 0:
                                speed_str = parts[i-1]
                                try:
                                    speed = float(speed_str)
                                    if "KiB/s" in p:
                                        speed = int(speed)
                                    elif "MiB/s" in p:
                                        speed = int(speed * 1024)
                                except:
                                    pass
                                break
                        return progress, speed
        except:
            pass
        return None
    
    def _should_resume(self, output_path):
        """检查是否应该断点续传"""
        if not os.path.exists(output_path):
            return False
        
        # 检查文件大小和修改时间
        file_size = os.path.getsize(output_path)
        if file_size > 0:
            # 检查是否有相应的断点续传信息
            resume_file = output_path + ".resume"
            if os.path.exists(resume_file):
                return True
        
        return False
    
    def _get_output_path(self):
        """获取输出路径"""
        output_dir = self.config.get('paths.output_dir')
        today = time.strftime("%Y%m%d")
        filename = f"{self.anchor_name}_{today}_{self.task_id}.flv"
        return os.path.join(output_dir, filename)
    
    def _check_download_result(self, output_path):
        """检查下载结果"""
        exit_code = self.process.returncode
        
        if exit_code == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            min_size = self.config.get('download.min_file_size_mb', 50) * 1024 * 1024
            
            if file_size >= min_size:
                self.status_signal.emit(self.task_id, "下载完成")
                self.finished_signal.emit(self.task_id, 0, "下载成功")
                
                # 生成缩略图
                self._generate_thumbnail(output_path)
            else:
                self.status_signal.emit(self.task_id, "文件过小")
                self.finished_signal.emit(self.task_id, -1, "文件大小不符合要求")
                os.remove(output_path)
        else:
            self.status_signal.emit(self.task_id, "下载失败")
            self.finished_signal.emit(self.task_id, exit_code, "下载失败")
    
    def _generate_thumbnail(self, video_path):
        """生成视频缩略图"""
        try:
            ffmpeg_path = self.config.get('paths.ffmpeg_path', 'ffmpeg')
            thumbnail_path = video_path.replace('.flv', '.jpg')
            
            command = [
                ffmpeg_path,
                '-i', video_path,
                '-vf', 'thumbnail,scale=320:240',
                '-vframes', '1',
                '-y',
                thumbnail_path
            ]
            
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                self.thumbnail_signal.emit(self.task_id, thumbnail_path)
        except Exception as e:
            self.log_signal.emit(self.task_id, f"生成缩略图失败: {str(e)}")
    
    def _terminate_process(self):
        """终止下载进程"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
    
    def stop(self):
        """停止下载"""
        self._is_stopped = True
        self._terminate_process()
    
    def pause(self):
        """暂停下载"""
        self._is_paused = True
        self.status_signal.emit(self.task_id, "已暂停")
    
    def resume(self):
        """恢复下载"""
        self._is_paused = False
        self.status_signal.emit(self.task_id, "继续下载")
    
    def get_download_info(self):
        """获取下载信息"""
        return {
            'task_id': self.task_id,
            'rtmp_url': self.rtmp_url,
            'anchor_name': self.anchor_name,
            'retry_count': self.retry_count,
            'is_paused': self._is_paused,
            'is_stopped': self._is_stopped
        }
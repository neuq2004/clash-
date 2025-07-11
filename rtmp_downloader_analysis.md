# RTMP Downloader GUI Analysis

## Overview
`rtmp_downloader_gui.py` is a sophisticated PyQt5-based GUI application designed for downloading RTMP (Real-Time Messaging Protocol) streams. The application is specifically configured to work with streams from `rtmp://hlive.whzhiyou.top/record/` and appears to be tailored for Chinese streaming platforms.

## Key Features

### 1. Stream Downloading
- **Primary Function**: Downloads RTMP streams using `yt-dlp` as the backend
- **Target Server**: `rtmp://hlive.whzhiyou.top/record/` 
- **File Format**: Saves streams as `.flv` files
- **Automatic Naming**: Files are named with format: `{anchor_name}_{YYYYMMDD}_{count}.flv`

### 2. Multi-threaded Operations
- **Concurrent Downloads**: Supports multiple simultaneous downloads
- **Thread Management**: Each download runs in its own `DownloadThread`
- **Queue System**: Users can queue multiple downloads for batch processing

### 3. Anchor/Streamer Management
- **Anchor List**: Maintains a list of streamers/anchors in `anchors.txt`
- **Search Functionality**: Search through anchor names
- **Editor Dialog**: Built-in editor for managing the anchor list
- **Dropdown Interface**: Multi-column dropdown for anchor selection

### 4. File Management
- **Size Filtering**: Automatically deletes files smaller than configured minimum size (50MB default)
- **Directory Organization**: Saves files to configured output directory
- **Duplicate Detection**: Prevents duplicate downloads of the same stream

### 5. Notification System
- **Desktop Notifications**: Uses `plyer` for cross-platform notifications
- **Server酱 Integration**: Sends notifications via Server酱 API
- **Sound Alerts**: Plays different sounds for success, warning, and error events
- **Custom Sound Files**: Configurable sound files for different events

### 6. Logging System
- **Daily Log Files**: Creates separate log files for each day
- **Selective Logging**: Only logs download start/end events to files
- **Real-time UI Logs**: Displays detailed progress in the GUI log area

## Architecture

### Main Classes

#### 1. `DownloadThread(QThread)`
- **Purpose**: Handles individual download operations
- **Key Methods**:
  - `run()`: Main download logic using yt-dlp
  - `stop()`: Graceful termination of downloads
  - `process_yt_dlp_output()`: Parses yt-dlp output for progress updates
- **Signals**: 
  - `log_signal`: Emits log messages
  - `status_signal`: Updates task status
  - `finished_signal`: Notifies completion

#### 2. `AnchorEditorDialog(QDialog)`
- **Purpose**: Dialog for managing the anchor/streamer list
- **Features**:
  - Add, edit, delete anchors
  - Reorder anchors
  - Save changes to file
- **Signal**: `anchors_updated` - notifies parent when list changes

#### 3. `RTMPDownloaderApp(QMainWindow)`
- **Purpose**: Main application window
- **Key Components**:
  - RTMP input field
  - Anchor selection dropdown
  - Download queue management
  - Task status display
  - Log area

### Configuration Constants

```python
OUTPUT_DIR = r"D:\RTMP_Downloads"
MIN_FILE_SIZE_MB = 50
SERVER_CHAN_SENDKEY = "sctp8915tireevunye59gauvucheojo"
FFMPEG_PATH = r"F:\Program\ffmpeg-2025-06-08-git-5fea5e3e11-full_build\bin\ffmpeg.exe"
YT_DLP_PATH = r"F:\Program\ffmpeg-2025-06-08-git-5fea5e3e11-full_build\bin\yt-dlp.exe"
```

## Dependencies

### Required Libraries
- **PyQt5**: GUI framework
- **requests**: HTTP requests for notifications
- **plyer**: Cross-platform notifications
- **subprocess**: Running external commands
- **threading**: Multi-threading support
- **unicodedata**: String width calculations
- **winsound**: Windows sound playback

### External Tools
- **yt-dlp**: Primary download tool
- **FFmpeg**: Video processing (optional but recommended)

## User Interface Features

### Main Window Components
1. **RTMP Input Field**: Enter stream variable part
2. **Anchor Selection**: Dropdown with search functionality
3. **Action Buttons**: 
   - Download (immediate)
   - Add to Queue
   - Start Queue Downloads
   - Edit Anchors
   - Refresh Anchor List
4. **Task Display**: Real-time status of all downloads
5. **Log Area**: Detailed operation logs

### Task Management
- **Visual Status**: Each task shows current status
- **Progress Updates**: Real-time progress from yt-dlp
- **Stop/Remove**: Individual task control
- **Queue Management**: Add, remove, and process queued downloads

## Error Handling

### Timeout Management
- **Startup Timeout**: 60 seconds for download initialization
- **Download Timeout**: 120 seconds for progress updates
- **Graceful Termination**: Proper cleanup on timeouts

### Validation
- **RTMP URL Validation**: Checks stream accessibility before download
- **File Existence**: Prevents overwriting existing files
- **Input Validation**: Ensures required fields are filled

### Error Recovery
- **Automatic Cleanup**: Removes failed/empty downloads
- **User Notifications**: Alerts for various error conditions
- **Detailed Logging**: Comprehensive error information

## File Organization

### Generated Files
- **Video Files**: `{anchor_name}_{YYYYMMDD}_{count}.flv`
- **Log Files**: `download_log_{YYYYMMDD}.txt`
- **Anchor List**: `anchors.txt`

### Directory Structure
```
D:\RTMP_Downloads\
├── {anchor_name}_{date}_{count}.flv
├── logs\
│   └── download_log_{date}.txt
└── anchors.txt
```

## Platform Considerations

### Windows-Specific Features
- **Sound Playback**: Uses `winsound` for Windows sound alerts
- **File Paths**: Configured for Windows-style paths
- **Process Creation**: Uses Windows-specific process flags

### Cross-Platform Elements
- **PyQt5**: Cross-platform GUI framework
- **Notifications**: `plyer` provides cross-platform notifications
- **External Tools**: yt-dlp and FFmpeg are cross-platform

## Notable Features

### Chinese Language Support
- **UI Text**: All interface text in Chinese
- **Filename Handling**: Proper support for Chinese characters
- **Character Width**: Calculates display width for Chinese characters

### Advanced UI Elements
- **Dynamic Layouts**: Responsive layout management
- **Multi-column Dropdowns**: Efficient display of large anchor lists
- **Real-time Updates**: Live status updates without blocking UI

### Robust Download Management
- **Duplicate Prevention**: Checks for duplicate streams
- **File Size Validation**: Removes downloads below minimum size
- **Concurrent Operations**: Multiple simultaneous downloads
- **Queue Processing**: Batch processing of multiple downloads

## Potential Use Cases

This application appears designed for:
1. **Content Archival**: Downloading and preserving live streams
2. **Batch Processing**: Managing multiple stream downloads
3. **Streamer Monitoring**: Tracking multiple streamers/anchors
4. **Educational/Research**: Collecting streaming content for analysis

## Summary

`rtmp_downloader_gui.py` is a feature-rich, production-ready application for RTMP stream downloading. It combines a user-friendly GUI with robust download management, comprehensive error handling, and extensive customization options. The application is well-structured with clear separation of concerns between UI, download logic, and file management.
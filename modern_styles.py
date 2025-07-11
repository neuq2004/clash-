class ModernStyles:
    """现代化UI样式"""
    
    @staticmethod
    def get_light_theme():
        """浅色主题"""
        return """
        QMainWindow {
            background-color: #f5f5f5;
            color: #333;
        }
        
        QWidget {
            background-color: #ffffff;
            color: #333;
        }
        
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: bold;
            min-width: 80px;
        }
        
        QPushButton:hover {
            background-color: #1976D2;
        }
        
        QPushButton:pressed {
            background-color: #0D47A1;
        }
        
        QPushButton:disabled {
            background-color: #BDBDBD;
            color: #757575;
        }
        
        QPushButton#dangerButton {
            background-color: #F44336;
        }
        
        QPushButton#dangerButton:hover {
            background-color: #D32F2F;
        }
        
        QPushButton#successButton {
            background-color: #4CAF50;
        }
        
        QPushButton#successButton:hover {
            background-color: #388E3C;
        }
        
        QLineEdit {
            border: 2px solid #E0E0E0;
            border-radius: 4px;
            padding: 8px;
            background-color: white;
            selection-background-color: #2196F3;
        }
        
        QLineEdit:focus {
            border-color: #2196F3;
        }
        
        QTextEdit {
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            background-color: white;
            selection-background-color: #2196F3;
        }
        
        QListWidget {
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            background-color: white;
            alternate-background-color: #f8f9fa;
        }
        
        QListWidget::item {
            padding: 8px;
            border-bottom: 1px solid #EEEEEE;
        }
        
        QListWidget::item:selected {
            background-color: #2196F3;
            color: white;
        }
        
        QListWidget::item:hover {
            background-color: #E3F2FD;
        }
        
        QLabel#titleLabel {
            font-size: 18px;
            font-weight: bold;
            color: #2196F3;
            margin: 10px 0;
        }
        
        QLabel#statusLabel {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        
        QLabel#successStatus {
            background-color: #E8F5E8;
            color: #2E7D32;
        }
        
        QLabel#errorStatus {
            background-color: #FFEBEE;
            color: #C62828;
        }
        
        QLabel#warningStatus {
            background-color: #FFF3E0;
            color: #EF6C00;
        }
        
        QProgressBar {
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            background-color: #F5F5F5;
            text-align: center;
        }
        
        QProgressBar::chunk {
            background-color: #2196F3;
            border-radius: 3px;
        }
        
        QMenuBar {
            background-color: white;
            border-bottom: 1px solid #E0E0E0;
        }
        
        QMenuBar::item {
            padding: 8px 16px;
        }
        
        QMenuBar::item:selected {
            background-color: #E3F2FD;
        }
        
        QMenu {
            background-color: white;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
        }
        
        QMenu::item {
            padding: 8px 16px;
        }
        
        QMenu::item:selected {
            background-color: #2196F3;
            color: white;
        }
        
        QScrollBar:vertical {
            background: #f0f0f0;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background: #c0c0c0;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background: #a0a0a0;
        }
        """
    
    @staticmethod
    def get_dark_theme():
        """深色主题"""
        return """
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        QWidget {
            background-color: #353535;
            color: #ffffff;
        }
        
        QPushButton {
            background-color: #0d7377;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: bold;
            min-width: 80px;
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
            border-radius: 4px;
            padding: 8px;
            background-color: #404040;
            color: white;
            selection-background-color: #0d7377;
        }
        
        QLineEdit:focus {
            border-color: #0d7377;
        }
        
        QTextEdit {
            border: 1px solid #555555;
            border-radius: 4px;
            background-color: #404040;
            color: white;
            selection-background-color: #0d7377;
        }
        
        QListWidget {
            border: 1px solid #555555;
            border-radius: 4px;
            background-color: #404040;
            color: white;
            alternate-background-color: #484848;
        }
        
        QListWidget::item {
            padding: 8px;
            border-bottom: 1px solid #555555;
        }
        
        QListWidget::item:selected {
            background-color: #0d7377;
            color: white;
        }
        
        QListWidget::item:hover {
            background-color: #505050;
        }
        
        QLabel#titleLabel {
            font-size: 18px;
            font-weight: bold;
            color: #14a085;
            margin: 10px 0;
        }
        
        QLabel#statusLabel {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        
        QLabel#successStatus {
            background-color: #155724;
            color: #d4edda;
        }
        
        QLabel#errorStatus {
            background-color: #721c24;
            color: #f8d7da;
        }
        
        QLabel#warningStatus {
            background-color: #856404;
            color: #fff3cd;
        }
        
        QProgressBar {
            border: 1px solid #555555;
            border-radius: 4px;
            background-color: #404040;
            text-align: center;
            color: white;
        }
        
        QProgressBar::chunk {
            background-color: #0d7377;
            border-radius: 3px;
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
    
    @staticmethod
    def get_card_style():
        """卡片样式"""
        return """
        QWidget#taskCard {
            background-color: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            margin: 4px;
        }
        
        QWidget#taskCard:hover {
            border-color: #2196F3;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        """
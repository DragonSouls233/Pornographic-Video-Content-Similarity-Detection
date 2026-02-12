#!/usr/bin/env python3
"""
打包前清理脚本
清理临时文件、缓存和测试相关文件，确保打包环境整洁
"""

import os
import shutil
import glob
from pathlib import Path

def clean_directory():
    """清理项目目录"""
    print("开始清理打包环境...")
    
    # 项目根目录
    root_dir = Path(__file__).parent
    
    # 需要清理的文件和目录
    cleanup_patterns = [
        # Python缓存
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        "**/*.pyd",
        
        # 测试文件
        "*test*.py",
        "test_*.py",
        "*test*.log",
        "test_*.log",
        
        # 临时文件
        "*.tmp",
        "*.temp",
        "~*",
        ".DS_Store",
        "Thumbs.db",
        
        # IDE文件
        ".vscode",
        ".idea",
        "*.swp",
        "*.swo",
        
        # 打包临时文件
        "build",
        "dist",
        "*.spec",
        
        # 其他临时目录
        ".pytest_cache",
        ".mypy_cache",
        ".coverage",
    ]
    
    cleaned_count = 0
    
    for pattern in cleanup_patterns:
        # 使用glob查找匹配的文件和目录
        matches = list(root_dir.glob(pattern))
        
        for match in matches:
            try:
                if match.is_dir():
                    shutil.rmtree(match)
                    print(f"  [目录] 删除: {match.relative_to(root_dir)}")
                else:
                    match.unlink()
                    print(f"  [文件] 删除: {match.relative_to(root_dir)}")
                cleaned_count += 1
            except Exception as e:
                print(f"  [错误] 无法删除 {match}: {e}")
    
    # 特殊清理：清理.log文件（但保留重要的日志）
    log_files = list(root_dir.glob("**/*.log"))
    for log_file in log_files:
        # 保留重要的日志文件
        important_logs = ['app.log', 'error.log', 'debug.log']
        if log_file.name not in important_logs:
            try:
                log_file.unlink()
                print(f"  [日志] 删除: {log_file.relative_to(root_dir)}")
                cleaned_count += 1
            except Exception as e:
                print(f"  [错误] 无法删除日志 {log_file}: {e}")
    
    print(f"[完成] 清理完成！共处理 {cleaned_count} 个文件/目录")
    
    # 检查项目结构
    print("\n项目结构检查:")
    important_files = [
        'gui/gui.py',
        'core/core.py', 
        'config.yaml',
        'requirements.txt',
        'README.md',
        'BATCH_MODEL_MANAGEMENT.md',
        '打包脚本.bat'
    ]
    
    for file_path in important_files:
        full_path = root_dir / file_path
        if full_path.exists():
            print(f"  [存在] {file_path}")
        else:
            print(f"  [缺失] {file_path}")
    
    # 检查新功能模块
    new_modules = [
        'gui/batch_model_processor.py',
        'gui/data_validator.py', 
        'gui/performance_optimizer.py'
    ]
    
    print("\n新功能模块检查:")
    for module_path in new_modules:
        full_path = root_dir / module_path
        if full_path.exists():
            print(f"  [存在] {module_path}")
        else:
            print(f"  [缺失] {module_path}")
    
    return cleaned_count

def check_dependencies():
    """检查关键依赖"""
    print("\n检查依赖包...")
    
    required_packages = [
        'pandas',
        'openpyxl', 
        'xlrd',
        'psutil',
        'PyYAML',
        'beautifulsoup4',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  [存在] {package}")
        except ImportError:
            print(f"  [缺失] {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n[警告] 缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    else:
        print("\n[完成] 所有依赖包检查通过！")
        return True

def main():
    """主函数"""
    print("模特查重管理系统 - 打包前环境检查")
    print("=" * 50)
    
    # 清理目录
    cleaned_count = clean_directory()
    
    # 检查依赖（可选）
    try:
        check_dependencies()
    except Exception as e:
        print(f"[警告] 依赖检查跳过: {e}")
    
    print("\n" + "=" * 50)
    print("[完成] 环境检查完成！可以开始打包了。")
    print(f"[提示] 已清理 {cleaned_count} 个文件/目录")
    print("[操作] 运行 '打包脚本.bat' 开始打包")
    
    return 0

if __name__ == "__main__":
    exit(main())
@echo off
chcp 65001 >nul
echo ========================================
echo 模特查重管理系统 - 打包脚本
echo ========================================
echo.

REM 检查是否安装了 PyInstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [错误] 未安装 PyInstaller
    echo 正在安装 PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败
        pause
        exit /b 1
    )
)

echo [1/5] 清理旧的打包文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del /f /q "*.spec"
echo      完成!
echo.

echo [2/5] 收集项目文件...
REM 创建临时目录结构
echo      - 核心模块
echo      - GUI模块
echo      - 配置文件
echo      完成!
echo.

echo [3/5] 开始打包...
pyinstaller --clean ^
    --onefile ^
    --noconsole ^
    --name "模特查重管理系统" ^
    --noupx ^
    --add-data "core;core" ^
    --add-data "gui;gui" ^
    --add-data "docs;docs" ^
    gui/gui.py ^
    --hidden-import yaml ^
    --hidden-import requests ^
    --hidden-import bs4 ^
    --hidden-import beautifulsoup4 ^
    --hidden-import lxml ^
    --hidden-import selenium ^
    --hidden-import selenium.webdriver ^
    --hidden-import selenium.webdriver.chrome.service ^
    --hidden-import selenium.webdriver.chrome.options ^
    --hidden-import selenium.webdriver.common.by ^
    --hidden-import selenium.webdriver.support.ui ^
    --hidden-import selenium.webdriver.support.expected_conditions ^
    --hidden-import webdriver_manager ^
    --hidden-import webdriver_manager.chrome ^
    --hidden-import yt_dlp ^
    --hidden-import yt_dlp.YoutubeDL ^
    --hidden-import urllib3 ^
    --hidden-import certifi ^
    --hidden-import PySocks ^
    --hidden-import socks ^
    --hidden-import socket ^
    --hidden-import json ^
    --hidden-import os ^
    --hidden-import time ^
    --hidden-import random ^
    --hidden-import re ^
    --hidden-import typing ^
    --hidden-import pathlib ^
    --hidden-import logging ^
    --hidden-import datetime ^
    --hidden-import functools ^
    --hidden-import webbrowser ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import tkinter.messagebox ^
    --hidden-import tkinter.filedialog ^
    --hidden-import threading ^
    --hidden-import queue ^
    --hidden-import colorama ^
    --hidden-import python_dateutil ^
    --hidden-import charset_normalizer ^
    --hidden-import core.modules ^
    --hidden-import core.modules.common ^
    --hidden-import core.modules.porn ^
    --hidden-import core.modules.porn.downloader ^
    --hidden-import core.modules.porn.porn ^
    --hidden-import core.modules.javdb ^
    --hidden-import core.modules.javdb.scraper ^
    --collect-submodules selenium ^
    --collect-submodules webdriver_manager

if errorlevel 1 (
    echo.
    echo [错误] 打包失败!
    pause
    exit /b 1
)
echo      完成!
echo.

echo [4/5] 复制配置文件...
if not exist "dist\config.yaml" (
    if exist "config.yaml" (
        copy "config.yaml" "dist\config.yaml" >nul
        echo      - config.yaml 已复制
    )
)
if not exist "dist\models.json" (
    if exist "models.json" (
        copy "models.json" "dist\models.json" >nul
        echo      - models.json 已复制
    )
)
if not exist "dist\local_dirs.json" (
    if exist "local_dirs.json" (
        copy "local_dirs.json" "dist\local_dirs.json" >nul
        echo      - local_dirs.json 已复制
    )
)
if not exist "dist\README.md" (
    if exist "README.md" (
        copy "README.md" "dist\README.md" >nul
        echo      - README.md 已复制
    )
)
if not exist "dist\requirements.txt" (
    if exist "requirements.txt" (
        copy "requirements.txt" "dist\requirements.txt" >nul
        echo      - requirements.txt 已复制
    )
)
echo      完成!
echo.

echo [5/5] 打包完成!
echo.
echo ========================================
echo 打包文件位置: dist\模特查重管理系统.exe
echo ========================================
echo.
echo 提示:
echo 1. 首次运行会自动下载 ChromeDriver
echo 2. 确保安装了 Chrome 浏览器
echo 3. 配置文件会自动生成
echo 4. PORN模块支持视频下载功能
echo 5. JAVDB模块专注于内容管理，无下载功能
echo 6. 支持porn和JAV分类目录配置
echo.
pause

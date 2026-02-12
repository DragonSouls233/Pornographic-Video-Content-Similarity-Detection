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

echo [重要] 此脚本支持统一配置文件路径和多目录管理模式
echo.

echo [1/5] 清理旧的打包文件和临时测试文件...
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
REM 打包命令 - 支持V1/V3统一下载器
pyinstaller --clean ^
    --onefile ^
    --console ^
    --name "模特查重管理系统" ^
    --noupx ^
    --add-data "core;core" ^
    --add-data "gui;gui" ^
    --add-data "docs;docs" ^
    --exclude-module tests ^
    --exclude-module test_*.py ^
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
    --hidden-import urllib.parse ^
    --hidden-import certifi ^
    --hidden-import PySocks ^
    --hidden-import socks ^
    --hidden-import socket ^
    --hidden-import hashlib ^
    --hidden-import json ^
    --hidden-import aiohttp ^
    --hidden-import aiofiles ^
    --hidden-import asyncio ^
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
    --hidden-import pandas ^
    --hidden-import openpyxl ^
    --hidden-import xlrd ^
    --hidden-import psutil ^
    --hidden-import concurrent.futures ^
    --hidden-import gui.batch_model_processor ^
    --hidden-import gui.data_validator ^
    --hidden-import gui.performance_optimizer ^
    --hidden-import gui.delete_optimizer ^
    --hidden-import core.modules ^
    --hidden-import core.modules.common ^
    --hidden-import core.modules.common.async_downloader ^
    --hidden-import core.modules.common.database_storage ^
    --hidden-import core.modules.common.intelligent_scheduler ^
    --hidden-import core.modules.porn ^
    --hidden-import core.modules.porn.downloader ^
    --hidden-import core.modules.porn.downloader_v3_fixed ^
    --hidden-import core.modules.porn.unified_downloader ^
    --hidden-import core.modules.porn.porn ^
    --hidden-import core.modules.javdb ^
    --hidden-import core.modules.javdb.scraper ^
    --hidden-import core.modules.common.model_database ^
    --hidden-import core.modules.common.db_path_manager ^
    --hidden-import core.modules.common.db_compatibility ^
    --hidden-import sqlite3 ^
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
if not exist "dist\BATCH_MODEL_MANAGEMENT.md" (
    if exist "BATCH_MODEL_MANAGEMENT.md" (
        copy "BATCH_MODEL_MANAGEMENT.md" "dist\BATCH_MODEL_MANAGEMENT.md" >nul
        echo      - BATCH_MODEL_MANAGEMENT.md 已复制
    )
)
echo      完成!
echo.

echo [5/5] 清理临时测试文件...
del /f /q "*测试*.bat" 2>nul
del /f /q "*验证*.bat" 2>nul
del /f /q "*check*.bat" 2>nul
del /f /q "*sync*.bat" 2>nul
echo      打包优化完成!
echo.

echo ========================================
echo ✅ 打包完成! 
echo 可执行文件位置: dist\模特查重管理系统.exe
echo ========================================
pause
echo.
pause

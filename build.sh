#!/bin/bash
# 模特查重管理系统 - Linux/Mac 打包脚本

echo "========================================"
echo "模特查重管理系统 - 打包脚本"
echo "========================================"
echo ""

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
echo "检测到 Python 版本: $python_version"

# 检查是否安装了 PyInstaller
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "[错误] 未安装 PyInstaller"
    echo "正在安装 PyInstaller..."
    pip3 install pyinstaller
    if [ $? -ne 0 ]; then
        echo "[错误] PyInstaller 安装失败"
        exit 1
    fi
fi

echo ""
echo "[1/5] 清理旧的打包文件..."
rm -rf build dist *.spec
echo "     完成!"
echo ""

echo "[2/5] 收集项目文件..."
echo "     - 核心模块"
echo "     - GUI模块"
echo "     - 配置文件"
echo "     完成!"
echo ""

echo "[3/5] 开始打包..."
# 打包命令 - 支持V1/V3统一下载器
pyinstaller --clean \
    --onefile \
    --noconsole \
    --noupx \
    --name "模特查重管理系统" \
    --add-data "core:core" \
    --add-data "gui:gui" \
    --add-data "docs:docs" \
    --exclude-module tests \
    gui/gui.py \
    --hidden-import yaml \
    --hidden-import requests \
    --hidden-import bs4 \
    --hidden-import beautifulsoup4 \
    --hidden-import lxml \
    --hidden-import selenium \
    --hidden-import selenium.webdriver \
    --hidden-import selenium.webdriver.chrome.service \
    --hidden-import selenium.webdriver.chrome.options \
    --hidden-import selenium.webdriver.common.by \
    --hidden-import selenium.webdriver.support.ui \
    --hidden-import selenium.webdriver.support.expected_conditions \
    --hidden-import webdriver_manager \
    --hidden-import webdriver_manager.chrome \
    --hidden-import yt_dlp \
    --hidden-import yt_dlp.YoutubeDL \
    --hidden-import urllib3 \
    --hidden-import urllib.parse \
    --hidden-import certifi \
    --hidden-import PySocks \
    --hidden-import socks \
    --hidden-import socket \
    --hidden-import hashlib \
    --hidden-import json \
    --hidden-import aiohttp \
    --hidden-import aiofiles \
    --hidden-import asyncio \
    --hidden-import os \
    --hidden-import time \
    --hidden-import random \
    --hidden-import re \
    --hidden-import typing \
    --hidden-import pathlib \
    --hidden-import logging \
    --hidden-import datetime \
    --hidden-import functools \
    --hidden-import webbrowser \
    --hidden-import tkinter \
    --hidden-import tkinter.ttk \
    --hidden-import tkinter.messagebox \
    --hidden-import tkinter.filedialog \
    --hidden-import threading \
    --hidden-import queue \
    --hidden-import colorama \
    --hidden-import python_dateutil \
    --hidden-import charset_normalizer \
    --hidden-import core.modules \
    --hidden-import core.modules.common \
    --hidden-import core.modules.common.async_downloader \
    --hidden-import core.modules.common.database_storage \
    --hidden-import core.modules.common.intelligent_scheduler \
    --hidden-import core.modules.porn \
    --hidden-import core.modules.porn.downloader \
    --hidden-import core.modules.porn.downloader_v3_fixed \
    --hidden-import core.modules.porn.unified_downloader \
    --hidden-import core.modules.porn.porn \
    --hidden-import core.modules.javdb \
    --hidden-import core.modules.javdb.scraper \
    --collect-submodules selenium \
    --collect-submodules webdriver_manager

if [ $? -ne 0 ]; then
    echo ""
    echo "[错误] 打包失败!"
    exit 1
fi
echo "     完成!"
echo ""

echo "[4/5] 复制配置文件..."
if [ ! -f "dist/config.yaml" ] && [ -f "config.yaml" ]; then
    cp config.yaml dist/config.yaml
    echo "     - config.yaml 已复制"
fi
if [ ! -f "dist/models.json" ] && [ -f "models.json" ]; then
    cp models.json dist/models.json
    echo "     - models.json 已复制"
fi
if [ ! -f "dist/local_dirs.json" ] && [ -f "local_dirs.json" ]; then
    cp local_dirs.json dist/local_dirs.json
    echo "     - local_dirs.json 已复制"
fi
if [ ! -f "dist/README.md" ] && [ -f "README.md" ]; then
    cp README.md dist/README.md
    echo "     - README.md 已复制"
fi
if [ ! -f "dist/requirements.txt" ] && [ -f "requirements.txt" ]; then
    cp requirements.txt dist/requirements.txt
    echo "     - requirements.txt 已复制"
fi
echo "     完成!"
echo ""

echo "[5/5] 打包完成!"
echo ""
echo "========================================"
echo "打包文件位置: dist/模特查重管理系统"
echo "========================================"
echo ""
echo "提示:"
echo "1. 首次运行会自动下载 ChromeDriver"
echo "2. 确保安装了 Chrome 浏览器"
echo "3. 配置文件会自动生成"
echo "4. PORN模块支持视频下载功能 (支V1-Standard和V3-Advanced两个版本)"
echo "5. JAVDB模块专注于内容管理，无下载功能"
echo "6. 支持porn和JAV分类目录配置"
echo ""

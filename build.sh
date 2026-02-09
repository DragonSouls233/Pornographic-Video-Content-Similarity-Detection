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
pyinstaller --clean \
    --onefile \
    --windowed \
    --name "模特查重管理系统" \
    --add-data "core:core" \
    --add-data "gui:gui" \
    --hidden-import yaml \
    --hidden-import requests \
    --hidden-import bs4 \
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
    --hidden-import urllib3 \
    --hidden-import certifi \
    --hidden-import PySocks \
    --hidden-import socks \
    --hidden-import json \
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
    --collect-all selenium \
    --collect-all webdriver_manager \
    gui/gui.py

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
echo ""

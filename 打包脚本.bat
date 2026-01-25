@echo off
chcp 65001 >nul

REM 极简打包脚本 - 直接在当前目录运行打包命令

REM 使用PyInstaller打包
pyinstaller --onefile --windowed --name "模特查重管理系统" --add-data "core;core" --hidden-import yaml --hidden-import requests --hidden-import bs4 --hidden-import bz2 --hidden-import urllib.parse --hidden-import importlib.util gui/gui.py

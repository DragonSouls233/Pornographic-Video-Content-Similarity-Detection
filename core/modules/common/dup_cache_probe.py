# -*- coding: utf-8 -*-
"""
远端轻量探测 + 本地快照签名
"""

import os
import time
import hashlib
from typing import List, Tuple, Dict, Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def compute_local_signature_from_files(folder: str, titles: List[str]) -> str:
    """基于文件数量 + 最近修改时间 + 标题集合生成本地签名"""
    latest_mtime = 0.0
    file_count = 0

    folders = [folder]
    if folder and not os.path.exists(folder) and ';' in folder:
        folders = [p.strip() for p in folder.split(';') if p.strip()]

    for path in folders:
        if os.path.exists(path):
            for root, _, files in os.walk(path):
                for f in files:
                    file_count += 1
                    try:
                        m = os.path.getmtime(os.path.join(root, f))
                        if m > latest_mtime:
                            latest_mtime = m
                    except Exception:
                        pass

    titles_sorted = sorted(titles)
    payload = f"{file_count}|{latest_mtime}|" + "|".join(titles_sorted)
    return hashlib.sha1(payload.encode('utf-8')).hexdigest()



def compute_remote_signature_from_titles(titles: List[str]) -> str:
    titles_sorted = sorted(titles)
    payload = "|".join(titles_sorted)
    return hashlib.sha1(payload.encode('utf-8')).hexdigest()


def probe_remote_signature(url: str, headers: Optional[Dict[str, str]] = None, proxies: Optional[Dict[str, str]] = None) -> Tuple[str, List[str]]:
    """轻量探测远端：抓取首页标题并生成签名"""
    headers = headers or {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    resp = requests.get(url, headers=headers, timeout=15, proxies=proxies, verify=False)
    resp.raise_for_status()
    if resp.encoding.lower() != 'utf-8':
        resp.encoding = 'utf-8'

    soup = BeautifulSoup(resp.text, 'html.parser')
    titles = []
    for elem in soup.select('a.thumbnailTitle, a.title, .video-title, h3.title'):
        t = elem.get_text(strip=True)
        if t and len(t) > 3:
            titles.append(t)

    signature = compute_remote_signature_from_titles(titles)
    return signature, titles


def check_url_available(url: str, headers: Optional[Dict[str, str]] = None, proxies: Optional[Dict[str, str]] = None, timeout: int = 8) -> bool:
    """校验链接是否可用（优先HEAD，失败后尝试GET）"""
    if not url or not isinstance(url, str):
        return False
    headers = headers or {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        resp = requests.head(url, headers=headers, timeout=timeout, proxies=proxies, allow_redirects=True, verify=False)
        if resp.status_code < 400:
            return True
        if resp.status_code in (403, 405):
            resp = requests.get(url, headers=headers, timeout=timeout, proxies=proxies, allow_redirects=True, verify=False)
            return resp.status_code < 400
        return False
    except Exception:
        return False


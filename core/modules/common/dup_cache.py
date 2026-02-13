# -*- coding: utf-8 -*-
"""
查重缓存模块（SQLite）
记录远端/本地快照签名与对比结果，支持快速判定是否补齐
"""

import os
import json
import sqlite3
import hashlib
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class DupCacheEntry:
    cache_key: str
    model_name: str
    module: str
    url: str
    remote_signature: str = ""
    remote_signature_full: str = ""
    local_signature: str = ""
    online_count: int = 0
    local_count: int = 0
    missing_titles: List[str] = None
    missing_with_urls: List[Tuple[str, str]] = None
    invalid_titles: List[str] = None
    local_changed: int = 0
    remote_changed: int = 0
    checked_at: Optional[str] = None
    created_at: Optional[str] = None
    cache_version: str = "v1"



class DupCacheStore:
    def __init__(self, db_path: str = "output/dup_cache.db"):
        self.db_path = db_path
        dir_path = os.path.dirname(db_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS dup_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT UNIQUE,
                    model_name TEXT,
                    module TEXT,
                    url TEXT,
                    remote_signature TEXT,
                    remote_signature_full TEXT,
                    local_signature TEXT,
                    online_count INTEGER,
                    local_count INTEGER,
                    missing_titles_json TEXT,
                    missing_with_urls_json TEXT,
                    invalid_titles_json TEXT,
                    local_changed INTEGER DEFAULT 0,
                    remote_changed INTEGER DEFAULT 0,
                    checked_at TIMESTAMP,
                    created_at TIMESTAMP,
                    cache_version TEXT
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_dup_cache_key ON dup_cache(cache_key)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_dup_cache_model ON dup_cache(model_name)')
            conn.commit()
            self._ensure_columns(conn)
            conn.close()
        except sqlite3.DatabaseError:
            self._recover_db()
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS dup_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT UNIQUE,
                    model_name TEXT,
                    module TEXT,
                    url TEXT,
                    remote_signature TEXT,
                    remote_signature_full TEXT,
                    local_signature TEXT,
                    online_count INTEGER,
                    local_count INTEGER,
                    missing_titles_json TEXT,
                    missing_with_urls_json TEXT,
                    invalid_titles_json TEXT,
                    local_changed INTEGER DEFAULT 0,
                    remote_changed INTEGER DEFAULT 0,
                    checked_at TIMESTAMP,
                    created_at TIMESTAMP,
                    cache_version TEXT
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_dup_cache_key ON dup_cache(cache_key)')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_dup_cache_model ON dup_cache(model_name)')
            conn.commit()
            self._ensure_columns(conn)
            conn.close()

    def _ensure_columns(self, conn: sqlite3.Connection):
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(dup_cache)")
        existing = {row[1] for row in cur.fetchall()}
        columns = {
            "remote_signature_full": "TEXT",
            "local_changed": "INTEGER DEFAULT 0",
            "remote_changed": "INTEGER DEFAULT 0"
        }
        for col, ddl in columns.items():
            if col not in existing:
                cur.execute(f"ALTER TABLE dup_cache ADD COLUMN {col} {ddl}")
        conn.commit()

    def _recover_db(self):
        if not os.path.exists(self.db_path):
            return
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.corrupted.{ts}.bak"
            os.rename(self.db_path, backup_path)
            logger.warning(f"缓存数据库损坏，已自动重建并备份: {backup_path}")
        except Exception as e:
            logger.warning(f"缓存数据库重建失败: {e}")


    @staticmethod
    def build_cache_key(model_name: str, module: str, url: str) -> str:
        raw = f"{model_name.strip().lower()}|{module.strip().upper()}|{url.strip().lower()}"
        return hashlib.sha1(raw.encode('utf-8')).hexdigest()

    def get(self, cache_key: str) -> Optional[DupCacheEntry]:
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('''
                SELECT cache_key, model_name, module, url, remote_signature, remote_signature_full,
                       local_signature, online_count, local_count, missing_titles_json,
                       missing_with_urls_json, invalid_titles_json, local_changed, remote_changed,
                       checked_at, created_at, cache_version
                FROM dup_cache WHERE cache_key = ?
            ''', (cache_key,))
            row = cur.fetchone()
            conn.close()
            if not row:
                return None
            return DupCacheEntry(
                cache_key=row[0],
                model_name=row[1],
                module=row[2],
                url=row[3],
                remote_signature=row[4] or "",
                remote_signature_full=row[5] or "",
                local_signature=row[6] or "",
                online_count=row[7] or 0,
                local_count=row[8] or 0,
                missing_titles=json.loads(row[9]) if row[9] else [],
                missing_with_urls=json.loads(row[10]) if row[10] else [],
                invalid_titles=json.loads(row[11]) if row[11] else [],
                local_changed=row[12] or 0,
                remote_changed=row[13] or 0,
                checked_at=row[14],
                created_at=row[15],
                cache_version=row[16] or "v1"
            )
        except sqlite3.DatabaseError as e:
            logger.warning(f"读取缓存失败，尝试重建: {e}")
            self._recover_db()
            self._init_db()
            return None
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
            return None


    def upsert(self, entry: DupCacheEntry):
        now = datetime.now().isoformat()
        if not entry.created_at:
            entry.created_at = now
        entry.checked_at = now

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO dup_cache (
                    cache_key, model_name, module, url, remote_signature, remote_signature_full,
                    local_signature, online_count, local_count, missing_titles_json,
                    missing_with_urls_json, invalid_titles_json, local_changed, remote_changed,
                    checked_at, created_at, cache_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    remote_signature=excluded.remote_signature,
                    remote_signature_full=excluded.remote_signature_full,
                    local_signature=excluded.local_signature,
                    online_count=excluded.online_count,
                    local_count=excluded.local_count,
                    missing_titles_json=excluded.missing_titles_json,
                    missing_with_urls_json=excluded.missing_with_urls_json,
                    invalid_titles_json=excluded.invalid_titles_json,
                    local_changed=excluded.local_changed,
                    remote_changed=excluded.remote_changed,
                    checked_at=excluded.checked_at,
                    cache_version=excluded.cache_version
            ''', (
                entry.cache_key,
                entry.model_name,
                entry.module,
                entry.url,
                entry.remote_signature,
                entry.remote_signature_full,
                entry.local_signature,
                entry.online_count,
                entry.local_count,
                json.dumps(entry.missing_titles or [], ensure_ascii=False),
                json.dumps(entry.missing_with_urls or [], ensure_ascii=False),
                json.dumps(entry.invalid_titles or [], ensure_ascii=False),
                entry.local_changed,
                entry.remote_changed,
                entry.checked_at,
                entry.created_at,
                entry.cache_version
            ))
            conn.commit()
            conn.close()
        except sqlite3.DatabaseError as e:
            logger.warning(f"写入缓存失败，尝试重建: {e}")
            self._recover_db()
            self._init_db()
        except Exception as e:
            logger.warning(f"写入缓存失败: {e}")


    def clear(self, model_name: Optional[str] = None):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        if model_name:
            cur.execute('DELETE FROM dup_cache WHERE model_name = ?', (model_name,))
        else:
            cur.execute('DELETE FROM dup_cache')
        conn.commit()
        conn.close()


# 辅助方法

def compute_local_signature(titles: List[str], file_count: int, latest_mtime: float) -> str:
    titles_sorted = sorted(titles)
    payload = f"{file_count}|{latest_mtime}|" + "|".join(titles_sorted)
    return hashlib.sha1(payload.encode('utf-8')).hexdigest()


def compute_remote_signature(titles: List[str], online_count: int) -> str:
    titles_sorted = sorted(titles)
    payload = f"{online_count}|" + "|".join(titles_sorted)
    return hashlib.sha1(payload.encode('utf-8')).hexdigest()

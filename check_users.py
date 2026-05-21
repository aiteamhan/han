#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import os

# 连接数据库
db_path = 'backend/instance/wechat.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 查询所有用户
    cursor.execute('SELECT id, username, password_hash, nickname, created_at, online FROM users')
    users = cursor.fetchall()

    print('\n=== 数据库中的所有用户 ===')
    print(f'总用户数: {len(users)}\n')

    for i, user in enumerate(users, 1):
        print(f'{i}. 用户名: {user["username"]}')
        print(f'   ID: {user["id"]}')
        # 显示密码哈希的前20个字符和后10个字符
        pwd_hash = user["password_hash"]
        pwd_display = f"{pwd_hash[:20]}...{pwd_hash[-10:]}" if len(pwd_hash) > 30 else pwd_hash
        print(f'   密码Hash: {pwd_display}')
        print(f'   昵称: {user["nickname"] if user["nickname"] else "(未设置)"}')
        print(f'   创建时间: {user["created_at"]}')
        print(f'   在线状态: {"在线" if user["online"] else "离线"}')
        print()

    conn.close()
else:
    print(f'数据库文件不存在: {db_path}')

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json

BASE_URL = 'http://localhost:5000'

# 首先登入用户"han"
print("1. 登入用户 'han'...")
login_response = requests.post(f'{BASE_URL}/api/auth/login', json={
    'username': 'han',
    'password': 'han123'
})
print(f"   状态: {login_response.status_code}")

if login_response.status_code == 200:
    token = login_response.json()['data']['token']
    print(f"   令牌: {token[:20]}...")
    
    # 现在添加 'testuser' 为联系人
    print("\n2. 添加 'testuser' 为联系人...")
    
    # 首先搜索用户
    search_response = requests.get(f'{BASE_URL}/api/users/search?q=testuser', headers={
        'Authorization': f'Bearer {token}'
    })
    print(f"   搜索状态: {search_response.status_code}")
    
    if search_response.status_code == 200:
        users = search_response.json()['data']
        print(f"   找到 {len(users)} 个用户")
        if users:
            testuser_id = users[0]['id']
            print(f"   testuser ID: {testuser_id}")
            
            # 添加联系人
            print("\n3. 发送 POST /api/contacts 请求...")
            contact_response = requests.post(f'{BASE_URL}/api/contacts', 
                headers={'Authorization': f'Bearer {token}'},
                json={'user_id': testuser_id}
            )
            print(f"   状态: {contact_response.status_code}")
            print(f"   响应: {json.dumps(contact_response.json(), indent=2, ensure_ascii=False)}")
else:
    print(f"   登入失败: {login_response.json()}")

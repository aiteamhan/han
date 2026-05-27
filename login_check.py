#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
登入检查脚本 - 完整验证登入流程
"""

import requests
import json
import sys
import sqlite3
import os
from datetime import datetime

BASE_URL = 'http://localhost:5000'
DB_PATH = 'backend/instance/wechat.db'

class LoginChecker:
    def __init__(self):
        self.results = {
            '后端连接': None,
            '数据库状态': None,
            '用户列表': None,
            '用户注册': None,
            '用户登入': None,
            'JWT令牌': None,
            '认证验证': None,
        }
        # 生成短用户名 (最多20个字符)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.test_username = f'test_{timestamp[-8:]}'  # 使用最后8位时间戳
        self.test_password = 'test123456'
        self.token = None
        
    def check_backend(self):
        """检查后端连接"""
        print("\n" + "="*50)
        print("1️⃣  检查后端连接")
        print("="*50)
        try:
            response = requests.get(f'{BASE_URL}/health', timeout=5)
            if response.status_code == 200:
                print("✅ 后端服务器正常运行")
                self.results['后端连接'] = '✅ 成功'
                return True
            else:
                print(f"❌ 后端返回异常状态码: {response.status_code}")
                self.results['后端连接'] = f'❌ 状态码 {response.status_code}'
                return False
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接到后端服务器 (http://localhost:5000)")
            print("   请确保后端服务器已启动")
            self.results['后端连接'] = '❌ 连接失败'
            return False
        except Exception as e:
            print(f"❌ 连接错误: {e}")
            self.results['后端连接'] = f'❌ {str(e)}'
            return False

    def check_database(self):
        """检查数据库状态"""
        print("\n" + "="*50)
        print("2️⃣  检查数据库状态")
        print("="*50)
        
        if not os.path.exists(DB_PATH):
            print(f"❌ 数据库文件不存在: {DB_PATH}")
            self.results['数据库状态'] = '❌ 数据库不存在'
            return False
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # 检查users表
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"✅ 数据库可访问")
            print(f"   📊 数据库中已有 {user_count} 个用户")
            
            # 查询所有用户
            cursor.execute("SELECT username FROM users")
            users = cursor.fetchall()
            if users:
                print(f"   📝 用户列表: {', '.join([u[0] for u in users])}")
            
            conn.close()
            self.results['数据库状态'] = f'✅ 正常 ({user_count} 个用户)'
            self.results['用户列表'] = ', '.join([u[0] for u in users]) if users else '(空)'
            return True
        except Exception as e:
            print(f"❌ 数据库错误: {e}")
            self.results['数据库状态'] = f'❌ {str(e)}'
            return False

    def test_register(self):
        """测试用户注册"""
        print("\n" + "="*50)
        print("3️⃣  测试用户注册")
        print("="*50)
        
        print(f"📝 尝试注册用户: {self.test_username}")
        print(f"   密码: {self.test_password}")
        
        try:
            response = requests.post(
                f'{BASE_URL}/api/auth/register',
                json={
                    'username': self.test_username,
                    'password': self.test_password
                },
                timeout=5
            )
            
            print(f"   📊 HTTP状态码: {response.status_code}")
            data = response.json()
            print(f"   📄 响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if response.status_code == 201 and data.get('code') == 0:
                print("✅ 注册成功")
                self.results['用户注册'] = '✅ 成功'
                return True
            else:
                print(f"❌ 注册失败")
                self.results['用户注册'] = f'❌ {data.get("message", "未知错误")}'
                return False
        except Exception as e:
            print(f"❌ 注册请求错误: {e}")
            self.results['用户注册'] = f'❌ {str(e)}'
            return False

    def test_login(self):
        """测试用户登入"""
        print("\n" + "="*50)
        print("4️⃣  测试用户登入")
        print("="*50)
        
        print(f"🔐 尝试登入用户: {self.test_username}")
        
        try:
            response = requests.post(
                f'{BASE_URL}/api/auth/login',
                json={
                    'username': self.test_username,
                    'password': self.test_password
                },
                timeout=5
            )
            
            print(f"   📊 HTTP状态码: {response.status_code}")
            data = response.json()
            print(f"   📄 响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if response.status_code == 200 and data.get('code') == 0:
                print("✅ 登入成功")
                
                # 提取令牌
                if 'data' in data and 'token' in data['data']:
                    self.token = data['data']['token']
                    print(f"   🔑 JWT令牌: {self.token[:30]}...{self.token[-10:]}")
                    
                    # 提取用户信息
                    user = data['data'].get('user', {})
                    print(f"   👤 用户ID: {user.get('id')}")
                    print(f"   👤 用户名: {user.get('username')}")
                    
                    self.results['用户登入'] = '✅ 成功'
                    self.results['JWT令牌'] = f"✅ 已获取 ({len(self.token)} 字符)"
                    return True
                else:
                    print("❌ 登入响应中缺少令牌")
                    self.results['用户登入'] = '❌ 缺少令牌'
                    return False
            else:
                print(f"❌ 登入失败")
                self.results['用户登入'] = f'❌ {data.get("message", "未知错误")}'
                return False
        except Exception as e:
            print(f"❌ 登入请求错误: {e}")
            self.results['用户登入'] = f'❌ {str(e)}'
            return False

    def test_authenticated_request(self):
        """测试认证请求"""
        print("\n" + "="*50)
        print("5️⃣  测试认证验证")
        print("="*50)
        
        if not self.token:
            print("❌ 没有可用的JWT令牌")
            self.results['认证验证'] = '❌ 缺少令牌'
            return False
        
        print(f"🔑 使用令牌: {self.token[:30]}...")
        
        try:
            response = requests.get(
                f'{BASE_URL}/api/users/me',
                headers={
                    'Authorization': f'Bearer {self.token}'
                },
                timeout=5
            )
            
            print(f"   📊 HTTP状态码: {response.status_code}")
            data = response.json()
            print(f"   📄 响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if response.status_code == 200 and data.get('code') == 0:
                print("✅ 认证验证成功 - JWT令牌有效")
                user = data.get('data', {})
                print(f"   👤 返回的用户: {user.get('username')}")
                self.results['认证验证'] = '✅ 成功 (令牌有效)'
                return True
            else:
                print(f"❌ 认证验证失败")
                self.results['认证验证'] = f'❌ {data.get("message", "未知错误")}'
                return False
        except Exception as e:
            print(f"❌ 认证请求错误: {e}")
            self.results['认证验证'] = f'❌ {str(e)}'
            return False

    def print_summary(self):
        """打印总结报告"""
        print("\n\n" + "="*50)
        print("📋 登入检查总结报告")
        print("="*50)
        
        for check_name, result in self.results.items():
            status = "✅" if result and "✅" in result else "❌"
            print(f"{status} {check_name}: {result}")
        
        # 统计结果
        passed = sum(1 for r in self.results.values() if r and "✅" in r)
        total = len(self.results)
        
        print("\n" + "="*50)
        print(f"📊 总体结果: {passed}/{total} 项通过")
        print("="*50)
        
        if passed == total:
            print("🎉 所有检查都已通过 - 登入系统正常!")
        elif passed >= total * 0.7:
            print("⚠️  大部分检查通过，但有一些问题需要解决")
        else:
            print("❌ 登入系统存在严重问题")

    def run_all_checks(self):
        """运行所有检查"""
        print("\n🚀 开始登入系统检查...")
        
        if not self.check_backend():
            print("\n❌ 后端未运行，无法继续检查")
            self.print_summary()
            return
        
        self.check_database()
        
        if self.test_register():
            self.test_login()
            if self.token:
                self.test_authenticated_request()
        
        self.print_summary()


if __name__ == '__main__':
    checker = LoginChecker()
    checker.run_all_checks()

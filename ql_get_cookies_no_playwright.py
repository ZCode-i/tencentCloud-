#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Author: 腾讯云秒杀工具 - 无Playwright版
# @Date: 2026-04-22
# @Description: 手动获取Cookie，避免Playwright依赖

"""
青龙面板友好版 - 不需要安装Playwright

使用方法：
1. 在本地浏览器手动登录腾讯云
2. 复制Cookie和CSRF Token
3. 在青龙面板中配置环境变量
4. 脚本自动生成cookies.json文件

优点：
- 无需安装Playwright
- 无需浏览器环境
- 青龙面板直接可用
"""

import os
import sys
import json
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('cookies_manual.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def get_env(name, default=None):
    """获取环境变量"""
    value = os.environ.get(name)
    if value is None or value.strip() == '':
        return default
    return value.strip()

def create_cookie_from_env():
    """从环境变量创建Cookie文件"""
    
    logger.info("=" * 60)
    logger.info("腾讯云Cookie手动配置工具")
    logger.info("=" * 60)
    
    # 从环境变量读取配置
    cookie_str = get_env("TENCENT_COOKIE_RAW", "")
    csrf_token = get_env("TENCENT_CSRF_TOKEN", "")
    
    if not cookie_str and not csrf_token:
        logger.error("❌ 未找到Cookie配置")
        logger.info("\n请按以下步骤操作：")
        logger.info("1. 在浏览器中登录腾讯云")
        logger.info("2. 按F12打开开发者工具")
        logger.info("3. 切换到Console控制台")
        logger.info("4. 输入: document.cookie")
        logger.info("5. 复制输出的Cookie字符串")
        logger.info("6. 设置为环境变量 TENCENT_COOKIE_RAW")
        logger.info("7. 同时设置 TENCENT_CSRF_TOKEN")
        return False
    
    # 解析Cookie字符串
    cookies = []
    
    # 添加CSRF Token作为Cookie
    if csrf_token:
        csrf_cookie = {
            "name": "x-csrf-token",
            "value": csrf_token,
            "domain": ".cloud.tencent.com",
            "path": "/",
            "expires": -1,
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax"
        }
        cookies.append(csrf_cookie)
        logger.info(f"✅ 添加CSRF Token Cookie")
    
    # 解析原始Cookie字符串（如果有）
    if cookie_str:
        try:
            # 简单的Cookie解析
            cookie_parts = cookie_str.split("; ")
            for part in cookie_parts:
                if "=" in part:
                    name, value = part.split("=", 1)
                    cookie_obj = {
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": ".cloud.tencent.com",
                        "path": "/",
                        "expires": -1,
                        "httpOnly": "HttpOnly" in cookie_str,
                        "secure": "Secure" in cookie_str,
                        "sameSite": "Lax"
                    }
                    cookies.append(cookie_obj)
                    logger.info(f"✅ 添加Cookie: {name}")
        except Exception as e:
            logger.warning(f"解析原始Cookie失败: {str(e)}")
    
    if not cookies:
        logger.error("❌ 未成功创建任何Cookie")
        return False
    
    # 保存到文件
    cookie_file = "cookies.json"
    try:
        with open(cookie_file, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Cookie文件已生成: {cookie_file}")
        logger.info(f"📊 共 {len(cookies)} 个Cookie")
        
        # 显示关键信息
        for cookie in cookies:
            if cookie["name"] == "x-csrf-token":
                logger.info(f"🔑 CSRF Token: {cookie['value'][:20]}...")
            elif "session" in cookie["name"].lower():
                logger.info(f"🔐 Session Cookie: {cookie['name']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 保存Cookie文件失败: {str(e)}")
        return False

def manual_guide():
    """显示手动获取指南"""
    logger.info("\n" + "=" * 60)
    logger.info("手动获取Cookie指南")
    logger.info("=" * 60)
    
    logger.info("\n📝 方法一：从浏览器控制台获取（推荐）")
    logger.info("1. 登录腾讯云: https://cloud.tencent.com")
    logger.info("2. 按F12 → Console标签")
    logger.info("3. 输入: document.cookie")
    logger.info("4. 复制全部输出内容")
    logger.info("5. 设置为 TENCENT_COOKIE_RAW 环境变量")
    
    logger.info("\n🔑 获取CSRF Token：")
    logger.info("1. 按F12 → Network标签")
    logger.info("2. 刷新页面")
    logger.info("3. 点击任意 cloud.tencent.com 请求")
    logger.info("4. 查看 Headers → Request Headers")
    logger.info("5. 找到 x-csrf-token 的值")
    logger.info("6. 设置为 TENCENT_CSRF_TOKEN 环境变量")
    
    logger.info("\n⚙️ 青龙面板环境变量配置示例：")
    logger.info("TENCENT_COOKIE_RAW=\"_ga=GA1.2.1234567890.1234567890; _gid=GA1.2.9876543210.1234567890; ...\"")
    logger.info("TENCENT_CSRF_TOKEN=\"427372853\"")
    
    logger.info("\n🔄 更新时机：")
    logger.info("• Cookie过期时（通常几天到几周）")
    logger.info("• 每次重要抢购前")
    logger.info("• 更换登录设备后")
    
    logger.info("\n✅ 验证方法：")
    logger.info("1. 配置好环境变量")
    logger.info("2. 运行本脚本生成 cookies.json")
    logger.info("3. 运行秒杀脚本测试")

def main():
    """主函数"""
    
    # 检查是否显示指南
    if len(sys.argv) > 1 and sys.argv[1] == "guide":
        manual_guide()
        return
    
    logger.info("🚀 开始生成Cookie文件...")
    
    # 尝试从环境变量创建
    success = create_cookie_from_env()
    
    if success:
        logger.info("\n" + "=" * 60)
        logger.info("✅ Cookie生成成功！")
        logger.info("=" * 60)
        logger.info("\n下一步操作：")
        logger.info("1. 确保秒杀脚本中引用了正确的Cookie文件")
        logger.info("2. 配置其他环境变量（秒杀时间、地域等）")
        logger.info("3. 测试运行秒杀脚本")
        logger.info("4. 创建定时任务")
    else:
        logger.info("\n" + "=" * 60)
        logger.info("❌ Cookie生成失败")
        logger.info("=" * 60)
        logger.info("\n请运行以下命令查看详细指南：")
        logger.info("python3 ql_get_cookies_no_playwright.py guide")
        
        # 显示简要指南
        manual_guide()

if __name__ == "__main__":
    main()
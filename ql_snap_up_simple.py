#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Author: 腾讯云秒杀工具 - 简化版
# @Date: 2026-04-22
# @Description: 青龙面板友好版，无需Cookie文件，无需Playwright

"""
简化版特点：
1. ✅ 无需Playwright依赖
2. ✅ 无需Cookie文件
3. ✅ 所有配置通过环境变量
4. ✅ 只需要 requests 库
5. ✅ 青龙面板直接可用

环境变量配置：
TENCENT_SECKILL_TIME="2026-04-22 15:00:00"
TENCENT_REGION_IDS="1,4,8"
TENCENT_CSRF_TOKEN="你的CSRF_TOKEN"
TENCENT_COOKIE_STRING="你的完整Cookie字符串"
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# =================== 配置读取 =================== #

def get_env(name, default=None):
    """获取环境变量"""
    value = os.environ.get(name)
    if value is None or value.strip() == '':
        return default
    return value.strip()

# 必需配置
SECKILL_TIME_STR = get_env("TENCENT_SECKILL_TIME")
CSRF_TOKEN = get_env("TENCENT_CSRF_TOKEN")
COOKIE_STRING = get_env("TENCENT_COOKIE_STRING")

# 可选配置
REGION_IDS_STR = get_env("TENCENT_REGION_IDS", "1,4,8")
region_ids = [int(x.strip()) for x in REGION_IDS_STR.split(",") if x.strip()]
ACTIVITY_ID = int(get_env("TENCENT_ACTIVITY_ID", "162634773874417"))
ACT_ID = int(get_env("TENCENT_ACT_ID", "1784747698901873"))

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('snap_up_simple.log', encoding='utf-8', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# =================== 初始化检查 =================== #

def check_config():
    """检查必需配置"""
    errors = []
    
    if not SECKILL_TIME_STR:
        errors.append("❌ 缺少 TENCENT_SECKILL_TIME 环境变量")
    
    if not CSRF_TOKEN:
        errors.append("❌ 缺少 TENCENT_CSRF_TOKEN 环境变量")
    
    if not COOKIE_STRING:
        errors.append("❌ 缺少 TENCENT_COOKIE_STRING 环境变量")
        logger.info("💡 获取Cookie字符串方法：")
        logger.info("1. 登录腾讯云后按F12")
        logger.info("2. 切换到Console控制台")
        logger.info("3. 输入: document.cookie")
        logger.info("4. 复制全部输出内容")
    
    if errors:
        for error in errors:
            logger.error(error)
        return False
    
    return True

def create_session():
    """创建带Cookie的Session"""
    session = requests.Session()
    
    # 设置CSRF Token到Header
    headers = {
        "x-csrf-token": CSRF_TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "referer": "https://cloud.tencent.com/act/pro/featured-202604?fromSource=gwzcw.10216579.10216579.10216579&utm_medium=cpc&utm_id=gwzcw.10216579.10216579.10216579&msclkid=6b370ba9f89c1d21e93a6225d46c8044&page=spring2026&s_source=https%3A%2F%2Fcloud.tencent.com%2Fact%2Fpro%2Fdouble12-2025"
    }
    
    # 设置Cookie
    if COOKIE_STRING:
        # 将Cookie字符串转换为字典
        cookies = {}
        for cookie in COOKIE_STRING.split("; "):
            if "=" in cookie:
                key, value = cookie.split("=", 1)
                cookies[key.strip()] = value.strip()
        
        # 添加到Session
        session.cookies.update(cookies)
        logger.info(f"✅ 已设置 {len(cookies)} 个Cookie")
    
    session.headers.update(headers)
    return session

# =================== 功能函数 =================== #

def get_server_time():
    """获取服务器时间"""
    try:
        url = "https://cloud.tencent.com/act/pro/double12-2025"
        response = requests.head(url, timeout=10)
        server_time = response.headers.get("Date")
        
        if server_time:
            dt = datetime.strptime(server_time, "%a, %d %b %Y %H:%M:%S GMT")
            beijing_time = dt + timedelta(hours=8)
            timestamp_ms = int(beijing_time.timestamp() * 1000)
            logger.info(f"服务器时间: {beijing_time}")
            return timestamp_ms
        else:
            return int(time.time() * 1000)
    except Exception as e:
        logger.error(f"获取服务器时间失败: {str(e)}，使用本地时间")
        return int(time.time() * 1000)

def check_available(session):
    """检查库存"""
    check_data = {
        "activity_id": ACTIVITY_ID,
        "goods": [
            {
                "act_id": ACT_ID,
                "region_id": region_ids
            }
        ],
        "preview": 0
    }
    
    try:
        resp = session.post(
            "https://act-api.cloud.tencent.com/dianshi/check-available",
            json=check_data,
            timeout=10
        )
        result = resp.json()
    except Exception as e:
        logger.error(f"❌ 库存检查失败: {str(e)}")
        return None
    
    # 检查返回
    if result.get("code") != 0 or result.get("msg") != "ok":
        logger.warning(f"库存检查异常: {result.get('msg')}")
        return None
    
    # 检查商品权限
    goods_data = result.get("data", [{}])[0]
    if goods_data.get("available") != 1 or goods_data.get("user_available") != 1:
        logger.warning("商品无购买权限")
        return None
    
    # 检查地域库存
    quota = goods_data.get("quota", {})
    region_map = {1: "华北", 4: "华东", 8: "华南"}
    
    for region_id, region_name in region_map.items():
        if str(region_id) not in quota:
            continue
            
        bundle_data = quota.get(str(region_id), {}).get("bundle_budget_mc_lg4_01", {})
        available = bundle_data.get("available", 0)
        
        if available > 0:
            logger.info(f"✅ 检测到{region_name}（{region_id}）有库存！")
            return region_id
    
    logger.info("❌ 所有地域均无库存")
    return None

def buy_now(session, region_id):
    """下单购买"""
    do_data = {
        "activity_id": ACTIVITY_ID,
        "agent_channel": {
            "fromChannel": "",
            "fromSales": "",
            "isAgentClient": False,
            "fromUrl": "https://cloud.tencent.com/act/pro/featured-202604?fromSource=gwzcw.10216579.10216579.10216579&utm_medium=cpc&utm_id=gwzcw.10216579.10216579.10216579&msclkid=6b370ba9f89c1d21e93a6225d46c8044&page=spring2026&s_source=https%3A%2F%2Fcloud.tencent.com%2Fact%2Fpro%2Fdouble12-2025"
        },
        "business": {
            "id": 22755,
            "from": "lightningDeals"
        },
        "goods": [
            {
                "act_id": ACT_ID,
                "type": "bundle_budget_mc_lg4_01",
                "goods_param": {
                    "BlueprintId": "LINUX_UNIX",
                    "area": 1,
                    "ddocUnionConnect": 0,
                    "goodsNum": 1,
                    "imageId": "lhbp-eqora508",
                    "scenario": "0",
                    "timeSpanUnit": "12m",
                    "zone": "",
                    "regionId": region_id,
                    "type": "bundle_budget_mc_lg4_01"
                }
            }
        ],
        "preview": 0
    }
    
    try:
        resp = session.post(
            "https://act-api.cloud.tencent.com/dianshi/do-goods",
            json=do_data,
            timeout=10
        )
        result = resp.json()
        logger.info(f"🎯 购买返回: {json.dumps(result, ensure_ascii=False)}")
        
        if result.get("code") == 0:
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"❌ 购买失败: {str(e)}")
        return False

def buy_now_concurrent(session, region_ids):
    """并发抢购"""
    logger.info(f"开始并发抢购，地域: {region_ids}")
    
    with ThreadPoolExecutor(max_workers=min(3, len(region_ids))) as executor:
        futures = [executor.submit(buy_now, session, rid) for rid in region_ids]
        
        success = False
        for future in futures:
            try:
                if future.result():
                    success = True
                    logger.info("✅ 有一个地域抢购成功")
            except Exception as e:
                logger.error(f"抢购任务异常: {str(e)}")
    
    return success

# =================== 主程序 =================== #

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("腾讯云秒杀工具 - 简化版（青龙面板友好）")
    logger.info("=" * 60)
    
    # 检查配置
    if not check_config():
        logger.error("❌ 配置检查失败，程序退出")
        return
    
    # 显示配置
    logger.info(f"📅 秒杀时间: {SECKILL_TIME_STR}")
    logger.info(f"📍 抢购地域: {region_ids}")
    logger.info(f"🔑 CSRF Token: {CSRF_TOKEN[:10]}...")
    logger.info(f"🍪 Cookie长度: {len(COOKIE_STRING)} 字符")
    
    # 创建Session
    session = create_session()
    
    # 计算秒杀时间
    try:
        SECKILL_TIMESTAMP = int(time.mktime(time.strptime(SECKILL_TIME_STR, "%Y-%m-%d %H:%M:%S"))) * 1000
        logger.info(f"⏰ 秒杀时间戳: {SECKILL_TIMESTAMP}")
    except Exception as e:
        logger.error(f"❌ 时间格式错误: {str(e)}")
        return
    
    # 主循环
    logger.info("🚀 开始等待秒杀...")
    
    while True:
        current_time = get_server_time()
        
        if current_time >= SECKILL_TIMESTAMP:
            logger.info("🎯 秒杀时间到！开始抢购...")
            
            # 检查库存
            available_region = check_available(session)
            if available_region:
                logger.info(f"✅ 检测到有库存的地域: {available_region}")
                success = buy_now(session, available_region)
            else:
                logger.info("🔄 未检测到库存，尝试所有地域")
                success = buy_now_concurrent(session, region_ids)
            
            if success:
                logger.info("🎉🎉🎉 抢购成功！请查看订单 🎉🎉🎉")
            else:
                logger.warning("😔 抢购失败")
            
            break
        else:
            # 等待逻辑
            remaining = (SECKILL_TIMESTAMP - current_time) / 1000
            if remaining > 300:
                logger.info(f"⏳ 距离秒杀还有 {int(remaining/60)} 分钟")
                time.sleep(60)
            elif remaining > 60:
                logger.info(f"⏳ 距离秒杀还有 {int(remaining/60)} 分钟 {int(remaining%60)} 秒")
                time.sleep(30)
            elif remaining > 10:
                logger.info(f"⏳ 距离秒杀还有 {int(remaining)} 秒")
                time.sleep(5)
            else:
                logger.info(f"⏳ 距离秒杀还有 {remaining:.1f} 秒")
                time.sleep(1)
    
    logger.info("=" * 60)
    logger.info("程序执行完成")
    logger.info("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序异常: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
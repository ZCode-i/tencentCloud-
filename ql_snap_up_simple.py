#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cron: 58 14 * * *
new Env('腾讯云秒杀多账号版-稳健时间版');
"""

import os
import re
import time
import random
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =================== 基础常量（按需改） =================== #
ACTIVITY_ID = 162634773874417
GOODS_ACT_ID = 1784747698901873
GOODS_TYPE = "bundle_budget_mc_lg4_01"

REFERER_URL = "https://cloud.tencent.com/act/pro/featured-202604"
DO_GOODS_URL = "https://act-api.cloud.tencent.com/dianshi/do-goods"
TIME_SYNC_URL = "https://cloud.tencent.com/act/pro/double12-2025"

DEFAULT_REGION_IDS = [1, 4, 8]  # 华北, 华东, 华南

# 并发与性能默认值（可用环境变量覆盖）
ACCOUNT_MAX_WORKERS = int(os.environ.get("ACCOUNT_MAX_WORKERS", "16"))
REGION_MAX_WORKERS = int(os.environ.get("REGION_MAX_WORKERS", "8"))
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "4"))
BURST_PER_REGION = int(os.environ.get("BURST_PER_REGION", "3"))
PREHEAT_ADVANCE_MS = int(os.environ.get("PREHEAT_ADVANCE_MS", "800"))
SPIN_SLEEP_MS = int(os.environ.get("SPIN_SLEEP_MS", "15"))
RETRY_TOTAL = int(os.environ.get("RETRY_TOTAL", "2"))

# =================== 工具函数 =================== #
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def safe_int(v, default):
    try:
        return int(str(v).strip())
    except Exception:
        return default


def parse_region_ids():
    """
    REGION_IDS 支持:
    - 不配：用默认 [1,4,8]
    - 配置："1,4,8" 或 "1|4|8" 或 "1 4 8"
    """
    raw = os.environ.get("REGION_IDS", "").strip()
    if not raw:
        return DEFAULT_REGION_IDS

    parts = re.split(r"[,|\s]+", raw)
    out = []
    for p in parts:
        if not p:
            continue
        n = safe_int(p, None)
        if n is not None and n > 0:
            out.append(n)

    return sorted(list(set(out))) if out else DEFAULT_REGION_IDS


def build_session():
    session = requests.Session()
    retry = Retry(
        total=max(0, RETRY_TOTAL),
        connect=max(0, RETRY_TOTAL),
        read=max(0, RETRY_TOTAL),
        backoff_factor=0.05,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["HEAD", "GET", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def parse_accounts():
    """
    环境变量：
    TENCENT_COOKIE=ck1&ck2&ck3
    TENCENT_CSRF_TOKEN=tk1&tk2&tk3
    """
    raw_cookies = os.environ.get("TENCENT_COOKIE", "").split("&")
    raw_tokens = os.environ.get("TENCENT_CSRF_TOKEN", "").split("&")

    default_token = ""
    if raw_tokens and raw_tokens[0].strip():
        default_token = raw_tokens[0].strip()

    accounts = []
    for i, ck in enumerate(raw_cookies):
        ck = ck.strip()
        if not ck:
            continue

        tk = raw_tokens[i].strip() if i < len(raw_tokens) and raw_tokens[i].strip() else default_token
        accounts.append({
            "id": i + 1,
            "cookie": ck,
            "token": tk
        })

    return accounts


def parse_target_timestamp():
    """
    支持两种目标时间：
    1) SECKILL_DATETIME=YYYY-mm-dd HH:MM:SS  （指定日期）
    2) SECKILL_CLOCK=HH:MM:SS                 （每天该时刻，若已过则自动+1天）
    默认：15:00:00
    """
    dt_raw = os.environ.get("SECKILL_DATETIME", "").strip()
    clock_raw = os.environ.get("SECKILL_CLOCK", "").strip() or "15:00:00"

    if dt_raw:
        try:
            dt = datetime.strptime(dt_raw, "%Y-%m-%d %H:%M:%S")
            return int(dt.timestamp() * 1000), f"指定日期时间 {dt_raw}"
        except Exception:
            raise ValueError("SECKILL_DATETIME 格式错误，应为 YYYY-mm-dd HH:MM:SS")

    # 每日时刻模式
    try:
        hh, mm, ss = [int(x) for x in clock_raw.split(":")]
        now = datetime.now()
        target = now.replace(hour=hh, minute=mm, second=ss, microsecond=0)
        if target <= now:
            target = target + timedelta(days=1)
        return int(target.timestamp() * 1000), f"每日时刻 {clock_raw}（若当天已过则顺延到明天）"
    except Exception:
        raise ValueError("SECKILL_CLOCK 格式错误，应为 HH:MM:SS")


def get_server_time_once(session):
    try:
        resp = session.head(TIME_SYNC_URL, timeout=3)
        date_header = resp.headers.get("Date")
        if not date_header:
            return None
        dt_utc = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S GMT")
        dt_bj = dt_utc + timedelta(hours=8)
        return int(dt_bj.timestamp() * 1000)
    except Exception:
        return None


def calibrate_offset_ms(samples=3):
    session = build_session()
    offsets = []
    for _ in range(max(1, samples)):
        local_before = int(time.time() * 1000)
        server_ms = get_server_time_once(session)
        local_after = int(time.time() * 1000)

        if server_ms is None:
            time.sleep(0.12)
            continue

        local_mid = (local_before + local_after) // 2
        offsets.append(server_ms - local_mid)
        time.sleep(0.08)

    if not offsets:
        log("⚠️ 时间校准失败，回退本地时间（offset=0）")
        return 0

    offsets.sort()
    offset = offsets[len(offsets) // 2]
    log(f"🕒 时间校准完成，offset={offset}ms")
    return offset


def now_ms(offset_ms):
    return int(time.time() * 1000) + offset_ms


def build_headers(cookie, token):
    return {
        "Cookie": cookie,
        "x-csrf-token": token,
        "Content-Type": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/141.0.0.0 Safari/537.36"
        ),
        "referer": REFERER_URL,
    }


def build_payload(region_id):
    return {
        "activity_id": ACTIVITY_ID,
        "agent_channel": {
            "fromChannel": "",
            "fromSales": "",
            "isAgentClient": False,
            "fromUrl": ""
        },
        "business": {"id": 22755, "from": "lightningDeals"},
        "goods": [{
            "act_id": GOODS_ACT_ID,
            "type": GOODS_TYPE,
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
                "type": GOODS_TYPE
            }
        }],
        "preview": 0
    }


def post_buy_once(session, headers, region_id, acc_id, burst_idx):
    payload = build_payload(region_id)
    t0 = time.time()
    try:
        resp = session.post(
            DO_GOODS_URL,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        cost_ms = int((time.time() - t0) * 1000)
        preview = (resp.text or "")[:180].replace("\n", " ")
        log(f"👤账号{acc_id} 地域{region_id} 第{burst_idx}次 | HTTP {resp.status_code} | {cost_ms}ms | {preview}")
        return True
    except Exception as e:
        log(f"❌ 账号{acc_id} 地域{region_id} 第{burst_idx}次异常: {e}")
        return False


def single_account_task(acc, region_ids):
    acc_id = acc["id"]
    headers = build_headers(acc["cookie"], acc["token"])
    session = build_session()

    # 单账号内：地域 * 突发次数并发
    max_workers = min(REGION_MAX_WORKERS, max(1, len(region_ids) * BURST_PER_REGION))
    futures = []

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for rid in region_ids:
            for idx in range(1, BURST_PER_REGION + 1):
                futures.append(ex.submit(post_buy_once, session, headers, rid, acc_id, idx))
                # 小抖动，减少完全同毫秒碰撞
                if idx < BURST_PER_REGION:
                    time.sleep(random.uniform(0.02, 0.08))

        for f in as_completed(futures):
            try:
                _ = f.result()
            except Exception as e:
                log(f"❌ 账号{acc_id} 子任务异常: {e}")


# =================== 主流程 =================== #
def main():
    # 1) 参数读取与校验
    accounts = parse_accounts()
    if not accounts:
        log("❌ 未找到有效账号：请设置 TENCENT_COOKIE")
        return 1

    region_ids = parse_region_ids()
    if not region_ids:
        log("❌ REGION_IDS 解析后为空")
        return 1

    try:
        seckill_ts, mode_desc = parse_target_timestamp()
    except Exception as e:
        log(f"❌ 时间参数错误: {e}")
        return 1

    # 防御性限制，避免误配导致异常值
    if ACCOUNT_MAX_WORKERS <= 0 or REGION_MAX_WORKERS <= 0 or BURST_PER_REGION <= 0:
        log("❌ 并发参数必须大于 0（ACCOUNT_MAX_WORKERS / REGION_MAX_WORKERS / BURST_PER_REGION）")
        return 1

    log(f"✅ 已加载账号数: {len(accounts)}")
    log(f"✅ 地域列表: {region_ids}")
    log(f"✅ 目标时间模式: {mode_desc}")
    log(f"✅ 并发参数: 账号并发{ACCOUNT_MAX_WORKERS}, 地域并发{REGION_MAX_WORKERS}, 每地域突发{BURST_PER_REGION}")

    # 2) 时间校准
    offset_ms = calibrate_offset_ms(samples=3)

    # 3) 等待到开抢
    while True:
        current = now_ms(offset_ms)
        diff_ms = seckill_ts - current

        if diff_ms <= PREHEAT_ADVANCE_MS:
            log(f"🚀 进入冲刺阶段，剩余 {max(diff_ms, 0)} ms")
            break

        diff_sec = diff_ms / 1000.0
        if diff_sec > 60:
            log(f"⏳ 距离开抢 {diff_sec/60:.1f} 分钟")
            time.sleep(30)
        elif diff_sec > 5:
            log(f"⏳ 倒计时 {diff_sec:.2f} 秒")
            time.sleep(1)
        else:
            time.sleep(max(1, SPIN_SLEEP_MS) / 1000.0)

    while now_ms(offset_ms) < seckill_ts:
        time.sleep(0.001)

    # 4) 全账号并发开抢
    log("🔥 时间到，全账号并发发起请求")
    acc_workers = min(ACCOUNT_MAX_WORKERS, max(1, len(accounts)))

    with ThreadPoolExecutor(max_workers=acc_workers) as ex:
        futures = [ex.submit(single_account_task, acc, region_ids) for acc in accounts]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                log(f"❌ 账号主线程异常: {e}")

    log("✅ 任务执行完成")
    return 0


if __name__ == "__main__":
    try:
        code = main()
        raise SystemExit(code)
    except KeyboardInterrupt:
        log("⚠️ 手动中断")
        raise SystemExit(130)
    except Exception as e:
        log(f"❌ 未捕获异常: {e}")
        raise SystemExit(1)

# tencentCloud-
这是一个秒杀38元/年服务器的青龙本，请勿商用，否则后果自负

ql_get_cookies_no_playwright.py   # Cookie配置助手
ql_snap_up_simple.py              # 秒杀主程序（简化版）
```

## 🔧 环境变量配置

在青龙面板「环境变量」中添加：

### 1. 必需配置
```bash
# 秒杀时间（格式必须正确）
TENCENT_SECKILL_TIME="2026-04-22 15:00:00"

# CSRF Token（从浏览器获取）
TENCENT_CSRF_TOKEN="427372853"

# Cookie字符串（从浏览器控制台获取）
TENCENT_COOKIE_STRING="_ga=GA1.2.1234567890.1234567890; _gid=GA1.2.9876543210.1234567890; x-csrf-token=427372853; ..."
```

### 2. 可选配置
```bash
# 抢购地域（1=华北,4=华东,8=华南）
TENCENT_REGION_IDS="1,4,8"

# 活动ID（通常不需要改）
TENCENT_ACTIVITY_ID="162634773874417"
TENCENT_ACT_ID="1784747698901873"
```

## 📝 获取配置信息的方法

### 1. 获取 CSRF Token
```bash
1. 登录腾讯云控制台
2. 按 F12 → Network 标签
3. 刷新页面
4. 点击任意 cloud.tencent.com 请求
5. 查看 Headers → x-csrf-token
6. 复制这个值
```

### 2. 获取 Cookie 字符串
```bash
1. 登录腾讯云后，保持页面打开
2. 按 F12 → Console 控制台
3. 输入: document.cookie
4. 按回车
5. 复制全部输出内容
```

**示例输出**：
```
_ga=GA1.2.1234567890.1234567890; _gid=GA1.2.9876543210.1234567890; x-csrf-token=427372853; session_id=abc123def456; ...
```

## 🚀 部署步骤

### 步骤1：上传文件
1. 进入青龙面板「脚本管理」
2. 创建文件夹 `tencentyun`
3. 上传两个Python文件

### 步骤2：安装依赖
```bash
# 只需要这一个依赖
pip install requests
```

在青龙面板：
1. 进入「依赖管理」
2. 选择「Python」
3. 添加：`requests`
4. 点击「安装」

### 步骤3：配置环境变量
按上面的示例配置所有环境变量

### 步骤4：生成Cookie文件（可选）
```bash
# 运行配置助手
cd /ql/scripts/tencentyun
python3 ql_get_cookies_no_playwright.py
```

这个脚本会：
1. 检查环境变量配置
2. 显示获取Cookie的指南
3. 如果配置完整，生成cookies.json（可选）

### 步骤5：测试运行
```bash
# 测试秒杀脚本
cd /ql/scripts/tencentyun
python3 ql_snap_up_simple.py
```

脚本会：
1. 检查配置
2. 显示等待时间
3. 测试网络连接
4. 如果时间未到，会显示剩余时间

### 步骤6：创建定时任务
```bash
# 在青龙面板「定时任务」中添加
任务名称: 腾讯云秒杀
定时规则: 50 14 * * *   # 秒杀时间前10分钟
命令: task ql_snap_up_simple.py
```

## 🔄 多账号方案

### 方案A：多个定时任务
```bash
# 账号1
任务名称: 腾讯云秒杀-账号1
定时规则: 50 14 * * *
命令: task ql_snap_up_simple.py
环境变量: TENCENT_COOKIE_STRING="账号1的Cookie" ...

# 账号2（延迟5秒）
任务名称: 腾讯云秒杀-账号2  
定时规则: 50 14 * * *
命令: sleep 5 && task ql_snap_up_simple.py
环境变量: TENCENT_COOKIE_STRING="账号2的Cookie" ...
```

### 方案B：修改脚本支持多账号
使用之前创建的 `ql_snap_up_multi_account.py`，但需要手动管理多个Cookie文件。

## 🐛 常见问题解决

### 问题1：依赖安装失败
```bash
# 尝试换源
pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题2：Cookie失效
```bash
# 重新获取
1. 重新登录腾讯云
2. 获取新的Cookie字符串和CSRF Token
3. 更新环境变量
```

### 问题3：时间不对
```bash
# 检查格式
正确: "2026-04-22 15:00:00"
错误: "2026-4-22 3:00:00"  # 缺少前导零
错误: "2026/04/22 15:00:00"  # 用了斜杠
```

### 问题4：权限错误
```bash
# 可能原因
1. CSRF Token 不正确
2. Cookie 已过期
3. 账号未实名认证
```

## 📊 日志查看

```bash
# 查看实时日志
tail -f /ql/scripts/tencentyun/snap_up_simple.log

# 查看最近100行
tail -100 /ql/scripts/tencentyun/snap_up_simple.log
```

## 🔒 安全建议

1. **定期更新**：每次抢购前更新Cookie和Token
2. **环境变量保护**：不要泄露环境变量内容
3. **账号安全**：使用子账号或专门抢购的账号
4. **监控日志**：定期检查运行日志

## ⚡ 性能优化

1. **时间校准**：脚本会自动获取腾讯云服务器时间
2. **并发抢购**：支持多个地域同时抢购
3. **智能检测**：先检测库存，再集中抢购
4. **错误重试**：内置错误处理机制

## 📅 维护计划

### 日常维护
- 每次抢购前1天：更新Cookie和Token
- 每次抢购前1小时：测试脚本运行
- 抢购后：检查日志，总结经验

### 长期维护
- 每月检查：API接口是否有变化
- 每次大促后：更新文档和脚本
- 定期备份：环境变量配置

## 🎉 成功标志

1. 脚本运行无报错
2. 日志显示"抢购成功"
3. 腾讯云控制台有订单
4. 收到腾讯云通知

## ❓ 获取帮助

1. 查看日志文件：`snap_up_simple.log`
2. 检查环境变量配置
3. 测试网络连接：`ping cloud.tencent.com`
4. 手动测试接口：使用Postman或curl

---

**祝您抢购成功！** 🚀

如果遇到问题，请按以下顺序排查：
1. 环境变量是否正确
2. 网络是否通畅  
3. 时间格式是否正确
4. Cookie和Token是否最新
5. 查看详细日志

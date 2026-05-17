# 胖乖饮水 — 开发文档

## 项目概述

将胖乖生活饮水机的命令行脚本改造为 Android 手机 App，基于 Flet（Python + Flutter）框架。

## 项目结构

```
d:\qiekj\
├── main.py                  # 唯一入口
├── pgsh.py                  # 原始命令行脚本（不动，参考用）
├── requirements.txt         # 依赖：flet, requests, jsonpath-ng
├── .gitignore               # 排除 .token, .devices.json, __pycache__, build, *.pyc
├── pgsh_app/
│   ├── __init__.py
│   ├── api.py               # API 层（封装所有 HTTP 请求）
│   ├── storage.py           # 本地存储（token、设备列表）
│   └── views/
│       ├── __init__.py
│       ├── login_view.py    # 登录页面（两步流程）
│       └── home_view.py     # 主页（设备卡片 + 出水）
├── .token                   # 本地存储的登录 token（gitignore）
└── .devices.json            # 本地缓存的设备列表（gitignore）
```

## 技术栈

| 组件 | 版本 | 说明 |
|------|------|------|
| Flet | 0.85.1 | Python + Flutter 移动端框架 |
| flet-desktop | 0.85.1 | 桌面预览 |
| requests | 2.34.2 | HTTP 请求 |
| jsonpath-ng | 1.8.0 | JSON 解析 |

## 依赖安装

```bash
pip install flet requests jsonpath-ng
```

## 运行方式

```bash
# 桌面预览
python main.py

# 打包 Android APK（需要 Flutter SDK + Android SDK，首次自动下载）
flet build apk
```

## API 接口

### 请求头（从原版 App v1.119.1 抓包确认）

```
Version: 1.119.1
channel: android_app
User-Agent: okhttp/4.12.0
Content-Type: application/x-www-form-urlencoded;charset=UTF-8
Host: userapi.qiekj.com
Authorization: <token>  （登录后所有请求）
timestamp: <毫秒时间戳>
```

### 使用的接口

| 接口路径 | 用途 | 备注 |
|---------|------|------|
| `POST /common/sms/sendCode` | 发送验证码 | 参数: phone, template=reg |
| `POST /user/reg` | 登录/注册 | 参数: channel, phone, verify；返回 token |
| `POST /user/balance` | 查询余额 | 返回 tokenCoin, integral, integralAmount；也用于验证 token 是否有效 |
| `POST /alipay/isSign` | 查询免密支付状态 | 返回 data: true/false |
| `POST /goods/latestUsed` | 最近使用设备 | 参数: categoryCode=5 |
| `POST /goods/normal/skus` | 获取 SKU | 参数: goodsId |
| `POST /goods/normal/details` | 获取设备详情 | 参数: goodsId；返回 imei |
| `POST /userIntegral/checkUserIsRisk` | 积分风控检查 | |
| `POST /payChannelRoute/addUserAfterPayChannel` | 注册支付通道 | 参数: method=15 |
| `POST /orderRisk/isCheckLocation` | 位置校验 | 参数: categoryCode=04, imei |
| `POST /goods/water/unlock` | 解锁出水 | 参数: skuId, promotions, token |
| `POST /goods/water/sync` | 轮询出水状态 | workStatus=2 表示出水中 |
| `POST /order/afterPay/creating` | 创建订单 | 参数: orderNo |
| `POST /order/detail` | 订单详情 | 参数: orderId |

### 未使用但已知的接口（抓包发现）

| 接口 | 用途 |
|------|------|
| `POST /common/isNeedCaptcha` | 检查是否需要图形验证码 |
| `POST /user/info` | 用户完整信息 |
| `POST /shop/nearby/list` | 附近店铺（需经纬度） |
| `POST /slot/get` | 广告位（大量调用，可忽略） |

## 页面流程

```
启动
 → 读取 .token
 → 有 token → check_token()
    → 有效 → 主页（加载设备+余额）
    → 无效 → 主页 + 自动跳转登录页（提示"登录已过期"）
 → 无 token → 登录页（提示"首次使用"）

登录页
 → 步骤1: 输入手机号 → 发送验证码
 → 步骤2: 输入4位验证码（自动跳转焦点，填满自动登录）
    → 成功 → 保存 token → 跳转主页
    → 失败 → 输入框变红 + 抖动 + 震动 + 提示"验证码错误"

主页
 → 顶栏: 标题 + 余额 + 免密标签
 → 设备卡片列表（冷水蓝色圆钮 / 热水橙色圆钮）
 → 右下角刷新 FAB
 → 出水前检查:
    - 已开通免密: 跳过余额检查
    - 未开通免密: 余额 < ¥0.20 拦截
```

## Token 机制

- 单一 token，无 refresh_token
- **每次重新登录会使旧 token 失效**（同时使用原版 App 会挤掉脚本的 token）
- Token 可能是长效的（推测 7-30 天），只要不在其他端重新登录就不会过期
- 存储在项目根目录 `.token` 文件中

## 本地存储

| 文件 | 内容 | 格式 |
|------|------|------|
| `.token` | 登录 token | 纯文本 |
| `.devices.json` | 缓存的设备列表 | JSON 数组，按位置分组 |

设备列表格式：
```json
[
  {"name": "15斋B1楼", "goodsId_hot": "1101620932", "goodsId_cold": "1101619459"},
  {"name": "12斋B1楼", "goodsId_hot": "...", "goodsId_cold": "..."}
]
```

## Flet 0.85 API 注意事项

Flet 0.85 相比 0.81 有破坏性变更：

| 0.81（旧） | 0.85（新） |
|------------|-----------|
| `ft.padding.symmetric(horizontal=, vertical=)` | `ft.Padding(left=, top=, right=, bottom=)` |
| `ft.padding.only(left=, right=, top=, bottom=)` | `ft.Padding(left=, top=, right=, bottom=)` |
| `ft.padding.all(12)` | `12`（直接用数字） |
| `ft.border_radius.only(bottom_left=, bottom_right=)` | `ft.BorderRadius(top_left=, top_right=, bottom_left=, bottom_right=)` |
| `ft.margin.only(top=, left=, right=)` | `ft.Margin(top=, left=, right=, bottom=)` |
| `ft.alignment.center` | `ft.Alignment(0, 0)` |
| `ft.app(target=main)` | `ft.run(main)` |
| `page.open(snack_bar)` | `page.overlay.append() + snack_bar.open = True` |
| `field.focus()` 同步调用 | `await field.focus()` 异步调用 |
| `ft.TextField(counter_text='')` | `ft.TextField(counter='')` |
| `ft.Expanded(child=...)` | `ft.Container(expand=True)` |

## 远程仓库

```
https://github.com/lingyezhixing/PGSH-FW.git
```

分支: main

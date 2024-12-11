# 🌐 Pipe Network Bot [v1.0]

## 📋 目录
- [功能特点](#-功能特点)
- [系统要求](#-系统要求) 
- [安装说明](#-安装说明)
- [配置说明](#️-配置说明)
- [使用方法](#-使用方法)
- [故障排除](#-故障排除)

## 🚀 功能特点

- 🔐 **账户管理**
  - ✅ 自动账户注册与推荐系统
  - 🔄 智能登录和会话管理
  - 📊 全面的账户数据统计

- 🤖 **节点操作**
  - 📡 自动节点测试和延迟检查
  - ⚡ 优化的积分获取系统
  - 🔄 高级心跳机制

- 🛡️ **安全性与性能**
  - 🔒 安全的会话管理
  - 🌐 完整代理支持(HTTP/SOCKS5)
  - ⚡ 多线程操作

## 💻 系统要求

- Python 3.10-3.11
- 稳定的网络连接
- 可用的代理(HTTP/SOCKS5)

## 🛠️ 安装说明

1. **克隆仓库**
   ```bash
   git clone [仓库地址]
   ```

2. **设置虚拟环境**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   source venv/bin/activate      # Unix/MacOS
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

## ⚙️ 配置说明

### 📁 settings.yaml

```yaml
# 核心配置
threads: 30                    # 并发线程数
keepalive_interval: 120        # 节点测试间隔(秒)
heartbeat_interval: 24         # 心跳间隔(小时)
referral_codes:               # 推荐码列表
  - ""                        # 在此添加您的推荐码

# 显示设置
show_points_stats: true       # 每次操作后显示积分

# 启动设置
delay_before_start:
  min: 2                      # 最小启动延迟(秒)
  max: 3                      # 最大启动延迟(秒)
```

### 📁 输入文件结构

#### data/farm.txt
```
email:password
email:password
```

#### data/register.txt
```
email:password
email:password
```

#### data/proxies.txt
```
http://user:pass@ip:port
socks5://user:pass@ip:port
```

## 📊 数据导出

机器人包含导出账户综合统计数据的功能：
- 已赚取的总积分
- 推荐链接

## 🚀 使用方法

1. 根据您的偏好配置settings.yaml文件
2. 将您的账户和代理添加到相应文件中
3. 启动机器人：
   ```bash
   python run.py
   ```

## 🔧 故障排除

### 常见问题及解决方案

#### 🔑 登录问题
- 验证账户凭据
- 检查代理功能
- 确保账户未被封禁

#### 🌐 节点测试问题
- 验证网络连接
- 检查代理响应时间
- 确保适当的保活间隔

#### 🐦 Twitter绑定问题
- 验证Twitter令牌
- 检查账户资格
- 确保Twitter账户处于活动状态
# 01 · 识别：三分钟戳穿虚假参数

## 核心思路

手机里有两套"参数"：

- **软件写的**（`build.prop`、设置界面）→ 想改什么都行
- **硬件报的**（USB 描述符、芯片工艺、GPU 型号、分区表）→ 改不了

验机就是拿后者去对前者的账。

---

## 第一步：USB 描述符（最硬的证据）

插上电脑，PowerShell：

```powershell
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like '*USB\VID_*' } |
  Select-Object Status, FriendlyName, InstanceId
```

再取固件自报的描述字符串：

```powershell
$id = 'USB\VID_1782&PID_4001\49694698185900'   # 换成实际 InstanceId
Get-PnpDeviceProperty -InstanceId $id -KeyName DEVPKEY_Device_BusReportedDeviceDesc
```

本机实测结果：

```
BusReportedDeviceDesc : Unisoc Phone
HardwareIds           : USB\VID_1782&PID_5D20
```

### VID 对照

| VID | 厂商 |
|---|---|
| `1782` | 紫光展锐 UNISOC |
| `05C6` | 高通 Qualcomm |
| `0E8D` | 联发科 MediaTek |
| `18D1` | Google |
| `12D1` / `2717` | 华为 / 小米 |

**宣称"骁龙 888"，VID 却是展锐——到此已经结束了。**

---

## 第二步：CPU-Z 看工艺和 GPU

| 字段 | 为什么可信 |
|---|---|
| **Process（工艺）** | 由 SoC 信息接口读取 |
| **GPU Renderer** | GPU 驱动上报 |

本机实测：

```
Model   : T616
Cores   : 10          ← 假！T616 是 8 核
Process : 12 nm       ← 真的
GPU     : Mali-G57    ← 真的
```

"10 核"本身就是破绽：主流旗舰没有 10 核（那是 Helio X20 时代的产物）。

### 常识对照

| 宣称 | 真实应该是什么 |
|---|---|
| 骁龙 888 | 8 核 / **5nm** / Adreno 660 |
| 骁龙 870 | 8 核 / 7nm / Adreno 650 |
| 天玑 1200 | 8 核 / 6nm / Mali-G77 |
| **T616** | 8 核 / **12nm** / Mali-G57 |

---

## 第三步：分区表反算容量

界面上的容量可以被 `statfs` 伪造，**分区表不会**。

本机 81 个分区，合计 `61,068,288`（单位 **KB**）：

```
61,068,288 KB ÷ 1024 ÷ 1024 = 58.2 GiB  →  64 GB 存储
```

**宣称 256GB，实际 64GB。**

### 一个容易踩的坑：单位

我第一次按 4KB 单位算，得出 233GB，误判"256GB 是真的"。

**正确做法**：用标准分区的大小去验证单位——

| 分区 | 标准大小 |
|---|---|
| `misc` | 1 MB |
| `boot` | 64 MB |
| `cache` | 300 MB |

对上了，单位就确定了（本机是 **1KB**）。

---

## 实测对照表

| 项目 | 宣称 | 实测 | 证据 |
|---|---|---|---|
| 处理器 | 骁龙 888，10 核 | **T616，8 核，12nm** | USB 描述符 + CPU-Z |
| GPU | — | Mali-G57 | GPU 驱动 |
| 内存 | 16 GB | 远小于此 | 平台不支持 |
| 存储 | 256 GB | **64 GB** | 分区表 58.2 GiB |
| 网络 | 5G | **4G LTE** | T616 是 4G 平台 |
| 售价 | "旗舰" | **165–188 元** | 电商在售 |

---

## 结论

**这四个东西造不了假：**

1. USB 描述符的 `VID` 和 `BusReportedDeviceDesc`
2. CPU-Z 的 `Process`（工艺）
3. CPU-Z 的 `GPU Renderer`
4. 分区表反算的总容量

买之前花十分钟看这四样，比看一百条商品描述都管用。

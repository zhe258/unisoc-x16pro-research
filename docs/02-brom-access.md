# 02 · 打通 BROM：驱动、CRC16 与 CVE 顺序

## 一、找到 BROM

设备历史里出现 `USB\VID_1782&PID_4D00` —— 这就是展锐的 **BootROM 模式**。

**进入方式**：按住音量键 + 插 USB。屏幕保持黑屏，电脑会响一声。

**窗口期**：约 5–30 秒，超时自动开机。按住两个键比只按一个键撑得久。

---

## 二、驱动：官方驱动装不上，用 WinUSB

展锐的 VCOM 驱动证书 **2017 年就过期了**，Windows 10 直接拒绝安装。

**解决方案：Zadig + WinUSB**

```
1. 下载 Zadig（zadig.akeo.ie）
2. 设备进入 BROM（VID_1782 PID_4D00）
3. Zadig → Options → List All Devices → 选中该设备
4. 驱动选 WinUSB → Replace Driver
```

之后用 `pyusb` 就能直接通信，**不需要任何展锐官方驱动**。

---

## 三、协议要点

### 帧格式（HDLC）

```
0x7E | 类型(1B) | 长度(2B) | 载荷 | CRC16(2B) | 0x7E
```

载荷中出现 `0x7D` / `0x7E` 时转义：`0x7D` + (`原值 ^ 0x20`)。

### 校验：两个阶段不一样（最大的坑）

| 阶段 | 算法 |
|---|---|
| **BROM**（刚进 4D00） | **CRC16**（多项式 `0x11021`，初值 0） |
| **FDL1/FDL2**（加载后） | **16 位求和，取反，偶数长度时字节交换** |

一开始只按"求和"实现，设备直接回：

```
bad checksum (0x570a, expected 0x26e4)
```

手工算 CRC16 = `0x570A`，完全吻合 —— 于是确定 BROM 阶段用 CRC16。

### 命令集

| 命令 | 值 | 用途 |
|---|---|---|
| `CONNECT` | `0x00` | 建立连接 |
| `START_DATA` / `MIDST_DATA` / `END_DATA` | `0x01/0x02/0x03` | 下载 |
| `EXEC_DATA` | `0x04` | 执行 |
| `READ_START` / `READ_MIDST` / `READ_END` | `0x10/0x11/0x12` | 读取 |
| `READ_PARTITION` | `0x2D` | 读分区表 |
| `CHECK_BAUD` | `0x1A` | 握手（**必须第一条发**） |

### 块大小（实测）

| 方向 | 有效上限 |
|---|---|
| **下载**（写内存/写分区） | **528 字节**（4096 会被拒） |
| **读取** | **32768 字节**（65535 失败） |

读取块长与速度关系（实测）：

| 块长 | 速度 |
|---|---|
| 2112 | 0.08 MB/s |
| 4096 | 0.13 MB/s |
| 8192 | 0.25 MB/s |
| 16384 | 0.55 MB/s |
| **32768** | **0.67 MB/s** |

---

## 四、CVE-2022-38694：绕过 fdl1 签名

参考：[TomKing062/CVE-2022-38694_unlock_bootloader](https://github.com/TomKing062/CVE-2022-38694_unlock_bootloader)

### 地址（ums9230 / T616）

| 项目 | 地址 |
|---|---|
| FDL1 | `0x65000800` |
| FDL2 | `0x9EFFFE00` |
| CVE 载荷 | `0x65015F08` |

### 顺序是关键（试错得出）

```
❌ 先写载荷 → 再发 END        → 设备复位（FDL1 还没进内存，跳过去是空的）
❌ 载 FDL1 → 写载荷 → 不 END   → BROM 不理后续命令（传输没结束）
✅ 载 FDL1 → 写载荷 → 发 END   → 成功
```

### 成功标志

```
BROM version : b'SPRD3\x00'
FDL1 version : b'Spreadtrum Boot Block version 1.'
EXEC FDL2    : 0x96（已初始化）
partition table: 81 项
```

---

## 五、其他踩过的坑

| 现象 | 原因 | 解决 |
|---|---|---|
| `Errno 19/5` | 物理断开（拔线/线材） | 换线重试，不是协议问题 |
| `0x00` 无回包 | 丢包或超时太短 | 超时提到 10 秒 |
| `0x8X` | 设备拒绝命令 | 检查地址/块大小 |
| 读一半串包 | 上一个 READ_END 的 ACK 没吃掉 | **按类型收包**，跳过非期望帧 |
| 最后一句 ACK 卡死 | 设备不回最后确认 | 不等它，直接收尾 |

---

## 六、能力边界

打通之后能做：

- ✅ 读 81 个分区（0.67 MB/s）
- ✅ 写任意分区（含 `splloader`）
- ✅ 备份/恢复
- ✅ 执行未签名代码（CVE 生效）

**但不能**：

- ❌ 解锁 Bootloader（见 [`04-unlock-attempts.md`](04-unlock-attempts.md)）
- ❌ 改引导（`splloader` 受校验）

---

## 七、工具

见 [`tools/brom.py`](../tools/brom.py)：Python + pyusb 实现，全部逻辑自己写，不依赖展锐驱动。

```bash
# 读分区表
python brom.py --wait 600 --quiet

# 备份分区
python brom.py --wait 600 --quiet --dump boot_a --blk 32768

# 写分区
python brom.py --wait 600 --quiet --write misc=dump/misc.bin --verify-write
```

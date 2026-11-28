# 07 · 全部尝试路径与结果（完整清单）

> 本文记录为了解锁这台设备而尝试过的**每一条路径**，包括失败的。
> 目的：后来者不必重复踩坑。
> 结论先行：**主路径全部失败，原因是 RSA-4096 签名验证。**

---

## 一、总览表

| # | 路径 | 手段 | 结果 |
|---|---|---|---|
| 1 | 识别真实硬件 | USB 描述符 / CPU-Z / 分区表 | ✅ 成功 |
| 2 | USB ADB | 开发者选项 + USB 调试 | ❌ 接口不存在 |
| 3 | 无线调试 | 开无线调试 + 端口扫描 | ❌ 0 个监听端口 |
| 4 | DSU 动态系统 | 装 GSI，重启 | ❌ bootloader 忽略标志 |
| 5 | fastboot | 三种按键组合 | ❌ 无 fastboot 接口 |
| 6 | BROM 入口 | 音量键 + 电源 | ✅ 成功 |
| 7 | BROM 协议 | 自研 Python 客户端 | ✅ 成功 |
| 8 | CVE-2022-38694 | ROP 劫持执行 FDL1 | ✅ 成功 |
| 9 | 分区读写 | FDL2 命令 | ✅ 成功 |
| 10 | 完整备份 | 8 个分区 | ✅ 成功 |
| 11 | 改 SPL（填充区 1 字节） | 测签名保护 | ❌ 黑屏 |
| 12 | 改 uboot（字符串 1 字符） | 测签名保护 | ❌ 黑屏 |
| 13 | 改 uboot + 修复 SHA256 | 绕过哈希校验 | ❌ 仍黑屏 |
| 14 | 写第三方 cboot（Realme） | 用别家签名的引导 | ❌ 硬件不匹配 |
| 15 | 官方解锁流程（擦 SPL + cboot + spl-unlock） | 复刻官方 bat | ⚠️ 解锁标记写入成功，但无效 |
| 16 | identifier 签名解锁 | 需 fastboot | ❌ 无 fastboot |
| 17 | misc 写 boot-fastboot | 让 uboot 进 fastboot | ❌ 被忽略 |
| 18 | 内核漏洞提权 | 5.4.161 内核 | ⚠️ Dirty Pipe 不适用，其余不可行 |
| 19 | OTA 伪造 | 替换更新包 | ❌ 需 OTA 私钥 + AVB |
| 20 | 解锁状态下再试 fastboot | 有解锁标记后 | ❌ 仍无 |

---

## 二、逐条详情

### 1. 识别真实硬件 ✅

```
USB 描述符：BusReportedDeviceDesc = "Unisoc Phone"，VID_1782
CPU-Z      ：T616 / 12nm / Mali-G57
分区表     ：81 项，单位 KB，总 58.2 GiB → 64GB
```

**结论**：宣称的"骁龙 888 / 16GB / 256GB / 5G"全假。

### 2 & 3 & 4 & 5. 常规通道 ❌

| 通道 | 尝试 | 结果 |
|---|---|---|
| USB ADB | 开发者选项开 USB 调试 | USB 用途列表只有：充电/文件传输/相机/MIDI/虚拟光驱，**无 ADB** |
| 无线调试 | 开启后扫端口 | 28k 端口扫描，**0 个监听** |
| DSU | 安装 GSI 镜像 | 能装，重启仍回原系统 |
| fastboot | 音量上/音量下/组合键 | 只进 BROM |
| OEM 解锁开关 | 可拨动 | 无 fastboot 可用，**是装饰** |

### 6 & 7. BROM 与协议 ✅

```
入口：VID_1782 & PID_4D00，按住音量键插 USB
驱动：Zadig + WinUSB（官方驱动证书 2017 年过期）
协议：HDLC 帧（0x7e 包裹 / 0x7d 转义）
校验：BROM 阶段 CRC16，FDL 阶段求和
```

**关键踩坑**：

- 一开始用"求和"→ 报 `bad checksum (0x570a)`；手算 CRC16 = 0x570A，确认 BROM 用 CRC16
- 下载块必须 ≤ **528 字节**（4096 会被拒）
- 读取块可用 **32768 字节**（0.67 MB/s）
- `END_DATA` 之后只等 300ms 即可，不必等 3 秒

### 8 & 9. CVE 与读写 ✅

**正确顺序（关键）**：

```
载入 FDL1 (0x65000800)
  → 写入 ROP 载荷 (0x65015F08，96 字节，不发 END)
  → 发 END_DATA 触发返回地址劫持
  → FDL1 开始运行
  → 载入 FDL2 (0x9EFFFE00) 并 EXEC
  → 获得分区读写能力
```

**顺序错了的后果**：

| 做法 | 结果 |
|---|---|
| 先写载荷再发 END | 设备复位（FDL1 还没进内存） |
| 载荷不发 END | BROM 不理后续命令 |

### 10. 完整备份 ✅

8 个分区，86.5 MB，全部用魔数验证（`DHTB` / `ANDROID!` / `AVB0` 等）。

### 11. 改 SPL —— 填充区 1 字节 ❌

```
位置：0x0FD0C（519 字节全零填充区中间）
改动：写入 0xAA
结果：设备完全黑屏，长按电源无反应
恢复：BROM 写回原版 → 立即正常
```

**结论**：SPL 受完整性/签名保护，**任何字节改动都会被拒绝**。

### 12. 改 uboot —— 字符串 1 字符 ❌

```
位置：0x0915A1（"mipi_dphy_configure" 字符串内，改成 "mipi_dphy_configuXe"）
改动：功能上完全无害
结果：黑屏
```

**结论**：uboot 同样受保护。

### 13. 改 uboot + **修复 SHA256** ❌（决定性实验）

**这是最关键的一次实验。**

先逆向出 DHTB 结构：

```
DHTB 头（512 字节）
  +0x00  "DHTB"
  +0x04  version = 1
  +0x08  SHA256(payload) —— 32 字节
  +0x30  payload 大小
```

验证：

```
SHA256(uboot[0x200 : 0x200+0xE49B0]) == 头部 0x08 处的 32 字节  ✅ 完全吻合
```

于是构造"改内容 + 重算并填入正确 SHA256"的镜像：

```
改动：0x0915A1 'r' → 'X'
重算：SHA256(payload) 覆盖 0x200..0xE4BB0
回填：头部 0x08..0x28
结果：写入成功（identical=True），重启后仍然黑屏 ❌
```

**结论**：SHA256 只是完整性字段，**信任根是 RSA 签名**。

### 14. 第三方 cboot ❌

从资源站下载 `ums9230_Realme_C31`、`ums9230_RYHT_X90` 等包，测试其 `fdl2-cboot.bin`：

```
所有包的 cboot 完全相同（sha256: 40BE7928B4444BBB）
→ 它们不是"某机型的引导"，而是通用镜像
写入 uboot_a/uboot_b 后 → 黑屏
```

**结论**：cboot 的存储控制器配置与这台设备不匹配。

**旁证**：这些包的 `fdl2-dl.bin` 是 1,062,104 字节，我们的 FDL2 是 934,088 字节——**存储类型不同**。

### 15. 官方解锁流程 ⚠️

官方 `unlock_autopatch_9230.bat` 的完整编排：

```bat
① 读 splloader + uboot，擦除 splloader 和 splloader_bak
② gen_spl-unlock splloader.bin → u-boot-spl-16k-sign.bin
③ 写 fdl2-cboot.bin 到 uboot
④ 重启
⑤ 执行 spl-unlock.bin（"unlock runs here"）
⑥ 读 miscdata[8192:64] 检查
⑦ 恢复 splloader / uboot / misc
```

**我们复刻的结果**：

- ① 擦除 ✅
- ③ 写 cboot ✅
- ⑤ 执行 spl-unlock ✅（END 后设备断链 = ROP 生效）
- ⑥ **miscdata 的 64 字节从全零变成了 32+16+16 字节 —— 解锁标记写入成功！**
- 但 ⑦ 恢复后，**原版 uboot 仍然强制 AVB**，修改过的 vbmeta 依然无法启动

**结论**：解锁标记写进去了，但**原版 uboot 不认这个标记**（或者认了仍然校验）。

### 16. identifier 签名解锁 ❌

资源站的 `sign_unlock_bl` 工具包：

```
sign.pem（私钥）+ unlockbl.sh（作者 shijiu.ren@spreadtrum.com）
流程：
  fastboot oem get_identifier_token
  → openssl dgst -sha256 -sign sign.pem → signature.bin
  → fastboot flashing unlock_bootloader signature.bin
```

**前提是设备能进 fastboot —— 这台不能。**

### 17. misc 写 boot-fastboot ❌

```
写 misc = "boot-fastboot"
重启 → 正常进系统（被忽略）
解锁状态下再试 → 仍然被忽略
```

### 18. 内核漏洞 ⚠️

```
内核版本：Linux 5.4.161（2021-08）
Dirty Pipe (CVE-2022-0847)：只影响 5.8+，不适用
其他 CVE：需要装 exploit App + 绕 SELinux，且装 App 有阻碍
```

**结论**：理论可行，实际不划算。

### 19. OTA 伪造 ❌

```
思路：把伪造的更新包放进 /data/ota_package，骗过 update_engine
障碍：
  · update_engine 用 otacerts.zip 里的公钥验签（需厂商 OTA 私钥）
  · 即使验签通过，写完后 uboot 仍要验 AVB
```

### 20. 解锁状态下再试 fastboot ❌

写入解锁标记后重新测试：

```
USB 设备监听 10 分钟：只出现 BROM(4D00)，无 fastboot 设备
音量组合键：仍只进 BROM
```

---

## 三、最终逆向结论：启动链的完整签名结构

### DHTB 头（512 字节，每个镜像开头）

| 偏移 | 内容 |
|---|---|
| 0x00 | `"DHTB"` |
| 0x04 | version = 1 |
| **0x08** | **SHA256(payload)，32 字节** |
| 0x30 / 0x3C / 0x40 | payload 大小等字段 |

### SIMGHDR（签名头，位于 payload 之后）

| 偏移 | 内容 |
|---|---|
| +0x00 | `"SIMGHDR"` |
| +0x10 | payload 大小 |
| +0x18 | payload 起始偏移（0x200） |
| +0x20 | 签名块大小（**0x458 = 1112 字节**） |
| +0x28 | 签名块绝对偏移 |

### 签名块（1112 字节）

| 偏移 | 内容 |
|---|---|
| +0x00 | 版本 = 1 |
| +0x04 | **0x1000 = 4096 → RSA-4096** |
| +0x08 | 哈希/签名算法标识 |
| +0x0C | **512 字节 RSA 签名** |
| +0x20C | **32 字节 SHA256** |

### 实测位置

| 镜像 | 大小 | SIMGHDR 位置 | payload | 签名块 |
|---|---|---|---|---|
| splloader | 66,248 | `0xFE10` | `0xFC10` | `0x458 @ 0xFE70` |
| uboot | 3 MB | `0xE4BB0` | `0xE49B0` | `0x458 @ 0xE4C10` |

### 验证关系

```
BootROM/SPL 计算 SHA256(payload)
  → 与 SIMGHDR 中的哈希比对（完整性）
  → 用 efuse 中的公钥验证 512 字节 RSA 签名（信任根）
```

**没有厂商私钥 = 无法伪造 = 无法修改任何引导镜像。**

---

## 四、为什么全部失败（一句话）

> **不是技术不够，是密码学：RSA-4096 + efuse 公钥，没有私钥就无解。**
>
> 能进、能读、能写、能救——**但改不了引导**。

---

## 五、给后来者的建议

1. **别再试改良引导镜像**——RSA 挡死，试一次黑屏一次
2. **别再找 fastboot**——这个 ROM 里没有这个组件
3. **想刷机，先确认三件事**：
   - 有 fastboot 吗？
   - 有厂商签名的 cboot 吗（且匹配你的存储类型）？
   - 有泄露的 identifier 私钥吗？
   
   **三样缺一，就别开始。**
4. **这台机器的正确用法**：BROM 读写通道 + 备份能力，当实验平台

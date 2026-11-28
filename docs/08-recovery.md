# 08 · 备份与恢复手册（给下一个拿到这台设备的人）

> 这台设备的引导层被 RSA-4096 锁死，**但 flash 是可读可写的**。
> 只要 BootROM 还能连上，任何软件层面的破坏都能救回来。
> 本文是完整的"怎么备份、怎么救"的手册。

---

## 一、先搞清楚：能救到什么程度

```
✅ 能救：任何分区被写坏/擦除（splloader、uboot、boot、vbmeta、misc…）
✅ 能救：系统起不来、黑屏、无限重启
❌ 不能救：efuse 被熔断（这个我们碰不到）
❌ 不能救：硬件损坏
```

**核心原理**：BootROM 在芯片的**掩膜 ROM**里，不依赖 flash 内容。
所以就算 splloader 被擦成全零，插 USB 按住音量键仍然能进下载模式。

---

## 二、BROM 入口（关键操作要点）

### 正确步骤

```
1. 拔掉 USB
2. 按住【音量减 + 电源】
3. 插入 USB
4. 听到电脑"叮"的一声（设备识别）
5. 【立刻松开两个键】  ← 这一步极其关键
```

### ⚠️ 为什么第 5 步关键

**一直按住会导致设备周期性复位**，表现为：

```
连上 → 传几十 KB → 设备消失 → 再连上 → 再消失
```

我们曾因此卡了 2 小时，误判为"线材问题"。

**正确做法：听到连接声立刻松手。**

---

## 三、分区表（81 个分区，关键部分）

| 分区 | 大小 | 说明 |
|---|---|---|
| `splloader` | 512 KB | **一级引导（受 RSA 保护）** |
| `splloader_bak` | 512 KB | 一级引导备份 |
| `uboot_a` / `uboot_b` | 3 MB ×2 | **二级引导（受 RSA 保护）** |
| `boot_a` / `boot_b` | 64 MB ×2 | 内核 + ramdisk |
| `vendor_boot_a` | 64 MB | Android 12 的 vendor ramdisk |
| `dtbo_a` | 8 MB | 设备树覆盖 |
| `vbmeta_a` | 1 MB | AVB 校验元数据 |
| `init_boot_a` | 8 MB | 全零（空分区） |
| `super` | 6.45 GB | 动态分区（system/vendor/product） |
| `userdata` | 50.75 GB | 用户数据 |
| `misc` | 1 MB | 启动命令（bootloader_message） |
| `miscdata` | 1 MB | **锁状态、序列号、主板号** |
| `prodnv` | 10 MB | ⚠️ **产品 NV 数据，不要动** |

**完整列表**：用 `brom.py` 读分区表（0x2D 命令），会输出到 `partitions.txt`。

---

## 四、必须备份的 8 个分区

| 序号 | 分区 | 大小 | 验证魔数 | 说明 |
|---|---|---|---|---|
| 1 | `splloader` | 512 KB | `DHTB` | **救砖最要紧的** |
| 2 | `uboot_a` | 3 MB | `DHTB` | 二级引导 |
| 3 | `boot_a` | 64 MB | `ANDROID!` | 内核 |
| 4 | `dtbo_a` | 8 MB | `0xD7B7AB1E` | 设备树 |
| 5 | `vbmeta_a` | 1 MB | `AVB0` | 校验元数据 |
| 6 | `misc` | 1 MB | 全零 | 启动命令 |
| 7 | `miscdata` | 1 MB | 序列号字符串 | **锁状态** |
| 8 | `init_boot_a` | 8 MB | 全零 | 空分区，可跳过 |

**总计约 86.5 MB。**

**建议同时备份 `uboot_b`**（我们当初只备份了 `uboot_a`，恢复时用它写两个槽，可行但不严谨）。

---

## 五、备份命令

```bash
# 读分区表
python brom.py --wait 600 --quiet
→ partitions.txt (81 项)

# 逐个备份（读块用 32768，速度 0.67 MB/s）
python brom.py --wait 600 --quiet --blk 32768 --dump splloader
python brom.py --wait 600 --quiet --blk 32768 --dump uboot_a
python brom.py --wait 600 --quiet --blk 32768 --dump boot_a
python brom.py --wait 600 --quiet --blk 32768 --dump dtbo_a
python brom.py --wait 600 --quiet --blk 32768 --dump vbmeta_a
python brom.py --wait 600 --quiet --blk 32768 --dump misc
python brom.py --wait 600 --quiet --blk 32768 --dump miscdata
```

**每个分区一次 BROM 会话**（工具不支持一次 dump 多个）。

---

## 六、恢复命令（写回）

```bash
# 写单个分区（带校验）
python brom.py --wait 600 --quiet --write splloader=dump/splloader.bin --verify-write

# 一次写多个分区
python brom.py --wait 600 --quiet \
  --write splloader=dump/splloader.bin \
  --write uboot_a=dump/uboot_a.bin \
  --write uboot_b=dump/uboot_a.bin \
  --write misc=dump/misc.bin

# 急救：只写 splloader（最快，约 3 秒）
python brom.py --wait 600 --quiet --write splloader=dump/splloader.bin
```

⚠️ **注意**：我们备份的 `splloader.bin` 是 524288 字节（整分区），
但实际有效镜像只有 **66248 字节**，后面全是零。
写回时写 66248 字节即可（其余本来就是零）。

---

## 七、分场景恢复流程

### 场景 A：改了 splloader/uboot 后黑屏

```
1. 按住音量减+电源，插 USB，听到"叮"立即松手
2. 写回 splloader（若还不行再写 uboot）
3. 拔线，长按电源 10 秒，开机
```

### 场景 B：splloader 被擦除（最麻烦）

**症状**：设备连上后几秒就断开，任何操作都传不完。

**原因**：没有有效 SPL，BootROM 进入"自动下载模式"并周期性复位。

**解法**：用**自动重试脚本**——设备复位后会重新枚举，循环重连总能撞上完整窗口。

```batch
:loop
set /a i+=1
python brom.py --wait 90 --quiet --write splloader=splloader_orig.bin
if %ERRORLEVEL%==0 goto ok
if %i% lss 20 goto loop
```

**实测：第 2 次尝试成功。**

### 场景 C：vbmeta 被改坏（启动循环）

```
写回 vbmeta_a → 立即恢复（1 MB，几秒）
```

### 场景 D：完全不确定哪里坏了

```
按顺序写回：splloader → uboot_a → uboot_b → boot_a → vbmeta_a → misc
```

---

## 八、危险操作警告

| 操作 | 后果 |
|---|---|
| 改 `splloader` / `uboot` | **黑屏**（RSA 校验失败）——可救，但要 BROM |
| 改 `vbmeta` | 启动循环——可救 |
| 写 `miscdata` | **可能改变锁状态/序列号**——谨慎 |
| 写 `prodnv` | **可能丢 IMEI/基带校准**——**不要动** |
| 写 `super` | 系统损坏——可救但需完整备份 |
| 改分区表（GPT） | 可能无法启动——**风险最高** |

---

## 九、工具链（brom.py）关键参数速查

| 参数 | 说明 |
|---|---|
| `--wait N` | 等待设备 N 秒 |
| `--dump 名称` | 备份分区 |
| `--write 名称=文件` | 写分区（可重复） |
| `--verify-write` | 写完读回校验 |
| `--blk N` | 读块大小（默认 2112，**推荐 32768**） |
| `--dchunk N` | BROM 下载块（**必须 ≤528**） |
| `--dchunk2 N` | FDL 下载块（可更大） |
| `--run-spl` | 把 spl-unlock.bin 当 FDL1 执行 |
| `--quiet` | 精简输出 |

---

## 十、设备身份信息（供核对）

```
商品名    ：铂为 X16Pro（Weimi X16 Pro）
型号代码  ：20200808A1
序列号    ：49694698185900
芯片      ：展锐 T616（UMS9230）
存储      ：64 GB
分区数    ：81
内核      ：Linux 5.4.161
系统      ：Android 12，PRIZE 公版 ROM
```

---

## 十一、最后一句

> **这台设备的救砖能力，全部来自 BootROM。**
> **只要 BootROM 还能枚举成 `VID_1782 & PID_4D00`，它就还有救。**
>
> **备份在手，随便折腾；备份没了，就别折腾引导层。**

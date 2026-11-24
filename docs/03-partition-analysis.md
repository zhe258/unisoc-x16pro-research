# 03 · 分区表与容量造假

## 一、分区表格式

`READ_PARTITION (0x2D)` 返回的每一项：

```
[0:72]   分区名（72 字节，UTF-16LE，以 \0 结尾）
[72:76]  分区大小（4 字节小端，**单位 KB**）
```

**单位是 KB**，不是字节，也不是 4KB 扇区 —— 这是最容易算错的地方。

### 验证单位的办法

用标准分区的大小对照：

| 分区 | 标准大小 | 换算 |
|---|---|---|
| `misc` | 1 MB | `1024 KB` |
| `boot` | 64 MB | `65536 KB` |
| `cache` | 300 MB | `307200 KB` |
| `userdata` | 剩余全部 | `53212160 KB` ≈ 50.75 GB |

对上就说明单位是 KB。

---

## 二、容量计算

本机 81 个分区，合计：

```
61,068,288 KB
= 61,068,288 / 1024 / 1024 GiB
= 58.2 GiB
≈ 64 GB 标称容量
```

**而界面显示 256GB。**

### 为什么界面会撒谎

`statfs` / `StorageManager` 的返回值来自框架层，ROM 可以改。MTP 报告的容量同样来自这里。

**只有分区表是硬件级的。**

---

## 三、分区布局（节选）

| 分区 | 大小 | 说明 |
|---|---|---|
| `splloader` | 512 KB | 一级引导（**受 BootROM 校验**） |
| `uboot_a` / `_b` | 3 MB | 二级引导 |
| `boot_a` / `_b` | 64 MB | 内核 + ramdisk |
| `vendor_boot_a` | 64 MB | Android 12 的 vendor ramdisk |
| `dtbo_a` | 8 MB | 设备树覆盖 |
| `vbmeta_a` | 1 MB | AVB 校验元数据 |
| `init_boot_a` | 8 MB | **全零（空分区）** |
| `super` | 6.45 GB | 动态分区（system/vendor/product） |
| `userdata` | 50.75 GB | 用户数据 |
| `misc` | 1 MB | 启动命令 |
| `miscdata` | 1 MB | **锁状态、序列号** |

### 一个有意思的细节

`init_boot_a` 是 **8MB 全零**。

`init_boot` 是 Android 13 引入的分区（存放 GKI 的 init）。这台机器号称 Android 12，但分区表里预留了它却没用 —— 说明 ROM 是从更新的公版方案裁剪下来的。

---

## 四、Bootloader 锁状态在哪

**`miscdata` 偏移 `8192`，长度 64 字节：**

```
全 64 字节为零  →  锁定
非零数据        →  已解锁
```

本机实测：

```
miscdata[8192:8256] = 00 00 ... (64 个 0)
→ Bootloader 锁定
```

### miscdata 头部还包含

```
90PS49694698185900..........KS20885012108918............DOWNLOAD
```

- 序列号
- 主板编号
- 最后写入时的状态字（`DOWNLOAD` = 下载模式）

---

## 五、读取与验证

```bash
# 读分区表
python brom.py --wait 600 --quiet
→ partitions.txt（81 项）

# 备份（32K 块长最快）
python brom.py --wait 600 --quiet --dump vbmeta_a --blk 32768
```

### 用魔数验证镜像完整性

| 分区 | 魔数 |
|---|---|
| `boot` | `ANDROID!` |
| `splloader` / `uboot` | `DHTB` |
| `vbmeta` | `AVB0` |
| `dtbo` | `0xD7B7AB1E` |

读出来的文件头对得上，才说明传输没错。

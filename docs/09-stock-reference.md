# 09 · 原版参考数据（分区表 + 校验和）

> **本文件只含元数据，不含任何固件二进制。**
> 用途：让同一型号的用户可以核对「我这台是不是原版」，以及判断哪些分区被动过。

---

## 一、分区表（81 项，单位 KB）

读取方式：BROM 命令 `0x2D` READ_PARTITION

| # | 分区名 | 大小 KB | 大小 MB |
|---|---|---|---|
| 0 | `prodnv` | 10240 | 10.0 |
| 1 | `miscdata` | 1024 | 1.0 |
| 2 | `misc` | 1024 | 1.0 |
| 3 | `trustos_a` | 6144 | 6.0 |
| 4 | `trustos_b` | 6144 | 6.0 |
| 5 | `sml_a` | 1024 | 1.0 |
| 6 | `sml_b` | 1024 | 1.0 |
| 7 | `uboot_a` | 3072 | 3.0 |
| 8 | `uboot_b` | 3072 | 3.0 |
| 9 | `uboot_log` | 4096 | 4.0 |
| 10 | `logo` | 8192 | 8.0 |
| 11 | `fbootlogo` | 8192 | 8.0 |
| 12 | `logo2` | 8192 | 8.0 |
| 13 | `logo3` | 8192 | 8.0 |
| 14 | `logo4` | 8192 | 8.0 |
| 15 | `logo5` | 8192 | 8.0 |
| 16 | `logo6` | 8192 | 8.0 |
| 17 | `logo7` | 8192 | 8.0 |
| 18 | `logo8` | 8192 | 8.0 |
| 19 | `logo9` | 8192 | 8.0 |
| 20 | `logo10` | 8192 | 8.0 |
| 21 | `l_fixnv1_a` | 2048 | 2.0 |
| 22 | `l_fixnv2_a` | 2048 | 2.0 |
| 23 | `l_fixnv1_b` | 2048 | 2.0 |
| 24 | `l_fixnv2_b` | 2048 | 2.0 |
| 25 | `l_runtimenv1` | 2048 | 2.0 |
| 26 | `l_runtimenv2` | 2048 | 2.0 |
| 27 | `gnssmodem_a` | 1024 | 1.0 |
| 28 | `gnssmodem_b` | 1024 | 1.0 |
| 29 | `wcnmodem_a` | 10240 | 10.0 |
| 30 | `wcnmodem_b` | 10240 | 10.0 |
| 31 | `persist` | 2048 | 2.0 |
| 32 | `l_modem_a` | 25600 | 25.0 |
| 33 | `l_modem_b` | 25600 | 25.0 |
| 34 | `l_deltanv_a` | 1024 | 1.0 |
| 35 | `l_deltanv_b` | 1024 | 1.0 |
| 36 | `l_gdsp_a` | 10240 | 10.0 |
| 37 | `l_gdsp_b` | 10240 | 10.0 |
| 38 | `l_ldsp_a` | 20480 | 20.0 |
| 39 | `l_ldsp_b` | 20480 | 20.0 |
| 40 | `l_agdsp_a` | 6144 | 6.0 |
| 41 | `l_agdsp_b` | 6144 | 6.0 |
| 42 | `pm_sys_a` | 1024 | 1.0 |
| 43 | `pm_sys_b` | 1024 | 1.0 |
| 44 | `teecfg_a` | 1024 | 1.0 |
| 45 | `teecfg_b` | 1024 | 1.0 |
| 46 | `hypervsior_a` | 10240 | 10.0 |
| 47 | `hypervsior_b` | 10240 | 10.0 |
| 48 | `boot_a` | 65536 | 64.0 |
| 49 | `boot_b` | 65536 | 64.0 |
| 50 | `vendor_boot_a` | 102400 | 100.0 |
| 51 | `vendor_boot_b` | 102400 | 100.0 |
| 52 | `init_boot_a` | 8192 | 8.0 |
| 53 | `init_boot_b` | 8192 | 8.0 |
| 54 | `dtb_a` | 8192 | 8.0 |
| 55 | `dtb_b` | 8192 | 8.0 |
| 56 | `dtbo_a` | 8192 | 8.0 |
| 57 | `dtbo_b` | 8192 | 8.0 |
| 58 | `super` | 6758400 | 6600.0 |
| 59 | `cache` | 307200 | 300.0 |
| 60 | `vbmeta_a` | 1024 | 1.0 |
| 61 | `vbmeta_b` | 1024 | 1.0 |
| 62 | `metadata` | 16384 | 16.0 |
| 63 | `sysdumpdb` | 10240 | 10.0 |
| 64 | `vbmeta_system_a` | 1024 | 1.0 |
| 65 | `vbmeta_system_b` | 1024 | 1.0 |
| 66 | `vbmeta_vendor_a` | 1024 | 1.0 |
| 67 | `vbmeta_vendor_b` | 1024 | 1.0 |
| 68 | `vbmeta_system_ext_a` | 1024 | 1.0 |
| 69 | `vbmeta_system_ext_b` | 1024 | 1.0 |
| 70 | `vbmeta_product_a` | 1024 | 1.0 |
| 71 | `vbmeta_product_b` | 1024 | 1.0 |
| 72 | `vbmeta_odm_a` | 1024 | 1.0 |
| 73 | `vbmeta_odm_b` | 1024 | 1.0 |
| 74 | `avbmeta_rs_a` | 1024 | 1.0 |
| 75 | `avbmeta_rs_b` | 1024 | 1.0 |
| 76 | `common_rs1_a` | 8192 | 8.0 |
| 77 | `common_rs1_b` | 8192 | 8.0 |
| 78 | `common_rs2_a` | 16384 | 16.0 |
| 79 | `common_rs2_b` | 16384 | 16.0 |
| 80 | `userdata` | 53212160 | 51965.0 |

---

## 二、备份镜像的 SHA256

**用途**：dump 之后算一下，如果和这里一致，说明你的设备是原版、没被动过。

| 分区 | 大小 | SHA256 |
|---|---|---|
| `splloader` | 524288 B | `9a4128ab26704112954b40300d850c6f338c5535f99251047d214995c0c1feb3` |
| `uboot_a` | 3145728 B | `592674c0fae8b1dcb53673e5e36db79146f9c46ebd146b040b58614868bd905c` |
| `uboot_b` | 3145728 B | `592674c0fae8b1dcb53673e5e36db79146f9c46ebd146b040b58614868bd905c` |
| `boot_a` | 67108864 B | `0ec18d007dc246c890174f65db616932027467e022306b00d3dde7750ce970ee` |
| `dtbo_a` | 8388608 B | `80c2666d1afd685672f761d323daf635ef464a19f3ea2eb5a48612f42cf5e0a9` |
| `vbmeta_a` | 1048576 B | `63b414be298e93d9db166255588b89d93ba4e9931a976918e92f9526f90e5e80` |
| `misc` | 1048576 B | `7db67f82f318dc58a285dff1a025db0b638cf8bd8d7fe9eb198afb11e7dcc5e6` |
| `miscdata` | 1048576 B | `5cf78bc810f307ddb59f30a0f9bc45c801833aa41f2bbd260ab65c72c6ee2f51` |

### 说明

- `splloader` / `uboot_a` / `uboot_b` / `boot_a` / `dtbo_a` / `vbmeta_a` / `misc` 的校验和对应**原版状态**
- `miscdata` 的校验和对应**已写入解锁标记之后**的状态（64 字节锁标记已非零）
- `uboot_a` 与 `uboot_b` 校验和相同 → 两个槽内容一致

---

## 三、各分区的魔数（用于快速判断镜像类型）

| 分区 | 偏移 | 魔数 | 含义 |
|---|---|---|---|
| `splloader` | 0x00 | `DHTB` | 展锐签名镜像 |
| `uboot_a/b` | 0x00 | `DHTB` | 同上 |
| `boot_a` | 0x00 | `ANDROID!` | Android boot image |
| `vbmeta_a` | 0x00 | `AVB0` | AVB 元数据 |
| `dtbo_a` | 0x00 | `0xD7B7AB1E`（小端） | 设备树覆盖 |
| `misc` | — | 全零 | bootloader_message |
| `miscdata` | 0x2000 | 32+16+16 字节 | 锁状态区（全零=锁定） |

---

## 四、怎么用这份数据

### 判断设备是否原版

```bash
# 1. 备份你自己的 splloader
python brom.py --wait 600 --quiet --dump splloader

# 2. 算 SHA256
certutil -hashfile dump\splloader.bin SHA256

# 3. 和上表比对
#    一致   → 原版，可以放心折腾
#    不一致 → 已被修改过
```

### 判断锁状态

```bash
python brom.py --wait 600 --quiet --dump miscdata
# 然后看偏移 8192 开始的 64 字节：
#   全零   → 锁定
#   非零   → 已写入解锁标记
```

---

## 五、为什么不提供固件本体

| 原因 | 说明 |
|---|---|
| 版权 | splloader / uboot / boot 是厂商固件，不是本项目的产物 |
| 隐私 | `miscdata` 含设备序列号与主板信息 |
| 无用 | 固件只对同一台设备有意义，别人无法用于自己的设备 |

**需要固件的人，正确做法是从自己的设备上 dump**——
这份文档给了你分区表、大小和校验和，足够判断你 dump 得对不对。
# Bytelens — 本地二进制文件透视工作台

![tests](https://github.com/18971181532/bytelens/actions/workflows/test.yml/badge.svg)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![deps](https://img.shields.io/badge/dependencies-zero-success)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

Bytelens（**Byte** + **lens**）是一个**零依赖、纯 Python 标准库**的本地二进制文件分析工作台，
把 `hexdump`、`binwalk`、`ent`、`strings` 等命令行工具的核心能力浓缩进一个
深色 Canvas 交互式仪表盘。面向逆向工程、CTF、数字取证、文件格式排查与"这个文件到底是什么"
的日常调试。**所有分析都在你的机器上完成，不上传任何字节。**

## 它能做什么

- **魔数识别（magic）**：内置 40+ 种文件签名（PNG/JPEG/GIF/BMP/TIFF、ZIP/GZ/BZ2/XZ/7Z/RAR、
  ELF/PE/Mach-O/Java class/WASM、PDF/OLE/SQLite、MP4/MP3/OGG/FLAC/WAV、UTF BOM、shebang 等），
  并对无签名数据做文本启发式判定。
- **Shannon 熵**：整体熵（0–8 bits/byte）+ **滑动窗口块熵曲线**，一眼看出哪些区段是文本、
  压缩数据，还是加壳/加密（>7.3）。
- **字节频率直方图**：256 个字节值的计数，ASCII 可打印 / 空字节 / 高位字节 / 控制字符占比，
  以及地址×字节类别的二维热力图。
- **字符串提取**：ASCII 与 UTF-16LE 连续可打印串，带偏移、长度、编码，支持搜索过滤。
- **容器结构解析**：逐区域解析 PNG 数据块、JPEG 标记段、GIF 头/色表、ZIP 中央目录/本地头、
  WAV RIFF、ELF 32/64 头与节表、PE 头与 Section、PDF 对象/startxref，全部容错。
- **嵌入文件雕刻（carve）**：在任意偏移扫描嵌套的 PNG/JPEG/GIF/ZIP/GZ/PDF/ELF/PE，并估算
  嵌入文件的结束位置与大小——可用于发现 polyglot 文件、附加载荷和误改后缀的文件。
- **双文件比对**：4 KiB 块哈希 Jaccard 相似度、等大文件逐字节差异密度条、熵差、增删字符串。
- **暗色 Canvas 仪表盘**：Overview / Hex / Strings / Structure / Map / Compare 六个标签，
  含熵仪表、十六进制翻页、结构地址空间条、字节热力图、熵曲线与直方图，零构建、零前端依赖。

## 环境与依赖

- Python **3.9+**（标准库），**无任何第三方依赖**。
- 跨平台：Linux / macOS / Windows。

## 安装

```bash
git clone https://github.com/18971181532/bytelens.git
cd bytelens
pip install -e .
```

也可以不安装，直接用模块方式运行：

```bash
python -m bytelens --help
```

## 快速开始

```bash
# 生成示例文件（PNG / ZIP / 高熵 packed.bin / 含嵌入文件的 polyglot.bin）
python examples/make_examples.py

# 打开浏览器仪表盘（默认 http://127.0.0.1:8854）
bytelens serve examples/polyglot.bin

# 自定义端口
bytelens serve examples/packed.bin --port 9000
```

## 命令行用法

所有子命令都支持 `--json` 输出机器可读结果。

```bash
# 完整报告：魔数、熵、直方图、哈希、字符串、结构、嵌入文件
bytelens analyze examples/sample.png
bytelens analyze examples/sample.zip --json

# 分页十六进制（带 ASCII 列）
bytelens hex examples/packed.bin --offset 0 --length 256

# 字符串提取（支持子串过滤）
bytelens strings examples/polyglot.bin --search PNG

# 熵与滑动窗口熵（ASCII 条形图）
bytelens entropy examples/packed.bin --block 8192

# 容器内部结构（区域 + 起止偏移）
bytelens structures examples/sample.zip

# 两个二进制比对
bytelens compare examples/sample.png examples/sample.zip
```

### 示例输出

```
$ bytelens structures examples/sample.zip
ZIP archive: 5 region(s)
       468..       490  end of central directory
       355..       410  central: hello.txt 11 -> 13
         0..        52  local: hello.txt   deflate
       410..       468  central: data/num.bin 256 -> 261
        52..       355  local: data/num.bin deflate
```

```
$ bytelens analyze examples/polyglot.bin
File:       polyglot.bin (519 bytes)
Entropy:    2.9893  (text or structured code)
Strings:    7
Embedded:   2 candidate(s)
   @       222 png size=73 PNG image
   @       438 jpg size=70 JPEG (JFIF)
```

## 仪表盘标签

| 标签 | 内容 |
|------|------|
| **Overview** | 魔数/类型、文件大小、熵半圆仪表、字节构成条形、MD5/SHA1/SHA256/CRC32、嵌入文件标签。 |
| **Hex** | 按偏移分页的十六进制 + ASCII 视图，空字节/高位字节/可打印字节着色，可跳转偏移。 |
| **Strings** | ASCII/UTF-16 字符串表（偏移、编码、长度、内容），实时搜索与分页加载。 |
| **Structure** | 结构区域表 + Canvas 地址空间条，悬停查看每个区域的起止偏移与细节。 |
| **Map** | 字节类别热力图（地址→高半字节桶）、滑动窗口熵曲线（含 6.5/7.3 阈值线）、256 字节频率直方图。 |
| **Compare** | 输入第二个文件，展示块相似度环形图、熵差、字符串增删、逐字节差异密度条。 |

## 目录结构

```
bytelens/
├── bytelens/
│   ├── __init__.py
│   ├── __main__.py
│   ├── magic.py          # 签名表、识别、嵌入扫描
│   ├── reader.py         # 安全的分块/范围读取
│   ├── entropy.py        # Shannon 熵与滑动窗口块熵
│   ├── histogram.py      # 字节计数、构成、二维热力图
│   ├── strings.py        # ASCII / UTF-16LE 字符串提取
│   ├── structures.py     # PNG/JPEG/GIF/ZIP/WAV/ELF/PE/PDF 解析
│   ├── carve.py          # 嵌入文件雕刻与边界估算
│   ├── hexview.py        # 分页十六进制渲染
│   ├── report.py         # 汇总报告 + 哈希
│   ├── compare.py        # 块相似度 / 对齐差异 / 字符串 diff
│   ├── cli.py            # argparse 子命令
│   ├── server.py         # 本地 HTTP 服务 + JSON API
│   └── web/              # 零构建前端（原生 HTML/CSS/JS + Canvas）
│       ├── index.html
│       ├── style.css
│       └── app.js
├── tests/                # 标准库 unittest（含内存生成合法 PNG/ZIP/ELF/PE）
├── examples/             # 示例夹具生成器与说明
├── .github/workflows/test.yml
├── pyproject.toml
├── LICENSE
└── README.md
```

## 设计说明

- **纯标准库**：`struct`/`zlib`/`hashlib`/`zipfile` 完成容器解析与哈希，`http.server` 提供
  本地服务，无 ORM、无前端构建。
- **大文件友好**：超过 64 MiB（可调 `--max-bytes`）时只全量读取头部，避免一次性吃满内存。
- **解析容错**：容器解析器逐区域 try/except，被截断/损坏的文件返回已解析部分而非崩溃。
- **安全**：服务默认只绑定 `127.0.0.1`；静态资源带路径穿越防护，compare 接口仅接受真实文件。
- **高 DPI 适配**：Canvas 使用正确的六参 `setTransform(dpr,0,0,dpr,0,0)`，高分屏不糊不累乘。

## 运行测试

```bash
python -m unittest discover -s tests -v
```

CI 在 Ubuntu 与 Windows × Python 3.9/3.10/3.11/3.12 上安装、生成示例、跑全套测试与 CLI 冒烟。

## 许可证

[MIT](LICENSE) © 2026 遥か

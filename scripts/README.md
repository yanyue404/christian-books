# 脚本说明

两个脚本均只需 Python 3.9+ 标准库，在仓库根目录执行。电子书须符合命名规范：`《书名》- 作者.pdf` / `.epub`。

| 脚本 | 作用 |
|------|------|
| [list_books.py](list_books.py) | 扫描仓库，列出已收录电子书 |
| [gen_book_guide.py](gen_book_guide.py) | 查公开互联网资料，生成简介与目录 |

## list_books.py

扫描仓库根目录，输出符合命名规范的书单。

```powershell
# 纯文本（默认）
python scripts/list_books.py

# Markdown 表格，可粘贴到仓库 README
python scripts/list_books.py --format markdown

# JSON，给其他工具读
python scripts/list_books.py --format json

# 指定扫描目录
python scripts/list_books.py --root D:\books
```

`--format` 可选：`text`、`markdown`、`json`。

## gen_book_guide.py

先拉取公开资料，再交给 AI 整理成 `guides/*.md` 那种简介、目录、依据。来源不限维基，按可用性取用：

- 网页检索（DuckDuckGo），并抓取出版社 / CCEL / Archive 等书页正文
- [Internet Archive](https://archive.org)
- [Google Books](https://developers.google.com/books)
- [Open Library](https://openlibrary.org)
- 维基百科（书 / 作者条目）

AI 只转述已拉取的来源，不会编造章题。未设置 API Key，或加了 `--no-ai` 时，输出资料草稿。

```powershell
# 单本，打印到终端
python scripts/gen_book_guide.py --title 天路历程 --author 约翰·班扬

# 指定英文原名（提高维基命中率），写入 guides/
python scripts/gen_book_guide.py --title 魔鬼家书 --author "C.S.路易斯" --en-title "The Screwtape Letters" --write

# 扫描仓库电子书（自动跳过注释类）
python scripts/gen_book_guide.py --from-repo --write

# 只拉资料，不调用模型
python scripts/gen_book_guide.py --title 渴慕神 --author 陶恕 --no-ai

# 覆盖已有导读
python scripts/gen_book_guide.py --title 天路历程 --author 约翰·班扬 --write --force
```

`--write` 默认不覆盖已有文件，需要覆盖时加 `--force`。

| 参数 | 说明 |
|------|------|
| `--title` / `--author` | 中文书名（不要带书名号）和作者 |
| `--en-title` | 英文原名 |
| `--from-repo` | 扫描仓库中符合命名规范的书 |
| `--no-ai` | 只拉资料，不调用模型 |
| `--write` | 写入 `guides/<书名>.md` |
| `--force` | 覆盖已有导读 |

单本模式必须同时给 `--title` 和 `--author`，或改用 `--from-repo`。

## 环境变量

`list_books.py` 不需要。`gen_book_guide.py` 调用 AI 时需要 `OPENAI_API_KEY`；另外两个可选。

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | 调用 AI 时必填 | 接口密钥 |
| `OPENAI_BASE_URL` | 否 | 默认 `https://api.openai.com/v1`，可换成 DeepSeek 等兼容接口 |
| `OPENAI_MODEL` | 否 | 默认 `gpt-4o-mini` |

不要把密钥写进仓库或脚本。

### Windows PowerShell（当前窗口，关掉即失效）

```powershell
$env:OPENAI_API_KEY = "sk-你的密钥"
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"
$env:OPENAI_MODEL = "gpt-4o-mini"
```

DeepSeek 等兼容接口：

```powershell
$env:OPENAI_API_KEY = "sk-你的密钥"
$env:OPENAI_BASE_URL = "https://api.deepseek.com/v1"
$env:OPENAI_MODEL = "deepseek-chat"
```

设完后在**同一个窗口**运行脚本。

### Windows 长期保存（新开终端也有效）

```powershell
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-你的密钥", "User")
[System.Environment]::SetEnvironmentVariable("OPENAI_BASE_URL", "https://api.openai.com/v1", "User")
[System.Environment]::SetEnvironmentVariable("OPENAI_MODEL", "gpt-4o-mini", "User")
```

写入用户环境后须**新开一个终端**才会生效。

### 查看是否已设置

```powershell
echo $env:OPENAI_API_KEY
echo $env:OPENAI_BASE_URL
echo $env:OPENAI_MODEL
```

未设置 `OPENAI_API_KEY` 时，脚本会自动走维基草稿，不报错退出。

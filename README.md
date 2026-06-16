# 电商图片 Seedream 批量翻译

这个仓库只保留火山方舟 Seedream 生图方案，用于把中文电商图片生成俄文版本。

## 配置

复制 `.env.example` 为 `.env`，填入火山方舟 API Key：

```bash
ARK_API_KEY=your_volcengine_ark_api_key
```

`.env` 已被 Git 忽略，不要提交。

## 批量处理

处理单张图片或目录：

```bash
set -a; source .env; set +a
python3 ark_batch_localize.py "/path/to/images"
```

输出目录：

```text
ark-image-output/
└── YYYYMMDD-HHMMSS/
    ├── 原名-seedream-ad.jpg
    ├── 参数图-seedream-spec.jpg
    ├── report.json
    └── report.csv
```

输入为目录时会保留子目录结构。

## 自动路由

默认 `--prompt-mode auto`：

- 文件名包含 `参数图`、`参数`、`规格`、`尺寸`、`尺码`、`详情参数` 时，走 `spec` 参数图提示词。
- 其他图片走 `ad` 海报/广告图提示词。

手动指定模式：

```bash
python3 ark_batch_localize.py "/path/to/image.jpg" --prompt-mode ad
python3 ark_batch_localize.py "/path/to/参数图.jpg" --prompt-mode spec
```

## 单图处理

```bash
python3 ark_image_localize.py "/path/to/image.jpg" --prompt-mode ad
python3 ark_image_localize.py "/path/to/参数图.jpg" --prompt-mode spec
```

默认模型是：

```text
doubao-seedream-4-5-251128
```

## 审核

Seedream 会重绘图片，不能保证商品细节和文字 100% 准确。所有输出默认标记为
`review`，需要人工检查。

已知风险：

- 广告图整体效果较好，但可能改变商品、人物、背景和英文标题。
- 参数图能保留表格和尺寸，但仍可能出现俄文错字、乱码或参数错位。
- 不适合无人审核直接发布。

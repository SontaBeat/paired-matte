# 本地检查与导出

Python 3.10+，安装 Pillow。以下在 Skill 文件夹内运行，示例工作路径是相对路径，可替换为本次任务目录。

```bash
python3 scripts/process_assets.py source-info --source-image work/source.png
```

若有可信原生透明度：

```bash
python3 scripts/process_assets.py from-alpha --source-image work/source.png --background '#808080' --solid-out work/solid.png --mask-out work/alpha.png
```

普通图片生成配对 raw 文件后：

```bash
python3 scripts/process_assets.py normalize-mask --source-image work/source.png --mask-image work/alpha-raw.png --mask-out work/alpha.png
python3 scripts/process_assets.py alignment-overlay --source-image work/source.png --solid-image work/solid-raw.png --mask-image work/alpha.png --overlay-out work/alignment-overlay.png
```

**停在这里检查叠加图**。归一化按源图尺寸缩放；不能修复画面中的局部位移。对烟雾等弱 Alpha，可降低 `--mask-threshold` 检查更外侧边缘。默认端点截断为 8/247；极弱光效必要时使用 `--black-threshold 0 --white-threshold 255` 保留细微灰度，并重新检查背景噪声。不要提高阈值隐藏错误。

只有检查通过后再运行：

```bash
python3 scripts/process_assets.py finalize-solid --source-image work/source.png --solid-image work/solid-raw.png --mask-image work/alpha.png --background '#808080' --solid-out work/solid.png
python3 scripts/process_assets.py validate --source-image work/source.png --solid-image work/solid.png --mask-image work/alpha.png --background '#808080'
```

`finalize-solid` 只将零 Alpha 区域设为纯色，不清除半透明区域内部的底色误差。`validate` 的通过结果不能作为对齐或真实透光率证明。

打开 Skill 自带 `assets/cutout-tool.html`，导入配对素材、指定底色、选择预设、检查黑白底后下载透明结果。网页不支持无界面命令行导出；本仓库浏览器测试脚本用于演示重现，不是通用批处理接口。

辅助脚本默认拒绝覆盖输出，只有用户授权替换时使用 `--force`。发布前删除工作日志中的私人绝对路径、会话信息和签名下载地址。

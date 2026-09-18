# 白纱女剑士

![配对素材与黑白底结果](comparison.jpg)

尺寸：1024 × 1536。关注大面积半透明白纱、金线、头发与两把剑。

| 文件 | 用途 |
|---|---|
| [source.png](source.png) | 历史原图 |
| [solid.png](solid.png) | #808080 底配对彩色图 |
| [alpha.png](alpha.png) | 单通道灰度遮罩 |
| [cutout.png](cutout.png) | 网页导出的透明 PNG |
| [preview-black.png](preview-black.png) / [preview-white.png](preview-white.png) | 深色 #111111 / 纯白合成预览 |
| [settings.json](settings.json) | 网页参数 |
| [manifest.json](manifest.json) | 来源说明、尺寸、文件 SHA-256 |

使用“白纱 · 历史经验参数”：黑场 0.004，白场 0.992，反推 0.90，灰边清理 0.95，白纱中和 0.72。它会改变遮罩与颜色，不等于原始材质真实透明度。

缩略图可见主要纱带在深色背景上仍有内部纹理，白底上明显变淡；白底减弱对比不应误判为文件丢失。验收时仍需原尺寸检查剑尖、发梢和金线。

历史配对素材来自内置生图路线。案例整理时仅运行本地网页导出，不把它描述为网页版端到端实测。图片许可见 [素材说明](../ASSETS.md)。

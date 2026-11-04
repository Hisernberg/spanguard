<!-- CURRENT -->
## 当前状态（v6.0.0 — 提交包完成，2026-11-05）

**GitHub main = 91ec506**，tags v1.0.0–v6.0.0 全部在库（v2.0.0/v4.0.0 本轮补齐），
Release v6.0.0 已换上 2:54 新视频。本轮新增：
- **YouTube 成品包**（repo docs/yt-package/ + HF Nabidnur/spanguard-suite demo-video/ +
  download/yt-package/）：spanguard-demo-v6.mp4（2:54，8 场景，分块 TTS 避开 30s 上限，
  0.5s 对齐拼装，10fps）、.srt/.vtt（20 条 cue，按 chunk 边界）、thumbnail.png、
  youtube-upload.md（标题/带时间戳描述/标签/设置）。渲染链：scripts/video_render.py →
  video_tts_chunks.py → video_finalize.py → yt_metadata.py（限流时用 video_fix_pacing.py）。
- **CHANGELOG.md** v0→v6 全版本 + tag 索引；README 加了 video badge、chapters、
  CHANGELOG 链接。
- **docs/SUBMISSION.md**（表单全字段含评分题）、**docs/X_POST.md**（单帖+4帖线程）、
  **docs/LINKEDIN_POST.md**。
- **网站 v6 终版**：内嵌 <video> 播放器（assets 内置 mp4+海报）、版本阶梯表、roadmap
  已上线标记（B/F/judge ✅，新增 D 与 group-conformal 两项）、fm-v6 链接、team blackbox
  footer。Vercel 已 CLI 部署验证：站点 200，/assets/spanguard-demo-v6.mp4 200。
- 用户待办：YT 上传（用 yt-package 元数据 + SRT）、发 X 帖回填表单、贴 YouTube 链接。

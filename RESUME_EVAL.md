<!-- CURRENT -->
## 当前状态（v6.0.0 — 全部推送完成，2026-11-05）

**GitHub 已是最新**：main = c04ec77（README 世界级打磨 + 全部 v6 内容），tag v6.0.0，
Release https://github.com/Hisernberg/spanguard/releases/tag/v6.0.0 （notes + 视频附件
spanguard-demo-v6.mp4）。新 GH token 已入 .secrets/env（GH_TOKEN）。
- README：badges（39 tests / 9.1 rating / fm-v6+taskgate / vercel-live / video）、
  Contents 锚点、模型家族表加了 fm-v6 与 taskgate 两行、v6 表格全部真实数字
  （6 列：fm-v6 tasked/plain、fast-v4、fm-1、rules）、4 张 v6 图表内嵌、roadmap
  B/F/harness/judge 标 ✅ 并留 Taint-link(D) 与 group-conformal 两项未来工作、
  Self-rating 9.1、citation 作者改为 {Abrar, Nabid Nur}、视频提交至
  docs/assets/spanguard-demo-v6.mp4。
- 站点 https://spanguard.vercel.app 200（v6 内容 9 处 conformal）。注意：Vercel
  曾出现 Standard Protection 导致 404 —— 已关（ssoProtection null）并重新 CLI 部署
  （website/ 目录已 vercel link 到 spanguard 项目）。GitHub push 仍会自动部署。
- HF 全部 200：spanguard-fm-v6 / spanguard-taskgate / spanguard-suite（records +
  charts）。fm-1 GET 偶发 429（限流，仓库存在）。
- 一切在 download/：spanguard-v6.0.0.bundle（备份）、v6-final/（记录+图表+模型+notes）、
  spanguard_website_v6/、spanguard-demo-v6.mp4、SPANGUARD_RESUME.md。

## 当前状态（v6.0.0 SHIPPED — 2026-11-05）

**全部 8 项完成**（GH 推送除外——token 失效，交付 git bundle）：
- fm-v6 2.23M（CPU 重训，Kaggle token 已死）+ task-gate 292k 均在 data/models/ 且已传
  HF（spanguard-fm-v6 / spanguard-taskgate / spanguard-suite records）。
- mega-run v6-final-2021：extended-v6/attacks/v4 全 0.0% escape、extended-v6 良性
  over-strip 0.8%、α=0.1 保形界在自家分布成立（10.8%）、agent-traffic OOD 不迁移
  14-15%（如实发布）。agent-loop：fm-v6 utility 100% + hijack 1.3%（fast-v4 93.3%/8.7%）；
  AgentDojo canonical 80.6%→40.3%（gate 效果）。语义裁判 fm-v6 与 fast-v4 均 0/30。
- rating 9.1/10（docs/rating.md）、README v6 段落、4 张 v6 图表、网站
  spanguard.vercel.app 已是 v6 内容（GitHub 集成项目，推 bundle 后自动更新）。
- 视频 download/spanguard-demo-v6.mp4（TTS 旁白 5 幕，数字来自 summary）。
- bundle：download/spanguard-v6.0.0.bundle（a910a12 之后全部提交 + v6.0.0 tag）。
  推送方法见 download/v6-final/HOW_TO_PUSH.txt。
- 注意：沙箱换过一轮（旧 spanguard 目录/权重被清），本次全部从 GitHub a910a12 克隆重建；
  Kaggle 旧 token 已死（KAGGLE_API_TOKEN 丢失）——重训 kernel 需新凭据。

## 历史：v6 IN FLIGHT（2026-11-04 晚，被会话时限截断）

- **v6 代码与资产全部完成并已 push（main @ 5833c85+）**：
  - v6-F conformal 校准（src/spanguard/detect/conformal.py，分級 split-conformal，
    α 扫描 [0.05,0.10,0.25,0.50]，smallest-passing-alpha 选择）+ Guard(fm-v6) 模式
    （无校准文件时拒绝默认阈值，degraded 可见）。
  - v6-B task-gate 运行时（Guard(task=…) 不确定带二次判定）。
  - 规则加固（语义裁判驱动的自审计闭环）：句子感知 gap 类（修 [^.\n] 无法跨 .env/URL
    点号的系统性盲区）+ 句级剥离窗口 + v6 红队模式（directives/commands/policies、
    passive exfil、output-restrict、secret-paste 等）—— **v3 red-team 30/30 全剥离**。
  - 评测资产：extended-v6 500-doc（250/250，20 族，7 语言，与训练不相交）、
    notinject_benign 120、agentdojo-wrapped 72（真实 agentdojo v1.1.1 官方模板×goal；
    import-cycle workaround：先 `import agentdojo.task_suite.task_suite`）。
  - ONNX：fm.onnx（fp32）+ onnx_export_report.json 已传 HF spanguard-fm-1；
    **int8（dynamic+static）判定漂移且不提速 → 拒绝**（诚实记录）。
  - 视频渲染器 scripts/video_render.py（帧+TTS+ffmpeg，NUMBERS 表待填）。
  - 测试 39 绿 1 skip（权重缺失自动跳过）。
- **v6 模型已训成（Kaggle P100，kernel v5，7 分钟）**：
  - fm-large 3.47M（corpus-v4+v6-addendum 22k docs）：dev escape 0.17% / over-strip
    0% / doc F1 0.999。task-gate 292k：dev acc 69%（弱，如实报告）。
  - 权重在 /tmp/kv6-out/（会话结束即失）+ 已复制 download/v6-artifacts/。
  - **HF 上传被 429 挡住（Nabidnur/spanguard-fm-large / spanguard-taskgate 未建）**——
    续作第一步：从 download/v6-artifacts/ 上传这两个仓库。
- **Mega-run（scripts/v6_mega_run.sh → v6_calibration_and_eval.py）跑到 D 阶段**：
  已知结果（第一次完整 A/B + 第二次进度）：fm-large+conformal 在
  extended-v6/extended-attacks/extended-v4 **全 0 逃逸**、extended-v6 良性过剥
  0.8%、notinject 0-1.7%；α 扫描显示 held-out benign 最差 14-16%（agent-traffic
  OOD 偏移，保形界不迁移——如实报告）；**OOD 短板仍在**：handwritten escape
  22.6%（fm-v6）vs fast-v4 ~4%；agentdojo-wrapped escape 37.5%（fm-v6, α=0.5）
  —— router 栈仍是 OOD 旗舰；task-gate 在 shipped α 下 band 为空、无可测效果
  （如实报告）。C 阶段（run_eval 直调已修）、D（harness f-string 已修）、
  E（latency）—— **重跑 `bash scripts/v6_mega_run.sh` 即得全量 v6-final 记录 +
  /tmp/v6-summary.json**。
- 下一步顺序：① 上传两个 v6 模型仓库到 HF（429 恢复后）→ ② 重跑 mega-run →
  ③ 语义裁判全量（eval/semantic_judge.py --modes fm-v6,fast-v4）→ ④ v6 图表 →
  ⑤ README v6 + rating 重评 → ⑥ website v6 数字 + Vercel 重部署（token 已存）→
  ⑦ suite 仓库 v6 更新 → ⑧ 视频（NUMBERS 填入后 python scripts/video_render.py）。

## 历史：v5.0.0 FINALIZATION ROUND SHIPPED（2026-11-04）

- **收尾轮全部完成并上线**（main @ 1620958+）：
  - **测试 33/33 绿**：新增 tests/test_v4_routing.py（is_structured 载体分类、route_v4
    三级路由、扩展域门控 —— 锁死 v5 编排修复的行为）。
  - **诚实自评**：docs/rating.md（8.3/10 rubric，逐项证据 + 9.5+ 差距清单），
    README 有 Self-rating 章节。
  - **README 世界级升级**：徽章行（release/tests/rating/suite/website/Vercel Deploy
    按钮）+ TOC + Self-rating + Website 章节。
  - **黑客松网站已上线**: https://hisernberg.github.io/spanguard/（gh-pages @ 80a1c2c，
    根路径 = website/ 内容；自包含单页：hero/浏览器内规则引擎 live demo/实测表/4 图/
    家族表/诚实代价/路线图/60 秒 quickstart；无构建步骤，Apache-2.0）。
    Vercel 零配置：website/vercel.json + README 顶部 Deploy 按钮
    （vercel.com/new/clone?...root-directory=website）—— 用户点一下即可部署到自己的 Vercel。
  - **统一 HF 仓库**: https://huggingface.co/Nabidnur/spanguard-suite（68 文件：
    models/ 4 个 CPU 级模型权重 + eval/ 4 条 release 记录 + 7 个 fixture + charts/
    4 PNG + 全套 SVG + corpus/ 清单 + code/ 源码镜像 zip；世界级 suite card；
    fm-1 从 suite 下载后端到端验证通过）。
- **⚠️ 沙箱大文件清理器**（本轮重要发现）：/home/z 下 >1MB 的模型权重会在命令间隔
  被后台清除（data/models/ 两度被清空）。**恢复/使用模型必须单进程内完成**：
  snapshot_download → 用 → 上传，不落地 /home/z；权重唯一可靠副本在 HF 各仓库。
- Space（spanguard-demo）仍是 cpu-basic 配额 PAUSED；文件为 v5，配额恢复自动重建。

## 下一步（v6，按价值排序）
1. fm 过删轴：任务条件化剥离（B）/ conformal 阈值（F）—— fm 唯一输给 fast-v4 的轴。
2. SPG-FM-Large（3.4M/8 blocks）冲 handwritten OOD 10.4%→<8%（Kaggle ~20 分钟）。
3. 对抗自训练：red-team 逃逸回流 corpus-v5。
4. ONNX int8 量化 fm：36.7ms→<5ms，让免费层 Space 可交互。
5. **最终视频**（用户明确要求，后续版本后录制）：脚本 docs/demo-video-script.md。
6. NotInject + AgentDojo 列。评分 9.5+ 差距清单见 docs/rating.md。

## 历史：v5.0.0 SHIPPED（2026-11-04 早）

- **v5.0.0 全部完成并发布**：GitHub main @ 865ba00 + release
  https://github.com/Hisernberg/spanguard/releases/tag/v5.0.0（新 PAT 生效，push 恢复）。
- **SPG-FM-1 已发布 HF**: https://huggingface.co/Nabidnur/spanguard-fm-1（实测表 model card）。
  Kaggle P100 kernel 训成（kragglenote2forwork/spanguard-fm-v5，~12k docs/min），
  数据集 kragglenote2forwork/spanguard-fm-train。
- **发布运行记录**：eval/results/v5-ship-1548（判据全过：fm 域内全 0% + 7 语言 0% +
  span F1 0.917/0.901；fast-v4 修复后 handwritten 4.2%（史上最佳）、全家族 0%）。
  中间态已留档：v5-fm-1504 / v5-check-1514 / v5-final-1519（可审计）。
- **编排修复**（本会话核心发现）：is_structured 重建（k=v 任意位置/紧凑CSV/tab）；
  fast-v4 union-everywhere 恢复（v4.0.0 原设计）；fm doc-head prose 门控（≥0.5→union）。
- **Space**（Nabidnur/spanguard-demo）：v5 文件已上传（Dockerfile 预拉 4 模型 +
  SPANGUARD_MODE=fast-v4 + fm 一键切换；README/index.html v5 文案）；账号 cpu-basic
  配额耗尽（403）仍 PAUSED —— 配额恢复后自动用新 Dockerfile 重建，无需改代码。
- 图表：docs/assets/v5_{flagship_bars,frontier,languages,cost}.png（脚本
  scripts/make_charts_v5.py，每个数字过账 committed records）。

## 下一步（v6 候选，按价值排序）
1. **fm 过删轴（最高价值）**：任务条件化剥离（roadmap B，cross-encoder）或 conformal
   阈值（roadmap F）—— 直击 fm 的 public 45.4%/handwritten 26.4% 过删；这是 fm 当前
   唯一败给 fast-v4 的轴。
2. SPG-FM-Large（3.4M/8 blocks，Kaggle 20 分钟）：冲 handwritten 10.4%→<8%。
3. 对抗自训练：red-team 逃逸回流 corpus-v5（adaptive loop 已有基础设施）。
4. ONNX int8 量化 fm：36.7ms→<5ms（Space cpu-basic 可跑交互 demo）。
5. **最终视频（用户明确要求，后续版本后做）**：3 分钟 demo 脚本在
   docs/demo-video-script.md —— v6 收尾时按脚本录制并挂 README。
6. NotInject + AgentDojo 列（roadmap）：替换 benign-only deepset 探针。


## 历史：v5 收尾轮开始时（2026-11-04 早）
- 沙箱二次回收：旧 spanguard/ 目录被 root 锁死（无 sudo）→ 工作树从 HF 镜像
  Nabidnur/spanguard-code-mirror（spanguard-head.zip）回填 + 新 PAT push 恢复。
- SPG-FM v5 训练在旧沙箱中断 → 本轮用 Kaggle GPU kernel 重训完成（见上）。


# SpanGuard — v3.0.0 shipped (2026-11-03 ~04:00 UTC)

## DONE & PUSHED (main) — release v3.0.0 published
- External-review hardening: teacher truth ($3.91 ran once, union==planted), real latency
  numbers, Wilson CIs, SPEC fixes (135M/21 tests/18 rules/PG2-gated-403), public-deepset
  reframed as benign-only over-strip probe, 2026 positioning table + roadmap.
- Engineering: tool-def scanning + rug-pull pins (C), typed markers (G), honest /healthz
  degradation, async httpx, Bearer default, /guard auth, build_public verify shim,
  ruff 0 errors, 21 tests green.
- Corpus v3 (MCP poisoning/skill files/buried multi-hop/md-image exfil/polite SE/+bn,
  14k docs, 16 families) → char-v3 trained + published (extended-domain 0.4% escape /
  spanF1 0.996 vs char-v2 11.6%/0.467; old-OOD regression 4.2→12.5% published).
- v2-model (135M boundary-weighted) published; public over-strip 34.2→18.1.
- Adaptive red-team: 25 mutations / 0 escapes / 30 attempts, record committed.
- Release: https://github.com/Hisernberg/spanguard/releases/tag/v3.0.0

## Remaining (if a next round happens)
1. fast-v2 ensemble with char-v3 (per-domain routing claim is roadmap, not built).
2. PromptGuard 2 head-to-head needs license acceptance on HF web UI (403 today).
3. NotInject + AgentDojo-embedded standard columns (roadmap in README).
4. Demo Space precomputed outputs still use plain [stripped] markers — rebuild
   scripts/build_demo.py run would refresh them.
5. Review claimed "span P/R 0.46 for fast" — visible in records; a span-metrics chart
   could make that first-class.

## Tokens: /home/z/my-project/.secrets/env (GH / KAGGLE / HF). Kaggle CLI 2.2.5 quirks:
kernel metadata key is `dataset_sources`; uploads need KAGGLE_API_TOKEN env.

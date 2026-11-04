<!-- CURRENT -->
## 当前状态（v5.0.0 SHIPPED，2026-11-04）

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

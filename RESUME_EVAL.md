<!-- CURRENT -->
## 当前状态（v5 收尾轮，2026-11-04）

- 沙箱二次回收：旧 spanguard/ 目录被 root 锁死（无 sudo）→ 已放弃，工作目录为 **/home/z/my-project/spanguard-work**（全新 clone + 本会话重放全部补丁）。
- v4.0.0 全部重建完成：记录从 download/ 回填，图表/README/demo 重做（e196939）。
- **GitHub push 不可用**（token 401）→ 代码快照镜像在 HF dataset: Nabidnur/spanguard-code-mirror（spanguard-head.zip，随每个里程碑更新）。
- **HF Space（Nabidnur/spanguard-demo）**：static SDK 已上线（index.html = v4 视觉 demo，真实 fast-v4 运行）；交互 gradio 版（app.py + spanguard/ 包 + requirements）已上传进 Space 仓库，因账号 cpu-basic 配额 limit=0（403）处于 PAUSED —— 配额恢复后把 Space README 的 sdk 改回 gradio 即可。
- **SPG-FM v5 训练中**（training/train_fm.py，1.70M params，corpus-v4 16k x 2 epochs；本轮结束时 ep1 step2200/3202，eta ~39min，loss 已收敛 ~0.0000）。
  每 500 步 checkpoint（data/models/spanguard-fm-1/checkpoint.pt + download/spanguard-fm-checkpoints/ 镜像），重跑同命令自动续训。

## 下一步（v5 收尾清单）
1. 先 ls data/models/spanguard-fm-1/calibration.json：存在→训练已完成，直接进第 3 步基准。不存在→重跑 `python3 training/train_fm.py --epochs 2 --batch 10 --out data/models/spanguard-fm-1`（自动从 step2000 checkpoint 续训，约 8 分钟跑完 + 校准）。
2. 校准确认 + fm 冒烟：SPANGUARD_FM_MODEL=data/models/spanguard-fm-1，Guard(mode="fm") 三例。
3. v5 基准：`python3 -m spanguard.eval.cli --detectors spg-fm,spanguard-fast-v4 --sets handwritten,agent-traffic,public-deepset,extended-attacks,extended-v4 --tag v5-fm`
   （spg-fm/char-v4 分支、SET_FILES extended-v4 已在 cli）。判据：spg-fm 5 集 0% 逃逸且 handwritten <16.7% 且 public-deepset 过删 <19.8% → 域内新最佳单模型。
4. python3 scripts/render_v5_charts.py（v5-frontier light/dark）→ README v5 小节填实测 + demo 加 fm 卡（可选）。
5. bash scripts/hf_push_fm.sh（需先在新 clone 重建该脚本）→ 发布 Nabidnur/spanguard-fm-1。
6. 版本 5.0.0（src/spanguard/__init__.py + pyproject.toml）+ RELEASE_NOTES + 更新代码镜像 zip + git commit。
7. download/ 交付（v5 报告 + 记录 + 图）+ 更新 RESUME。
8. v6 候选（roadmap）：(a) SPG-FM-Large 3.4M/8 blocks 冲 handwritten 16.7%→<10%；(b) 对抗自训练（red-team 逃逸回流 corpus-v5）；
   (c) ONNX int8 量化 fm → <1ms；(d) 任务条件化剥离（roadmap B）+ conformal 阈值（roadmap F）。


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

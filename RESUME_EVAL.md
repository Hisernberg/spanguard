# SpanGuard — status (2026-11-03 ~02:10 UTC)

## DONE & PUSHED (main @ latest)
- **135M v2 模型已训练完成并抢救到本地**：Kaggle kernel spanguard-train-v2 v5 COMPLETE
  (12k docs corpus-v2, 4 epochs, boundary-weighted CE x3, GPU 16.8 min)。
  DEV span P/R/F1 = **1.0/1.0/1.0** (256/0/0)。权重在 data/models/spanguard-span-mdistil-v2/
  (539MB safetensors + config + fast tokenizer + training_meta.json)，加载冒烟通过。
- fast-v2 互证 ensemble + char 模型 + 全部文档/图表/hero 切换 —— 已发布已推送（见 git log）。
- char: handwritten escape **4.2%** 全场最低；fast-v2: 10.4/14.0 handwritten, 0/32.9 public。
- Kaggle CLI 2.2.5 两个坑已记录：metadata 键改名 dataset_sources（旧键静默丢挂载）；
  上传需 KAGGLE_API_TOKEN env（kaggle.json 只能读）。

## 未完成（下轮从这里继续，全部命令就绪）
1. **v2-model 三集基准在跑**（nohup /tmp/v2bench.log, tag v2-model, ~10 min 总长；handwritten+
   agent 已跑完，public 收尾）。若 record 未落盘则重跑：
   `SPANGUARD_MODEL=$PWD/data/models/spanguard-span-mdistil-v2 python3 -m spanguard.eval.cli
   --detectors spanguard-fast-mdistil-v2 --sets handwritten,agent-traffic,public-deepset --tag v2-model`
2. **HF 发布 v2 模型**：`bash scripts/hf_push_v2.sh`（脚本已备好，会带 model card + training_meta）。
3. `python3 -m spanguard.eval.report` 重渲染（新系统 spanguard-fast-mdistil-v2 已注册 config），
   按结果更新 README/answers 的 v2-model 数字。
4. **release v1.1.0**（gh release create v1.1.0，notes 覆盖 char+fast-v2+corpus-v2+v2 model）。
5. download/ 最终同步 + bundle。

## Tokens（.secrets/env）：GH、KAGGLE KGAT_8971...（无尾点！）、HF。沙箱回收即用 restart 流程。

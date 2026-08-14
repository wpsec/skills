# to-spec

> 来源: [mattpocock/skills - to-spec](https://github.com/mattpocock/skills/tree/main/skills/engineering/to-spec)

## 作用

把当前对话和代码库理解收敛成一份 spec,不额外采访用户,直接做结构化沉淀。

## 适用时机

- 需求、边界、关键决策已经在对话里讲清
- 准备把方案沉淀成正式规格,再交给后续实现或拆票
- 希望把测试 seam、实现决策、范围边界一次整理完整

## 上游约束

- 默认依赖已配置好的 issue tracker 和 triage label vocabulary
- 如果 issue tracker 集成尚未接通,可先把输出作为本地 spec 草案使用
- 该 skill 会先理解代码库现状,再整理 spec,不会重新做 grilling

## 常见链路

`grill-me` -> `to-spec` -> `to-tickets`

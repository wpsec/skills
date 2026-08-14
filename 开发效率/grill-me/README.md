# grill-me

> 来源: [mattpocock/skills - grill-me](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me)

## 作用

对一个方案、设计或实现思路做连续追问,沿决策树逐层收敛到共享理解。

## 适用时机

- 需求还模糊,但已经有初步方向
- 想在写 spec 前先暴露隐含假设、依赖和边界
- 想对一个实现方案做压力测试,提前发现遗漏决策

## 上游约束

- 一次只问一个问题
- 每个问题都要给出推荐答案
- 能从代码库或现有上下文得到答案的问题,先看代码,不要先问人

## 常见链路

`grill-me` -> `to-spec` -> `to-tickets`

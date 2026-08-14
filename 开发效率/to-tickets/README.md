# to-tickets

> 来源: [mattpocock/skills - to-tickets](https://github.com/mattpocock/skills/tree/main/skills/engineering/to-tickets)

## 作用

把 plan、spec 或当前对话拆成 tracer-bullet tickets,每张票都声明自己的 blocking edges。

## 适用时机

- spec 已经确定,准备进入执行阶段
- 需要把一个功能拆成可独立验证的 vertical slices
- 需要明确 prefactoring 顺序、依赖关系和可并行边界

## 上游约束

- 默认依赖已配置好的 issue tracker 和 triage label vocabulary
- 如果没有真实 issue tracker,可按 skill 说明落到本地 issue files
- 拆票时优先 vertical slice,只有 wide refactor 才走 expand-contract 例外路径

## 常见链路

`grill-me` -> `to-spec` -> `to-tickets`

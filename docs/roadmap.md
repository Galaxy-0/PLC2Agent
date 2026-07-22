# 实施路线图

## 当前策略

PLC2Agent 当前是用于学习和评估 AI Coding Agent 参与 PLC 工程流程的实验仓库，
不是待自研的通用 PLC 平台。

路线图遵循三条约束：

1. 优先复用 IronPLC、STruC++、OpenPLC、CODESYS 和现有 Plant Simulator；
2. 先证明 Agent 能完成设计、诊断、修复、运行和验收闭环；
3. 只有现成工具缺少稳定的机器接口时，才实现最薄的 Adapter。

长期架构中的 IR、统一工具层和内建 Plant 都是可选演进方向，不是开始下一阶段的
前置条件。

## 总成功标准

```text
自然语言需求
→ Agent 创建或修改 ST
→ 真实编译器返回诊断
→ Agent 修复编译或行为缺陷
→ Runtime 执行
→ Plant 产生物理/离散反馈
→ Verifier 检查场景和不变量
→ Agent 重跑
→ 输出可审计证据
```

主链路不得依赖 GUI；GUI 和 2D/3D 场景只用于人类观察或提供被控对象。

## M0：开源工具与单机闭环基线

状态：已完成。

- [x] IronPLC 官方 Quick Start；
- [x] `ironplcc` 与 `ironplcvm` 基线；
- [x] ACC Conveyor + Modbus 闭环；
- [x] STruC++ 编译和原生 ST Runtime；
- [x] 正转、反转、停止和真实传感器反馈；
- [x] 急停锁存、安全复位和禁止自动重启 ST 测试。

退出证据：`labs/00-*`、`labs/01-*` 和 `labs/02-*` 可重复运行。

## M1：Agent 诊断修复闭环

状态：下一阶段。

- [ ] 从一份最小自然语言需求开始；
- [ ] 修复至少一个真实 ST 编译错误；
- [ ] 修复至少一个可编译但测试失败的安全行为错误；
- [ ] 保存原始诊断、失败断言、修复 diff 和重跑结果；
- [ ] 记录编译器版本、源文件哈希和最终 Runtime 轨迹；
- [ ] 全流程不依赖 PLC GUI。

退出条件：Agent 独立完成一次
`compile -> diagnose -> repair -> compile -> test -> run -> evidence`，且证据可机械检查。

## M2：自动化单元 Plant v0.1

仿真等级：单元级。

- [ ] 实现或接入 2～5 段输送带；
- [ ] 支持 A/B 箱体、缓存、分流和推杆；
- [ ] 约 20～40 个 I/O；
- [ ] 支持至少 10 个物料连续运行；
- [ ] 支持急停、堵塞、传感器卡死、执行器卡死和通信中断；
- [ ] 支持 reset/step/run/snapshot 和结构化 Trace；
- [ ] 相同种子产生相同 Trace；
- [ ] 自动检查互锁、响应时间和禁止自动重启。

退出条件：现有 `specs/plant.yaml` 双输送带分拣单元的正常和核心故障场景自动通过。

## M3：完整 SoftPLC 与产线级闭环

仿真等级：产线级。

- [ ] OpenPLC Runtime v4 或等价 SoftPLC Adapter；
- [ ] Runtime 直接连接 Plant Adapter；
- [ ] deploy/start/stop/status/trace；
- [ ] 证明实际加载构建哈希；
- [ ] 多工位与约 100～300 个 I/O；
- [ ] 配方、换型、报警、区域安全和工位握手；
- [ ] 需求、状态、转换、报警和故障覆盖；
- [ ] 生成自动 FAT 报告。

退出条件：Agent 能发现一个跨工位时序或联锁缺陷，修复后重跑全部核心场景，
并输出需求到 Trace 的完整证据链。

## M4：多 PLC 小型工厂离散仿真

仿真等级：小型工厂级。

- [ ] 5～10 个自动化单元；
- [ ] 多 PLC 或多控制任务；
- [ ] 多产线共享物流、缓存和设备资源；
- [ ] 网络延迟、掉线、恢复和控制器重启；
- [ ] 跨 PLC 握手和区域故障隔离；
- [ ] 批次、班次与基本生产统计；
- [ ] Agent 变更影响分析和回归选择。

退出条件：局部故障不会产生未受控的跨区域动作，多控制器协同和恢复可被自动验收。

## M5：外部高精度 Plant Adapter

仿真等级：高精度数字孪生与专业工艺仿真接入。

- [ ] 定义稳定的 Canonical Plant Contract；
- [ ] 接入至少一个外部三维或物理模拟器；
- [ ] 声明时间、同步、确定性、快照和故障能力；
- [ ] 同一份 PLC I/O 契约可切换内建与外部 Plant；
- [ ] 外部运行结果归一化为结构化 Trace；
- [ ] 专业工艺模型留在专业工具内，不复制进 PLC2Agent。

退出条件：外部高精度场景仍可被 Agent 无 GUI 地运行、读取、比较和验收。

## 并行对照路线

以下工作用于验证可移植性，不阻塞主线：

- CODESYS Control + MCP 对照实验；
- IronPLC、STruC++ 与 OpenPLC ST 兼容性；
- OPC UA 和 Modbus Adapter；
- Factory-style 三维场景；
- HIL 与隔离远程 I/O；
- Siemens/TIA 工程导出与诊断映射。

## 仿真边界

复杂度分级、Plant Adapter 契约和防止领域漂移的规则见
[仿真复杂度、阶段目标与边界](architecture/simulation-scope.md)。

PLC2Agent 可以扩展到产线和小型工厂的离散控制仿真，但不自研通用机器人动力学、
流体、热力、电网暂态或 CNC 物理求解器。这些能力通过外部 Plant Adapter 接入，
核心仍是 PLC 控制、时序、安全、诊断和 FAT。

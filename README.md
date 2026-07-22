# PLC2Agent

PLC2Agent 是一个面向 AI Agent 的自动化工程工作台。它的目标不是让 Agent 模仿人类点击传统 PLC IDE，而是让 Agent 通过稳定、结构化、可测试的接口完成：

```text
需求理解 → I/O 设计 → 控制模型 → PLC 代码 → 编译部署
        → 被控对象仿真 → 故障注入 → 轨迹分析 → FAT 验收
```

## 为什么要做

传统 PLC 工具通常以 GUI 为事实来源，工程文件和自动化接口只是附属能力。这对人类工程师有效，但对 Agent 存在明显问题：

- 编辑器状态、磁盘状态和 Runtime 状态可能不一致；
- 关键操作依赖设备树、表格、弹窗和厂商私有格式；
- 编译、下载、在线监控和错误日志缺少统一结构；
- 三维仿真适合肉眼观察，却不适合批量测试、故障注入与机器判定；
- Agent 很难证明程序满足时序、安全和异常恢复要求。

长期架构将使用统一 PLC IR 协调 ST、LD、I/O 表、Runtime、Plant 和 FAT 证据；
但当前实验阶段不先实现通用 IR。现阶段以每个 Lab 的 ST、I/O 契约、测试和 Trace
为事实来源，先用现有开源工具证明 Agent 闭环，再从真实 Adapter 需求中提炼公共语义。

## 核心架构

```text
                         +--------------------------+
                         |       Human / Agent      |
                         +------------+-------------+
                                      |
                                      v
                         +--------------------------+
                         |   Natural-language Req.  |
                         +------------+-------------+
                                      |
                                      v
                         +--------------------------+
                         |     PLC Design Agent     |
                         +------------+-------------+
                                      |
                                      v
             +------------------------------------------------+
             |             Agent-native PLC IR                |
             |                                                |
             | requirements / I/O / control / plant / tests  |
             +------+----------------+----------------+--------+
                    |                |                |
                    v                v                v
             +-------------+  +---------------+  +------------+
             |  Compiler   |  | Plant         |  | Scenarios  |
             | ST / config |  | Simulator     |  | Invariants |
             +------+------+  +-------+-------+  +------+-----+
                    |                 ^                 |
                    v                 |                 v
             +-------------+          |          +-------------+
             | Runtime     |          +--------->|  Verifier   |
             | Adapter     |<------------------->| Trace / FAT |
             +------+------+                     +-------------+
                    |                                   |
                    v                                   v
       +---------------------------+          +------------------+
       | OpenPLC / CODESYS /       |          | Diagnostics and  |
       | vendor PLC                |          | FAT Report       |
       +---------------------------+          +---------+--------+
                                                        |
                                                        v
                                               PLC Design Agent

             +------------------------------------------------+
             | Web UI / LD View / State View / Trace View    |
             | Human-facing projections; not source of truth |
             +-----------------------+------------------------+
                                     |
                                     +------> PLC IR
```

## 仓库结构

```text
PLC2Agent/
├── docs/                 产品、架构、决策、路线图和历史资料
├── specs/                Agent 可读写的工程事实来源与验收场景
├── compiler/             校验、代码生成和构建产物生成
├── runtime/              Runtime 生命周期与 OpenPLC 适配器
├── simulator/            确定性被控对象模拟器
├── verifier/             场景执行、属性检查、轨迹分析和 FAT 报告
├── web/                  人类可视化投影，不作为事实来源
├── adapters/             CODESYS、Siemens、Factory I/O 等外围适配器
├── labs/                 已运行、可复现的开源工具与闭环实验
├── examples/             示例和历史实验工程
└── artifacts/            生成物、报告、轨迹及保留的实验备份
```

## 当前阶段

当前阶段先复用成熟开源组件熟悉并跑通全链路，不启动通用 PLC IR、编译器或
大型模拟器的原创开发。上面的架构图是长期方向，不代表这些模块已经实现。

目前已完成三条可复现实验：

1. IronPLC 官方 CLI 编译与 Runtime Quick Start；
2. ACC 浏览器 3D 场景、Modbus Bridge 与轻量 Node 扫描控制器闭环；
3. 官方 STruC++ 编译执行 IEC 61131-3 ST，Node 仅搬运 I/O 的 ACC 闭环。

ST 中现已包含急停锁存、安全复位与禁止自动重启测试。下一步是完成 Agent
编译诊断修复实验，并为急停/Reset 增加实体模拟 I/O，再评估把执行层替换成
完整的 OpenPLC Runtime v4。具体状态以 [TODO](TODO.md) 为准。

## 仿真扩展边界

仿真复杂度按以下阶段扩展：

```text
单机级
  -> 自动化单元级
  -> 产线级
  -> 小型工厂离散仿真
  -> 外部高精度 Plant Adapter
  -> 专业工艺仿真 Adapter
```

内建模拟器主要覆盖 PLC 关心的设备状态、物料流、扫描周期、顺控、联锁、报警、
故障和恢复。机器人动力学、液压、热力、流体和其他专业物理模型由外部模拟器负责，
通过 Plant Adapter 接入。本仓库不扩展成通用物理仿真平台。

完整阶段目标见
[仿真复杂度、阶段目标与边界](docs/architecture/simulation-scope.md)。

## 阅读顺序

1. [产品愿景](docs/vision/agent-native-plc.md)
2. [系统架构](docs/architecture/system-architecture.md)
3. [PLC IR](docs/architecture/plc-ir.md)
4. [Agent 工具接口](docs/architecture/tool-api.md)
5. [仿真与验证](docs/architecture/simulator-and-verification.md)
6. [仿真复杂度与边界](docs/architecture/simulation-scope.md)
7. [实施路线图](docs/roadmap.md)
8. [首个工程规范](specs/README.md)

## 历史实验

- [IronPLC 官方 Quick Start](labs/00-ironplc-smoke/)
- [ACC + Node Modbus 闭环](labs/01-acc-conveyor-closed-loop/)
- [STruC++ ST Runtime + ACC 闭环](labs/02-strucpp-acc-closed-loop/)

- [OpenPLC + Factory I/O 实验工程](examples/legacy-openplc-demo/)
- [旧版 Factory I/O 学习 TODO](docs/legacy/factoryio-learning-todo.md)

这些内容作为兼容性研究和需求素材保留，不再代表项目主架构。

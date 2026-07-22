# TODO

## 当前目标

PLC2Agent 当前不是一个待自研的通用 PLC Agent 平台，而是一个用于学习和评估 AI Coding Agent 参与 PLC 工程流程的实验仓库。

第一阶段优先复用 IronPLC、CODESYS MCP、OpenPLC 等现有项目，跑通：

```text
自然语言需求
→ Codex 创建或修改 Structured Text
→ 调用真实编译器
→ 读取结构化诊断
→ 修复并重新编译
→ 在 SoftPLC Runtime 中运行
→ 读取变量和运行结果
→ 用自动断言验证行为
```

只有在现有工具明确缺失时，才实现最薄的适配层。

## 当前成功标准

- [ ] Codex 能读取一个最小控制需求；
- [x] Codex 能创建或修改 ST；
- [x] 能调用真实 PLC 编译器并取得诊断；
- [ ] Codex 能根据编译错误完成至少一次修复；
- [ ] 程序能在 SoftPLC 上运行；
- [x] 能通过变量变化和自动断言证明控制行为正确。

## 实验路线

### Lab 0：IronPLC 官方基线

- [x] 在 Apple Silicon Mac 上安装 IronPLC；
- [x] 运行官方 Quick Start；
- [x] 验证 `ironplcc` 编译器；
- [x] 验证 `ironplcvm` Runtime；
- [x] 保存版本、命令、输出和已知限制。

退出条件：官方示例可以编译、运行，并观察到文档所述结果。

### Lab 1：Codex 编译修复闭环

- [x] 检查 IronPLC MCP Server 暴露的实际工具；
- [ ] 将 IronPLC MCP 接入 Codex；
- [ ] 让 Codex 编译一个包含明确错误的 ST；
- [ ] 读取诊断、修改代码并重新编译；
- [ ] 保存修复前后 diff 和编译证据。

退出条件：Codex 完成一次真实的 `compile → diagnose → repair → compile` 循环。

### Lab 2：最小传送带控制

- [x] 用 Mac 浏览器原生 ACC 场景跑通 Modbus 传感器/执行器闭环；
- [x] 保存零第三方依赖的 Modbus TCP 扫描控制器；
- [x] 用官方 STruC++ 编译并执行真正的 IEC 61131-3 ST；
- [x] 将 JavaScript 限定为 Modbus/Runtime I/O 搬运层；
- [x] 定义 `EmergencyStopHealthy`、`Reset` 和 `FaultLatched`；
- [x] 实现急停锁存、安全复位和禁止自动重启逻辑；
- [x] 增加正常运行场景；
- [x] 增加急停、恢复回路、复位和禁止自动重启 ST 测试场景；
- [ ] 为 ACC 或远程 I/O 增加实体急停与 Reset 点位；
- [x] 用 ST 单元测试、变量轨迹和真实 3D 反馈验证行为。

退出条件：程序可以运行，并且正常与急停场景自动通过。

### Lab 3：CODESYS MCP 对照实验

- [ ] 准备 Windows + CODESYS SP22 + SoftPLC；
- [ ] 试用 `zbest1000/mcptoolkit-for-codesys`；
- [ ] 让 Codex 创建工程、POU 和 ST；
- [ ] 调用 Build 并完成一次错误修复；
- [ ] 下载到 SoftPLC，只读取测试变量；
- [ ] 与 IronPLC 的体验和能力做对照。

退出条件：同一个最小传送带需求在 CODESYS 中完成工程、编译和 SoftPLC 在线闭环。

### Lab 4：可选兼容性实验

- [ ] 评估同一份 ST 在 IronPLC 与 OpenPLC 下的兼容性；
- [ ] 评估 OpenPLC Runtime v4 REST API；
- [ ] 仅在需要视觉演示时重新接入 Factory I/O；
- [ ] 根据实测缺口决定是否需要薄适配层。

## 仿真复杂度阶段目标

完整定义见
[仿真复杂度、阶段目标与边界](docs/architecture/simulation-scope.md)。

### S0：单机级

- [x] 电机、按钮和端点传感器；
- [x] 正转、反转和停止；
- [x] 急停锁存、安全复位和禁止自动重启 ST 测试；
- [x] 编译后的 ST Runtime + Modbus + ACC 反馈闭环。

### S1：自动化单元级

- [ ] 2～5 段输送带；
- [ ] 20～40 个 I/O；
- [ ] A/B 物料、缓存、分流和推杆；
- [ ] 至少 10 个物料连续运行；
- [ ] 堵塞、传感器卡死、执行器卡死和通信中断；
- [ ] 确定性种子、快照和结构化 Trace。

### S2：产线级

- [ ] 多工位与约 100～300 个 I/O；
- [ ] 10～100 个并发物料；
- [ ] 配方、换型、报警、工位握手和区域安全；
- [ ] 自动 FAT、覆盖率和跨工位缺陷修复。

### S3：小型工厂离散仿真

- [ ] 5～10 个自动化单元；
- [ ] 多 PLC、多产线和共享资源；
- [ ] 网络延迟、掉线、恢复和控制器重启；
- [ ] 跨区域故障隔离和回归分析。

### S4/S5：外部高精度与专业工艺仿真

- [ ] 定义 Canonical Plant Contract；
- [ ] 接入至少一个外部三维或物理模拟器；
- [ ] 归一化 I/O、时间、故障、状态和 Trace；
- [ ] 通过 Adapter 接入机器人、流体、热力等能力，不在本仓库复制求解器。

## 暂停项目

下列内容保留为未来研究，不进入当前实施主线：

- 通用 PLC IR 和完整 Schema 系统；
- 自研 PLC 编译器；
- 自研通用 Runtime Adapter 框架；
- 自研大型确定性工厂模拟器；
- 自研形式化验证平台和 FAT 报告平台；
- Web/LD/三维可视化系统；
- 多厂商统一适配；
- 多 Agent 角色编排。
- 通用三维编辑器和高精度物理求解器；
- 与 PLC 控制、诊断和验收无关的通用模拟内容。

## 安全边界

- 第一阶段只连接本地 SoftPLC、虚拟控制器或隔离测试设备；
- 不连接生产 PLC；
- 不允许 Agent 未经人工确认执行下载、启动、停止、Force 或真实 I/O 写入；
- 优先开放读取、离线编辑、编译和仿真工具；
- 保存所有编译、部署和运行证据。

## 当前下一步

1. 完成一次明确的 `compile -> diagnose -> repair -> compile` Agent 闭环；
2. 为 ACC 或独立远程 I/O 增加实体急停与 Reset 点位；
3. 评估 OpenPLC Runtime v4 程序包与 Modbus Master 插件，逐步删除 Node I/O 适配器；
4. 保留 CODESYS MCP 作为 Windows 对照实验，不阻塞 Mac 原生主线。

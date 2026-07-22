# Adapters

Adapter 隔离外部系统、Runtime、仿真器和厂商私有协议，避免它们污染上层 PLC
控制契约。

## 类型

### Runtime Adapter

- OpenPLC；
- CODESYS；
- Siemens/TIA；
- OPC UA；
- Modbus TCP/RTU；
- 真实远程 I/O。

### Plant Adapter

- ACC 或其他浏览器三维场景；
- Factory-style 工厂模拟器；
- Open Industry Project；
- 机器人或通用物理模拟器；
- 化工、热力、电网或其他专业工艺模拟器。

## Plant Adapter 契约

最小能力：

```text
capabilities / reset / read_inputs / write_outputs
run or step / get_state / get_time / get_trace
```

可选能力：

```text
snapshot / restore / inject_fault / clear_fault
spawn / remove material / accelerated_time / seeded_replay
```

Adapter 必须声明：

- 目标类别：`simulation`、`softplc` 或 `physical`；
- 时间模型和 PLC scan 同步方式；
- 是否确定性以及是否支持重放；
- 可用的快照、故障注入和加速能力；
- 状态与 Trace 的精度、限制和缺失项。

外部模拟器只提供 Plant 能力。它的场景树、几何对象和私有工程格式不得成为
PLC2Agent 的核心事实来源。完整边界见
[仿真复杂度、阶段目标与边界](../docs/architecture/simulation-scope.md)。

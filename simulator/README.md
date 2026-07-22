# Simulator

确定性、离散时间的被控对象模拟器。第一版不追求通用三维物理，而是支持输送带、传感器、物料、气缸、面板、故障和状态回放。

核心 API：

```text
reset / step / run / snapshot / restore / inject_fault / get_state
```

Runtime 通信由 Adapter 完成，模拟器内核不绑定 Modbus。

## 目标上限

内建模拟器逐级覆盖：

```text
单机 -> 自动化单元 -> 产线 -> 小型工厂离散仿真
```

下一阶段是 2～5 段输送带、20～40 个 I/O、多物料、缓存、分流和故障注入；
后期产线级目标约为 100～300 个 I/O、多工位、配方、报警和区域安全。

机器人动力学、液压、热力、流体、柔性物体和专业工艺求解不进入本内核，统一通过
Plant Adapter 接入。详见
[仿真复杂度、阶段目标与边界](../docs/architecture/simulation-scope.md)。

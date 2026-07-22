# PLC IR 设计

> 当前状态：长期设计草案。通用 IR 实现已延后，不是现阶段接入 Runtime 或 Plant
> Adapter 的前置条件。当前实验以各 Lab 的 ST、I/O 契约、测试和 Trace 为准。

## 目标

PLC IR 用统一、可版本控制的形式表达控制系统语义，避免将某个 IDE 的 GUI 状态或私有二进制工程作为事实来源。

## 顶层对象

```yaml
schema_version: plc2agent/v1alpha1
project:
  id: conveyor-sorter
  title: 箱体自动分拣站
  cycle_time: 20ms

signals: []
modes: []
sequences: []
function_blocks: []
invariants: []
alarms: []
plant: {}
scenarios: []
targets: []
```

## Signal

每个信号同时具有控制语义、物理语义和目标后端映射：

```yaml
- id: conveyor_motor
  direction: output
  data_type: bool
  safety_class: motion
  description: 主输送带运行命令
  plc:
    address: "%QX0.0"
  plant:
    target: main_conveyor.command
  modbus:
    area: coil
    offset: 0
```

校验器至少检查：

- ID 唯一；
- 地址冲突；
- 数据类型与协议区域兼容；
- 输入不得被 PLC 逻辑赋值；
- 输出必须有安全默认值；
- Plant 引用必须存在；
- safety class 对应的停机策略存在。

## Control Model

顺控优先表达为显式状态机，而不是直接生成匿名触点网络：

```yaml
sequences:
  - id: sorter
    initial: idle
    states:
      idle:
        outputs:
          main_conveyor: false
        transitions:
          - when: mode == automatic && start_request
            to: waiting
      waiting:
        outputs:
          main_conveyor: true
        transitions:
          - when: push_sensor && current_box == B
            to: stop_for_push
```

编译器负责将状态机降低为 ST、LD 或厂商后端支持的结构。

## Invariant

不变量表达任何时刻都不得违反的条件：

```yaml
invariants:
  - id: pusher_conveyor_interlock
    expression: "!(pusher_extend && main_conveyor)"
    severity: critical
    rationale: 推料气缸伸出时主输送带不得运行
```

第一版表达式应限制为可解析的安全子集，不直接执行任意 Python 或 JavaScript。

## Timing Contract

```yaml
- id: stop_response
  trigger: estop_ok == false
  expectation: main_conveyor == false
  within: 40ms
```

时序检查应区分：

- `within`：最迟响应时间；
- `for`：持续时间；
- `after`：最早发生时间；
- `until`：保持条件；
- debounce 与 edge 语义。

## Fault Model

```yaml
faults:
  - id: entry_sensor_stuck_on
    target: entry_sensor
    behavior: stuck_at
    value: true
  - id: pusher_jammed
    target: pusher
    behavior: actuator_jam
```

故障是 Plant 行为变体，不应偷偷改写 PLC 程序。

## Trace

每个采样点至少包含：

```json
{
  "tick": 137,
  "virtual_time_ms": 2740,
  "plc_scan": 137,
  "inputs": {},
  "outputs": {},
  "control_state": {},
  "plant_state": {},
  "events": [],
  "violations": []
}
```

Trace 必须记录工程构建哈希、场景哈希、Runtime Adapter 版本和随机种子。

## 版本与迁移

IR 使用显式 `schema_version`。破坏性变更必须提供迁移器，并在报告中记录迁移前后版本，不允许静默解释旧字段。

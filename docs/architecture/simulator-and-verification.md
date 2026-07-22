# Plant Simulator 与验证系统

本文描述内建确定性 Plant 和通用验证语义。完整的复杂度分级、外部模拟器接入
条件及领域边界见 [仿真复杂度、阶段目标与边界](simulation-scope.md)。

## 为什么不先做三维

首要目标是验证控制行为，不是复刻工厂画面。第一版使用二维 Web 投影和确定性离散模型，可更快获得批量运行、故障注入、回放和自动判定能力。

## 组件模型

模拟器以可组合组件构建被控对象：

- conveyor；
- photoelectric sensor；
- source/sink；
- pneumatic pusher；
- cylinder limit；
- button/selector；
- lamp/buzzer；
- motor/valve；
- material item。

组件通过端口连接，不直接引用 PLC 地址。地址绑定由 IR 中的 signal mapping 完成。

## 示例 Plant

```yaml
tick: 10ms
components:
  - id: main_conveyor
    type: conveyor
    length: 3m
    speed: 0.5m/s
    command: conveyor_motor
  - id: push_sensor
    type: photoelectric_sensor
    position: 2.2m
    output: push_sensor
  - id: pusher
    type: pneumatic_pusher
    position: 2.25m
    extend_command: pusher_extend
    extend_time: 400ms
    retract_time: 350ms
```

## 场景 DSL

场景以 Given/When/Then 语义表达，但保存为结构化数据：

```yaml
id: normal-b-box
given:
  - plant.reset
  - set: { estop_ok: true }
when:
  - pulse: { signal: start_pb, duration: 100ms }
  - spawn: { item: box_b, at: entry }
then:
  - eventually:
      expression: count_b == 1
      within: 10s
  - always:
      expression: "!(pusher_extend && main_conveyor)"
```

## 故障注入

必须支持：

- stuck-at；
- delayed response；
- dropped pulse；
- noisy/chattering sensor；
- actuator jam；
- communication timeout；
- power cycle；
- restart with retained/non-retained state。

## 验证层次

1. **Schema validation**：结构、类型和引用；
2. **Static control checks**：地址、未绑定变量、不可达状态和危险输出组合；
3. **Compile checks**：目标后端是否接受；
4. **Scenario tests**：正常与故障流程；
5. **Invariant monitoring**：每个 tick 检查；
6. **Timing checks**：响应上限、持续时间和超时；
7. **Coverage**：需求、状态、转换、报警和故障覆盖；
8. **Regression**：新旧 Trace 与行为契约比较。

## FAT 报告

报告必须能回答：

- 测了哪条需求；
- 使用哪个构建和场景；
- 输入事件是什么；
- 实际输出和响应时间是什么；
- 是否出现属性违例；
- 证据位于哪个 Trace 区间；
- 哪些需求尚未覆盖。

示例：

```text
FAT-08 急停响应                 PASS
触发时间                       4.200s
主输送带关闭时间               4.220s
响应时间                       20ms
要求                           <= 40ms
证据                           trace tick 420..422
```

## 可视化

Web 层提供：

- 二维产线；
- I/O 监视表；
- 状态机高亮；
- LD/ST 只读投影；
- Trace 时间线；
- 属性违例定位；
- 受控的模拟输入和故障注入。

所有操作调用正式工具接口，Web 不直接修改隐藏状态。

## 复杂度演进

内建 Plant 按以下顺序演进：

```text
单机级
  -> 自动化单元级
  -> 产线级
  -> 小型工厂离散仿真
```

下一阶段优先实现双输送带、A/B 物料、缓存和推杆组成的自动化单元，而不是增加
更逼真的画面。产线级目标约为 100～300 个 I/O、多工位、配方、报警和区域安全。

机器人动力学、液压、热力、流体和专业工艺模型不进入内建组件库；这些能力由外部
Plant Adapter 提供。无论后端精度如何，都必须尽量归一化为相同的 I/O、时间、
故障和 Trace 证据。

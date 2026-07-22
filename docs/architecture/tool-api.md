# Agent 工具接口

## 设计要求

所有工具必须：

- 接受结构化参数；
- 返回机器可判定结果；
- 使用稳定错误码；
- 区分诊断、警告和失败；
- 返回受影响路径和建议修复；
- 记录工程版本、目标和执行证据；
- 不要求 Agent 从截图或非结构化日志猜状态。

## 工具域

### Project

```text
project.create
project.inspect
project.validate
project.diff
project.apply_patch
```

### I/O

```text
io.allocate
io.check_conflicts
io.explain_mapping
io.export_table
```

### Logic

```text
logic.generate
logic.compile
logic.explain
logic.render_ladder
logic.trace_requirement
```

### Runtime

```text
runtime.deploy
runtime.start
runtime.stop
runtime.status
runtime.read_variables
runtime.write_simulated_input
runtime.force_variable
runtime.get_logs
```

### Simulation

```text
simulation.reset
simulation.step
simulation.run
simulation.inject_fault
simulation.snapshot
simulation.restore
simulation.get_state
```

### Verification

```text
verification.run_scenario
verification.check_invariants
verification.compare_trace
verification.coverage
verification.generate_fat_report
```

## 诊断格式

```json
{
  "ok": false,
  "diagnostics": [
    {
      "code": "UNBOUND_SIGNAL",
      "severity": "error",
      "path": "sequences.sorter.states.pushing.transitions[0]",
      "subject": "pusher_extended_limit",
      "message": "状态转换引用了未定义输入信号",
      "suggestions": [
        "在 signals 中声明 pusher_extended_limit",
        "或修改转换条件引用已有信号"
      ]
    }
  ]
}
```

## 写操作协议

Agent 修改工程应提交结构化 patch，而不是直接覆盖整个文件：

```json
{
  "base_revision": "sha256:...",
  "operations": [
    {
      "op": "replace",
      "path": "/project/cycle_time",
      "value": "20ms",
      "reason": "满足最大40ms急停响应要求"
    }
  ]
}
```

系统必须拒绝基于过期 revision 的写入，并返回冲突信息。

## 部署回执

`runtime.deploy` 成功不能只表示文件已传输。回执至少包含：

- 构建哈希；
- Runtime 实际加载哈希；
- PLC 状态；
- 实际 cycle time；
- Adapter 和 Runtime 版本；
- 通信端点；
- 加载后的诊断。

这可以避免出现“本地已生成20ms，Runtime仍执行旧程序”的假成功。

## 权限

`runtime.force_variable` 必须声明：

```json
{
  "target_class": "simulation | softplc | physical",
  "signal": "pusher_extend",
  "value": true,
  "duration": "500ms",
  "justification": "FAT-05 执行器超时测试"
}
```

物理目标的强制输出默认需要确认，并写入不可变审计日志。

# Compiler

IR 的离线校验和目标代码生成模块。

第一阶段职责：

- 加载并合并 `specs/`；
- schema 与语义校验；
- I/O 地址和协议映射检查；
- 状态机降低；
- Structured Text 生成；
- OpenPLC 配置生成；
- 构建清单与哈希；
- 结构化诊断。

建议的未来命令：

```text
plc2agent validate specs/
plc2agent build specs/ --target openplc
plc2agent explain diagnostic UNBOUND_SIGNAL
```

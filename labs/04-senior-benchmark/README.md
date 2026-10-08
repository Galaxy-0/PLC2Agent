# Lab 04：高阶 PLC Agent 验证环境（bauhinia）

基线是 `ca62cf1` 的已提交仓库；此 Lab 仅新增文件，不依赖 Mac 上用户未提交的模拟器、Web、Runtime 或 package.json。实际部署和所有计算都在 `/home/galaxy/Project/PLC2Agent`（bauhinia）完成。Mac 仅 SSH、仓库操作与小文件传输。

[岗位、考题、评分及边界](../../docs/benchmarks/senior-plc-2026-10-08.md) · [机器可读招聘记录](jobs.json)

## 复现

在 Linux x86_64（建议同一 bauhinia；已有 Node ≥22、Python3、GCC、npm、curl、tar、timeout、rg）执行：

```sh
cd ~/Project/PLC2Agent
./labs/04-senior-benchmark/verify.sh
```

`setup-linux.sh` 只写本 Lab 的 `.cache/`，固定 STruC++ 0.6.0 官方 Node 资产及 SHA-256 `e59b876031b8e9f5d1431ec93d5cd630b2455b79bf1b2f3da224808028294ab0`，依赖 `chevrotain@11.0.3` 的 7 个包锁定版本和 integrity，使用 npm 官方仓库且禁用所有生命周期脚本。GitHub TLS/重定向协议保持 HTTPS。每段下载最多 45 秒，网络未完成返回 75，可手动重跑续传；不执行未通过完整哈希校验的下载。没有 sudo、全局 PATH/代理/SSH/服务修改，也没有 Mac 安装。

构建：官方 ST→C++，`driver.cpp` 只读写变量并调用一个扫描，不作控制决策。Python Plant 用种子 17 决定 4–7 个扫描的行程，接收事件生成带序号 ACK，ST 输出再次驱动 Plant。命令→实际位置→传感器/ACK→ST 构成闭环。每步记录采样前输入与输出、Plant 前/后位置和接收台账，避免把动作后的传感器误标为当前扫描输入。

```text
15/15 reference cases passed
15/15 byte-identical replay traces
5/5 compileable negative controls detected
compiler rejected undeclared MissingSequence
```

`build/` 保留原始日志、完整轨迹和各缺陷版本；不会提交二进制或依赖。`evidence/` 保存小型审阅证据、轨迹片段及哈希；全量轨迹可重跑获得。

## 契约与接口

扫描固定为 20ms 模拟时间，不声称 Linux 实时调度。状态：0 停止、10 等待、20 伸出、30 等匹配 ACK、40 收回、90 故障。默认每阶段 30 scans=600ms；反馈/匹配 ACK 在截止扫描到达时优先成功。配方允许超时 5…200 scans、等待 0…timeout−1，只接受新的提交边沿和递增版本，忙态拒绝；周期参数在接件时快照。

请求为正、单调 DINT，最大 2147483000。`DownstreamReady` 在接件时视作资源预约，之后不能用 Ready 变化表示取消预约；异常须通过独立故障信号。旧 ACK 被忽略直至超时。故障事务不可自动重发旧序号；清故障要求回原位、清请求、Start=0、安全/通信正常且新的 Reset 边沿。物料未明时须人工核对，接口没有自动回原位动作。序号、台账未做 RETAIN，进程重启后不保证跨重启 exactly-once，不能用于上线运行。

故障码：101 急停输入、102 通信失鲜、103 反馈矛盾、104 忙态切手动、201 伸出超时、202 ACK 超时、203 收回超时。首因保持，动作命令按故障后的状态同一扫描置零。

Agent 使用标准输入输出 NDJSON（进程内接口，无端口、无真实 I/O）：

```sh
python3 labs/04-senior-benchmark/bench.py --cli
```

```json
{"op":"reset","seed":17}
{"op":"set_inputs","inputs":{"StartPb":1}}
{"op":"step","scans":1}
{"op":"set_inputs","inputs":{"StartPb":0,"ReqValid":1,"ReqSeq":11}}
{"op":"step","scans":30}
{"op":"snapshot"}
{"op":"inject_fault","fault":"communication_stale","enabled":true}
{"op":"step"}
{"op":"trace"}
```

可注入 `actuator_stuck`、`retract_stuck`、`ack_drop`、`ack_mismatch`、`feedback_conflict`、`communication_stale`。反馈与 ACK 归 Plant 管理，外部写入被拒绝。BOOL 仅 0/1，INT/DINT 按位宽验证，未知输入和故障拒绝；单次 step 为 1…1000、每次 reset 后最多 10000 scans。native 子进程每扫描墙钟超时 2s、CPU 总计上限 10s、地址空间 256MiB。这是资源限额，不是对恶意程序的安全沙箱。

## 审阅证据与回滚

[evidence/manifest.json](evidence/manifest.json) 绑定输入源码与工具摘要；[reference-report.json](evidence/reference-report.json) 列出每场景和哈希；[mutations.json](evidence/mutations.json) 保存可编译坏版本的退出码和失败场景；[compile-error.log](evidence/compile-error.log) 保存真实诊断；[cli-transcript.ndjson](evidence/cli-transcript.ndjson) 保存实际接口调用。

无后台 Runtime、tmux 任务、监听端口或服务被启动。每个子进程在用例结束关闭。回滚可在服务器执行本 Lab 的受限缓存删除脚本：

```sh
python3 labs/04-senior-benchmark/rollback.py --confirm
```

仅删除经真实路径核对的本 Lab `.cache/` 与 `build/`；保留源码、证据、用户文件与原项目。移除已提交成果用正常 Git revert，并另行 review；不 merge、不 reset、不 stash、不清用户工作树。Windows 工业套件、总线报文、运动实时性、硬件安全与现场 SAT 未覆盖。

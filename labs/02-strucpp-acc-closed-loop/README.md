# Lab 2：原生 ST Runtime + ACC 闭环

## 结果

这条链路已经在 Apple Silicon Mac 上跑通：

```text
ACC 3D conveyor
  |  DI 10001..10004
  v
Modbus TCP bridge
  |
  |  copy inputs only
  v
modbus-runtime-adapter.mjs
  |
  |  set inputs -> step -> get outputs
  v
STruC++ native runtime
  |
  |  conveyor.st makes every control decision
  v
modbus-runtime-adapter.mjs
  |
  |  copy outputs only
  v
Modbus TCP bridge
  |  Coil 00001..00002
  v
ACC 3D conveyor
```

与 Lab 1 的区别是：JavaScript 不再包含启动保持、换向或停止判断。
这些判断全部位于真正编译执行的 IEC 61131-3 Structured Text 中。

## 文件

- `conveyor.st`：传送带 IEC 61131-3 控制程序；
- `test_conveyor.st`：七个原生 ST 单元测试；
- `setup-strucpp.sh`：固定下载官方 STruC++ 0.6.0 macOS arm64 版本；
- `build.sh`：运行测试并构建可执行 Runtime；
- `modbus-runtime-adapter.mjs`：只搬运 I/O 的 Modbus/Runtime 适配器。

## 构建和测试

```sh
./build.sh
```

成功输出应包含：

```text
7 tests, 7 passed, 0 failed
Binary built: .../build/conveyor
```

`build/` 和 `.cache/` 都是本机生成目录，不进入 Git。

## 运行闭环

先按 Lab 1 的说明启动 ACC Bridge 并连接浏览器场景，然后运行：

```sh
node modbus-runtime-adapter.mjs --port 5020 --exit-after-cycle
```

在 ACC 场景中按住 `START` 约 0.1 秒。完成一个往返后，适配器将输出
归零并自动退出。

如果由只能产生极短 click 的自动化工具触发 START，可暂时提高轮询频率：

```sh
node modbus-runtime-adapter.mjs --port 5020 --scan-ms 0 --exit-after-cycle
```

这只改变外部 I/O 采样频率，不改变 ST 的控制逻辑。

## I/O 契约

| Modbus 地址 | ST 变量 | 方向 | 含义 |
|---|---|---|---|
| DI 10001 | `%IX0.0` / `Start` | ACC -> ST | 启动按钮，常开 |
| DI 10002 | `%IX0.1` / `StopHealthy` | ACC -> ST | 停止回路，正常为 1 |
| DI 10003 | `%IX0.2` / `LeftSensor` | ACC -> ST | 左端传感器 |
| DI 10004 | `%IX0.3` / `RightSensor` | ACC -> ST | 右端传感器 |
| Coil 00001 | `%QX0.0` / `Motor` | ST -> ACC | 电机运行 |
| Coil 00002 | `%QX0.1` / `Reverse` | ST -> ACC | 方向；0 正转，1 反转 |
| Runtime 变量 | `EmergencyStopHealthy` | Test/Adapter -> ST | 急停回路，正常为 1 |
| Runtime 变量 | `Reset` | Test/Adapter -> ST | 故障复位脉冲 |
| Runtime 变量 | `FaultLatched` | ST -> Test/Adapter | 急停故障锁存状态 |

ACC 当前没有独立的 X5/X6，因此急停与 Reset 暂不伪装成场景中的物理地址。
等场景或远程 I/O Adapter 增加实体点位后，只需映射这两个 Runtime 变量，
现有 X1-X4/Y1-Y2 地址不变。

## 安全语义

```text
STOP circuit opens
  -> Motor=0, Reverse=0
  -> FaultLatched stays 0
  -> a new START edge may run again

Emergency-stop circuit opens
  -> Motor=0, Reverse=0
  -> FaultLatched=1
  -> restoring the circuit alone cannot restart
  -> Reset is accepted only with healthy safety/stop circuits and Motor=0
  -> Reset never acts as START; START must be released and pressed again
```

## 本机实测证据

环境：macOS 26.5.2、Apple Silicon arm64、Node.js v22.22.3、
STruC++ 0.6.0。

```text
X=1110 ST.motor=1 ST.reverse=0 ST.fault=0 Y=10
X=0100 ST.motor=1 ST.reverse=0 ST.fault=0 Y=10
X=0101 ST.motor=1 ST.reverse=1 ST.fault=0 Y=11
X=0100 ST.motor=1 ST.reverse=1 ST.fault=0 Y=11
ST CYCLE_COMPLETE pulse -> cycle 1 complete
X=0110 ST.motor=0 ST.reverse=0 ST.fault=0 Y=00
```

ACC 场景日志同时出现：

```text
18:21:14 X4 -> Right sensor triggered
18:21:17 X3 -> Left sensor triggered
POS: -3.42 STOP
MB LINKED
```

因此这里不是预制变量序列：箱体运动产生 X4/X3，ST 根据输入改变 Y1/Y2，
输出再次驱动箱体运动，物理反馈闭环成立。

普通 STOP 也在箱体运动途中完成在线验证：

```text
X=0100 ST.motor=1 ST.reverse=0 ST.fault=0 Y=10
X=0000 ST.motor=0 ST.reverse=0 ST.fault=0 Y=00
X=0100 ST.motor=0 ST.reverse=0 ST.fault=0 Y=00
ACC position: 0.05 STOP
```

随后重新按 START，箱体继续前往右端、反转并回到左端，说明 STOP 没有错误地
锁存为急停故障。

## 当前边界

这是官方 STruC++ 生成的原生可执行测试 Runtime，适合 CLI、Agent 和自动测试，
但还不是带完整设备管理、在线下载和现场驱动能力的 OpenPLC Runtime。

下一层替换不会改 `conveyor.st` 的控制意图或 ACC I/O 地址：将 Runtime 换成
OpenPLC Runtime v4，并由它的 Modbus Master 插件直接连接 ACC Bridge，即可进一步
删除 Node I/O 适配器。

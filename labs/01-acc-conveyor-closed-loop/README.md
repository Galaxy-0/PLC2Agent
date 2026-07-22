# Lab 1：ACC 传送带 Modbus 闭环

## 目标

在 Apple Silicon Mac 上验证一条不依赖 Windows 或 CrossOver 的真实闭环：

```text
ACC 3D scene
  ├─ X1 Start / X2 Stop / X3 Left / X4 Right
  │                         ↓ Modbus TCP FC02
  └─ Y1 Motor / Y2 Direction ← Modbus TCP FC15
                        controller.mjs
```

控制顺序：

```text
按 START
→ 正转到右端
→ X4 触发后反转
→ 返回左端
→ X3 触发后停止
```

## 组成

- 3D 场景：ACC Conveyor Scene，运行在浏览器；
- Modbus Bridge：ACC 官方 MIT 许可 Node.js 桥；
- `controller.mjs`：零第三方依赖的 Modbus TCP 主站和扫描循环；
- 默认 Modbus TCP 端口：`5020`，避免 macOS 上使用特权端口 `502`。

## 运行

准备并启动桥：

```sh
BRIDGE_DIR=$(./setup-bridge.sh)
node "$BRIDGE_DIR/acc-modbus-bridge.js" --modbus-port 5020
```

打开场景：

```text
https://accautomation.ca/simulator/acc-conveyor-scene.html
```

在页面中展开 `MODBUS`，保持 WebSocket 地址为
`ws://127.0.0.1:8502`，然后点击 `CONNECT`。

另开终端运行控制器：

```sh
node controller.mjs --port 5020 --exit-after-cycle
```

最后在场景中点击 `START`。控制器完成一个往返周期后自动关闭
`Y1`、`Y2` 并退出。

## I/O 映射

| 地址 | 变量 | 含义 |
|---|---|---|
| DI 10001 | X1 | 启动按钮，常开 |
| DI 10002 | X2 | 停止按钮，常闭；正常为 1 |
| DI 10003 | X3 | 左端传感器 |
| DI 10004 | X4 | 右端传感器 |
| Coil 00001 | Y1 | 电机运行 |
| Coil 00002 | Y2 | 方向；0 正转，1 反转 |

## 边界

这个控制器用于证明通讯和物理反馈闭环，不冒充 IEC 61131-3 Runtime。
后续可以保留同一份 I/O 契约，将扫描逻辑替换为支持外部 I/O 的
SoftPLC Runtime。

## 本机实测

测试环境：macOS 26.5.2、Apple Silicon arm64、Node.js v22.22.3。

控制器轨迹：

```text
CONNECTED modbus://127.0.0.1:5020 scan=50ms
X=0100 Y=00
X1 START rising edge -> Y1 RUN forward
X=1100 Y=10
X=0100 Y=10
X4 RIGHT sensor -> Y2 REVERSE
X=0101 Y=11
X=0100 Y=11
X3 LEFT sensor -> cycle 1 complete, STOP
X=0110 Y=00
```

场景最终状态：

```text
Modbus: MB LINKED
Position: -3.47, STOP
X3 left sensor: ON
X4 right sensor: OFF
Y1 motor: OFF
Y2 direction: OFF
```

结论：输入不是预先伪造的变量序列；X4、X3 均由 3D 箱体运动触发，
控制器读取传感器后改变输出，场景再产生下一次传感器反馈，闭环成立。

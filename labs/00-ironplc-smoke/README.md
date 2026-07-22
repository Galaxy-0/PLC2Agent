# Lab 0：IronPLC 官方基线

## 目标

在 Apple Silicon Mac 上验证 IronPLC 官方工具链的三个基础能力：

```text
ST source → check → compile → VM run
                      └──────→ MCP check/compile/run
```

## 环境

- macOS：26.5.2，arm64；
- IronPLC：v0.228.0；
- `ironplcc`、`ironplcvm`、`ironplcmcp`：`~/.ironplc/bin/`；
- MCP 协议：2025-03-26；
- MCP Server 自报版本：rmcp 2.1.0。

## 安装记录

官方文档推荐 macOS 使用 Homebrew，但实测 tap 中 v0.231.0 Formula 指向 `x86_64-macos` 包，且新版 Homebrew 要求额外信任第三方 tap。为避免在 arm64 Mac 上安装错误架构，本实验改用检查过内容的官方安装脚本。脚本会选择 `ironplcc-aarch64-macos.tar.gz` 并校验随 Release 发布的 SHA-256 文件。

```sh
curl -fsSL https://www.ironplc.com/install.sh | sh
```

## 官方 Doorbell 示例

源码位于 `main.st`。验证命令：

```sh
~/.ironplc/bin/ironplcc check main.st
~/.ironplc/bin/ironplcc compile main.st --output main.iplc
~/.ironplc/bin/ironplcvm run main.iplc --scans 1 --dump-vars
```

实测输出：

```text
Button: FALSE
Buzzer: TRUE
```

结论：编译器和虚拟机均可在本机运行，结果符合官方 Quick Start。

## MCP smoke test

`mcp-smoke.mjs` 是一个零第三方依赖的最小 MCP 客户端。它启动本机 `ironplcmcp`，依次调用：

```text
initialize
→ list_options
→ check
→ compile
→ run
```

运行：

```sh
node mcp-smoke.mjs
```

实测结果：

- 使用 `iec61131-3-ed3` dialect；
- `check.ok = true`，无诊断；
- `compile.ok = true`；
- `run.ok = true`；
- 完成一个 scan cycle；
- Trace 中 `main.Button = false`；
- Trace 中 `main.Buzzer = true`；
- `terminated_reason = completed`。

## MCP 实际边界

本机 v0.228.0 实际暴露的 MCP 工具包括：

- `parse`、`check`、`explain_diagnostic`；
- `symbols`、`project_manifest`、`project_io`；
- `pou_scope`、`pou_lineage`、`types_all`；
- `compile`、`run`、`container_drop`；
- `list_options`。

`run` 已经可以执行编译产物并返回变量 Trace。不过其工具描述明确说明当前里程碑只支持无 stimuli 的运行；按时间写入输入变量仍是后续能力。因此 Lab 1 可以直接验证 Codex 的编译修复闭环，带输入序列的控制场景需要等待上游支持或增加很薄的测试适配。

## 下一步

将 `~/.ironplc/bin/ironplcmcp` 接入 Codex，故意引入一个 ST 错误，让 Codex 完成一次：

```text
check → diagnose → repair → check → compile → run
```

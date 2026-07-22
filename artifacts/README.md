# Artifacts

构建与验证产生的非事实来源内容：

```text
artifacts/
├── generated/   ST、目标工程、映射和构建清单
├── traces/      确定性运行轨迹
├── reports/     FAT 与覆盖率报告
└── legacy/      早期实验备份
```

`generated/`、`traces/` 和 `reports/` 默认不进入 Git；需要作为发布证据时再显式纳入。

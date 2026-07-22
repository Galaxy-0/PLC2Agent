# Runtime

统一 Runtime 生命周期与在线状态协议。核心接口不得泄露厂商 UI 细节。

```text
deploy → verify_loaded_hash → start → status → trace → stop
```

第一目标是 OpenPLC Runtime v4；后续增加 CODESYS Control for Linux 和厂商 Adapter。

# PS5 Pro Stock Watch

每 5 分钟检查一次 JB Hi-Fi Australia 的 PS5 Pro 库存，有货时通过 [ntfy](https://ntfy.sh) 推送到手机。

## 设置

1. iPhone 安装 **ntfy** app，订阅一个只有你知道的 topic 名（例如 `leo-ps5pro-8371`）。
2. 在这个 repo 的 **Settings → Secrets and variables → Actions → New repository secret** 里添加：
   - Name: `NTFY_TOPIC`
   - Secret: 你刚才订阅的 topic 名
3. 打开 **Actions** 页面，选择 "PS5 Pro stock watch"，点 **Run workflow**。手机收到测试推送就说明设置成功。

之后它会自动每 5 分钟运行一次。

## 停止

Actions → PS5 Pro stock watch → 右上角 `···` → **Disable workflow**。

## 说明

- 有货期间每次检查都会推送，直到你停用 workflow 或者商品再次卖完。
- 如果某次运行显示红色失败，可能是 JB 拦截了 GitHub 服务器的访问，或者网页改版了。

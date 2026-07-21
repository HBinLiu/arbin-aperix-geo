# 微信支付证书 / 公钥

本目录只需保留两个文件（另加本说明）：

| 文件 | 说明 | 环境变量 |
|------|------|----------|
| `apiclient_key.pem` | 商户 API 私钥，发请求签名 | `WECHAT_PAY_PRIVATE_KEY_PATH` |
| `public_key.pem` | 微信支付公钥，回调验签 | `WECHAT_PAY_PUBLIC_KEY_PATH` |

## 其它必填配置（写在 `backend/.env`）

| 变量 | 说明 |
|------|------|
| `WECHAT_PAY_MCH_ID` | 商户号 |
| `WECHAT_PAY_APP_ID` | AppID |
| `WECHAT_PAY_API_V3_KEY` | API v3 密钥（32 字节，回调解密用） |
| `WECHAT_PAY_MCH_CERT_SERIAL_NO` | 商户 API 证书序列号（商户平台可见） |
| `WECHAT_PAY_PUBLIC_KEY_ID` | 微信支付公钥 ID（`PUB_KEY_ID_...`） |
| `WECHAT_PAY_NOTIFY_URL` | 公网 HTTPS 回调地址 |

## `.env` 路径示例（相对 `backend/`）

```bash
WECHAT_PAY_PRIVATE_KEY_PATH=certs/wechat/apiclient_key.pem
WECHAT_PAY_PUBLIC_KEY_PATH=certs/wechat/public_key.pem
```

验签靠 `public_key.pem` + `WECHAT_PAY_PUBLIC_KEY_ID`；解密靠 `WECHAT_PAY_API_V3_KEY`。

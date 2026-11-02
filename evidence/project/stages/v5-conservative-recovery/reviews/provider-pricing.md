# 免费费用预检的费率来源（2026-11-02）

本轮只读官方公开资料，没有项目模型/API请求。通过搜索取得的官方价格页正文列出deepseek-flash峰值每百万tokens：缓存命中0.04元、未命中2元、输出8元；闲时一半。现有evaluation/provider.py使用峰值上界，不依赖当前时段折扣，也不假定命中缓存。

来源：[官方模型与价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)。本次直接打开标准URL有缓存/抓取失败；搜索所返回的该官方页面正文包含DeepSeek-V4.1-Flash-1017及上述峰谷价格（搜索缓存标示两周前抓取），不声称直接请求了供应商实时账单。

[官方更新日志](https://api-docs.deepseek.com/zh-cn/updates/)说明2026-10-17升级后仍使用deepseek-flash，调用方式与价格保持不变；[版本公告](https://api-docs.deepseek.com/zh-cn/news/news261017/)说明模型服务版本更新。服务版本说明不证明实际HTTP响应model字段使用某个新字符串，因此不扩充现有受信响应名列表。

费用预览按现有PaidProvider精确文本请求体的UTF-8字节数构造保守输入上界，再加有限输出上界。它不是供应商实际token或账单。当前请求体不带搜索/抓取工具，搜索API的独立计次价格不计入本轮纯文本三Claim提案。正式执行前仍须有效有限批准、账本就绪和未过期的来源绑定；此记录不授予调用权限。

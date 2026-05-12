# 贡献指南 / Contributing Guide

感谢你对本项目的兴趣！以下是参与贡献的方式。

---

## 如何添加新信用卡 / Adding a New Card

### 方法一：通过 App 内置功能（推荐）
打开 App → 点击"添加卡片" → "从网址添加新卡" → 输入信用卡介绍页链接，自动解析后确认保存。

### 方法二：手动编辑代码

**1. 在 `index.html` 的 `CARDS` 对象中添加卡片配置：**

```javascript
your_card_id: {
    id: 'your_card_id',
    name: { zh: '卡片中文名', en: 'Card English Name' },
    annualFee: 95,
    headerBg: 'bg-blue-800',   // Tailwind 背景色
    benefits: [
        {
            id: 'benefit_id',
            name:        { zh: '福利名称', en: 'Benefit Name' },
            type: 'annual',       // annual | monthly | monthly_uber | semi-annual | quarterly | toggle
            totalValue: 100,
            resetPeriod: { zh: '每年', en: 'Annual' },
            description: { zh: '说明文字', en: 'Description' },
        },
    ],
},
```

**2. 在 `server.py` 中添加 PDF 账单关键词：**

```python
# BENEFIT_KEYWORDS — PDF 中匹配福利的关键词
'your_card_id': {
    'benefit_id': ['KEYWORD IN STATEMENT', 'ANOTHER KEYWORD'],
},

# BENEFIT_TYPES — 福利类型
'your_card_id': {
    'benefit_id': 'annual',
},

# CARD_TYPE_KEYWORDS — 识别账单属于哪张卡
'your_card_id': ['CARD NAME IN PDF', 'ALTERNATE NAME'],
```

---

## PR 规范 / Pull Request Guidelines

- 一个 PR 只做一件事（添加一张卡、修复一个 bug、改一个功能）
- PR 标题格式：
  - `add: Chase Freedom Flex` — 新卡片
  - `fix: Amex Platinum hotel credit type` — Bug 修复
  - `feat: 添加深色模式` — 新功能
- UI 改动请附截图

---

## Bug 报告 / Bug Reports

请在 [Issues](../../issues) 中提交，包含：
- 操作系统版本
- 复现步骤
- 截图或错误信息

---

## 功能建议 / Feature Requests

在 [Issues](../../issues) 中提交，说明：
- 使用场景
- 期望的效果

---

## 开发注意事项

- 修改 `index.html` 或 `server.py` 后需要重新打包才能在 EXE 中生效
- 前端使用 React (Babel CDN，无构建步骤) + Tailwind CSS
- 后端使用 Flask + SQLite，数据存储在用户 `AppData/Local/AmexTracker/` 目录（沿用旧目录名以兼容已安装的版本）

---

Copyright © 2025 Yu Guan (Teddy) — GPL v3

# 🏥 Global ADR Intelligence Dashboard

## FDA FAERS 風格藥物不良反應監測平台

一個專業級的藥物警戒分析儀表板，使用 FDA openFDA API 進行即時 ADR (不良藥物反應) 監測與分析。

![Dashboard Preview](https://img.shields.io/badge/FDA-FAERS-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.9+-green?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red?style=for-the-badge)

---

## ✨ 功能特色

### 📋 雙層風險評估
- **Tier 1**: 檢查 FDA 官方藥物標籤 (Label) 中是否記載該副作用
- **Tier 2**: 統計 FAERS 資料庫中的通報案件數量
- 自動偵測商品名/學名並進行智能聯集搜尋

### 🌍 全球地理分析
- 世界地圖視覺化：顯示各國 ADR 通報分布
- Top 10 通報國家排名
- 支援 190+ 個通報國家

### 📈 趨勢與人口統計
- 通報者類型分析（醫師、藥師、消費者等）
- 給藥途徑分布
- 月度通報趨勢圖
- 劑量分布統計

### 📤 資料匯出
- 下載 Case-level 詳細資料
- 支援 CSV、Excel、JSON 格式
- 包含：安全報告 ID、通報日期、患者資訊、劑量、給藥途徑等

---

## 🚀 快速開始

### 安裝相依套件

```bash
pip install -r requirements.txt
```

### 啟動應用程式

```bash
streamlit run app.py
```

### 瀏覽器開啟

預設會在 `http://localhost:8501` 啟動

---

## 📖 使用指南

### 1️⃣ 輸入分析參數

在左側邊欄輸入：
- **藥物名稱**：可輸入多個藥物，用逗號分隔（例：`Zoloft, Lexapro, Prozac`）
- **副作用**：使用 MedDRA 標準術語（例：`Nausea`, `QT prolongation`）
- **風險閾值**：自訂高/中風險的通報數門檻

### 2️⃣ 執行分析

點擊「🚀 Run Analysis」按鈕

### 3️⃣ 檢視結果

四個分頁提供不同面向的分析：

| 分頁 | 內容 |
|------|------|
| 📋 Risk Assessment | 風險等級評估與標籤檢查結果 |
| 🌍 Geographic Analysis | 全球通報分布地圖 |
| 📈 Trend & Demographics | 時間趨勢與通報者分析 |
| 📤 Export Data | 下載 Case-level 原始資料 |

---

## 🔧 技術架構

```
faers_dashboard/
├── app.py              # 主應用程式
├── requirements.txt    # Python 相依套件
└── README.md          # 說明文件
```

### API 端點使用

| 端點 | 用途 |
|------|------|
| `/drug/label.json` | 查詢藥物標籤資訊 |
| `/drug/event.json` | 查詢 FAERS 通報事件 |

### 主要技術

- **Streamlit**: 前端框架
- **Plotly**: 互動式圖表
- **Pandas**: 資料處理
- **OpenFDA API**: 資料來源

---

## 📊 資料欄位說明

### 匯出資料包含

| 欄位 | 說明 |
|------|------|
| Safety Report ID | FDA 安全報告編號 |
| Receive Date | 通報接收日期 |
| Serious | 是否為嚴重不良事件 |
| Reporter Country | 通報者所在國家 |
| Patient Age | 患者年齡 |
| Patient Sex | 患者性別 |
| Drug Name | 藥物名稱 |
| Dose | 使用劑量 |
| Route | 給藥途徑 |
| Indication | 使用適應症 |
| Reactions | 不良反應 (MedDRA PT) |
| Reporter Type | 通報者類型 |

---

## ⚠️ 注意事項

1. **API 速率限制**: OpenFDA API 有請求頻率限制，大量查詢時請適當間隔
2. **資料解讀**: FAERS 為自發性通報系統，不代表因果關係
3. **資料時效**: 資料有 5 分鐘快取，重複查詢會使用快取資料
4. **學術用途**: 本工具僅供學術研究參考，不應作為臨床決策依據

---

## 🔮 未來規劃

- [ ] 加入 PRR/ROR 信號偵測演算法
- [ ] 支援 EudraVigilance 歐盟資料
- [ ] 藥物交互作用分析
- [ ] 批次分析模式
- [ ] API 金鑰支援（提高查詢上限）

---

## 📜 授權條款

MIT License

---

## 🙏 致謝

- [openFDA](https://open.fda.gov/) - 提供公開 API
- [Streamlit](https://streamlit.io/) - 優秀的 Python 前端框架
- [Plotly](https://plotly.com/) - 互動式視覺化

---

**Made with ❤️ for Clinical Pharmacists**

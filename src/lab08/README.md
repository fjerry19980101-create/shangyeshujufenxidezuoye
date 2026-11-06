# lab08 SQL 基础与多表整合

## 一、教材出处与业务背景

- 教材：第 8 章 SQL 语言基础与 MySQL 入门（PDF p238-266），原案例在 MySQL 的 `kdd99` 库中执行 SQL。
- 业务问题：数据分析师需要"自助取数"，不依赖 IT 出报表，自己完成单表筛选、指标计算、多表关联、结果合并。
- 教材覆盖：SELECT/WHERE/ORDER BY/LIMIT/DISTINCT → 表达式与 CASE 新列 → COUNT/AVG/SUM + GROUP BY + HAVING → 内/左/右/全连接与不等值连接 → 子查询 → UNION/UNION ALL → 建表与视图。

## 二、Python 迁移思路

| 教材（MySQL） | 本实验（Python） |
|---|---|
| MySQL 服务 + `kdd99` 库 | Python 标准库 `sqlite3`（零安装、单文件数据库） |
| `weekday()` 函数（0=周一） | SQLite `(strftime('%w', date)+6)%7`，等价实现 |
| 多表 JOIN | 同结构 SQL，在 SQLite 中执行 |
| 结果人工核对 | 每条 SQL 配一份 `pandas` 等价实现，自动对拍行列与数值 |

实现分三层：

1. [data_prep.py](file:///c:/Users/fjwsm/Desktop/学习资料/大三上%20第一学期/商业数据分析/T/src/lab08/data_prep.py)：按 KDD99 表结构生成 sale/clients/disp/card/trans/loans 六张表并建库；
2. [main.py](file:///c:/Users/fjwsm/Desktop/学习资料/大三上%20第一学期/商业数据分析/T/src/lab08/main.py)：9 组 SQL + pandas 对拍；
3. 产物：`output/figures/lab08_*.png`、`output/tables/lab08_*.csv`。

## 三、数据说明

按教材表结构模拟的小样本（固定种子 42）：

| 表 | 行数 | 关键字段 |
|---|---|---|
| sale | 80 | year, market, sale, profit |
| clients | 400 | client_id, sex, birth_date, district_id |
| disp | 500 | disp_id, client_id, account_id, type |
| card | 350 | card_id, disp_id, type, issued |
| trans | 3,000 | trans_id, account_id, date, amount, balance, k_symbol |
| loans | 200 | loan_id, account_id, date, amount, duration, status |

数据库落在 `data/processed/lab08_kdd99.db`，每次运行重建。

> 教材 HAVING 示例阈值是 300（原始数据量大）；本样本将阈值等比调整为 60，SQL 逻辑不变。

## 四、运行方式

```bash
cd T
python src/lab08/main.py
```

## 五、运行结果（SQL 与 pandas 全部对拍通过）

| 检查项 | 结果 |
|---|---|
| 单表筛选排序（1998-12 房屋贷款） | PASS，307 行 |
| 新列 rate + WHERE 表达式 | PASS，20 行 |
| weekday + CASE 工作日标记 | PASS，307 行 |
| 按日汇总 + HAVING > 60 | PASS，23 个交易日 |
| 三表左连接 card→disp→clients | PASS，350 张卡 |
| 不等值连接（放款前 365 天交易） | PASS，255 行 |
| 非关联子查询（高于平均贷款额） | PASS，97 笔 |
| 关联子查询（EXISTS 有 OWNER 账户） | PASS，229 人 |
| UNION / UNION ALL | PASS，7 / 40 行 |
| 视图与三表连接一致 | PASS，350 行 |

**对拍汇总：10 项全部通过。**

补充结论：各市场平均销售利润率 10.1%~10.8%，差异不大，利润问题不在市场结构；
12 月有 23 个交易日交易笔数超过 60，交易活跃度集中。

## 六、产物清单

| 文件 | 内容 |
|---|---|
| `lab08_daily_trans.png` | 1998-12 每日交易笔数与日交易总额（双轴） |
| `lab08_market_rate.png` | 各市场平均销售利润率 |
| `lab08_sql_vs_pandas.csv` | 10 项对拍结果（行数、状态） |
| `lab08_daily_summary.csv` | 按日汇总结果 |
| `lab08_card_client.csv` | 三表连接结果（350 张卡） |

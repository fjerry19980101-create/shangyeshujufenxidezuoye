# lab12 KDD99 数据模型：E-R 图与星型模型

- **教材出处**：第 12 章 12.2 数据模型（PDF p324-346，Power BI 实现）
- **迁移目标**：把 Power BI 模型视图里的"表关系、主外键、基数、交叉筛选方向"，落成可校验的 SQLite 关系库，并把雪花结构展开成星型模型。
- **数据**：KDD99 银行数据集结构（900 张卡）。公开站点在本机不可达，复用 lab09 的固定种子模拟数据，并补齐 `district / account / loan / perm_order` 四张表。

## 1. 业务问题

拿到银行数据集后，先要回答：哪些字段是主键、哪些是外键、关系是一对一还是一对多、筛选条件朝哪个方向传递。模型关系错了，后续度量值（消费额、交易笔数、客户数）一定算错。

## 2. 规范化模型（8 张表）

```
district ─┬─< client ─< disp >─ account ─┬─< trans
          └─< account                    ├─< loan
                                         └─< perm_order
                                  disp ─< card
```

| 关系 | 外键 | 基数 | 校验 |
|---|---|---|---|
| district → client | client.district_id | 1:N | 通过 |
| district → account | account.district_id | 1:N | 通过 |
| client → disp | disp.client_id | 1:N | 通过 |
| account → disp | disp.account_id | 1:N | 通过 |
| disp → card | card.disp_id | 1:N | 通过 |
| account → trans | trans.account_id | 1:N | 通过 |
| account → loan | loan.account_id | 1:N | 通过 |
| account → perm_order | perm_order.account_id | 1:N | 通过 |

- 全部外键在 `CREATE TABLE` 中显式声明，并开启 `PRAGMA foreign_keys = ON`；
- `PRAGMA foreign_key_check` 返回 0 条违规；
- 逐关系验证"父键无重复 + 子表无孤儿外键"，8/8 通过；
- `disp` 是 `client` 与 `account` 的桥表，因此整体是**雪花结构**而非纯星型。

## 3. 星型模型（1 张事实表 + 4 张维度表）

| 表 | 主键 | 内容 |
|---|---|---|
| `fact_trans` | trans_id | 12,464 笔交易：金额、借贷类型、操作、用途 |
| `dim_date` | date_key | 2,341 个日期：年/月/日/星期/是否周末 |
| `dim_client` | client_key | 性别、年龄段、地区 |
| `dim_account` | account_key | 发卡频率、开户年、地区 |
| `dim_card` | card_key | 卡类型、发卡年 |

事实表直接持有 `date_key / account_key / client_key / card_key` 四个外键；`disp` 与 `account` 的层级被展开进维度，查询时不再需要多跳 JOIN。

## 4. 等价性校验

同一口径"按卡类型汇总消费额"分别走两套模型：

| 卡类型 | 规范化模型金额 | 星型模型金额 | 笔数 | 一致 |
|---|---|---|---|---|
| 普通卡 | 30,115,610.23 | 30,115,610.23 | 7,387 | 是 |
| 金卡 | 15,651,393.60 | 15,651,393.60 | 3,810 | 是 |
| 青年卡 | 5,175,824.66 | 5,175,824.66 | 1,267 | 是 |

规范化 SQL 需要 `trans → account → disp → card` 三次 JOIN；星型 SQL 只需 `fact_trans → dim_card` 一次 JOIN，结果逐行一致。

## 5. 交叉筛选方向

| 场景 | 查询 | 结果 | 占比 |
|---|---|---|---|
| 维度 → 事实（单向，默认） | 性别='女' 的交易笔数 | 5,172 | 41.5% |
| 事实 → 维度（需双向） | 金额>7500 涉及的客户数 | 528 | 58.7% |
| 参照 | 金额>7500 的交易笔数 | 814 | 6.5% |

注意最后两行的差别：6.5% 是**交易**占比，58.7% 是**客户**占比。Power BI 默认单向筛选时，事实表上的筛选不会反向过滤维度表；只有把关系设为"双向"才能得到 528 这类反向结果。双向关系容易产生歧义与循环，建模时应默认单向、按需开启。

## 6. 交付文件

| 文件 | 内容 |
|---|---|
| `data_prep.py` | 8 张规范化表 + 星型展开 + SQLite 建库（含外键） |
| `model.py` | 关系清单、外键/基数校验、两套查询、交叉筛选演示 |
| `main.py` | 全流程 + 2 张图 + 5 张表 |
| `output/figures/lab12_er.png` | E-R 图（表、主外键、1:N、箭头方向） |
| `output/figures/lab12_star.png` | 星型模型图（事实表居中，维度环绕） |
| `output/tables/lab12_schema.csv` | 全库字段、类型、主键、外键清单 |
| `output/tables/lab12_relationships.csv` | 8 条关系与基数 |
| `output/tables/lab12_cardinality_check.csv` | 逐关系校验结果 |
| `output/tables/lab12_compare.csv` | 规范化 vs 星型查询对拍 |
| `output/tables/lab12_cross_filter.csv` | 交叉筛选方向量化 |

## 7. 运行

```bash
# 在仓库根目录 T/ 下运行
python src/lab12/main.py
```

首次运行会重建 `data/processed/lab12_model.db`（该文件已加入 `.gitignore`）。

## 8. 迁移说明与局限

- Power BI 的"关系视图"是图形化操作，本实验用 DDL 外键 + PRAGMA 校验替代：关系是否存在不再靠肉眼，而由数据库强制约束。
- 教材演示的 KDD99 中一个客户可持有多个账户、一个账户可有多张卡（真实 1:N）；本实验的模拟数据为简化的一卡一账户，关系基数虽为 1:N，但实际度数多为 1。校验逻辑对真实数据同样适用。
- 交叉筛选的"双向"在 SQL 里没有直接对应物，本实验用两个方向的查询结果做量化说明，不模拟 Power BI 的筛选传播引擎。

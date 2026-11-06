# lab09 信用卡用户画像（旗舰实验）

## 一、教材出处与业务背景

- 教材：第 9 章 9.4 信用卡用户画像（PDF p281-294），原案例为 **SQL 取数 + Excel 画像**。
- 业务问题：不同类型信用卡（普通卡/金卡/青年卡）的持卡人，在基本信息、交易行为、财务水平上有何差异？运营据此做差异化产品推荐与精准营销。
- 技术主线：三种用户标签（静态标签、时点标签、时期标签）→ 三段 SQL 生成 `Creditcard` 宽表 → Excel 画 5 张画像图。

## 二、教材三段取数逻辑（Python 复现）

### var1：基本信息（三表左连接）

```sql
select a.card_id, a.disp_id, a.issued, a.type, b.sex, datediff(a.issued, b.birth_date)/365 as age
from card a
left join disp c on a.disp_id = c.disp_id
left join clients b on c.client_id = b.client_id
```

pandas：`card.merge(disp).merge(clients)`，年龄 = `(issued - birth_date).days / 365`。

### var2：时点标签（不等值连接 + 聚合）

发卡前的所有交易 → 最近一次交易日距发卡天数 `last_days`、发卡前平均余额 `balance`。

pandas：按 `account_id` 合并后过滤 `trans.date < issued`，`groupby(card_id)` 取 `max(date)` 与 `mean(balance)`。

### var3：时期标签（发卡前 365 天窗口）

```sql
sum(if(type='借', amount, 0)) as trans_in_amount,
sum(if(type='贷', amount, 0)) as trans_out_amount,
count(*) as trans_count,
avg(balance) as avg_balance,
trans_out_amount / avg_balance as out_ratio,
trans_out_amount / trans_in_amount as out_in_ratio
```

pandas：窗口过滤 → 条件求和 → 计算两个比率。

最终 `Creditcard` 宽表 13 列：`card_id, disp_id, issued, type, sex, age, last_days, balance, trans_count, trans_in_amount, trans_out_amount, out_ratio, out_in_ratio`。

## 三、Python 迁移思路

| 教材（SQL + Excel） | 本实验（Python） |
|---|---|
| MySQL 三段 SQL | pandas 合并/过滤/分组，逐字段对应 |
| Excel 柱形图 | matplotlib 柱状图（发卡量、性别分布） |
| Excel 分类盒须图 | seaborn 盒须图（年龄、交易次数、余额） |
| 人工读图下结论 | 计算各卡类型中位数/占比并打印结论 |

实现分两层：

1. [data_prep.py](file:///c:/Users/fjwsm/Desktop/学习资料/大三上%20第一学期/商业数据分析/T/src/lab09/data_prep.py)：构造 4 张源表，`build_creditcard()` 复现三段取数；
2. [main.py](file:///c:/Users/fjwsm/Desktop/学习资料/大三上%20第一学期/商业数据分析/T/src/lab09/main.py)：画像统计 + 5 张图。

## 四、数据说明

本实验优先尝试下载公开 KDD99 金融数据集，但数据站点在本机网络下 DNS 解析失败（`Could not resolve host: sorry.vse.cz`），因此按书中表结构与画像结论**反向构造模拟数据**（固定种子 42）：

| 表 | 规模 |
|---|---|
| clients | 900 |
| disp | 900 |
| card | 900（普通卡 540 / 金卡 270 / 青年卡 90） |
| trans | 12,464（每卡发卡前 2 年 8~20 笔，一半落在发卡前 1 年） |

**数据为模拟还原，不代表真实银行客户。**

## 五、运行方式

```bash
cd T
python src/lab09/main.py
```

## 六、运行结果（与教材 5 条结论一致）

| 教材结论 | 模拟结果 |
|---|---|
| 普通卡发行量远多于青年卡和金卡 | 540（60%）/ 270（30%）/ 90（10%） |
| 金卡与普通卡年龄中位数接近，青年卡约 20 岁 | 42.7 / 40.4 / 20.3 岁 |
| 金卡男性占比大，普通卡/青年卡两性相当 | 71% / 52% / 51% |
| 三类卡交易次数相当 | 三类中位数均为 7 笔 |
| 余额中位数：金卡 > 普通卡 > 青年卡 | 62,169 / 35,786 / 11,977 元 |

运营含义：青年卡做年轻客群拉新、普通卡做大众留存、金卡做高净值经营；`out_ratio`、`out_in_ratio` 可作为活跃度与风险监控指标。

## 七、产物清单

| 文件 | 内容 |
|---|---|
| `lab09_card_count.png` | 各卡类型发卡量 |
| `lab09_age_box.png` | 持卡年龄盒须图 |
| `lab09_gender_type.png` | 性别 × 卡类型分布 |
| `lab09_trans_count_box.png` | 发卡前一年交易次数盒须图 |
| `lab09_balance_box.png` | 发卡前账户余额盒须图 |
| `lab09_creditcard.csv` | Creditcard 宽表（900 行 × 13 列） |
| `lab09_profile_summary.csv` | 各卡类型画像指标汇总 |

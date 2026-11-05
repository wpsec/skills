# 输入与报告结构

## report-data.json

asset_report.py 接收一个 UTF-8 JSON 对象：

- region：目标区域名称。
- scope：本次授权范围，包括可追溯的 `authorization_reference`、`authorized_units`、`authorized_ips`，以及单独的 `authorized_vendors`。只有区域名而无授权依据时，脚本不把任何资产写入主表。
- subregions：下级行政区名称数组。
- assets：资产记录数组。
- appendices：附表记录，键包括 subunits、icp_candidates、network_candidates、vendor_links、wildcard_candidates、name_mappings、leads。
- coverage：覆盖说明行数组。

资产记录字段映射：

- unit：规范单位名称
- name_variants：来源表中的简称、旧名、英文名、拼音等变体，归入单位名称映射表
- asset_type：资产类型
- host：域名或主机
- fofa_domain：FOFA domain 字段
- ip、ip_geo：IP 和 IP 属地
- port、protocol：仅记录来源中明确给出的端口/协议
- product、title、icp、cert_serial、cert_cn：服务、标题、备案和证书信息
- relation_status：confirmed 或 candidate
- scope_status：in_scope、scope_pending 或 out_of_scope；供应商仅在本次声明纳入范围时使用 in_scope
- relation_basis：可追溯的关联依据
- confidence：高/中/低
- source：来源平台、查询线索或来源 URL
- updated_at：本次采集时间
- subregion：经单位行政隶属/官方地址确认的下级行政区
- ip_geo_match：是否有可靠 IP 属地证据匹配目标区域

仅当授权依据存在、规范单位名称命中 `scope.authorized_units` 或 `scope.authorized_vendors`，且 `relation_status=confirmed`、`scope_status=in_scope` 时，资产进入区域/下级行政区主表；candidate、scope_pending、out_of_scope、未列入授权清单的记录不得进入主表。供应商范围必须单独列明。没有可靠 subregion 的已确认资产留在区域级工作表。工作表归属优先使用单位行政隶属；未知单位归属时使用可靠 IP 地理区划；两者冲突时留在区域级表并在关联依据注明，不凭标题猜区县。

## 主表字段

严格使用以下 17 列：

规范单位名称 | 资产类型 | 域名/主机 | FOFA domain字段 | IP | IP属地 | 端口/协议 | 服务/产品/版本 | 页面标题 | ICP备案号 | 证书序列号 | 证书Subject CN | 重点标注 | 关联依据 | 置信度 | 更新时间 | 数据来源

重点标注由生成脚本计算：relation_status=confirmed、ip_geo_match=true、标题命中 collection-methodology.md 关键词表三者同时成立。模型不能通过传入自定义“重点”绕过此条件。

## 附表

- 下属单位补充：属地、上级单位、下属单位、官方依据要点、域名线索、资产核验状态、依据链接1、依据链接2。
- ICP备案候选：关联单位、域名/主机、FOFA domain字段、IP、端口/协议、服务/产品、页面标题、ICP备案号、证书序列号、证书Subject CN、关联依据、置信度、数据来源。
- 网段候选：前缀长度、网段、相关单位/主机样例、网段内已知目标IP数、已知目标FOFA记录数、FOFA整段结果数量、置信度、说明。
- 供应商关联：属地、关联单位、目标主机、观察到的IP集合、端口/协议、关系依据、置信度、范围判定、范围边界。
- 泛解析候选：根域、测试标签、返回A、返回AAAA、返回CNAME、结论、数据来源。
- 单位名称映射：原始名称、规范单位名称/归属、来源类型、归并状态、来源文件。
- 待核源线索：名称/归属线索、标题/系统、属地、关系说明、来源文件。
- 覆盖说明：项目、结果、状态。

附表中已确认单位清单的 sheet 名为“下属单位补充”，覆盖统计与运行限制的 sheet 名为“覆盖说明”。按目标区域生成一个区域级工作表，并为各下级行政区生成工作表。工作表名称遵循 XLSX 31 字符限制；主表只放其行政归属明确的资产，不因 IP 共址复制记录。

## 输出约束

- 输出到工作区资产目录，文件名为“{区域}资产_fofa_shodan补全.xlsx”。
- 样表只作为字段、工作表结构和视觉格式参考；不读取、复制或继承其中任何数据行。
- 所有用户输入字符串按文本写入，禁止生成公式单元格；输出文件不得包含 API 凭据。
- 自动冻结首行、设置筛选和适当列宽；不增加样表没有的宽泛原始字段。
- 更新时间记录本次采集时间；平台最后观测时间有值时放入来源或关联依据。

## 平台查询计划

collect_passive.py 的输入 query-plan.json 采用以下结构。区域必填；调用平台前必须提供授权依据。名称查询绑定授权单位；Shodan 单 IP 查询必须命中授权 IP 清单。FOFA 查询还需确认当前账户下该检索不消耗 F 币；不得用该标记绕过实际额度反馈。

    {
      "region": "目标区域",
      "scope": {
        "authorization_reference": "演练授权编号或可追溯依据",
        "authorized_units": ["明确纳入范围的单位"],
        "authorized_ips": ["明确纳入范围的公网 IP"],
        "authorized_vendors": []
      },
      "fofa_queries": [{"query": "FOFA 查询语句", "unit": "规范单位", "label": "线索说明", "fpoint_free_confirmed": true}],
      "shodan_ips": ["已知公网 IP"],
      "shodan_queries": [{"query": "Shodan 查询语句", "unit": "规范单位", "label": "线索说明"}]
    }

脚本默认凭据目录为当前工作区根目录。先把 query-plan.json 和原始 JSONL 输出放到临时目录，再把经核验记录整理为 report-data.json。

    python3 scripts/normalize_inputs.py --region 西藏自治区 --input-dir /路径 --output /tmp/region-seeds.json
    python3 scripts/collect_passive.py --plan /tmp/query-plan.json --workdir /工作区 --output /tmp/platform-records.jsonl
    python3 scripts/asset_report.py --input /tmp/report-data.json --output /工作区/资产目录/西藏自治区资产_fofa_shodan补全.xlsx

官方 API 文档：[FOFA 连续翻页 API](https://fofa.info/api/batches_pages)；[Shodan REST API](https://developer.shodan.io/api)。

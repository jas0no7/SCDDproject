请你帮我仔细核查以下五个问题，次本地环境没有生产数据库 只核查代码逻辑
1、
    [panoramaOverview.py](modules/panoramaOverview.py)请你帮我看下这里面的。 DF.loc[DF['title'] == '
    公司回本进度', ['totalSite', 'rate', 'site']] = [str(i) for i in [d1, d3, d2]]中的
    totalSite 这个字段 应该和 [cityPublic_typeMonitoring.py](modules/cityPublic_typeMonitoring.py)中的{
    table_comment = "类型检测_横幅"
    column_comments = {
    'targetData': '横幅',
    'update_time': '更新日期'
    }
    DF_targetData = pd.DataFrame([{
    'targetData': json.dumps(targetData, ensure_ascii=False),
    'update_time': M
    }])中的{
    "title": "站点总数",
    "value": str(int(ybzdsl)),
    "unit": "座",
    "prefix": "共计"
    },}
    一致才对吧 都应该是 筛选的 【投运+停运】

2、
    [panoramaOverview.py](modules/panoramaOverview.py)请你帮我看下这里面的
    【 DF.loc[DF['title'] == '公司自建站点情况', ['chargingCable', 'chargingCapacity']] = [str(i) for i in
    [int(d10), f"{d11:.2f}"]]】中的
    chargingCable应该和[typeMonitoringOverview.py](modules/typeMonitoringOverview.py)中的
    {table_comment = "类型检测_首页_四川电动旗下基础设施建设现状"
    column_comments = {
    'infrastructure': '四川电动旗下基础设施建设现状',
    'update_time': '更新日期'
    }
    DF_scdd_Infrastructure = pd.DataFrame([{
    'infrastructure': infrastructure,
    'update_time': M
    }])
    
        import_data_with_cursor(
            df=DF_scdd_Infrastructure,
            table_name="dp_scdd_Infrastructure",
    
            table_comment=table_comment,
            column_comments=column_comments,
            append_data=False,
            update_columns=True
        )}
    
    中的 total_guns 一致吧。都是筛选的 【投运+停运】

3、
    [industryAndProvincialCompany.py](modules/industryAndProvincialCompany.py)中的  
    { DF = pd.DataFrame()
    x1 = [
    {'title': '累计接入充电枪数', 'value': d1, 'unit': '个'},
    {'title': '本年功率利用率', 'value': d2, 'unit': '%'},
    {'title': '本年累计充电量', 'value': d3, 'unit': '万kWh'},
    {'title': '本年累计充电收入', 'value': d4, 'unit': '万元'}]
    x1 = json.dumps(x1, ensure_ascii=False)
    DF = pd.DataFrame({
    'target': [x1],
    'month': [M]
    })
    DF
    
        # ### 数据存储
    
        # In[35]:
    
    
        # 定义注释
        table_comment = "产业单位接入情况页-产业单位接入情况-顶部的4个重点展示数据"
        column_comments = {
            'target': '重点指标展示1',
            'month': '年月'
        }
    
        # 执行导入（覆盖数据，更新列结构）
        import_data_with_cursor(
            df=DF,
            table_name="dp_industrial_unit_TopKeyMetrics1",
            table_comment=table_comment,
            column_comments=column_comments
        )}  和 {
        DF = pd.DataFrame()
        x1 = [
            {'title': '累计接入充电枪数', 'value': d1, 'unit': '个'},
            {'title': '本年功率利用率', 'value': d2, 'unit': '%'},
            {'title': '本年累计充电量', 'value': d3, 'unit': '万kWh'},
            {'title': '本年累计充电收入', 'value': d4, 'unit': '万元'}]
        x1 = json.dumps(x1, ensure_ascii=False)
        DF = pd.DataFrame({
            'target': [x1],
            'month': [M]
        })
        DF
    
        # ### 数据存储
    
        # In[39]:
    
    
        # 定义注释
        table_comment = "主业单位接入情况页-主业单位接入情况-顶部的4个重点展示数据"
        column_comments = {
            'target': '重点指标展示2',
            'month': '年月'
        }
    }
    应该分别和 [companyWarningOverview.py](modules/companyWarningOverview.py)中的 DF.loc[DF['title'] == '社会桩接入情况', ['chargingCable', 'chargingCapacity']] = [str(i) for i in
                                                                                          [int(d4), f"{d5:.2f}"]]
        DF.loc[DF['title'] == '产业单位接入情况', ['chargingCable', 'chargingCapacity']] = [str(i) for i in
                                                                                            [int(d6), f"{d7:.2f}"]]
    中的chargingCapacity 一致。应该都是 （投运+退运+停运） 三个 因为是累计的

4、
    [techUpgradeStation.py](modules/techUpgradeStation.py) 技改站点的{ table_comment = "技改站点_技改成效总览"
    column_comments = {
        'result': '技改成效总览',
        'update_time': '更新日期'
    }
    DF = pd.DataFrame([{
        'result': json.dumps(result, ensure_ascii=False),
        'update_time': M
    }])

    import_data_with_cursor(
        df=DF,
        table_name="dp_jigai_all",

        table_comment=table_comment,
        column_comments=column_comments,
        append_data=False,
        update_columns=True
    )}   为什么技改前的 故障率、停运率、离线率、一次成功率都为0.功率利用率变成了50.xx% 这种数字？正常应该是 个位数

5、
    社会桩的 本年功率利用率 是不是用的 平均值？ 怀疑跟下面的数值对不上
# 柜组数据导入说明

## 概述

本系统支持通过多种方式导入柜组（CounterGroup）的初始数据到数据库中。

## 数据格式

### 必需字段
- `group_code`: 柜组编码（唯一标识）
- `group_name`: 柜组名称
- `store_id`: 门店ID（数字）

### 可选字段
- `department_code`: 部门编码
- `department_name`: 部门名称
- `area_code`: 区域编码
- `area_name`: 区域名称
- `category_code`: 类别编码
- `category_name`: 类别名称
- `operation_method`: 经营方式（租赁/联营/自营）
- `brand_name`: 品牌名称
- `is_active`: 是否启用（true/false，默认为true）

## 导入方式

### 1. CSV文件导入

创建CSV文件，格式如下：

```csv
group_code,group_name,store_id,department_code,department_name,area_code,area_name,category_code,category_name,operation_method,brand_name,is_active
G001,女装柜组,1,D001,女装部,A001,东区,C001,服装,租赁,品牌A,true
G002,男装柜组,1,D002,男装部,A001,东区,C001,服装,联营,品牌B,true
```

运行导入命令：
```bash
cd python_app
python import_counter_groups.py csv your_data.csv
```

### 2. JSON文件导入

创建JSON文件，格式如下：

```json
[
  {
    "group_code": "G001",
    "group_name": "女装柜组",
    "store_id": 1,
    "department_code": "D001",
    "department_name": "女装部",
    "area_code": "A001",
    "area_name": "东区",
    "category_code": "C001",
    "category_name": "服装",
    "operation_method": "租赁",
    "brand_name": "品牌A",
    "is_active": true
  }
]
```

运行导入命令：
```bash
cd python_app
python import_counter_groups.py json your_data.json
```

### 3. 查看现有数据

查看数据库中现有的柜组数据：
```bash
cd python_app
python import_counter_groups.py list
```

## 使用步骤

1. **准备数据文件**
   - 根据您的数据格式选择CSV或JSON格式
   - 确保数据格式正确，特别是必需字段

2. **运行导入脚本**
   - 进入python_app目录
   - 执行相应的导入命令

3. **验证导入结果**
   - 使用list命令查看导入的数据
   - 检查数据是否正确

## 注意事项

- 如果柜组编码已存在，系统会跳过该记录
- 导入过程中如果出现错误，会回滚所有更改
- 建议先备份数据库再进行大量数据导入
- 确保数据库连接正常

## 示例文件

项目中提供了示例文件：
- `sample_counter_groups.csv` - CSV格式示例
- `sample_counter_groups.json` - JSON格式示例

您可以直接使用这些示例文件进行测试。

"""数据分析工具"""

from typing import Optional
from langchain_core.tools import tool
import pandas as pd
import io
import json


@tool
async def data_analyze(file_path: str, operation: str = "describe", columns: Optional[list] = None) -> str:
    """分析 CSV 或 Excel 文件的数据。支持多种分析操作如描述统计、分组、筛选等。"""
    try:
        # 根据文件扩展名确定读取方式
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            return f"Error: Unsupported file format. Only CSV and Excel files are supported: {file_path}"
        
        # 如果指定了列，则只选择这些列
        if columns:
            missing_cols = [col for col in columns if col not in df.columns]
            if missing_cols:
                return f"Error: Columns not found in file: {missing_cols}. Available columns: {list(df.columns)}"
            df = df[columns]
        
        # 执行不同的分析操作
        if operation == "describe":
            # 基本描述统计
            desc = df.describe(include='all')
            return f"Descriptive Statistics:\n{desc.to_string()}"
        
        elif operation == "head":
            # 显示前几行
            return f"First 5 rows:\n{df.head().to_string()}"
        
        elif operation == "info":
            # 数据框信息
            buffer = io.StringIO()
            df.info(buf=buffer)
            return f"DataFrame Info:\n{buffer.getvalue()}"
        
        elif operation == "columns":
            # 列出所有列名
            return f"Columns in dataset:\n{list(df.columns)}"
        
        elif operation == "shape":
            # 数据形状
            return f"Dataset shape: {df.shape} (rows, columns)"
        
        elif operation == "value_counts":
            # 如果指定了列，计算值计数
            if not columns or len(columns) != 1:
                return "Error: For value_counts operation, please specify exactly one column using the columns parameter."
            col = columns[0]
            value_counts = df[col].value_counts()
            return f"Value counts for column '{col}':\n{value_counts.to_string()}"
        
        else:
            return f"Error: Unsupported operation '{operation}'. Supported operations: describe, head, info, columns, shape, value_counts"
    
    except FileNotFoundError:
        return f"Error: File not found: {file_path}"
    except Exception as e:
        return f"Error analyzing data in {file_path}: {str(e)}"
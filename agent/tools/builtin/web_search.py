"""网络搜索工具"""

from typing import Optional
from langchain_core.tools import tool
import requests
from urllib.parse import urlencode
import json


@tool
async def web_search(query: str, num_results: int = 5, site: Optional[str] = None) -> str:
    """使用网络搜索引擎获取信息。支持限制结果数量和特定网站搜索。"""
    try:
        # 构建搜索查询
        search_query = query
        if site:
            search_query = f"site:{site} {query}"
        
        # 使用 DuckDuckGo API 进行搜索 (免费且无需API密钥)
        params = {
            'q': search_query,
            'format': 'json',
            'no_html': '1',
            'skip_disambig': '1',
            'limit': str(num_results)
        }
        
        search_url = f"https://api.duckduckgo.com/?{urlencode(params)}"
        
        response = requests.get(search_url, timeout=10)
        if response.status_code != 200:
            return f"Error: Search request failed with status code {response.status_code}"
        
        # 解析搜索结果
        data = response.json()
        
        # 提取相关结果
        results = []
        if 'RelatedTopics' in data:
            topics = data['RelatedTopics']
            for topic in topics[:num_results]:
                if 'FirstURL' in topic and 'Text' in topic:
                    results.append({
                        'title': topic.get('Text', 'No Title'),
                        'url': topic['FirstURL'],
                        'snippet': topic.get('Result', '')
                    })
        
        if not results:
            return f"No search results found for query: '{query}'"
        
        # 格式化输出
        output = f"Search results for: '{query}'\n"
        output += "=" * 50 + "\n"
        
        for i, result in enumerate(results, 1):
            output += f"{i}. {result['title']}\n"
            output += f"   URL: {result['url']}\n"
            output += f"   Snippet: {result['snippet'][:200]}...\n\n"
        
        return output.strip()
    
    except requests.RequestException as e:
        return f"Error performing search: {str(e)}"
    except json.JSONDecodeError:
        return f"Error: Could not parse search results"
    except Exception as e:
        return f"Error in web_search: {str(e)}"
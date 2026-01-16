import requests
import json
import time
from scripts.user_agent_generator import get_random_user_agent

def search_reddit_posts(keyword, limit=5):
    # 1. 构造搜索 URL
    # limit 参数控制返回数量
    # sort 参数可以是 'relevance' (相关度), 'new' (最新), 'top' (热度)
    base_url = "https://www.reddit.com/search.json"
    params = {
        'q': keyword,
        'limit': limit,
        'sort': 'relevance', 
        'type': 'link' # 限制为帖子，不搜用户
    }

    # 2. 伪装 Header (非常重要，否则直接 429/403)
    headers = {
        'User-Agent': get_random_user_agent()
    }

    print(f"正在搜索: {keyword} ...")
    
    try:
        response = requests.get(base_url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            posts = data['data']['children']
            
            results = []
            
            for index, post in enumerate(posts):
                post_data = post['data']
                
                # 提取关键信息
                title = post_data.get('title', 'No Title')
                url = post_data.get('url', '')
                # selftext 是纯文本内容
                content = post_data.get('selftext', '')
                author = post_data.get('author', 'Unknown')
                permalink = f"https://www.reddit.com{post_data.get('permalink')}"
                
                print(f"\n--- 第 {index + 1} 个帖子 ---")
                print(f"标题: {title}")
                print(f"链接: {permalink}")
                # 简单的文本清理，如果是空内容（比如只有图片的帖子），做个标记
                if content:
                    print(f"内容预览: {content[:100].replace(chr(10), ' ')}...") 
                else:
                    print("内容: [非文本帖子或只有标题/图片]")
                
                # 如果你需要保存完整内容，可以在这里存入 list 或写入文件
                results.append({
                    'title': title,
                    'content': content,
                    'link': permalink
                })
            
            return results

        elif response.status_code == 429:
            print("错误：请求过快 (Rate Limit)。Reddit 限制了你的 IP。")
        else:
            print(f"错误：状态码 {response.status_code}")
            
    except Exception as e:
        print(f"发生异常: {e}")

# 执行搜索
# 关键词可以是英文或中文，requests 会自动 URL 编码
search_reddit_posts("deepseek new model", limit=5)

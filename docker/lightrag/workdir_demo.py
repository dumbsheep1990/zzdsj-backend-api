"""
LightRAG工作目录管理示例
演示如何通过API动态创建和管理工作目录
"""
import os
import sys
import json
import argparse
import requests

# 添加项目根目录到sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    # 尝试导入项目API客户端
    from app.frameworks.lightrag.api_client import get_lightrag_api_client
    USE_PROJECT_CLIENT = True
except ImportError:
    # 回退到独立模式
    USE_PROJECT_CLIENT = False
    print("警告: 无法导入项目API客户端，将使用独立模式")


class WorkdirManager:
    """工作目录管理示例"""
    
    def __init__(self, api_url="http://localhost:9621"):
        """初始化工作目录管理器"""
        self.api_url = api_url
        
        # 根据可用性使用不同的客户端
        if USE_PROJECT_CLIENT:
            self.client = get_lightrag_api_client()
            print(f"使用项目API客户端连接 {self.client.base_url}")
        else:
            self.client = None
            print(f"使用独立模式连接 {api_url}")
    
    def health_check(self):
        """检查服务健康状态"""
        if self.client:
            return self.client.health_check()
        
        try:
            response = requests.get(f"{self.api_url}/health")
            if response.status_code == 200:
                print("服务健康状态: 正常")
                return {"success": True, "data": response.json()}
            else:
                print(f"服务健康状态: 异常 (状态码: {response.status_code})")
                return {"success": False, "error": response.text}
        except Exception as e:
            print(f"无法连接到LightRAG服务: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def list_workdirs(self):
        """列出所有工作目录"""
        print("\n=== 工作目录列表 ===")
        
        if self.client:
            result = self.client.list_workdirs()
            if result["success"]:
                workdirs = result["data"]
                if not workdirs:
                    print("  暂无工作目录")
                else:
                    for idx, workdir in enumerate(workdirs, 1):
                        print(f"  {idx}. {workdir.get('graph_id', workdir)}")
            else:
                print(f"获取工作目录列表失败: {result.get('error', '')}")
            return result
        
        try:
            response = requests.get(f"{self.api_url}/graphs")
            if response.status_code == 200:
                workdirs = response.json()
                if not workdirs:
                    print("  暂无工作目录")
                else:
                    for idx, workdir in enumerate(workdirs, 1):
                        print(f"  {idx}. {workdir.get('graph_id', workdir)}")
                return {"success": True, "data": workdirs}
            else:
                print(f"获取工作目录列表失败: {response.text}")
                return {"success": False, "error": response.text}
        except Exception as e:
            print(f"列出工作目录时出错: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_workdir(self, workdir_id, description=None):
        """创建新的工作目录"""
        print(f"\n=== 创建工作目录: {workdir_id} ===")
        
        if self.client:
            result = self.client.create_workdir(workdir_id, description)
            if result["success"]:
                print(f"工作目录 '{workdir_id}' 创建成功!")
            else:
                print(f"创建工作目录失败: {result.get('error', '')}")
            return result
        
        try:
            data = {"graph_id": workdir_id}
            if description:
                data["description"] = description
                
            response = requests.post(f"{self.api_url}/graphs", json=data)
            if response.status_code in (200, 201):
                print(f"工作目录 '{workdir_id}' 创建成功!")
                return {"success": True, "data": response.json() if response.text else {}}
            else:
                print(f"创建工作目录失败: {response.text}")
                return {"success": False, "error": response.text}
        except Exception as e:
            print(f"创建工作目录时出错: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def delete_workdir(self, workdir_id):
        """删除工作目录"""
        print(f"\n=== 删除工作目录: {workdir_id} ===")
        
        if self.client:
            result = self.client.delete_workdir(workdir_id)
            if result["success"]:
                print(f"工作目录 '{workdir_id}' 删除成功!")
            else:
                print(f"删除工作目录失败: {result.get('error', '')}")
            return result
            
        try:
            response = requests.delete(f"{self.api_url}/graphs/{workdir_id}")
            if response.status_code in (200, 204):
                print(f"工作目录 '{workdir_id}' 删除成功!")
                return {"success": True}
            else:
                print(f"删除工作目录失败: {response.text}")
                return {"success": False, "error": response.text}
        except Exception as e:
            print(f"删除工作目录时出错: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_workdir_stats(self, workdir_id):
        """获取工作目录统计信息"""
        print(f"\n=== 工作目录统计: {workdir_id} ===")
        
        if self.client:
            result = self.client.get_workdir_stats(workdir_id)
            if result["success"]:
                stats = result["data"]
                print(f"  文档数量: {stats.get('document_count', 0)}")
                print(f"  节点数量: {stats.get('node_count', 0)}")
                print(f"  关系数量: {stats.get('relation_count', 0)}")
            else:
                print(f"获取统计信息失败: {result.get('error', '')}")
            return result
            
        try:
            response = requests.get(f"{self.api_url}/graphs/{workdir_id}/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"  文档数量: {stats.get('document_count', 0)}")
                print(f"  节点数量: {stats.get('node_count', 0)}")
                print(f"  关系数量: {stats.get('relation_count', 0)}")
                return {"success": True, "data": stats}
            else:
                print(f"获取统计信息失败: {response.text}")
                return {"success": False, "error": response.text}
        except Exception as e:
            print(f"获取工作目录统计信息时出错: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def add_text_document(self, workdir_id, text, description=None):
        """向工作目录添加文本文档"""
        print(f"\n=== 添加文本到工作目录: {workdir_id} ===")
        
        if self.client:
            result = self.client.upload_text(text, workdir_id, description)
            if result["success"]:
                print("文本添加成功!")
            else:
                print(f"添加文本失败: {result.get('error', '')}")
            return result
            
        try:
            data = {
                "text": text,
                "graph_id": workdir_id
            }
            if description:
                data["description"] = description
                
            response = requests.post(f"{self.api_url}/documents/text", json=data)
            if response.status_code in (200, 201):
                print("文本添加成功!")
                return {"success": True, "data": response.json() if response.text else {}}
            else:
                print(f"添加文本失败: {response.text}")
                return {"success": False, "error": response.text}
        except Exception as e:
            print(f"添加文本时出错: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def run_interactive_demo(self):
        """运行交互式演示"""
        print("\n=== LightRAG工作目录管理演示 ===")
        print(f"API地址: {self.api_url}")
        
        # 检查服务健康状态
        health = self.health_check()
        if not health["success"]:
            print("服务不可用，请检查LightRAG API服务是否正常运行")
            return
        
        # 列出现有工作目录
        self.list_workdirs()
        
        while True:
            print("\n--- 可用操作 ---")
            print("1. 创建工作目录")
            print("2. 列出工作目录")
            print("3. 查看工作目录统计")
            print("4. 添加文本到工作目录")
            print("5. 删除工作目录")
            print("6. 退出")
            
            choice = input("\n请选择操作 (1-6): ")
            
            if choice == "1":
                workdir_id = input("输入工作目录ID: ")
                description = input("输入描述(可选): ")
                self.create_workdir(workdir_id, description)
            
            elif choice == "2":
                self.list_workdirs()
            
            elif choice == "3":
                workdir_id = input("输入工作目录ID: ")
                self.get_workdir_stats(workdir_id)
            
            elif choice == "4":
                workdir_id = input("输入工作目录ID: ")
                description = input("输入文档描述(可选): ")
                text = input("输入文本内容: ")
                self.add_text_document(workdir_id, text, description)
            
            elif choice == "5":
                workdir_id = input("输入要删除的工作目录ID: ")
                confirm = input(f"确定删除工作目录 '{workdir_id}'? (y/n): ")
                if confirm.lower() == 'y':
                    self.delete_workdir(workdir_id)
            
            elif choice == "6":
                print("退出演示")
                break
                
            else:
                print("无效选择，请重试")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="LightRAG工作目录管理演示")
    parser.add_argument("--url", default="http://localhost:9621", help="LightRAG API地址")
    parser.add_argument("--workdir", help="要操作的工作目录ID")
    parser.add_argument("--mode", choices=["interactive", "list", "create", "delete", "stats", "add-text"], 
                        default="interactive", help="操作模式")
    parser.add_argument("--text", help="添加文本模式下的文本内容")
    parser.add_argument("--description", help="描述信息")
    
    args = parser.parse_args()
    
    manager = WorkdirManager(args.url)
    
    # 执行健康检查
    health = manager.health_check()
    if not health["success"] and args.mode != "interactive":
        print("服务不可用，无法继续操作")
        return
    
    # 根据模式执行不同操作
    if args.mode == "interactive":
        manager.run_interactive_demo()
    
    elif args.mode == "list":
        manager.list_workdirs()
    
    elif args.mode == "create":
        if not args.workdir:
            print("错误: 创建模式需要指定--workdir参数")
            return
        manager.create_workdir(args.workdir, args.description)
    
    elif args.mode == "delete":
        if not args.workdir:
            print("错误: 删除模式需要指定--workdir参数")
            return
        manager.delete_workdir(args.workdir)
    
    elif args.mode == "stats":
        if not args.workdir:
            print("错误: 统计模式需要指定--workdir参数")
            return
        manager.get_workdir_stats(args.workdir)
    
    elif args.mode == "add-text":
        if not args.workdir or not args.text:
            print("错误: 添加文本模式需要同时指定--workdir和--text参数")
            return
        manager.add_text_document(args.workdir, args.text, args.description)


if __name__ == "__main__":
    main()

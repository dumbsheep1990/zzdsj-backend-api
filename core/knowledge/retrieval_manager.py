"""
检索管理器 - 核心业务逻辑
提供知识检索和混合搜索功能
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

# 导入数据访问层
from app.repositories.knowledge import DocumentChunkRepository

logger = logging.getLogger(__name__)


class RetrievalManager:
    """检索管理器 - 核心业务逻辑类"""
    
    def __init__(self, db: Session):
        """初始化检索管理器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.chunk_repository = DocumentChunkRepository(db)
        
    # ============ 检索方法 ============
    
    async def semantic_search(
        self,
        query: str,
        kb_id: str,
        top_k: int = 10,
        threshold: float = 0.7,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """语义搜索
        
        Args:
            query: 查询文本
            kb_id: 知识库ID
            top_k: 返回结果数量
            threshold: 相似度阈值
            filters: 过滤条件
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        try:
            if not query or not query.strip():
                return {
                    "success": False,
                    "error": "查询文本不能为空",
                    "error_code": "EMPTY_QUERY"
                }
            
            # 1. 将查询文本转换为向量
            # 这里应该调用嵌入服务
            query_vector = [0.1] * 1536  # 模拟查询向量
            
            # 2. 向量相似性搜索
            # 这里应该调用向量数据库搜索
            # 模拟搜索结果
            vector_results = []
            for i in range(min(top_k, 5)):
                similarity = 0.9 - (i * 0.1)
                if similarity >= threshold:
                    vector_results.append({
                        "chunk_id": f"chunk_{i}",
                        "similarity": similarity,
                        "content": f"模拟内容 {i}",
                        "metadata": {
                            "document_id": f"doc_{i}",
                            "position": i
                        }
                    })
            
            # 3. 获取完整的分块信息
            results = []
            for result in vector_results:
                # 这里应该从数据库获取完整的分块信息
                chunk_data = {
                    "id": result["chunk_id"],
                    "content": result["content"],
                    "similarity": result["similarity"],
                    "metadata": result["metadata"],
                    "document_id": result["metadata"]["document_id"],
                    "kb_id": kb_id
                }
                results.append(chunk_data)
            
            logger.info(f"语义搜索完成，查询: '{query}', 返回 {len(results)} 个结果")
            
            return {
                "success": True,
                "data": {
                    "query": query,
                    "results": results,
                    "total": len(results),
                    "search_type": "semantic",
                    "kb_id": kb_id,
                    "parameters": {
                        "top_k": top_k,
                        "threshold": threshold,
                        "filters": filters
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"语义搜索失败: {str(e)}")
            return {
                "success": False,
                "error": f"语义搜索失败: {str(e)}",
                "error_code": "SEMANTIC_SEARCH_FAILED"
            }
    
    async def keyword_search(
        self,
        query: str,
        kb_id: str,
        top_k: int = 10,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """关键词搜索
        
        Args:
            query: 查询文本
            kb_id: 知识库ID
            top_k: 返回结果数量
            filters: 过滤条件
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        try:
            if not query or not query.strip():
                return {
                    "success": False,
                    "error": "查询文本不能为空",
                    "error_code": "EMPTY_QUERY"
                }
            
            # 这里应该实现全文搜索逻辑
            # 可以使用 PostgreSQL 的全文搜索或 Elasticsearch
            
            # 模拟关键词搜索结果
            results = []
            keywords = query.strip().split()
            
            for i in range(min(top_k, 3)):
                # 模拟匹配分数
                score = 1.0 - (i * 0.2)
                results.append({
                    "id": f"chunk_kw_{i}",
                    "content": f"包含关键词 {keywords[0] if keywords else 'test'} 的模拟内容 {i}",
                    "score": score,
                    "matched_keywords": keywords[:2],  # 模拟匹配的关键词
                    "metadata": {
                        "document_id": f"doc_kw_{i}",
                        "position": i
                    },
                    "document_id": f"doc_kw_{i}",
                    "kb_id": kb_id
                })
            
            logger.info(f"关键词搜索完成，查询: '{query}', 返回 {len(results)} 个结果")
            
            return {
                "success": True,
                "data": {
                    "query": query,
                    "results": results,
                    "total": len(results),
                    "search_type": "keyword",
                    "kb_id": kb_id,
                    "parameters": {
                        "top_k": top_k,
                        "filters": filters
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"关键词搜索失败: {str(e)}")
            return {
                "success": False,
                "error": f"关键词搜索失败: {str(e)}",
                "error_code": "KEYWORD_SEARCH_FAILED"
            }
    
    async def hybrid_search(
        self,
        query: str,
        kb_id: str,
        top_k: int = 10,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        threshold: float = 0.5,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """混合搜索（语义搜索 + 关键词搜索）
        
        Args:
            query: 查询文本
            kb_id: 知识库ID
            top_k: 返回结果数量
            semantic_weight: 语义搜索权重
            keyword_weight: 关键词搜索权重
            threshold: 最终分数阈值
            filters: 过滤条件
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        try:
            if not query or not query.strip():
                return {
                    "success": False,
                    "error": "查询文本不能为空",
                    "error_code": "EMPTY_QUERY"
                }
            
            # 验证权重
            if abs(semantic_weight + keyword_weight - 1.0) > 0.01:
                return {
                    "success": False,
                    "error": "语义搜索权重和关键词搜索权重之和必须等于1.0",
                    "error_code": "INVALID_WEIGHTS"
                }
            
            # 1. 执行语义搜索
            semantic_result = await self.semantic_search(
                query, kb_id, top_k * 2, 0.0, filters  # 获取更多结果，阈值设为0
            )
            
            # 2. 执行关键词搜索
            keyword_result = await self.keyword_search(
                query, kb_id, top_k * 2, filters
            )
            
            if not semantic_result["success"] or not keyword_result["success"]:
                return {
                    "success": False,
                    "error": "子搜索失败",
                    "error_code": "SUB_SEARCH_FAILED"
                }
            
            # 3. 合并和重新排序结果
            combined_results = {}
            
            # 处理语义搜索结果
            for result in semantic_result["data"]["results"]:
                chunk_id = result["id"]
                semantic_score = result.get("similarity", 0.0)
                
                combined_results[chunk_id] = {
                    "id": chunk_id,
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "document_id": result["document_id"],
                    "kb_id": kb_id,
                    "semantic_score": semantic_score,
                    "keyword_score": 0.0,
                    "final_score": semantic_score * semantic_weight
                }
            
            # 处理关键词搜索结果
            for result in keyword_result["data"]["results"]:
                chunk_id = result["id"]
                keyword_score = result.get("score", 0.0)
                
                if chunk_id in combined_results:
                    # 更新现有结果
                    combined_results[chunk_id]["keyword_score"] = keyword_score
                    combined_results[chunk_id]["final_score"] = (
                        combined_results[chunk_id]["semantic_score"] * semantic_weight +
                        keyword_score * keyword_weight
                    )
                else:
                    # 添加新结果
                    combined_results[chunk_id] = {
                        "id": chunk_id,
                        "content": result["content"],
                        "metadata": result["metadata"],
                        "document_id": result["document_id"],
                        "kb_id": kb_id,
                        "semantic_score": 0.0,
                        "keyword_score": keyword_score,
                        "final_score": keyword_score * keyword_weight
                    }
            
            # 4. 过滤和排序
            filtered_results = [
                result for result in combined_results.values()
                if result["final_score"] >= threshold
            ]
            
            # 按最终分数排序
            filtered_results.sort(key=lambda x: x["final_score"], reverse=True)
            
            # 取前 top_k 个结果
            final_results = filtered_results[:top_k]
            
            logger.info(f"混合搜索完成，查询: '{query}', 返回 {len(final_results)} 个结果")
            
            return {
                "success": True,
                "data": {
                    "query": query,
                    "results": final_results,
                    "total": len(final_results),
                    "search_type": "hybrid",
                    "kb_id": kb_id,
                    "parameters": {
                        "top_k": top_k,
                        "semantic_weight": semantic_weight,
                        "keyword_weight": keyword_weight,
                        "threshold": threshold,
                        "filters": filters
                    },
                    "sub_results": {
                        "semantic_count": len(semantic_result["data"]["results"]),
                        "keyword_count": len(keyword_result["data"]["results"]),
                        "combined_count": len(combined_results),
                        "filtered_count": len(filtered_results)
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"混合搜索失败: {str(e)}")
            return {
                "success": False,
                "error": f"混合搜索失败: {str(e)}",
                "error_code": "HYBRID_SEARCH_FAILED"
            }
    
    async def search_by_document(
        self,
        query: str,
        doc_id: str,
        search_type: str = "hybrid",
        top_k: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """在特定文档中搜索
        
        Args:
            query: 查询文本
            doc_id: 文档ID
            search_type: 搜索类型 (semantic, keyword, hybrid)
            top_k: 返回结果数量
            **kwargs: 其他搜索参数
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        try:
            # 添加文档过滤条件
            filters = kwargs.get("filters", {})
            filters["document_id"] = doc_id
            kwargs["filters"] = filters
            
            # 根据搜索类型调用相应方法
            if search_type == "semantic":
                return await self.semantic_search(query, "", top_k, **kwargs)
            elif search_type == "keyword":
                return await self.keyword_search(query, "", top_k, **kwargs)
            elif search_type == "hybrid":
                return await self.hybrid_search(query, "", top_k, **kwargs)
            else:
                return {
                    "success": False,
                    "error": f"不支持的搜索类型: {search_type}",
                    "error_code": "INVALID_SEARCH_TYPE"
                }
                
        except Exception as e:
            logger.error(f"文档内搜索失败: {str(e)}")
            return {
                "success": False,
                "error": f"文档内搜索失败: {str(e)}",
                "error_code": "DOCUMENT_SEARCH_FAILED"
            }
    
    # ============ 检索配置方法 ============
    
    def get_search_strategies(self) -> Dict[str, Any]:
        """获取可用的搜索策略
        
        Returns:
            Dict[str, Any]: 搜索策略列表
        """
        strategies = {
            "semantic": {
                "name": "语义搜索",
                "description": "基于向量相似度的语义搜索，理解查询意图",
                "parameters": {
                    "top_k": {"type": "int", "default": 10, "min": 1, "max": 100},
                    "threshold": {"type": "float", "default": 0.7, "min": 0.0, "max": 1.0}
                },
                "pros": ["理解语义", "处理同义词", "跨语言支持"],
                "cons": ["计算开销大", "需要向量化"]
            },
            "keyword": {
                "name": "关键词搜索",
                "description": "基于关键词匹配的传统搜索",
                "parameters": {
                    "top_k": {"type": "int", "default": 10, "min": 1, "max": 100}
                },
                "pros": ["速度快", "精确匹配", "易于理解"],
                "cons": ["无法理解语义", "同义词问题"]
            },
            "hybrid": {
                "name": "混合搜索",
                "description": "结合语义搜索和关键词搜索的优势",
                "parameters": {
                    "top_k": {"type": "int", "default": 10, "min": 1, "max": 100},
                    "semantic_weight": {"type": "float", "default": 0.7, "min": 0.0, "max": 1.0},
                    "keyword_weight": {"type": "float", "default": 0.3, "min": 0.0, "max": 1.0},
                    "threshold": {"type": "float", "default": 0.5, "min": 0.0, "max": 1.0}
                },
                "pros": ["综合优势", "灵活权重", "更好的召回率"],
                "cons": ["配置复杂", "计算开销较大"]
            }
        }
        
        return {
            "success": True,
            "data": {"strategies": strategies}
        }
    
    def validate_search_config(
        self,
        strategy: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证搜索配置
        
        Args:
            strategy: 搜索策略
            parameters: 搜索参数
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            strategies = self.get_search_strategies()["data"]["strategies"]
            
            if strategy not in strategies:
                return {
                    "success": False,
                    "error": f"不支持的搜索策略: {strategy}",
                    "error_code": "INVALID_STRATEGY"
                }
            
            strategy_config = strategies[strategy]
            errors = []
            
            # 验证参数
            for param_name, param_config in strategy_config["parameters"].items():
                if param_name in parameters:
                    value = parameters[param_name]
                    param_type = param_config["type"]
                    
                    # 类型检查
                    if param_type == "int" and not isinstance(value, int):
                        errors.append(f"参数 {param_name} 必须是整数")
                    elif param_type == "float" and not isinstance(value, (int, float)):
                        errors.append(f"参数 {param_name} 必须是数字")
                    
                    # 范围检查
                    if "min" in param_config and value < param_config["min"]:
                        errors.append(f"参数 {param_name} 不能小于 {param_config['min']}")
                    if "max" in param_config and value > param_config["max"]:
                        errors.append(f"参数 {param_name} 不能大于 {param_config['max']}")
            
            # 混合搜索特殊验证
            if strategy == "hybrid":
                semantic_weight = parameters.get("semantic_weight", 0.7)
                keyword_weight = parameters.get("keyword_weight", 0.3)
                if abs(semantic_weight + keyword_weight - 1.0) > 0.01:
                    errors.append("语义搜索权重和关键词搜索权重之和必须等于1.0")
            
            if errors:
                return {
                    "success": False,
                    "error": "参数验证失败: " + "; ".join(errors),
                    "error_code": "INVALID_PARAMETERS"
                }
            
            return {
                "success": True,
                "data": {"validated": True}
            }
            
        except Exception as e:
            logger.error(f"验证搜索配置失败: {str(e)}")
            return {
                "success": False,
                "error": f"验证搜索配置失败: {str(e)}",
                "error_code": "VALIDATION_FAILED"
            }
    
    # ============ 统计方法 ============
    
    async def get_search_stats(self, kb_id: str = None) -> Dict[str, Any]:
        """获取搜索统计信息
        
        Args:
            kb_id: 知识库ID（可选）
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            # 这里应该从搜索日志或统计表中获取真实数据
            # 目前返回模拟数据
            stats = {
                "total_searches": 1000,
                "semantic_searches": 600,
                "keyword_searches": 250,
                "hybrid_searches": 150,
                "avg_response_time": 0.5,  # 秒
                "avg_results_per_search": 8.5,
                "popular_queries": [
                    {"query": "如何使用API", "count": 50},
                    {"query": "配置说明", "count": 35},
                    {"query": "错误处理", "count": 28}
                ]
            }
            
            if kb_id:
                stats["kb_id"] = kb_id
            
            return {
                "success": True,
                "data": stats
            }
            
        except Exception as e:
            logger.error(f"获取搜索统计信息失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取搜索统计信息失败: {str(e)}",
                "error_code": "STATS_FAILED"
            } 
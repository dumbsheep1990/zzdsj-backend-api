#!/usr/bin/env python3
"""
Elasticsearch初始化脚本
配置混合检索所需的索引模板、映射和搜索模板
确保ES存储能够完全支持混合检索功能
"""

import json
import sys
import time
import logging
from typing import Dict, Any, Optional
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, RequestError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ElasticsearchInitializer:
    """Elasticsearch初始化器"""
    
    def __init__(self, es_url: str = "http://localhost:9200", 
                 username: Optional[str] = None, 
                 password: Optional[str] = None):
        """初始化ES客户端"""
        self.es_url = es_url
        
        # 构建连接参数
        es_kwargs = {}
        if username and password:
            es_kwargs["basic_auth"] = (username, password)
        
        try:
            self.client = Elasticsearch(es_url, **es_kwargs)
            self.client.cluster.health()
            logger.info(f"成功连接到Elasticsearch: {es_url}")
        except Exception as e:
            logger.error(f"无法连接到Elasticsearch: {e}")
            raise
    
    def wait_for_es(self, timeout: int = 60) -> bool:
        """等待ES服务就绪"""
        logger.info("等待Elasticsearch服务就绪...")
        
        for i in range(timeout):
            try:
                health = self.client.cluster.health()
                if health.get("status") in ["yellow", "green"]:
                    logger.info(f"Elasticsearch就绪，状态: {health.get('status')}")
                    return True
            except Exception:
                pass
            
            time.sleep(1)
            if i % 10 == 0:
                logger.info(f"等待中... ({i}/{timeout})")
        
        logger.error("Elasticsearch服务未在指定时间内就绪")
        return False
    
    def create_index_template(self) -> bool:
        """创建混合检索索引模板"""
        template_name = "zzdsj-hybrid-search-template"
        
        template_config = {
            "index_patterns": ["kb_*", "document_*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "chinese_analyzer": {
                                "type": "custom",
                                "tokenizer": "ik_max_word",
                                "filter": ["lowercase", "stop"]
                            },
                            "chinese_search_analyzer": {
                                "type": "custom", 
                                "tokenizer": "ik_smart",
                                "filter": ["lowercase", "stop"]
                            }
                        }
                    },
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 100
                    }
                },
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "knowledge_base_id": {"type": "keyword"},
                        "title": {
                            "type": "text",
                            "analyzer": "chinese_analyzer",
                            "search_analyzer": "chinese_search_analyzer",
                            "fields": {
                                "keyword": {"type": "keyword"},
                                "suggest": {
                                    "type": "completion",
                                    "analyzer": "chinese_analyzer"
                                }
                            }
                        },
                        "content": {
                            "type": "text",
                            "analyzer": "chinese_analyzer", 
                            "search_analyzer": "chinese_search_analyzer",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        "content_vector": {
                            "type": "dense_vector",
                            "dims": 1536,
                            "index": True,
                            "similarity": "cosine"
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "source": {"type": "keyword"},
                                "page": {"type": "integer"},
                                "section": {"type": "keyword"},
                                "created_at": {"type": "date"},
                                "updated_at": {"type": "date"}
                            }
                        },
                        "chunk_index": {"type": "integer"},
                        "chunk_total": {"type": "integer"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"}
                    }
                }
            }
        }
        
        try:
            # 检查模板是否存在
            if self.client.indices.exists_index_template(name=template_name):
                logger.info(f"索引模板 {template_name} 已存在，正在更新...")
                self.client.indices.delete_index_template(name=template_name)
            
            # 创建新模板
            self.client.indices.put_index_template(
                name=template_name,
                body=template_config
            )
            logger.info(f"成功创建索引模板: {template_name}")
            return True
            
        except Exception as e:
            logger.error(f"创建索引模板失败: {e}")
            return False
    
    def create_search_templates(self) -> bool:
        """创建混合搜索模板"""
        templates = {
            "hybrid_search_template": {
                "script": {
                    "lang": "mustache",
                    "source": {
                        "query": {
                            "script_score": {
                                "query": {
                                    "bool": {
                                        "should": [
                                            {
                                                "multi_match": {
                                                    "query": "{{text_query}}",
                                                    "fields": [
                                                        "title^{{title_boost}}",
                                                        "content^{{content_boost}}"
                                                    ],
                                                    "type": "best_fields",
                                                    "boost": "{{text_boost}}"
                                                }
                                            }
                                        ],
                                        "minimum_should_match": 1
                                    }
                                },
                                "script": {
                                    "source": "cosineSimilarity(params.query_vector, 'content_vector') * params.vector_boost + _score * params.text_boost",
                                    "params": {
                                        "query_vector": "{{query_vector}}",
                                        "vector_boost": "{{vector_boost}}",
                                        "text_boost": "{{text_boost}}"
                                    }
                                }
                            }
                        },
                        "size": "{{size}}",
                        "_source": "{{source_fields}}"
                    }
                }
            },
            "vector_search_template": {
                "script": {
                    "lang": "mustache",
                    "source": {
                        "query": {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {
                                    "source": "cosineSimilarity(params.query_vector, 'content_vector')",
                                    "params": {
                                        "query_vector": "{{query_vector}}"
                                    }
                                }
                            }
                        },
                        "size": "{{size}}",
                        "_source": "{{source_fields}}"
                    }
                }
            },
            "keyword_search_template": {
                "script": {
                    "lang": "mustache",
                    "source": {
                        "query": {
                            "multi_match": {
                                "query": "{{text_query}}",
                                "fields": [
                                    "title^{{title_boost}}",
                                    "content^{{content_boost}}"
                                ],
                                "type": "best_fields"
                            }
                        },
                        "size": "{{size}}",
                        "_source": "{{source_fields}}"
                    }
                }
            }
        }
        
        success_count = 0
        for template_name, template_config in templates.items():
            try:
                # 检查模板是否存在
                if self.client.cluster.state()["metadata"].get("stored_scripts", {}).get(template_name):
                    logger.info(f"搜索模板 {template_name} 已存在，正在更新...")
                
                # 创建或更新模板
                self.client.put_script(
                    id=template_name,
                    body=template_config
                )
                logger.info(f"成功创建搜索模板: {template_name}")
                success_count += 1
                
            except Exception as e:
                logger.error(f"创建搜索模板 {template_name} 失败: {e}")
        
        return success_count == len(templates)
    
    def create_default_pipeline(self) -> bool:
        """创建文档处理管道"""
        pipeline_name = "zzdsj-document-pipeline"
        
        pipeline_config = {
            "description": "智政知识库文档处理管道",
            "processors": [
                {
                    "set": {
                        "field": "indexed_at",
                        "value": "{{_ingest.timestamp}}"
                    }
                },
                {
                    "script": {
                        "source": """
                        if (ctx.content != null && ctx.content.length() > 0) {
                            ctx.content_length = ctx.content.length();
                            ctx.word_count = ctx.content.split("\\s+").length;
                        }
                        """,
                        "ignore_failure": true
                    }
                }
            ]
        }
        
        try:
            self.client.ingest.put_pipeline(
                id=pipeline_name,
                body=pipeline_config
            )
            logger.info(f"成功创建处理管道: {pipeline_name}")
            return True
            
        except Exception as e:
            logger.error(f"创建处理管道失败: {e}")
            return False
    
    def test_hybrid_search(self) -> bool:
        """测试混合检索功能"""
        test_index = "test_hybrid_search"
        
        try:
            # 创建测试索引
            if self.client.indices.exists(index=test_index):
                self.client.indices.delete(index=test_index)
            
            # 插入测试文档
            test_doc = {
                "id": "test_001",
                "title": "测试文档",
                "content": "这是一个测试文档，用于验证混合检索功能",
                "content_vector": [0.1] * 1536,  # 测试向量
                "knowledge_base_id": "test_kb",
                "metadata": {
                    "source": "test",
                    "created_at": "2024-01-01T00:00:00Z"
                }
            }
            
            self.client.index(
                index=test_index,
                id="test_001",
                body=test_doc,
                refresh=True
            )
            
            # 测试混合搜索
            search_body = {
                "id": "hybrid_search_template",
                "params": {
                    "query_vector": [0.1] * 1536,
                    "text_query": "测试",
                    "vector_boost": 0.7,
                    "text_boost": 0.3,
                    "title_boost": 3.0,
                    "content_boost": 2.0,
                    "size": 10,
                    "source_fields": ["id", "title", "content"]
                }
            }
            
            response = self.client.search_template(
                index=test_index,
                body=search_body
            )
            
            # 检查结果
            hits = response.get("hits", {}).get("hits", [])
            if len(hits) > 0:
                logger.info("混合检索测试成功")
                success = True
            else:
                logger.warning("混合检索测试未返回结果")
                success = False
            
            # 清理测试数据
            self.client.indices.delete(index=test_index)
            return success
            
        except Exception as e:
            logger.error(f"混合检索测试失败: {e}")
            # 尝试清理
            try:
                self.client.indices.delete(index=test_index)
            except:
                pass
            return False
    
    def initialize_all(self) -> bool:
        """执行完整初始化"""
        logger.info("开始初始化Elasticsearch混合检索配置...")
        
        success_steps = 0
        total_steps = 5
        
        # 1. 等待ES就绪
        if self.wait_for_es():
            success_steps += 1
        else:
            return False
        
        # 2. 创建索引模板
        if self.create_index_template():
            success_steps += 1
        
        # 3. 创建搜索模板  
        if self.create_search_templates():
            success_steps += 1
        
        # 4. 创建处理管道
        if self.create_default_pipeline():
            success_steps += 1
        
        # 5. 测试混合检索
        if self.test_hybrid_search():
            success_steps += 1
        
        success = success_steps == total_steps
        
        if success:
            logger.info("✅ Elasticsearch混合检索初始化完成")
            logger.info("系统已配置为优先使用混合检索模式")
        else:
            logger.error(f"❌ 初始化部分失败 ({success_steps}/{total_steps})")
        
        return success


def main():
    """主函数"""
    import os
    
    # 从环境变量获取配置
    es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    es_username = os.getenv("ELASTICSEARCH_USERNAME", "")
    es_password = os.getenv("ELASTICSEARCH_PASSWORD", "")
    
    try:
        initializer = ElasticsearchInitializer(
            es_url=es_url,
            username=es_username if es_username else None,
            password=es_password if es_password else None
        )
        
        success = initializer.initialize_all()
        
        if success:
            print("\n🎉 Elasticsearch混合检索配置成功!")
            print("📋 已完成的配置:")
            print("   ✓ 索引模板 (支持向量和文本字段)")
            print("   ✓ 搜索模板 (混合检索、向量检索、关键词检索)")
            print("   ✓ 文档处理管道")
            print("   ✓ 功能测试")
            print("\n💡 现在系统将默认使用混合检索模式，结合语义理解和关键词匹配")
            sys.exit(0)
        else:
            print("\n❌ 配置过程中出现错误，请检查日志")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
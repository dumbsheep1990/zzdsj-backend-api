"""
文本处理工厂：统一的文本处理组件创建入口
支持多种实现策略和智能组件选择
"""

import logging
from typing import Type, Optional, Dict, Any, Union

from .base import (
    TextChunker, TokenCounter, TextAnalyzer, LanguageDetector,
    KeywordExtractor, TextNormalizer,
    ChunkConfig, TokenConfig, AnalysisConfig, DetectionConfig,
    ExtractionConfig, NormalizationConfig
)

# 导入实现
from .implementations import (
    LlamaIndexTextChunker, LlamaIndexTokenCounter,
    EnhancedTextAnalyzer, AdvancedLanguageDetector,
    YakeKeywordExtractor, MultiLevelTextNormalizer
)

# 简单实现（保持兼容性）
from .simple import (
    SimpleTextChunker, SimpleTokenCounter, SimpleTextAnalyzer,
    SimpleLanguageDetector, SimpleKeywordExtractor, SimpleTextNormalizer
)

logger = logging.getLogger(__name__)


class TextProcessingFactory:
    """
    文本处理工厂类
    提供统一的组件创建接口，支持多种实现策略
    """
    
    # 注册的实现
    _chunker_implementations = {
        "llamaindex": LlamaIndexTextChunker,
        "simple": SimpleTextChunker,
        "default": LlamaIndexTextChunker
    }
    
    _token_counter_implementations = {
        "llamaindex": LlamaIndexTokenCounter,
        "simple": SimpleTokenCounter,
        "default": LlamaIndexTokenCounter
    }
    
    _analyzer_implementations = {
        "enhanced": EnhancedTextAnalyzer,
        "simple": SimpleTextAnalyzer,
        "default": EnhancedTextAnalyzer
    }
    
    _language_detector_implementations = {
        "advanced": AdvancedLanguageDetector,
        "simple": SimpleLanguageDetector,
        "default": AdvancedLanguageDetector
    }
    
    _keyword_extractor_implementations = {
        "yake": YakeKeywordExtractor,
        "simple": SimpleKeywordExtractor,
        "default": YakeKeywordExtractor
    }
    
    _normalizer_implementations = {
        "multilevel": MultiLevelTextNormalizer,
        "simple": SimpleTextNormalizer,
        "default": MultiLevelTextNormalizer
    }
    
    @classmethod
    def create_text_chunker(
        cls,
        implementation: str = "default",
        config: Optional[ChunkConfig] = None
    ) -> TextChunker:
        """
        创建文本分块器
        
        参数:
            implementation: 实现类型 ("llamaindex", "simple", "default")
            config: 分块配置
            
        返回:
            文本分块器实例
        """
        impl_class = cls._chunker_implementations.get(implementation)
        if not impl_class:
            logger.warning(f"未知的分块器实现: {implementation}，使用默认实现")
            impl_class = cls._chunker_implementations["default"]
        
        try:
            instance = impl_class(config)
            logger.info(f"创建文本分块器: {impl_class.__name__}")
            return instance
        except Exception as e:
            logger.error(f"创建文本分块器失败: {str(e)}")
            # 后备到简单实现
            return SimpleTextChunker(config)
    
    @classmethod
    def create_token_counter(
        cls,
        implementation: str = "default",
        config: Optional[TokenConfig] = None
    ) -> TokenCounter:
        """
        创建令牌计数器
        
        参数:
            implementation: 实现类型 ("llamaindex", "simple", "default")
            config: 计数配置
            
        返回:
            令牌计数器实例
        """
        impl_class = cls._token_counter_implementations.get(implementation)
        if not impl_class:
            logger.warning(f"未知的令牌计数器实现: {implementation}，使用默认实现")
            impl_class = cls._token_counter_implementations["default"]
        
        try:
            instance = impl_class(config)
            logger.info(f"创建令牌计数器: {impl_class.__name__}")
            return instance
        except Exception as e:
            logger.error(f"创建令牌计数器失败: {str(e)}")
            # 后备到简单实现
            return SimpleTokenCounter(config)
    
    @classmethod
    def create_text_analyzer(
        cls,
        implementation: str = "default",
        config: Optional[AnalysisConfig] = None
    ) -> TextAnalyzer:
        """
        创建文本分析器
        
        参数:
            implementation: 实现类型 ("enhanced", "simple", "default")
            config: 分析配置
            
        返回:
            文本分析器实例
        """
        impl_class = cls._analyzer_implementations.get(implementation)
        if not impl_class:
            logger.warning(f"未知的文本分析器实现: {implementation}，使用默认实现")
            impl_class = cls._analyzer_implementations["default"]
        
        try:
            instance = impl_class(config)
            logger.info(f"创建文本分析器: {impl_class.__name__}")
            return instance
        except Exception as e:
            logger.error(f"创建文本分析器失败: {str(e)}")
            # 后备到简单实现
            return SimpleTextAnalyzer(config)
    
    @classmethod
    def create_language_detector(
        cls,
        implementation: str = "default",
        config: Optional[DetectionConfig] = None
    ) -> LanguageDetector:
        """
        创建语言检测器
        
        参数:
            implementation: 实现类型 ("advanced", "simple", "default")
            config: 检测配置
            
        返回:
            语言检测器实例
        """
        impl_class = cls._language_detector_implementations.get(implementation)
        if not impl_class:
            logger.warning(f"未知的语言检测器实现: {implementation}，使用默认实现")
            impl_class = cls._language_detector_implementations["default"]
        
        try:
            instance = impl_class(config)
            logger.info(f"创建语言检测器: {impl_class.__name__}")
            return instance
        except Exception as e:
            logger.error(f"创建语言检测器失败: {str(e)}")
            # 后备到简单实现
            return SimpleLanguageDetector(config)
    
    @classmethod
    def create_keyword_extractor(
        cls,
        implementation: str = "default",
        config: Optional[ExtractionConfig] = None
    ) -> KeywordExtractor:
        """
        创建关键词提取器
        
        参数:
            implementation: 实现类型 ("yake", "simple", "default")
            config: 提取配置
            
        返回:
            关键词提取器实例
        """
        impl_class = cls._keyword_extractor_implementations.get(implementation)
        if not impl_class:
            logger.warning(f"未知的关键词提取器实现: {implementation}，使用默认实现")
            impl_class = cls._keyword_extractor_implementations["default"]
        
        try:
            instance = impl_class(config)
            logger.info(f"创建关键词提取器: {impl_class.__name__}")
            return instance
        except Exception as e:
            logger.error(f"创建关键词提取器失败: {str(e)}")
            # 后备到简单实现
            return SimpleKeywordExtractor(config)
    
    @classmethod
    def create_text_normalizer(
        cls,
        implementation: str = "default",
        config: Optional[NormalizationConfig] = None
    ) -> TextNormalizer:
        """
        创建文本规范化器
        
        参数:
            implementation: 实现类型 ("multilevel", "simple", "default")
            config: 规范化配置
            
        返回:
            文本规范化器实例
        """
        impl_class = cls._normalizer_implementations.get(implementation)
        if not impl_class:
            logger.warning(f"未知的文本规范化器实现: {implementation}，使用默认实现")
            impl_class = cls._normalizer_implementations["default"]
        
        try:
            instance = impl_class(config)
            logger.info(f"创建文本规范化器: {impl_class.__name__}")
            return instance
        except Exception as e:
            logger.error(f"创建文本规范化器失败: {str(e)}")
            # 后备到简单实现
            return SimpleTextNormalizer(config)
    
    @classmethod
    def create_complete_pipeline(
        cls,
        chunker_impl: str = "default",
        analyzer_impl: str = "default",
        extractor_impl: str = "default",
        normalizer_impl: str = "default",
        configs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建完整的文本处理管道
        
        参数:
            chunker_impl: 分块器实现
            analyzer_impl: 分析器实现
            extractor_impl: 提取器实现
            normalizer_impl: 规范化器实现
            configs: 各组件的配置
            
        返回:
            包含所有组件的字典
        """
        if configs is None:
            configs = {}
        
        pipeline = {
            "chunker": cls.create_text_chunker(
                chunker_impl, configs.get("chunk_config")
            ),
            "token_counter": cls.create_token_counter(
                "default", configs.get("token_config")
            ),
            "analyzer": cls.create_text_analyzer(
                analyzer_impl, configs.get("analysis_config")
            ),
            "language_detector": cls.create_language_detector(
                "default", configs.get("detection_config")
            ),
            "keyword_extractor": cls.create_keyword_extractor(
                extractor_impl, configs.get("extraction_config")
            ),
            "normalizer": cls.create_text_normalizer(
                normalizer_impl, configs.get("normalization_config")
            )
        }
        
        logger.info("创建完整文本处理管道")
        
        return pipeline
    
    @classmethod
    def create_smart_pipeline(
        cls,
        text_sample: str,
        use_case: str = "general",
        performance_mode: str = "balanced"
    ) -> Dict[str, Any]:
        """
        基于文本样本和使用场景智能创建最优管道
        
        参数:
            text_sample: 文本样本，用于分析特征
            use_case: 使用场景 ("general", "academic", "social", "technical")
            performance_mode: 性能模式 ("fast", "balanced", "accurate")
            
        返回:
            优化的文本处理管道
        """
        # 分析文本特征
        text_features = cls._analyze_text_features(text_sample)
        
        # 根据使用场景和性能模式选择实现
        implementations = cls._select_implementations(
            text_features, use_case, performance_mode
        )
        
        # 创建优化配置
        configs = cls._create_optimized_configs(text_features, use_case)
        
        # 创建管道
        pipeline = cls.create_complete_pipeline(
            chunker_impl=implementations["chunker"],
            analyzer_impl=implementations["analyzer"],
            extractor_impl=implementations["extractor"],
            normalizer_impl=implementations["normalizer"],
            configs=configs
        )
        
        logger.info(f"创建智能文本处理管道 - 使用场景: {use_case}, 性能模式: {performance_mode}")
        
        return pipeline
    
    @classmethod
    def get_available_implementations(cls) -> Dict[str, List[str]]:
        """
        获取所有可用的实现
        
        返回:
            各组件的可用实现列表
        """
        return {
            "chunker": list(cls._chunker_implementations.keys()),
            "token_counter": list(cls._token_counter_implementations.keys()),
            "analyzer": list(cls._analyzer_implementations.keys()),
            "language_detector": list(cls._language_detector_implementations.keys()),
            "keyword_extractor": list(cls._keyword_extractor_implementations.keys()),
            "normalizer": list(cls._normalizer_implementations.keys())
        }
    
    @classmethod
    def register_implementation(
        cls,
        component_type: str,
        name: str,
        implementation_class: Type
    ):
        """
        注册新的实现
        
        参数:
            component_type: 组件类型
            name: 实现名称
            implementation_class: 实现类
        """
        registry_map = {
            "chunker": cls._chunker_implementations,
            "token_counter": cls._token_counter_implementations,
            "analyzer": cls._analyzer_implementations,
            "language_detector": cls._language_detector_implementations,
            "keyword_extractor": cls._keyword_extractor_implementations,
            "normalizer": cls._normalizer_implementations
        }
        
        if component_type in registry_map:
            registry_map[component_type][name] = implementation_class
            logger.info(f"注册{component_type}实现: {name}")
        else:
            logger.error(f"未知的组件类型: {component_type}")
    
    @classmethod
    def _analyze_text_features(cls, text: str) -> Dict[str, Any]:
        """分析文本特征以选择最优实现"""
        import re
        
        features = {
            "length": len(text),
            "word_count": len(text.split()),
            "chinese_ratio": len(re.findall(r'[\u4e00-\u9fff]', text)) / max(len(text), 1),
            "english_ratio": len(re.findall(r'[a-zA-Z]', text)) / max(len(text), 1),
            "has_technical_content": bool(re.search(r'[{}()[\];]|https?://', text)),
            "complexity": len(set(text.split())) / max(len(text.split()), 1)
        }
        
        return features
    
    @classmethod
    def _select_implementations(
        cls,
        features: Dict[str, Any],
        use_case: str,
        performance_mode: str
    ) -> Dict[str, str]:
        """根据特征选择最优实现"""
        
        # 基于性能模式的基础选择
        if performance_mode == "fast":
            base_selection = {
                "chunker": "simple",
                "analyzer": "simple",
                "extractor": "simple",
                "normalizer": "simple"
            }
        elif performance_mode == "accurate":
            base_selection = {
                "chunker": "llamaindex",
                "analyzer": "enhanced",
                "extractor": "yake",
                "normalizer": "multilevel"
            }
        else:  # balanced
            base_selection = {
                "chunker": "llamaindex",
                "analyzer": "enhanced",
                "extractor": "yake",
                "normalizer": "multilevel"
            }
        
        # 根据文本特征调整
        if features["length"] > 100000:  # 大文本优先性能
            if performance_mode != "accurate":
                base_selection["chunker"] = "simple"
        
        if features["chinese_ratio"] > 0.8:  # 中文文本
            # 中文文本使用专门优化的实现
            pass
        
        if features["has_technical_content"]:  # 技术文档
            if use_case != "fast":
                base_selection["normalizer"] = "multilevel"
        
        return base_selection
    
    @classmethod
    def _create_optimized_configs(
        cls,
        features: Dict[str, Any],
        use_case: str
    ) -> Dict[str, Any]:
        """创建优化的配置"""
        
        configs = {}
        
        # 分块配置
        if features["length"] > 50000:
            chunk_size = 2000
        elif features["length"] > 10000:
            chunk_size = 1000
        else:
            chunk_size = 500
        
        configs["chunk_config"] = ChunkConfig(
            chunk_size=chunk_size,
            chunk_overlap=int(chunk_size * 0.1),
            respect_boundaries=True
        )
        
        # 分析配置
        configs["analysis_config"] = AnalysisConfig(
            include_sentiment=use_case in ["social", "general"],
            include_readability=use_case in ["academic", "general"],
            include_language_detection=features["chinese_ratio"] > 0.1 and features["english_ratio"] > 0.1
        )
        
        # 提取配置
        max_keywords = {
            "general": 20,
            "academic": 30,
            "social": 15,
            "technical": 25
        }.get(use_case, 20)
        
        configs["extraction_config"] = ExtractionConfig(
            max_keywords=max_keywords,
            min_word_length=2 if features["chinese_ratio"] > 0.5 else 3,
            max_ngram_size=3
        )
        
        # 规范化配置
        normalization_level = {
            "social": 3,    # 社交文本需要深度清理
            "academic": 2,  # 学术文本中等清理
            "technical": 1, # 技术文档保守清理
            "general": 2    # 通用场景中等清理
        }.get(use_case, 2)
        
        configs["normalization_config"] = NormalizationConfig(
            level=normalization_level,
            preserve_formatting=use_case == "technical"
        )
        
        return configs


# 便捷的工厂函数
def create_text_chunker(implementation: str = "default", **kwargs) -> TextChunker:
    """便捷函数：创建文本分块器"""
    config = ChunkConfig(**kwargs) if kwargs else None
    return TextProcessingFactory.create_text_chunker(implementation, config)


def create_token_counter(implementation: str = "default", **kwargs) -> TokenCounter:
    """便捷函数：创建令牌计数器"""
    config = TokenConfig(**kwargs) if kwargs else None
    return TextProcessingFactory.create_token_counter(implementation, config)


def create_text_analyzer(implementation: str = "default", **kwargs) -> TextAnalyzer:
    """便捷函数：创建文本分析器"""
    config = AnalysisConfig(**kwargs) if kwargs else None
    return TextProcessingFactory.create_text_analyzer(implementation, config)


def create_language_detector(implementation: str = "default", **kwargs) -> LanguageDetector:
    """便捷函数：创建语言检测器"""
    config = DetectionConfig(**kwargs) if kwargs else None
    return TextProcessingFactory.create_language_detector(implementation, config)


def create_keyword_extractor(implementation: str = "default", **kwargs) -> KeywordExtractor:
    """便捷函数：创建关键词提取器"""
    config = ExtractionConfig(**kwargs) if kwargs else None
    return TextProcessingFactory.create_keyword_extractor(implementation, config)


def create_text_normalizer(implementation: str = "default", **kwargs) -> TextNormalizer:
    """便捷函数：创建文本规范化器"""
    config = NormalizationConfig(**kwargs) if kwargs else None
    return TextProcessingFactory.create_text_normalizer(implementation, config)


def create_smart_pipeline(text_sample: str, use_case: str = "general", 
                         performance_mode: str = "balanced") -> Dict[str, Any]:
    """便捷函数：创建智能文本处理管道"""
    return TextProcessingFactory.create_smart_pipeline(text_sample, use_case, performance_mode) 
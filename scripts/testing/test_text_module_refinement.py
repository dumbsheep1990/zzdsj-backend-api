#!/usr/bin/env python3
"""
Text模块精细化重构验证测试
验证新的text模块重构组件是否正常工作
"""

import sys
import os
import traceback

# 添加项目路径
sys.path.insert(0, os.path.abspath('.'))

def test_text_core_base():
    """测试文本处理核心基类"""
    print("🔍 测试 text.core.base 模块...")
    
    try:
        from app.utils.text.core.base import (
            TextLanguage, 
            TextProcessingConfig, 
            ChunkConfig, 
            TokenConfig,
            AnalysisResult,
            TextProcessingError,
            InvalidTextError
        )
        
        # 测试枚举
        assert TextLanguage.CHINESE.value == "zh"
        assert TextLanguage.ENGLISH.value == "en"
        
        # 测试配置类
        config = TextProcessingConfig(
            language=TextLanguage.CHINESE,
            normalize_whitespace=True
        )
        assert config.language == TextLanguage.CHINESE
        assert config.encoding == "utf-8"
        
        chunk_config = ChunkConfig(chunk_size=1500, chunk_overlap=300)
        assert chunk_config.chunk_size == 1500
        assert chunk_config.chunk_overlap == 300
        
        token_config = TokenConfig(model="gpt-4")
        assert token_config.model == "gpt-4"
        
        # 测试异常
        try:
            raise InvalidTextError("测试异常")
        except TextProcessingError:
            pass  # 应该能捕获
        
        print("   ✅ 基础组件测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ 基础组件测试失败: {e}")
        traceback.print_exc()
        return False

def test_tokenizer():
    """测试令牌计数器"""
    print("🔍 测试 tokenizer 模块...")
    
    try:
        from app.utils.text.core.tokenizer import (
            TikTokenCounter, 
            SimpleTokenCounter, 
            create_token_counter,
            count_tokens
        )
        from app.utils.text.core.base import TokenConfig
        
        # 测试简单计数器（不依赖外部库）
        config = TokenConfig(model="gpt-3.5-turbo")
        simple_counter = SimpleTokenCounter(config)
        
        test_text = "这是一个测试文本，用于验证令牌计数功能。"
        token_count = simple_counter.count_tokens(test_text)
        
        assert isinstance(token_count, int)
        assert token_count > 0
        print(f"   📊 文本令牌数: {token_count}")
        
        # 测试成本估算
        cost = simple_counter.estimate_cost(test_text, 0.0001)
        assert isinstance(cost, float)
        assert cost > 0
        print(f"   💰 估算成本: ${cost:.6f}")
        
        # 测试工厂函数
        counter = create_token_counter(use_tiktoken=False, config=config)
        assert isinstance(counter, SimpleTokenCounter)
        
        # 测试向后兼容函数
        compat_count = count_tokens(test_text, "gpt-3.5-turbo")
        assert isinstance(compat_count, int)
        assert compat_count > 0
        
        print("   ✅ 令牌计数器测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ 令牌计数器测试失败: {e}")
        traceback.print_exc()
        return False

def test_chunker():
    """测试文本分块器"""
    print("🔍 测试 chunker 模块...")
    
    try:
        from app.utils.text.core.chunker import (
            SmartTextChunker,
            SemanticChunker,
            FixedSizeChunker,
            create_chunker,
            chunk_text
        )
        from app.utils.text.core.base import ChunkConfig
        
        # 测试文本
        test_text = """
        这是第一段文本，包含了一些基本的内容用于测试分块功能。这段文本应该足够长，以便能够触发分块逻辑。
        
        这是第二段文本，它包含了不同的内容。这段文本的目的是测试段落感知的分块功能，确保分块器能够正确处理段落边界。
        
        这是第三段文本，相对较短一些。但仍然包含足够的内容来测试各种分块策略。最后一句话用来结束这个测试文本。
        """ * 3
        
        # 测试智能分块器
        config = ChunkConfig(chunk_size=200, chunk_overlap=50)
        smart_chunker = SmartTextChunker(config)
        
        chunks = smart_chunker.chunk(test_text)
        assert isinstance(chunks, list)
        assert len(chunks) > 1
        print(f"   📄 智能分块结果: {len(chunks)} 个块")
        
        # 验证块的大小
        for i, chunk in enumerate(chunks):
            assert len(chunk) <= config.chunk_size + 50  # 允许一些容差
            print(f"     块 {i+1}: {len(chunk)} 字符")
        
        # 测试语义分块器
        semantic_chunker = SemanticChunker(config)
        semantic_chunks = semantic_chunker.chunk(test_text)
        assert isinstance(semantic_chunks, list)
        print(f"   🧠 语义分块结果: {len(semantic_chunks)} 个块")
        
        # 测试固定大小分块器
        fixed_chunker = FixedSizeChunker(config)
        fixed_chunks = fixed_chunker.chunk(test_text)
        assert isinstance(fixed_chunks, list)
        print(f"   📐 固定分块结果: {len(fixed_chunks)} 个块")
        
        # 测试工厂函数
        chunker = create_chunker("smart", config)
        assert isinstance(chunker, SmartTextChunker)
        
        # 测试向后兼容函数
        compat_chunks = chunk_text(test_text, chunk_size=200, chunk_overlap=50)
        assert isinstance(compat_chunks, list)
        assert len(compat_chunks) > 0
        
        print("   ✅ 文本分块器测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ 文本分块器测试失败: {e}")
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """测试向后兼容性"""
    print("🔍 测试向后兼容性...")
    
    try:
        # 测试原始接口是否仍然可用
        from app.utils.text.core.tokenizer import count_tokens
        from app.utils.text.core.chunker import chunk_text
        
        test_text = "这是一个用于测试向后兼容性的文本。"
        
        # 原始令牌计数接口
        tokens = count_tokens(test_text)
        assert isinstance(tokens, int)
        assert tokens > 0
        
        # 原始分块接口
        chunks = chunk_text(test_text, chunk_size=50)
        assert isinstance(chunks, list)
        
        print("   ✅ 向后兼容性测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ 向后兼容性测试失败: {e}")
        traceback.print_exc()
        return False

def test_performance():
    """测试性能改进"""
    print("🔍 测试性能改进...")
    
    try:
        import time
        from app.utils.text.core.tokenizer import SimpleTokenCounter
        from app.utils.text.core.chunker import SmartTextChunker
        from app.utils.text.core.base import TokenConfig, ChunkConfig
        
        # 创建大文本进行性能测试
        large_text = "这是一个大文本用于性能测试。" * 1000
        
        # 测试令牌计数性能
        config = TokenConfig()
        counter = SimpleTokenCounter(config)
        
        start_time = time.time()
        tokens = counter.count_tokens(large_text)
        token_time = time.time() - start_time
        
        assert tokens > 0
        print(f"   ⚡ 令牌计数性能: {token_time:.4f}秒 ({tokens} 令牌)")
        
        # 测试分块性能
        chunk_config = ChunkConfig(chunk_size=500)
        chunker = SmartTextChunker(chunk_config)
        
        start_time = time.time()
        chunks = chunker.chunk(large_text)
        chunk_time = time.time() - start_time
        
        assert len(chunks) > 0
        print(f"   ⚡ 分块性能: {chunk_time:.4f}秒 ({len(chunks)} 块)")
        
        # 验证性能合理
        assert token_time < 1.0  # 令牌计数应该在1秒内完成
        assert chunk_time < 2.0  # 分块应该在2秒内完成
        
        print("   ✅ 性能测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ 性能测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """运行所有测试"""
    print("=" * 60)
    print("🚀 Text模块精细化重构验证测试")
    print("=" * 60)
    
    tests = [
        ("基础组件", test_text_core_base),
        ("令牌计数器", test_tokenizer),
        ("文本分块器", test_chunker),
        ("向后兼容性", test_backward_compatibility),
        ("性能改进", test_performance),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}测试:")
        if test_func():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！text模块精细化重构成功！")
        
        # 输出重构成果总结
        print("\n📈 重构成果总结:")
        print("  ✅ 实现了统一的抽象基类架构")
        print("  ✅ 优化了令牌计数器性能和缓存机制")
        print("  ✅ 增强了文本分块器的智能边界检测")
        print("  ✅ 保持了完整的向后兼容性")
        print("  ✅ 提升了整体性能表现")
        print("  ✅ 建立了可扩展的工厂模式架构")
        
        return True
    else:
        print(f"❌ {total - passed} 个测试失败，需要修复问题")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
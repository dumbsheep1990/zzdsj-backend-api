#!/usr/bin/env python3
"""
Text核心模块直接测试
避免复杂依赖，直接测试重构的组件
"""

import sys
import os

# 添加路径以直接导入我们的模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'utils', 'text', 'core'))

def test_base_components():
    """测试基础组件"""
    print("🔍 测试基础组件...")
    
    try:
        # 直接导入base模块
        import base
        
        # 测试枚举
        assert base.TextLanguage.CHINESE.value == "zh"
        assert base.TextLanguage.ENGLISH.value == "en"
        print("   ✅ 语言枚举正常")
        
        # 测试配置类
        config = base.TextProcessingConfig(
            language=base.TextLanguage.CHINESE,
            normalize_whitespace=True
        )
        assert config.language == base.TextLanguage.CHINESE
        assert config.encoding == "utf-8"
        print("   ✅ 配置类正常")
        
        # 测试分块配置
        chunk_config = base.ChunkConfig(chunk_size=1500, chunk_overlap=300)
        assert chunk_config.chunk_size == 1500
        assert chunk_config.chunk_overlap == 300
        print("   ✅ 分块配置正常")
        
        # 测试令牌配置
        token_config = base.TokenConfig(model="gpt-4")
        assert token_config.model == "gpt-4"
        print("   ✅ 令牌配置正常")
        
        # 测试异常体系
        try:
            raise base.InvalidTextError("测试异常")
        except base.TextProcessingError:
            print("   ✅ 异常体系正常")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 基础组件测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tokenizer_direct():
    """直接测试令牌计数器"""
    print("🔍 测试令牌计数器...")
    
    try:
        import base
        import tokenizer
        
        # 测试简单计数器
        config = base.TokenConfig(model="gpt-3.5-turbo")
        simple_counter = tokenizer.SimpleTokenCounter(config)
        
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
        
        # 测试批量计数
        texts = ["第一个文本", "第二个文本", "第三个更长的文本用于测试"]
        batch_counts = simple_counter.batch_count_tokens(texts)
        assert len(batch_counts) == 3
        assert all(isinstance(count, int) and count > 0 for count in batch_counts)
        print(f"   📚 批量计数: {batch_counts}")
        
        # 测试语言检测
        zh_text = "这是中文文本"
        en_text = "This is English text"
        
        zh_lang = simple_counter._detect_simple_language(zh_text)
        en_lang = simple_counter._detect_simple_language(en_text)
        
        assert zh_lang == 'zh'
        assert en_lang == 'en'
        print(f"   🌐 语言检测: 中文={zh_lang}, 英文={en_lang}")
        
        # 测试工厂函数
        counter = tokenizer.create_token_counter(use_tiktoken=False, config=config)
        assert isinstance(counter, tokenizer.SimpleTokenCounter)
        print("   ✅ 工厂函数正常")
        
        # 测试向后兼容函数
        compat_count = tokenizer.count_tokens(test_text, "gpt-3.5-turbo")
        assert isinstance(compat_count, int)
        print(f"   🔄 兼容接口: {compat_count} 令牌")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 令牌计数器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chunker_direct():
    """直接测试文本分块器"""
    print("🔍 测试文本分块器...")
    
    try:
        import base
        import chunker
        
        # 测试文本
        test_text = """
        这是第一段文本，包含了一些基本的内容用于测试分块功能。这段文本应该足够长，以便能够触发分块逻辑。
        
        这是第二段文本，它包含了不同的内容。这段文本的目的是测试段落感知的分块功能，确保分块器能够正确处理段落边界。
        
        这是第三段文本，相对较短一些。但仍然包含足够的内容来测试各种分块策略。最后一句话用来结束这个测试文本。
        """ * 2
        
        # 测试智能分块器
        config = base.ChunkConfig(chunk_size=200, chunk_overlap=50, min_chunk_size=50)
        smart_chunker = chunker.SmartTextChunker(config)
        
        chunks = smart_chunker.chunk(test_text)
        assert isinstance(chunks, list)
        assert len(chunks) > 1
        print(f"   📄 智能分块结果: {len(chunks)} 个块")
        
        # 验证块的大小和内容
        total_chars = 0
        for i, chunk in enumerate(chunks):
            chunk_len = len(chunk)
            total_chars += chunk_len
            print(f"     块 {i+1}: {chunk_len} 字符")
            assert chunk_len >= config.min_chunk_size
            assert chunk.strip()  # 确保没有空块
        
        # 测试语义分块器
        semantic_chunker = chunker.SemanticChunker(config)
        semantic_chunks = semantic_chunker.chunk(test_text)
        assert isinstance(semantic_chunks, list)
        print(f"   🧠 语义分块结果: {len(semantic_chunks)} 个块")
        
        # 测试固定大小分块器
        fixed_chunker = chunker.FixedSizeChunker(config)
        fixed_chunks = fixed_chunker.chunk(test_text)
        assert isinstance(fixed_chunks, list)
        print(f"   📐 固定分块结果: {len(fixed_chunks)} 个块")
        
        # 测试边界检测
        boundary_text = "句子1。句子2！句子3？新段落\n\n另一个段落。"
        boundary_config = base.ChunkConfig(chunk_size=15, chunk_overlap=5)
        boundary_chunker = chunker.SmartTextChunker(boundary_config)
        boundary_chunks = boundary_chunker.chunk(boundary_text)
        print(f"   🎯 边界检测: {len(boundary_chunks)} 个块")
        for i, chunk in enumerate(boundary_chunks):
            print(f"     边界块 {i+1}: '{chunk}'")
        
        # 测试工厂函数
        factory_chunker = chunker.create_chunker("smart", config)
        assert isinstance(factory_chunker, chunker.SmartTextChunker)
        
        factory_chunker2 = chunker.create_chunker("semantic", config)
        assert isinstance(factory_chunker2, chunker.SemanticChunker)
        print("   ✅ 工厂函数正常")
        
        # 测试向后兼容函数
        compat_chunks = chunker.chunk_text(test_text, chunk_size=200, chunk_overlap=50)
        assert isinstance(compat_chunks, list)
        print(f"   🔄 兼容接口: {len(compat_chunks)} 个块")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 文本分块器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_comparison():
    """测试性能对比"""
    print("🔍 测试性能对比...")
    
    try:
        import time
        import base
        import tokenizer
        import chunker
        
        # 创建大文本进行性能测试
        large_text = "这是一个用于性能测试的长文本。它包含了多个句子和段落，用来测试我们重构后的组件性能。" * 200
        
        print(f"   📏 测试文本长度: {len(large_text)} 字符")
        
        # 令牌计数性能测试
        config = base.TokenConfig()
        counter = tokenizer.SimpleTokenCounter(config)
        
        start_time = time.time()
        for _ in range(10):  # 多次测试取平均
            tokens = counter.count_tokens(large_text)
        token_time = (time.time() - start_time) / 10
        
        print(f"   ⚡ 令牌计数性能: {token_time:.4f}秒/次 ({tokens} 令牌)")
        
        # 分块性能测试
        chunk_config = base.ChunkConfig(chunk_size=500, chunk_overlap=100)
        smart_chunker = chunker.SmartTextChunker(chunk_config)
        
        start_time = time.time()
        for _ in range(5):  # 分块比较耗时，测试次数少一些
            chunks = smart_chunker.chunk(large_text)
        chunk_time = (time.time() - start_time) / 5
        
        print(f"   ⚡ 智能分块性能: {chunk_time:.4f}秒/次 ({len(chunks)} 块)")
        
        # 比较不同分块器的性能
        fixed_chunker = chunker.FixedSizeChunker(chunk_config)
        semantic_chunker = chunker.SemanticChunker(chunk_config)
        
        start_time = time.time()
        fixed_chunks = fixed_chunker.chunk(large_text)
        fixed_time = time.time() - start_time
        
        start_time = time.time()
        semantic_chunks = semantic_chunker.chunk(large_text)
        semantic_time = time.time() - start_time
        
        print(f"   📊 性能对比:")
        print(f"     固定分块: {fixed_time:.4f}秒 ({len(fixed_chunks)} 块)")
        print(f"     语义分块: {semantic_time:.4f}秒 ({len(semantic_chunks)} 块)")
        print(f"     智能分块: {chunk_time:.4f}秒 ({len(chunks)} 块)")
        
        # 验证性能要求
        assert token_time < 0.1  # 令牌计数应该很快
        assert chunk_time < 1.0  # 分块应该在合理时间内完成
        
        return True
        
    except Exception as e:
        print(f"   ❌ 性能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有测试"""
    print("=" * 70)
    print("🚀 Text核心模块直接测试")
    print("=" * 70)
    
    tests = [
        ("基础组件", test_base_components),
        ("令牌计数器", test_tokenizer_direct),
        ("文本分块器", test_chunker_direct),
        ("性能对比", test_performance_comparison),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}测试:")
        try:
            if test_func():
                passed += 1
                print(f"   ✅ {test_name}测试通过")
            else:
                print(f"   ❌ {test_name}测试失败")
        except Exception as e:
            print(f"   ❌ {test_name}测试异常: {e}")
    
    print("\n" + "=" * 70)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！text核心模块重构成功！")
        
        print("\n📈 重构成果:")
        print("  ✅ 抽象基类架构 - 建立了统一的接口标准")
        print("  ✅ 令牌计数器优化 - 支持多种模型和缓存机制")
        print("  ✅ 智能文本分块 - 边界感知和语义分割")
        print("  ✅ 性能优化 - 预编译正则和算法改进")
        print("  ✅ 向后兼容 - 保持原有接口可用")
        print("  ✅ 工厂模式 - 支持灵活的组件创建")
        
        print("\n🎯 下一步计划:")
        print("  1. 完成文本分析器(analyzer.py)重构")
        print("  2. 完成embedding_utils.py重构")
        print("  3. 完成template_renderer.py重构")
        print("  4. 创建统一的__init__.py接口")
        print("  5. 编写完整的单元测试")
        
        return True
    else:
        print(f"❌ {total - passed} 个测试失败，需要修复问题")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
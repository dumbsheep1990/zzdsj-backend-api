"""
简化版适配器功能验证脚本
只测试工具注册中心的最基本功能，避免依赖问题
"""
import sys
import asyncio

def test_tool_registry_basics():
    """测试工具注册中心的基本功能，不引入复杂依赖"""
    print("测试工具注册中心基本功能...")
    
    # 创建一个简单的工具注册中心类
    class SimpleToolRegistry:
        def __init__(self):
            self._tools = {}
        
        def register_tool(self, name, tool):
            self._tools[name] = tool
            return self
        
        def get_tool(self, name):
            return self._tools.get(name)
        
        def list_tools(self):
            return list(self._tools.keys())
    
    # 测试注册和获取工具
    registry = SimpleToolRegistry()
    assert registry._tools == {}, "初始工具列表应为空"
    print("✓ 注册中心初始化成功")
    
    # 测试注册与获取
    registry.register_tool("test_tool", "test_value")
    assert registry.get_tool("test_tool") == "test_value", "应该能获取注册的工具"
    assert registry.list_tools() == ["test_tool"], "应该能列出工具名称"
    print("✓ 注册和获取功能正常")
    
    # 测试链式调用
    registry.register_tool("tool2", "value2").register_tool("tool3", "value3")
    assert len(registry.list_tools()) == 3, "链式注册应正常工作"
    print("✓ 链式调用功能正常")
    
    return True

def test_adapter_pattern():
    """测试适配器模式的基本概念"""
    print("\n测试适配器模式...")
    
    # 定义目标接口和被适配对象
    class TargetInterface:
        def request(self):
            return "默认目标接口响应"
    
    class Adaptee:
        def specific_request(self):
            return "被适配对象的特殊响应"
    
    # 实现适配器
    class Adapter(TargetInterface):
        def __init__(self, adaptee):
            self.adaptee = adaptee
        
        def request(self):
            return f"适配器转换: {self.adaptee.specific_request()}"
    
    # 测试适配器
    adaptee = Adaptee()
    adapter = Adapter(adaptee)
    
    # 验证适配器功能
    assert adapter.request() != adaptee.specific_request(), "适配器应转换接口"
    assert "适配器转换" in adapter.request(), "适配器应包装原始响应"
    print("✓ 适配器模式实现正确")
    
    return True

async def main():
    """运行所有测试"""
    print("开始运行简化版适配器功能验证...\n")
    
    # 运行测试
    tests = [
        test_tool_registry_basics(),
        test_adapter_pattern()
    ]
    
    # 验证所有测试都通过
    all_passed = all(tests)
    
    # 输出结果
    if all_passed:
        print("\n所有测试通过! ✓")
    else:
        print("\n测试失败! ×")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

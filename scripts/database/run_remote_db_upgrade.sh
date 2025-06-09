#!/bin/bash
# 远程数据库增强版升级启动脚本
# 基于昨天的远程数据库连接配置执行数据库表更新

echo "🚀 智政知识库远程数据库增强版升级工具"
echo "=========================================="
echo "🌍 目标远程服务器: 167.71.85.231:5432"
echo "🗄️ 数据库: zzdsj"
echo "👤 用户: zzdsj"
echo "📁 当前目录: $(pwd)"
echo "🐍 Python版本: $(python3 --version)"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查Python依赖..."
    
    # 检查psycopg2
    python3 -c "import psycopg2" 2>/dev/null
    if [ $? -ne 0 ]; then
        log_warning "psycopg2 未安装，正在安装..."
        pip3 install psycopg2-binary
        if [ $? -eq 0 ]; then
            log_success "psycopg2-binary 安装成功"
        else
            log_error "psycopg2-binary 安装失败"
            return 1
        fi
    else
        log_success "psycopg2 已安装"
    fi
    
    return 0
}

# 检查脚本文件
check_remote_upgrade_script() {
    log_info "检查远程升级脚本..."
    
    script_path="scripts/execute_remote_db_upgrade.py"
    
    if [ -f "$script_path" ]; then
        log_success "远程升级脚本存在: $script_path"
        return 0
    else
        log_error "远程升级脚本不存在: $script_path"
        return 1
    fi
}

# 测试网络连接
test_network_connection() {
    log_info "测试到远程服务器的网络连接..."
    
    # 尝试ping远程服务器
    ping -c 1 167.71.85.231 > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        log_success "网络连接正常"
    else
        log_warning "网络ping测试失败，但可能仍能连接数据库"
    fi
    
    # 尝试telnet测试端口
    if command -v telnet &> /dev/null; then
        timeout 5 telnet 167.71.85.231 5432 2>/dev/null | grep Connected > /dev/null
        if [ $? -eq 0 ]; then
            log_success "数据库端口 5432 可访问"
        else
            log_warning "无法通过telnet连接到数据库端口"
        fi
    else
        log_warning "telnet 命令不可用，跳过端口测试"
    fi
}

# 执行远程数据库升级
execute_remote_upgrade() {
    log_info "开始执行远程数据库升级..."
    echo "----------------------------------------"
    
    # 运行远程数据库升级脚本
    python3 scripts/execute_remote_db_upgrade.py
    upgrade_result=$?
    
    if [ $upgrade_result -eq 0 ]; then
        log_success "远程数据库升级成功!"
        return 0
    else
        log_error "远程数据库升级失败，退出码: $upgrade_result"
        return 1
    fi
}

# 显示升级完成后的信息
show_completion_info() {
    echo ""
    echo "🎉 远程数据库增强版升级完成!"
    echo "=========================================="
    echo "📝 升级内容总结："
    echo ""
    echo "✅ 已创建的增强版表："
    echo "   • document_registry_enhanced - 增强版文档注册表"
    echo "   • document_chunks - 文档切片表"
    echo "   • document_vectors_enhanced - 增强版向量关联表"
    echo "   • document_es_shards - ES分片关联表"
    echo "   • document_processing_history - 处理历史表"
    echo ""
    echo "🔗 远程服务器信息："
    echo "   地址: 167.71.85.231:5432"
    echo "   数据库: zzdsj"
    echo "   用户: zzdsj"
    echo ""
    echo "📊 升级特性："
    echo "   ✅ 完整的向量chunk ID追踪"
    echo "   ✅ ES文档分片数据关联"
    echo "   ✅ 统一删除操作支持"
    echo "   ✅ 详细的处理历史记录"
    echo "   ✅ 外键约束和索引优化"
    echo "   ✅ 演示数据创建"
    echo ""
    echo "🔧 后续可进行的操作："
    echo "   1. 配置应用程序连接远程数据库"
    echo "   2. 测试增强版文档管理器功能"
    echo "   3. 运行完整系统测试"
    echo "   4. 部署生产环境应用"
    echo ""
}

# 主执行流程
main() {
    echo ""
    
    # 1. 检查依赖
    if ! check_dependencies; then
        log_error "依赖检查失败"
        exit 1
    fi
    
    # 2. 检查升级脚本
    if ! check_remote_upgrade_script; then
        log_error "升级脚本检查失败"
        exit 1
    fi
    
    # 3. 测试网络连接
    test_network_connection
    
    # 4. 确认执行
    echo ""
    log_warning "即将连接到远程服务器 167.71.85.231 执行数据库升级"
    read -p "确认继续? (y/N): " confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "用户取消操作"
        exit 0
    fi
    
    # 5. 执行远程数据库升级
    if execute_remote_upgrade; then
        log_success "远程数据库升级执行成功"
        
        # 6. 显示完成信息
        show_completion_info
        
        exit 0
    else
        log_error "远程数据库升级执行失败"
        echo ""
        echo "💡 故障排除建议："
        echo "   1. 检查网络连接是否正常"
        echo "   2. 验证远程数据库服务是否运行"
        echo "   3. 确认数据库连接参数正确"
        echo "   4. 检查用户权限是否足够"
        echo "   5. 查看详细错误信息"
        exit 1
    fi
}

# 显示帮助信息
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "远程数据库增强版升级启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项："
    echo "  --help, -h     显示此帮助信息"
    echo "  --force        强制执行，跳过确认"
    echo ""
    echo "🎯 升级目标:"
    echo "  远程服务器: 167.71.85.231:5432"
    echo "  数据库: zzdsj"
    echo "  用户: zzdsj"
    echo ""
    echo "📋 升级内容:"
    echo "  • 创建增强版文档管理表结构"
    echo "  • 添加完整的关联追踪功能"
    echo "  • 建立外键约束和索引"
    echo "  • 创建演示数据进行验证"
    echo ""
    echo "⚠️ 注意事项:"
    echo "  • 需要网络连接到远程服务器"
    echo "  • 需要有数据库CREATE权限"
    echo "  • 脚本会创建新表，不会删除现有数据"
    echo ""
    exit 0
fi

# 强制执行模式
if [ "$1" = "--force" ]; then
    log_info "强制执行模式，跳过确认"
    check_dependencies && check_remote_upgrade_script && execute_remote_upgrade
    if [ $? -eq 0 ]; then
        show_completion_info
    fi
    exit $?
fi

# 捕获信号以优雅关闭
trap 'log_info "收到关闭信号，正在停止..."; exit 0' SIGTERM SIGINT

# 执行主程序
main "$@" 
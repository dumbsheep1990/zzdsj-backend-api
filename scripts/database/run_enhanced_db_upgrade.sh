#!/bin/bash
# 数据库增强版升级快速启动脚本
# 自动执行所有数据库字段增加和表结构创建

echo "🚀 智政知识库数据库增强版升级工具"
echo "=========================================="
echo "💡 目标：创建增强版文档管理表结构"
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
    else
        log_success "psycopg2 已安装"
    fi
    
    # 检查其他依赖
    dependencies=("datetime" "pathlib" "logging")
    for dep in "${dependencies[@]}"; do
        python3 -c "import $dep" 2>/dev/null
        if [ $? -eq 0 ]; then
            log_success "$dep 可用"
        else
            log_error "$dep 不可用"
        fi
    done
}

# 设置环境变量
setup_environment() {
    log_info "设置环境变量..."
    
    # 如果没有设置环境变量，使用默认值
    if [ -z "$POSTGRES_HOST" ]; then
        export POSTGRES_HOST="localhost"
        log_info "设置 POSTGRES_HOST=$POSTGRES_HOST"
    fi
    
    if [ -z "$POSTGRES_PORT" ]; then
        export POSTGRES_PORT="5432"
        log_info "设置 POSTGRES_PORT=$POSTGRES_PORT"
    fi
    
    if [ -z "$POSTGRES_DB" ]; then
        export POSTGRES_DB="zzdsj"
        log_info "设置 POSTGRES_DB=$POSTGRES_DB"
    fi
    
    if [ -z "$POSTGRES_USER" ]; then
        export POSTGRES_USER="zzdsj_user"
        log_info "设置 POSTGRES_USER=$POSTGRES_USER"
    fi
    
    if [ -z "$POSTGRES_PASSWORD" ]; then
        export POSTGRES_PASSWORD="zzdsj_pass"
        log_info "设置 POSTGRES_PASSWORD=***"
    fi
    
    log_success "环境变量配置完成"
}

# 检查脚本文件
check_upgrade_script() {
    log_info "检查升级脚本..."
    
    script_path="scripts/execute_enhanced_db_upgrade.py"
    
    if [ -f "$script_path" ]; then
        log_success "升级脚本存在: $script_path"
        return 0
    else
        log_error "升级脚本不存在: $script_path"
        return 1
    fi
}

# 执行数据库升级
execute_upgrade() {
    log_info "开始执行数据库升级..."
    echo "----------------------------------------"
    
    # 运行数据库升级脚本
    python3 scripts/execute_enhanced_db_upgrade.py
    upgrade_result=$?
    
    if [ $upgrade_result -eq 0 ]; then
        log_success "数据库升级成功!"
        return 0
    else
        log_error "数据库升级失败，退出码: $upgrade_result"
        return 1
    fi
}

# 验证升级结果
verify_upgrade() {
    log_info "验证升级结果..."
    
    # 使用psql验证表是否创建成功
    if command -v psql &> /dev/null; then
        log_info "使用psql验证表结构..."
        
        PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c "
        SELECT 
            schemaname, 
            tablename,
            hasindexes,
            hasrules,
            hastriggers
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename LIKE '%enhanced%' OR tablename LIKE '%chunks%' OR tablename LIKE '%shards%' OR tablename LIKE '%history%'
        ORDER BY tablename;
        " 2>/dev/null
        
        if [ $? -eq 0 ]; then
            log_success "数据库连接和表结构验证成功"
        else
            log_warning "psql验证失败，但升级可能仍然成功"
        fi
    else
        log_warning "psql 命令不可用，跳过验证"
    fi
}

# 显示后续步骤
show_next_steps() {
    echo ""
    echo "🎉 数据库增强版升级完成!"
    echo "=========================================="
    echo "📝 接下来可以执行的操作:"
    echo ""
    echo "1. 🧪 运行完整系统测试:"
    echo "   cd .."
    echo "   ./run_complete_system_test.sh"
    echo ""
    echo "2. 🔍 启动混合搜索服务:"
    echo "   ./scripts/start_with_hybrid_search.sh development"
    echo ""
    echo "3. 📊 查看数据库表结构:"
    echo "   psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB"
    echo "   \\dt *enhanced*"
    echo ""
    echo "4. 🔧 使用增强版文档管理器:"
    echo "   python3 -c \"from enhanced_document_manager import get_enhanced_document_manager; print('增强版文档管理器可用')\""
    echo ""
    echo "📄 升级总结："
    echo "   ✅ document_registry_enhanced - 增强版文档注册表"
    echo "   ✅ document_chunks - 文档切片表"
    echo "   ✅ document_vectors_enhanced - 增强版向量关联表"
    echo "   ✅ document_es_shards - ES分片关联表"
    echo "   ✅ document_processing_history - 处理历史表"
    echo "   ✅ 完整的索引和约束"
    echo ""
}

# 主执行流程
main() {
    echo ""
    
    # 1. 检查依赖
    check_dependencies
    
    # 2. 设置环境变量
    setup_environment
    
    # 3. 检查升级脚本
    if ! check_upgrade_script; then
        log_error "升级脚本检查失败"
        exit 1
    fi
    
    # 4. 执行数据库升级
    if execute_upgrade; then
        log_success "数据库升级执行成功"
        
        # 5. 验证升级结果
        verify_upgrade
        
        # 6. 显示后续步骤
        show_next_steps
        
        exit 0
    else
        log_error "数据库升级执行失败"
        echo ""
        echo "💡 故障排除建议："
        echo "   1. 检查数据库连接: psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB"
        echo "   2. 检查环境变量设置"
        echo "   3. 查看详细错误信息"
        echo "   4. 手动运行升级脚本: python3 scripts/execute_enhanced_db_upgrade.py"
        exit 1
    fi
}

# 显示帮助信息
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "数据库增强版升级快速启动脚本"
    echo ""
    echo "用法: $0"
    echo ""
    echo "🎯 升级内容:"
    echo "  文档注册增强表     - 添加用户ID、状态、统计字段"
    echo "  文档切片表         - 完整的切片追踪和元数据"
    echo "  向量关联增强表     - 详细的向量配置和关联"
    echo "  ES分片关联表       - ES文档分片数据追踪"
    echo "  处理历史表         - 完整的操作审计日志"
    echo ""
    echo "🔧 环境变量 (可选设置):"
    echo "  POSTGRES_HOST      - PostgreSQL主机 (默认: localhost)"
    echo "  POSTGRES_PORT      - PostgreSQL端口 (默认: 5432)"
    echo "  POSTGRES_DB        - 数据库名称 (默认: zzdsj)"
    echo "  POSTGRES_USER      - 数据库用户 (默认: zzdsj_user)"
    echo "  POSTGRES_PASSWORD  - 数据库密码 (默认: zzdsj_pass)"
    echo ""
    echo "📝 执行步骤:"
    echo "  1. 检查Python依赖"
    echo "  2. 设置环境变量"
    echo "  3. 测试数据库连接"
    echo "  4. 创建增强版表结构"
    echo "  5. 创建索引和约束"
    echo "  6. 创建演示数据"
    echo "  7. 验证升级结果"
    echo ""
    echo "💡 这个脚本会自动安装缺失的依赖，并创建完整的增强版表结构"
    exit 0
fi

# 捕获信号以优雅关闭
trap 'log_info "收到关闭信号，正在停止..."; exit 0' SIGTERM SIGINT

# 执行主程序
main "$@" 
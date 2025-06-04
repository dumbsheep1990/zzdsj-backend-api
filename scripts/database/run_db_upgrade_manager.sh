#!/bin/bash
# 统一的数据库升级管理脚本
# 提供多种升级选项：字段增强、完整升级、混合模式

echo "🚀 智政知识库数据库升级管理器"
echo "=========================================="
echo "💡 提供多种升级策略满足不同需求"
echo "📁 当前目录: $(pwd)"
echo "🐍 Python版本: $(python3 --version)"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_menu() {
    echo -e "${PURPLE}[MENU]${NC} $1"
}

# 显示升级选项菜单
show_upgrade_menu() {
    echo ""
    echo "🎯 请选择数据库升级策略："
    echo ""
    log_menu "1) 字段增强模式 - 为现有表添加增强版字段"
    echo "   ✓ 保留现有数据和结构"
    echo "   ✓ 添加user_id、processing_status、chunk_count等字段"
    echo "   ✓ 创建新的索引优化查询"
    echo "   ✓ 迁移现有数据到新字段"
    echo ""
    log_menu "2) 完整升级模式 - 创建完整的增强版表结构"
    echo "   ✓ 创建document_registry_enhanced等新表"
    echo "   ✓ 完整的文档切片和向量关联追踪"
    echo "   ✓ ES分片关联和处理历史记录"
    echo "   ✓ 演示数据和完整验证"
    echo ""
    log_menu "3) 混合升级模式 - 先字段增强，再完整升级"
    echo "   ✓ 最全面的升级策略"
    echo "   ✓ 确保新旧系统兼容"
    echo "   ✓ 渐进式迁移路径"
    echo ""
    log_menu "4) 检查模式 - 仅检查当前数据库状态"
    echo "   ✓ 不做任何修改"
    echo "   ✓ 显示表结构和字段信息"
    echo "   ✓ 提供升级建议"
    echo ""
    log_menu "5) 退出"
    echo ""
}

# 检查数据库连接
check_database_connection() {
    log_info "检查数据库连接..."
    
    # 设置默认环境变量
    export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
    export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
    export POSTGRES_DB="${POSTGRES_DB:-zzdsj}"
    export POSTGRES_USER="${POSTGRES_USER:-zzdsj_user}"
    export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-zzdsj_pass}"
    
    # 尝试连接数据库
    if command -v psql &> /dev/null; then
        PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT version();" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            log_success "数据库连接成功"
            return 0
        else
            log_error "数据库连接失败"
            return 1
        fi
    else
        log_warning "psql 命令不可用，跳过连接测试"
        return 0
    fi
}

# 检查当前数据库状态
check_database_status() {
    log_info "检查当前数据库状态..."
    
    if command -v psql &> /dev/null; then
        echo "📊 当前表结构："
        PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -c "
        SELECT 
            table_name,
            (SELECT count(*) FROM information_schema.columns WHERE table_name = t.table_name AND table_schema = 'public') as column_count
        FROM information_schema.tables t
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        AND (table_name LIKE '%document%' OR table_name LIKE '%vector%' OR table_name LIKE '%chunk%')
        ORDER BY table_name;
        " 2>/dev/null || log_warning "无法获取表结构信息"
    fi
}

# 执行字段增强升级
execute_field_enhancement() {
    log_info "开始执行字段增强升级..."
    echo "----------------------------------------"
    
    if [ -f "scripts/add_enhanced_fields_to_existing_tables.py" ]; then
        python3 scripts/add_enhanced_fields_to_existing_tables.py
        return $?
    else
        log_error "字段增强脚本不存在"
        return 1
    fi
}

# 执行完整升级
execute_full_upgrade() {
    log_info "开始执行完整升级..."
    echo "----------------------------------------"
    
    if [ -f "scripts/execute_enhanced_db_upgrade.py" ]; then
        python3 scripts/execute_enhanced_db_upgrade.py
        return $?
    else
        log_error "完整升级脚本不存在"
        return 1
    fi
}

# 执行混合升级
execute_hybrid_upgrade() {
    log_info "开始执行混合升级模式..."
    echo "========================================"
    
    # 第一步：字段增强
    log_info "第一步：为现有表添加增强版字段"
    if execute_field_enhancement; then
        log_success "字段增强完成"
    else
        log_error "字段增强失败，但继续执行完整升级"
    fi
    
    echo ""
    log_info "等待3秒后开始第二步..."
    sleep 3
    
    # 第二步：完整升级
    log_info "第二步：创建完整的增强版表结构"
    if execute_full_upgrade; then
        log_success "完整升级完成"
        return 0
    else
        log_error "完整升级失败"
        return 1
    fi
}

# 显示升级后的后续步骤
show_post_upgrade_steps() {
    echo ""
    echo "🎉 数据库升级完成!"
    echo "=========================================="
    echo "📝 接下来可以执行的操作:"
    echo ""
    echo "1. 🧪 运行完整系统测试:"
    echo "   cd .."
    echo "   ./run_complete_system_test.sh"
    echo ""
    echo "2. 🔍 测试增强版文档管理器:"
    echo "   python3 -c \"from enhanced_document_manager import get_enhanced_document_manager; print('增强版可用')\""
    echo ""
    echo "3. 🔧 查看数据库状态:"
    echo "   psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB"
    echo "   \\dt"
    echo ""
    echo "4. 📊 启动混合搜索服务:"
    echo "   ./scripts/start_with_hybrid_search.sh development"
    echo ""
}

# 主执行流程
main() {
    # 检查环境变量和数据库连接
    if ! check_database_connection; then
        echo ""
        echo "💡 数据库连接问题排查:"
        echo "   1. 检查PostgreSQL服务是否运行"
        echo "   2. 验证连接参数："
        echo "      POSTGRES_HOST=$POSTGRES_HOST"
        echo "      POSTGRES_PORT=$POSTGRES_PORT"
        echo "      POSTGRES_DB=$POSTGRES_DB"
        echo "      POSTGRES_USER=$POSTGRES_USER"
        echo "   3. 确认网络连接和防火墙设置"
        exit 1
    fi
    
    # 显示当前数据库状态
    check_database_status
    
    # 主菜单循环
    while true; do
        show_upgrade_menu
        read -p "请选择操作 (1-5): " choice
        
        case $choice in
            1)
                log_info "您选择了：字段增强模式"
                if execute_field_enhancement; then
                    log_success "字段增强升级成功!"
                    show_post_upgrade_steps
                    break
                else
                    log_error "字段增强升级失败"
                    read -p "是否重试? (y/n): " retry
                    if [ "$retry" != "y" ]; then
                        break
                    fi
                fi
                ;;
            2)
                log_info "您选择了：完整升级模式"
                if execute_full_upgrade; then
                    log_success "完整升级成功!"
                    show_post_upgrade_steps
                    break
                else
                    log_error "完整升级失败"
                    read -p "是否重试? (y/n): " retry
                    if [ "$retry" != "y" ]; then
                        break
                    fi
                fi
                ;;
            3)
                log_info "您选择了：混合升级模式"
                if execute_hybrid_upgrade; then
                    log_success "混合升级成功!"
                    show_post_upgrade_steps
                    break
                else
                    log_error "混合升级失败"
                    read -p "是否重试? (y/n): " retry
                    if [ "$retry" != "y" ]; then
                        break
                    fi
                fi
                ;;
            4)
                log_info "您选择了：检查模式"
                check_database_status
                echo ""
                echo "🔍 数据库状态检查完成"
                echo "💡 建议根据当前状态选择合适的升级模式"
                echo ""
                ;;
            5)
                log_info "退出升级管理器"
                break
                ;;
            *)
                log_error "无效选择，请输入 1-5"
                ;;
        esac
    done
}

# 显示帮助信息
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "数据库升级管理器 - 智政知识库"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项："
    echo "  --help, -h     显示此帮助信息"
    echo "  --check        仅检查数据库状态"
    echo "  --field        执行字段增强升级"
    echo "  --full         执行完整升级"
    echo "  --hybrid       执行混合升级"
    echo ""
    echo "🎯 升级模式说明:"
    echo ""
    echo "字段增强模式:"
    echo "  - 适用于已有基础表结构的情况"
    echo "  - 仅添加新字段和索引"
    echo "  - 保持现有数据完整性"
    echo ""
    echo "完整升级模式:"
    echo "  - 创建全新的增强版表结构"
    echo "  - 支持完整的文档生命周期管理"
    echo "  - 包含演示数据和验证"
    echo ""
    echo "混合升级模式:"
    echo "  - 结合两种模式的优点"
    echo "  - 提供最大的兼容性"
    echo "  - 推荐用于生产环境"
    echo ""
    echo "🔧 环境变量:"
    echo "  POSTGRES_HOST      - 数据库主机 (默认: localhost)"
    echo "  POSTGRES_PORT      - 数据库端口 (默认: 5432)"
    echo "  POSTGRES_DB        - 数据库名称 (默认: zzdsj)"
    echo "  POSTGRES_USER      - 数据库用户 (默认: zzdsj_user)"
    echo "  POSTGRES_PASSWORD  - 数据库密码 (默认: zzdsj_pass)"
    exit 0
fi

# 命令行参数处理
case "$1" in
    --check)
        check_database_connection && check_database_status
        exit 0
        ;;
    --field)
        check_database_connection && execute_field_enhancement
        exit $?
        ;;
    --full)
        check_database_connection && execute_full_upgrade
        exit $?
        ;;
    --hybrid)
        check_database_connection && execute_hybrid_upgrade
        exit $?
        ;;
    "")
        # 交互模式
        main
        ;;
    *)
        log_error "未知参数: $1"
        echo "使用 --help 查看帮助信息"
        exit 1
        ;;
esac 
#!/bin/bash
# 完整系统测试启动脚本
# 整合PostgreSQL增强版数据库 + Elasticsearch混合搜索 + 存储系统验证

echo "🚀 智政知识库完整系统测试"
echo "=========================================="
echo "💡 包含：增强版PostgreSQL + 混合搜索ES + 存储系统验证"
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
    
    dependencies=("psycopg2" "elasticsearch" "yaml")
    missing_deps=()
    
    for dep in "${dependencies[@]}"; do
        python3 -c "import $dep" 2>/dev/null
        if [ $? -ne 0 ]; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_warning "缺少以下依赖: ${missing_deps[*]}"
        log_info "正在安装缺失的依赖..."
        
        for dep in "${missing_deps[@]}"; do
            case $dep in
                "psycopg2")
                    pip3 install psycopg2-binary
                    ;;
                "elasticsearch")
                    pip3 install elasticsearch
                    ;;
                "yaml")
                    pip3 install pyyaml
                    ;;
            esac
        done
    else
        log_success "所有Python依赖都已安装"
    fi
}

# 检查环境变量
check_environment() {
    log_info "检查环境变量配置..."
    
    # 设置默认环境变量
    if [ -z "$ELASTICSEARCH_URL" ]; then
        export ELASTICSEARCH_URL="http://localhost:9200"
        log_info "设置 ELASTICSEARCH_URL=$ELASTICSEARCH_URL"
    fi
    
    if [ -z "$ELASTICSEARCH_HYBRID_SEARCH" ]; then
        export ELASTICSEARCH_HYBRID_SEARCH="true"
        log_info "设置 ELASTICSEARCH_HYBRID_SEARCH=$ELASTICSEARCH_HYBRID_SEARCH"
    fi
    
    if [ -z "$ELASTICSEARCH_HYBRID_WEIGHT" ]; then
        export ELASTICSEARCH_HYBRID_WEIGHT="0.7"
        log_info "设置 ELASTICSEARCH_HYBRID_WEIGHT=$ELASTICSEARCH_HYBRID_WEIGHT"
    fi
    
    log_success "环境变量配置完成"
}

# 检查项目结构
check_project_structure() {
    log_info "检查项目结构..."
    
    required_paths=(
        "zzdsj-backend-api"
        "zzdsj-backend-api/scripts"
        "zzdsj-backend-api/scripts/run_complete_db_test.py"
    )
    
    missing_paths=()
    for path in "${required_paths[@]}"; do
        if [ ! -e "$path" ]; then
            missing_paths+=("$path")
        fi
    done
    
    if [ ${#missing_paths[@]} -gt 0 ]; then
        log_error "缺少必需的项目文件/目录:"
        for path in "${missing_paths[@]}"; do
            echo "  ❌ $path"
        done
        return 1
    fi
    
    log_success "项目结构检查通过"
    return 0
}

# 运行完整系统测试
run_system_test() {
    log_info "启动完整系统测试..."
    echo "----------------------------------------"
    
    # 进入后端API目录
    cd zzdsj-backend-api
    
    # 运行完整系统测试脚本
    if [ -f "scripts/run_complete_db_test.py" ]; then
        python3 scripts/run_complete_db_test.py
        test_result=$?
    else
        log_error "未找到完整系统测试脚本"
        return 1
    fi
    
    # 返回原目录
    cd ..
    
    return $test_result
}

# 主执行流程
main() {
    echo ""
    
    # 1. 检查项目结构
    if ! check_project_structure; then
        log_error "项目结构检查失败"
        exit 1
    fi
    
    # 2. 检查依赖
    check_dependencies
    
    # 3. 检查环境变量
    check_environment
    
    # 4. 运行系统测试
    if run_system_test; then
        log_success "完整系统测试成功!"
        echo ""
        echo "🎉 系统测试总结："
        echo "   ✅ PostgreSQL增强版数据库: 测试通过"
        echo "   ✅ Elasticsearch混合搜索: 测试通过"
        echo "   ✅ 存储系统验证: 测试通过"
        echo "   ✅ 文档管理器: 测试通过"
        echo ""
        echo "💡 系统已准备就绪，可以开始使用混合搜索功能!"
        exit 0
    else
        log_error "完整系统测试失败"
        echo ""
        echo "💡 故障排除建议："
        echo "   1. 检查PostgreSQL数据库连接"
        echo "   2. 检查Elasticsearch服务状态: curl $ELASTICSEARCH_URL"
        echo "   3. 查看详细测试报告: cat zzdsj-backend-api/complete_test_report.json"
        exit 1
    fi
}

# 显示帮助信息
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "智政知识库完整系统测试脚本"
    echo ""
    echo "用法: $0"
    echo ""
    echo "🎯 测试内容:"
    echo "  环境检查          - Python依赖和环境变量"
    echo "  PostgreSQL测试    - 增强版数据库表结构"
    echo "  Elasticsearch测试 - 混合搜索索引和模板"
    echo "  存储系统测试      - 存储架构和配置验证"
    echo "  混合搜索验证      - 完整配置和功能验证"
    echo "  文档管理器测试    - 增强版文档管理功能"
    echo ""
    echo "🔧 关键环境变量:"
    echo "  ELASTICSEARCH_URL           - ES服务地址 (默认: http://localhost:9200)"
    echo "  ELASTICSEARCH_HYBRID_SEARCH - 混合搜索开关 (默认: true)"
    echo "  ELASTICSEARCH_HYBRID_WEIGHT - 混合搜索权重 (默认: 0.7)"
    echo ""
    echo "📄 输出文件:"
    echo "  zzdsj-backend-api/complete_test_report.json - 详细测试报告"
    echo ""
    echo "💡 这个脚本会自动安装缺失的Python依赖，并设置必要的环境变量"
    exit 0
fi

# 捕获信号以优雅关闭
trap 'log_info "收到关闭信号，正在停止..."; exit 0' SIGTERM SIGINT

# 执行主程序
main "$@" 
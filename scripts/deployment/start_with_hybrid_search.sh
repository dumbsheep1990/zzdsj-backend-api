#!/bin/bash
set -e

# 智政知识库核心存储系统启动脚本
# 确保Elasticsearch和MinIO作为基础必需组件正确配置并启动应用程序
# 无论在任何部署模式下，这两个组件都是必需的

echo "🚀 智政知识库核心存储系统启动脚本"
echo "=========================================="
echo "💡 核心理念：ES+MinIO双存储引擎是系统基础"

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

log_highlight() {
    echo -e "${PURPLE}[HIGHLIGHT]${NC} $1"
}

# 检查环境变量
check_environment() {
    log_info "检查环境配置..."
    
    # 检查部署模式
    if [ -z "$DEPLOYMENT_MODE" ]; then
        log_info "设置默认部署模式 (DEPLOYMENT_MODE=standard)"
        export DEPLOYMENT_MODE="standard"
    fi
    
    log_highlight "当前部署模式: $DEPLOYMENT_MODE"
    
    # 检查Elasticsearch配置 (基础必需)
    if [ -z "$ELASTICSEARCH_URL" ]; then
        log_warning "ELASTICSEARCH_URL 未设置，使用默认值: http://localhost:9200"
        export ELASTICSEARCH_URL="http://localhost:9200"
    fi
    
    # 确保混合检索配置正确 (系统核心功能)
    if [ -z "$ELASTICSEARCH_HYBRID_SEARCH" ]; then
        log_info "强制启用混合检索 (ELASTICSEARCH_HYBRID_SEARCH=true)"
        export ELASTICSEARCH_HYBRID_SEARCH="true"
    fi
    
    if [ -z "$ELASTICSEARCH_HYBRID_WEIGHT" ]; then
        log_info "设置混合检索权重 (ELASTICSEARCH_HYBRID_WEIGHT=0.7)"
        export ELASTICSEARCH_HYBRID_WEIGHT="0.7"
    fi
    
    # 检查MinIO配置 (基础必需)
    if [ -z "$MINIO_ENDPOINT" ]; then
        log_warning "MINIO_ENDPOINT 未设置，使用默认值: localhost:9000"
        export MINIO_ENDPOINT="localhost:9000"
    fi
    
    if [ -z "$MINIO_ACCESS_KEY" ]; then
        log_warning "MINIO_ACCESS_KEY 未设置，使用默认值: minioadmin"
        export MINIO_ACCESS_KEY="minioadmin"
    fi
    
    if [ -z "$MINIO_SECRET_KEY" ]; then
        log_warning "MINIO_SECRET_KEY 未设置，使用默认值: minioadmin"
        export MINIO_SECRET_KEY="minioadmin"
    fi
    
    if [ -z "$MINIO_BUCKET" ]; then
        log_info "设置默认存储桶 (MINIO_BUCKET=knowledge-docs)"
        export MINIO_BUCKET="knowledge-docs"
    fi
    
    # 禁用非核心组件（在最小化模式下）
    if [ "$DEPLOYMENT_MODE" = "minimal" ]; then
        log_info "最小化模式：禁用Milvus和Nacos"
        export MILVUS_ENABLED="false"
        export NACOS_ENABLED="false"
    fi
    
    log_success "环境配置检查完成"
}

# 显示系统架构信息
display_architecture_info() {
    echo ""
    log_highlight "🏗️ 智政知识库存储架构"
    echo "=========================================="
    echo "📋 核心存储引擎 (基础必需):"
    echo "   📁 MinIO: 用户文件上传存储引擎"
    echo "   🔍 Elasticsearch: 文档分片和混合检索引擎"
    echo ""
    echo "🤖 混合检索算法:"
    echo "   🧠 语义搜索: ${ELASTICSEARCH_HYBRID_WEIGHT:-0.7}"
    echo "   🔤 关键词搜索: $(echo "1.0 - ${ELASTICSEARCH_HYBRID_WEIGHT:-0.7}" | bc -l)"
    echo ""
    echo "🎯 部署模式: $DEPLOYMENT_MODE"
    
    case "$DEPLOYMENT_MODE" in
        "minimal")
            echo "   📦 仅包含基础必需组件"
            echo "   ✅ PostgreSQL + Elasticsearch + MinIO + Redis + RabbitMQ"
            ;;
        "standard")
            echo "   📦 包含完整功能组件"
            echo "   ✅ 基础组件 + Milvus + Nacos + 完整监控"
            ;;
        "production")
            echo "   📦 包含全部服务和监控"
            echo "   ✅ 标准组件 + 高级安全 + 完整告警 + 性能监控"
            ;;
    esac
    echo "=========================================="
}

# 等待核心服务就绪
wait_for_core_services() {
    log_info "等待核心存储服务就绪..."
    
    local max_attempts=60
    local attempt=1
    
    # 等待Elasticsearch (基础必需)
    log_info "等待Elasticsearch服务..."
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$ELASTICSEARCH_URL/_cluster/health" > /dev/null 2>&1; then
            log_success "Elasticsearch服务已就绪"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "Elasticsearch服务在指定时间内未就绪 - 这是基础必需组件"
            return 1
        fi
        
        log_info "尝试 $attempt/$max_attempts - Elasticsearch未就绪，等待5秒..."
        sleep 5
        ((attempt++))
    done
    
    # 等待MinIO (基础必需)
    attempt=1
    local minio_url="http://${MINIO_ENDPOINT}/minio/health/live"
    log_info "等待MinIO服务..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$minio_url" > /dev/null 2>&1; then
            log_success "MinIO服务已就绪"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "MinIO服务在指定时间内未就绪 - 这是基础必需组件"
            return 1
        fi
        
        log_info "尝试 $attempt/$max_attempts - MinIO未就绪，等待5秒..."
        sleep 5
        ((attempt++))
    done
    
    log_success "核心存储服务已就绪"
    return 0
}

# 运行核心存储初始化
run_core_storage_initialization() {
    log_info "运行核心存储系统初始化..."
    
    # 检查Python环境
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未找到"
        return 1
    fi
    
    # 运行核心存储初始化脚本
    if python3 scripts/init_core_storage.py; then
        log_success "核心存储系统初始化完成"
        return 0
    else
        log_error "核心存储系统初始化失败"
        return 1
    fi
}

# 验证存储系统配置
verify_storage_system() {
    log_info "验证存储系统配置..."
    
    # 使用Python验证配置
    python3 -c "
import os
import sys
sys.path.append('.')

try:
    from app.config import settings
    from app.utils.storage.storage_detector import StorageDetector
    
    # 检查部署模式
    print(f'部署模式: {settings.DEPLOYMENT_MODE}')
    
    # 检查核心存储引擎
    detector = StorageDetector()
    
    # 验证核心存储组件
    validation = detector.validate_core_storage()
    
    print(f'核心存储状态: {validation[\"overall_status\"]}')
    
    # 检查Elasticsearch配置
    print(f'Elasticsearch URL: {settings.ELASTICSEARCH_URL}')
    print(f'混合检索启用: {settings.ELASTICSEARCH_HYBRID_SEARCH}')
    print(f'混合检索权重: {settings.ELASTICSEARCH_HYBRID_WEIGHT}')
    
    # 检查MinIO配置
    print(f'MinIO端点: {settings.MINIO_ENDPOINT}')
    print(f'MinIO存储桶: {settings.MINIO_BUCKET}')
    
    # 获取存储架构信息
    storage_info = detector.get_vector_store_info()
    
    if validation['overall_status'] == 'healthy':
        print('✅ 核心存储系统配置验证成功')
        print('📋 存储架构总览:')
        print(f'  • 架构类型: {storage_info[\"storage_architecture\"][\"type\"]}')
        print(f'  • 文件存储: {storage_info[\"storage_architecture\"][\"file_storage_engine\"]}')
        print(f'  • 检索引擎: {storage_info[\"storage_architecture\"][\"search_engine\"]}')
        print(f'  • 混合检索: {\"启用\" if storage_info[\"hybrid_search_status\"][\"enabled\"] else \"禁用\"}')
        sys.exit(0)
    else:
        print('❌ 核心存储系统配置验证失败')
        if validation.get('recommendations'):
            print('建议:')
            for rec in validation['recommendations']:
                print(f'  • {rec}')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ 验证过程出错: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "存储系统配置验证通过"
        return 0
    else
        log_error "存储系统配置验证失败"
        return 1
    fi
}

# 启动应用程序
start_application() {
    log_info "启动应用程序..."
    
    # 检查启动模式
    case "${1:-development}" in
        "development"|"dev")
            log_info "开发模式启动"
            exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
            ;;
        "production"|"prod")
            log_info "生产模式启动"
            exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
            ;;
        "minimal")
            log_info "最小化模式启动"
            exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
            ;;
        *)
            log_warning "未知启动模式: $1，使用开发模式"
            exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
            ;;
    esac
}

# 主要执行流程
main() {
    local start_mode="${1:-development}"
    
    echo "启动模式: $start_mode"
    echo ""
    
    # 1. 检查环境配置
    if ! check_environment; then
        log_error "环境检查失败"
        exit 1
    fi
    
    # 2. 显示架构信息
    display_architecture_info
    
    # 3. 等待核心服务就绪
    log_info "检查核心存储服务状态..."
    
    if ! wait_for_core_services; then
        log_error "核心存储服务不可用，无法启动系统"
        echo ""
        echo "💡 故障排除建议："
        echo "   1. 检查Docker Compose服务状态: docker-compose ps"
        echo "   2. 查看Elasticsearch日志: docker-compose logs elasticsearch"
        echo "   3. 查看MinIO日志: docker-compose logs minio"
        echo "   4. 确认网络连接正常"
        exit 1
    fi
    
    # 4. 运行核心存储初始化
    log_info "初始化核心存储系统..."
    
    if ! run_core_storage_initialization; then
        log_warning "核心存储初始化失败，但继续启动..."
        echo ""
        echo "⚠️ 可能的问题："
        echo "   • 索引或存储桶可能需要手动创建"
        echo "   • 某些高级功能可能受限"
    fi
    
    # 5. 验证存储系统配置
    if ! verify_storage_system; then
        log_warning "存储系统配置验证失败，但继续启动..."
    fi
    
    # 6. 启动应用
    log_success "核心存储系统准备就绪，启动应用程序..."
    echo ""
    echo "🎉 系统启动总结："
    echo "   ✅ Elasticsearch: 文档分片和混合检索引擎"
    echo "   ✅ MinIO: 用户文件上传存储引擎"
    echo "   ✅ 混合检索: 语义搜索($ELASTICSEARCH_HYBRID_WEIGHT) + 关键词搜索"
    echo "   ✅ 部署模式: $DEPLOYMENT_MODE"
    echo ""
    start_application "$start_mode"
}

# 捕获信号以优雅关闭
trap 'log_info "收到关闭信号，正在停止..."; exit 0' SIGTERM SIGINT

# 显示帮助信息
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "智政知识库核心存储系统启动脚本"
    echo ""
    echo "用法: $0 [模式]"
    echo ""
    echo "可用模式:"
    echo "  development, dev    - 开发模式 (默认，支持热重载)"
    echo "  production, prod    - 生产模式 (多进程)"
    echo "  minimal            - 最小化模式"
    echo ""
    echo "🏗️ 核心存储架构:"
    echo "  Elasticsearch      - 文档分片和混合检索引擎 (基础必需)"
    echo "  MinIO              - 用户文件上传存储引擎 (基础必需)"
    echo ""
    echo "🎯 部署模式说明:"
    echo "  minimal            - 仅启用核心组件 (ES + MinIO + 基础服务)"
    echo "  standard           - 标准配置 (核心组件 + Milvus + Nacos)"
    echo "  production         - 生产配置 (标准配置 + 完整监控)"
    echo ""
    echo "🔧 关键环境变量:"
    echo "  # 部署模式"
    echo "  DEPLOYMENT_MODE            - 部署模式 (minimal/standard/production)"
    echo ""
    echo "  # Elasticsearch配置 (基础必需)"
    echo "  ELASTICSEARCH_URL           - Elasticsearch连接URL"
    echo "  ELASTICSEARCH_HYBRID_SEARCH - 混合检索启用状态 (强制true)"
    echo "  ELASTICSEARCH_HYBRID_WEIGHT - 混合检索权重 (默认: 0.7)"
    echo ""
    echo "  # MinIO配置 (基础必需)"
    echo "  MINIO_ENDPOINT             - MinIO端点地址 (默认: localhost:9000)"
    echo "  MINIO_ACCESS_KEY           - MinIO访问密钥 (默认: minioadmin)"
    echo "  MINIO_SECRET_KEY           - MinIO密钥 (默认: minioadmin)"
    echo "  MINIO_BUCKET               - MinIO存储桶 (默认: knowledge-docs)"
    echo ""
    echo "💡 核心理念:"
    echo "  无论选择哪种部署模式，Elasticsearch和MinIO都是基础必需组件"
    echo "  系统强制启用混合检索功能，提供最佳的搜索体验"
    echo ""
    echo "示例:"
    echo "  $0 development              # 开发模式"
    echo "  $0 production               # 生产模式"
    echo "  DEPLOYMENT_MODE=minimal $0  # 最小化模式"
    exit 0
fi

# 执行主程序
main "$@" 
#!/bin/bash

# Celery启动脚本
# 用于开发环境启动Celery相关服务

set -e

# 颜色输出
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
    log_info "检查依赖..."
    
    # 检查Python环境
    if ! command -v python &> /dev/null; then
        log_error "Python未安装或不在PATH中"
        exit 1
    fi
    
    # 检查Celery
    if ! python -c "import celery" &> /dev/null; then
        log_error "Celery未安装，请运行: pip install celery"
        exit 1
    fi
    
    # 检查Flower
    if ! python -c "import flower" &> /dev/null; then
        log_error "Flower未安装，请运行: pip install flower"
        exit 1
    fi
    
    # 检查Redis连接
    if ! python -c "import redis; r = redis.Redis(host='localhost', port=6379); r.ping()" &> /dev/null; then
        log_warning "Redis连接失败，请确保Redis服务正在运行"
    fi
    
    # 检查RabbitMQ连接
    if ! python -c "import pika; pika.BlockingConnection(pika.ConnectionParameters('localhost'))" &> /dev/null; then
        log_warning "RabbitMQ连接失败，请确保RabbitMQ服务正在运行"
    fi
    
    log_success "依赖检查完成"
}

# 启动Celery Worker
start_worker() {
    log_info "启动Celery Worker..."
    
    # 创建日志目录
    mkdir -p logs
    
    # 启动默认队列worker
    celery -A app.worker worker \
        --loglevel=info \
        --concurrency=4 \
        --queues=default,cache \
        --logfile=logs/celery-worker.log \
        --pidfile=logs/celery-worker.pid \
        --detach
    
    # 启动维护队列worker
    celery -A app.worker worker \
        --loglevel=info \
        --concurrency=2 \
        --queues=maintenance,monitoring \
        --logfile=logs/celery-worker-maintenance.log \
        --pidfile=logs/celery-worker-maintenance.pid \
        --detach
    
    # 启动报表队列worker
    celery -A app.worker worker \
        --loglevel=info \
        --concurrency=1 \
        --queues=reports,analytics \
        --logfile=logs/celery-worker-reports.log \
        --pidfile=logs/celery-worker-reports.pid \
        --detach
    
    log_success "Celery Worker已启动"
}

# 启动Celery Beat
start_beat() {
    log_info "启动Celery Beat..."
    
    # 创建数据目录
    mkdir -p data/celery
    
    celery -A app.worker beat \
        --loglevel=info \
        --schedule=data/celery/celerybeat-schedule \
        --logfile=logs/celery-beat.log \
        --pidfile=logs/celery-beat.pid \
        --detach
    
    log_success "Celery Beat已启动"
}

# 启动Flower监控
start_flower() {
    log_info "启动Flower监控..."
    
    celery -A app.worker flower \
        --port=5555 \
        --basic_auth=admin:password \
        --logfile=logs/flower.log \
        --logging=info &
    
    echo $! > logs/flower.pid
    
    log_success "Flower监控已启动，访问地址: http://localhost:5555"
    log_info "用户名: admin, 密码: password"
}

# 停止所有Celery服务
stop_all() {
    log_info "停止所有Celery服务..."
    
    # 停止worker进程
    if [ -f logs/celery-worker.pid ]; then
        kill -TERM $(cat logs/celery-worker.pid) 2>/dev/null || true
        rm -f logs/celery-worker.pid
    fi
    
    if [ -f logs/celery-worker-maintenance.pid ]; then
        kill -TERM $(cat logs/celery-worker-maintenance.pid) 2>/dev/null || true
        rm -f logs/celery-worker-maintenance.pid
    fi
    
    if [ -f logs/celery-worker-reports.pid ]; then
        kill -TERM $(cat logs/celery-worker-reports.pid) 2>/dev/null || true
        rm -f logs/celery-worker-reports.pid
    fi
    
    # 停止beat进程
    if [ -f logs/celery-beat.pid ]; then
        kill -TERM $(cat logs/celery-beat.pid) 2>/dev/null || true
        rm -f logs/celery-beat.pid
    fi
    
    # 停止flower进程
    if [ -f logs/flower.pid ]; then
        kill -TERM $(cat logs/flower.pid) 2>/dev/null || true
        rm -f logs/flower.pid
    fi
    
    # 等待进程结束
    sleep 2
    
    # 强制杀死剩余进程
    pkill -f "celery.*worker" 2>/dev/null || true
    pkill -f "celery.*beat" 2>/dev/null || true
    pkill -f "celery.*flower" 2>/dev/null || true
    
    log_success "所有Celery服务已停止"
}

# 查看状态
status() {
    log_info "Celery服务状态:"
    
    echo "Worker进程:"
    if [ -f logs/celery-worker.pid ] && kill -0 $(cat logs/celery-worker.pid) 2>/dev/null; then
        echo "  ✅ Default Worker (PID: $(cat logs/celery-worker.pid))"
    else
        echo "  ❌ Default Worker"
    fi
    
    if [ -f logs/celery-worker-maintenance.pid ] && kill -0 $(cat logs/celery-worker-maintenance.pid) 2>/dev/null; then
        echo "  ✅ Maintenance Worker (PID: $(cat logs/celery-worker-maintenance.pid))"
    else
        echo "  ❌ Maintenance Worker"
    fi
    
    if [ -f logs/celery-worker-reports.pid ] && kill -0 $(cat logs/celery-worker-reports.pid) 2>/dev/null; then
        echo "  ✅ Reports Worker (PID: $(cat logs/celery-worker-reports.pid))"
    else
        echo "  ❌ Reports Worker"
    fi
    
    echo "Beat调度器:"
    if [ -f logs/celery-beat.pid ] && kill -0 $(cat logs/celery-beat.pid) 2>/dev/null; then
        echo "  ✅ Celery Beat (PID: $(cat logs/celery-beat.pid))"
    else
        echo "  ❌ Celery Beat"
    fi
    
    echo "监控界面:"
    if [ -f logs/flower.pid ] && kill -0 $(cat logs/flower.pid) 2>/dev/null; then
        echo "  ✅ Flower (PID: $(cat logs/flower.pid)) - http://localhost:5555"
    else
        echo "  ❌ Flower"
    fi
}

# 显示帮助
show_help() {
    echo "Celery管理脚本"
    echo ""
    echo "用法:"
    echo "  $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start       启动所有Celery服务 (worker + beat + flower)"
    echo "  worker      仅启动Celery Worker"
    echo "  beat        仅启动Celery Beat"
    echo "  flower      仅启动Flower监控"
    echo "  stop        停止所有Celery服务"
    echo "  restart     重启所有Celery服务"
    echo "  status      查看服务状态"
    echo "  logs        查看日志"
    echo "  check       检查依赖和配置"
    echo "  help        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start           # 启动所有服务"
    echo "  $0 worker          # 仅启动worker"
    echo "  $0 status          # 查看状态"
    echo "  $0 logs worker     # 查看worker日志"
}

# 查看日志
show_logs() {
    local service=$1
    
    case $service in
        worker|w)
            tail -f logs/celery-worker.log
            ;;
        maintenance|m)
            tail -f logs/celery-worker-maintenance.log
            ;;
        reports|r)
            tail -f logs/celery-worker-reports.log
            ;;
        beat|b)
            tail -f logs/celery-beat.log
            ;;
        flower|f)
            tail -f logs/flower.log
            ;;
        all|*)
            echo "请选择要查看的日志:"
            echo "  worker      - 默认Worker日志"
            echo "  maintenance - 维护Worker日志"
            echo "  reports     - 报表Worker日志"
            echo "  beat        - Beat调度器日志"
            echo "  flower      - Flower监控日志"
            echo "  all         - 所有日志"
            ;;
    esac
}

# 主函数
main() {
    case ${1:-help} in
        start)
            check_dependencies
            stop_all
            start_worker
            start_beat
            start_flower
            status
            ;;
        worker)
            check_dependencies
            start_worker
            ;;
        beat)
            check_dependencies
            start_beat
            ;;
        flower)
            check_dependencies
            start_flower
            ;;
        stop)
            stop_all
            ;;
        restart)
            stop_all
            sleep 2
            check_dependencies
            start_worker
            start_beat
            start_flower
            status
            ;;
        status)
            status
            ;;
        logs)
            show_logs $2
            ;;
        check)
            check_dependencies
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@" 
@echo off
echo ================================
echo AI助手项目 Docker 部署脚本
echo ================================

echo.
echo 1. 检查Docker是否运行...
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker未运行或未安装，请先启动Docker Desktop
    pause
    exit /b 1
)
echo [OK] Docker运行正常

echo.
echo 2. 停止并删除旧容器...
docker-compose down -v

echo.
echo 3. 构建并启动服务...
docker-compose up --build -d

echo.
echo 4. 等待服务启动完成...
timeout /t 30 /nobreak

echo.
echo 5. 检查服务状态...
docker-compose ps

echo.
echo ================================
echo 部署完成！
echo ================================
echo.
echo 服务访问地址：
echo - AI助手API: http://localhost:8000
echo - API文档: http://localhost:8000/docs
echo - 数据库管理: http://localhost:5050
echo.
echo 数据库连接信息：
echo - 主机: localhost:5432
echo - 用户名: postgres
echo - 密码: securepassword123
echo - 数据库: ai_assistant
echo.
echo 按任意键查看日志...
pause >nul
docker-compose logs -f 
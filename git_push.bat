@echo off
chcp 65001 >nul

echo ============================
echo      Git 快速提交工具
echo ============================

echo.

:: 检查是否Git仓库
git status >nul 2>&1

if %errorlevel% neq 0 (
    echo 当前目录不是Git仓库！
    pause
    exit
)

echo 当前修改：
git status

echo.
set /p msg=请输入提交说明：

if "%msg%"=="" (
    echo 提交说明不能为空！
    pause
    exit
)


echo.
echo ===== 添加文件 =====
git add .


echo.
echo ===== 提交 =====
git commit -m "%msg%"


if %errorlevel% neq 0 (
    echo 提交失败！
    pause
    exit
)


echo.
echo ===== 推送远程 =====
git push


if %errorlevel% neq 0 (
    echo 推送失败，请检查远程仓库！
    pause
    exit
)


echo.
echo ============================
echo 提交并推送完成！
echo ============================

pause
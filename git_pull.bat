@echo off
chcp 65001 >nul


echo ============================
echo      Git 拉取工具
echo ============================


echo.

git status


echo.
echo 当前分支：

git branch --show-current


echo.

pause


echo.
echo ===== 开始拉取 =====

git pull


if %errorlevel% neq 0 (
    echo.
    echo 拉取失败！
    pause
    exit
)


echo.
echo ============================
echo 拉取完成！
echo ============================

pause
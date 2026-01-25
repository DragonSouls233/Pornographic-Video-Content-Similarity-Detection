@echo off

REM 打包脚本 - 将GUI程序打包成EXE文件

echo =========================================
echo 模特查重管理系统 - 打包脚本
echo =========================================
echo 

REM 检查是否存在测试目录，如果不存在则创建
if not exist "F:\测试" (
    echo 创建测试目录...
    mkdir "F:\测试"
)

REM 复制核心文件到测试目录
echo 复制核心文件到测试目录...
xcopy /E /I /Y "core" "F:\测试\core"
xcopy /E /I /Y "gui" "F:\测试\gui"
copy /Y ".gitignore" "F:\测试\.gitignore"
copy /Y "README.md" "F:\测试\README.md"
copy /Y "config.yaml" "F:\测试\config.yaml"
copy /Y "models.json" "F:\测试\models.json"

echo 

REM 切换到测试目录并执行打包命令
echo 开始打包EXE文件...
echo 请稍候，这可能需要几分钟时间...

cd "F:\测试"

REM 使用PyInstaller打包
echo 执行打包命令...
pyinstaller --onefile --windowed --name "模特查重管理系统" --add-data "core;core" gui/gui.py

echo 

REM 检查打包结果
if exist "dist\模特查重管理系统.exe" (
    echo =========================================
    echo 打包成功！
    echo =========================================
    echo 生成的EXE文件位置：
    echo F:\测试\dist\模特查重管理系统.exe
    echo 
    echo 您可以将此EXE文件复制到任何位置使用。
    echo 首次运行时，程序会自动创建必要的配置文件。
) else (
    echo =========================================
    echo 打包失败！
    echo =========================================
    echo 请检查错误信息并尝试解决问题。
)

echo 
echo 按任意键退出...
pause > nul

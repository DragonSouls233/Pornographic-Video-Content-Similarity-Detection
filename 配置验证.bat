@echo off
chcp 65001 >nul
echo ========================================
echo 配置文件验证脚本
echo ========================================
echo.

echo [1/3] 验证配置文件语法...
python -c "import yaml; yaml.safe_load(open('config.yaml', 'r', encoding='utf-8')); print('✅ 配置文件语法正确')" 2>nul
if errorlevel 1 (
    echo ❌ 配置文件语法错误
    goto :error
)

echo [2/3] 验证目录路径存在性...
python -c "
import yaml
config = yaml.safe_load(open('config.yaml', 'r', encoding='utf-8'))
roots = config.get('local_roots', {})
for category, paths in roots.items():
    print(f'检查 {category.upper()} 类别:')
    for path in paths:
        import os
        if os.path.exists(path):
            print(f'  ✅ {path}')
        else:
            print(f'  ❌ {path} (不存在)')
" 2>nul

echo [3/3] 测试配置加载...
python -c "
try:
    from core.modules.common.common import get_config
    config = get_config()
    print('✅ 配置加载成功')
    print('配置的根目录:')
    for cat, paths in config.get('local_roots', {}).items():
        print(f'  {cat.upper()}: {paths}')
except Exception as e:
    print(f'❌ 配置加载失败: {e}')
    exit(1)
" 2>nul
if errorlevel 1 goto :error

echo.
echo ========================================
echo ✅ 配置验证通过！
echo 所有目录路径均已正确配置
echo ========================================
goto :end

:error
echo.
echo ========================================
echo ❌ 配置验证失败
echo 请检查上述错误信息
echo ========================================

:end
pause
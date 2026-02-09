@echo off
chcp 65001 >nul
echo ========================================
echo 配置文件同步工具
echo ========================================
echo.

echo [1/4] 同步local_dirs.json到config.yaml...
python -c "
import json
import yaml
import os

# 读取local_dirs.json
if os.path.exists('local_dirs.json'):
    with open('local_dirs.json', 'r', encoding='utf-8') as f:
        local_dirs = json.load(f)
    
    # 读取config.yaml
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config_text = f.read()
            config_text = config_text.replace('\\\\', '\\\\\\\\')
            config = yaml.safe_load(config_text)
    else:
        config = {}
    
    # 同步目录配置
    if 'local_roots' not in config:
        config['local_roots'] = {}
    
    # 将local_dirs.json的配置转换为config.yaml格式
    for category, dirs in local_dirs.items():
        if isinstance(dirs, list) and dirs:
            config['local_roots'][category] = dirs
        elif isinstance(dirs, str) and dirs:
            config['local_roots'][category] = [dirs]
    
    # 写回config.yaml
    with open('config.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
    
    print('✅ 同步完成')
else:
    print('❌ local_dirs.json不存在')
" 2>nul

echo [2/4] 验证config.yaml配置...
python -c "
import yaml
import os

if os.path.exists('config.yaml'):
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config_text = f.read()
        config_text = config_text.replace('\\\\', '\\\\\\\\')
        config = yaml.safe_load(config_text)
    
    local_roots = config.get('local_roots', {})
    print('config.yaml中的目录配置:')
    for category, dirs in local_roots.items():
        print(f'  {category.upper()}: {dirs}')
else:
    print('❌ config.yaml不存在')
" 2>nul

echo [3/4] 验证local_dirs.json配置...
python -c "
import json
import os

if os.path.exists('local_dirs.json'):
    with open('local_dirs.json', 'r', encoding='utf-8') as f:
        local_dirs = json.load(f)
    
    print('local_dirs.json中的目录配置:')
    for category, dirs in local_dirs.items():
        if isinstance(dirs, list):
            print(f'  {category.upper()}: {dirs}')
        else:
            print(f'  {category.upper()}: [{dirs}]')
else:
    print('❌ local_dirs.json不存在')
" 2>nul

echo [4/4] 测试配置加载...
python -c "
from core.modules.common.common import get_config
config = get_config()
local_roots = config.get('local_roots', {})
print('程序实际使用的目录配置:')
for category, dirs in local_roots.items():
    print(f'  {category.upper()}: {dirs}')
" 2>nul

echo.
echo ========================================
echo 配置同步完成！
echo ========================================
pause
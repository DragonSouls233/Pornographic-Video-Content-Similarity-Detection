from core.modules.common.model_database import ModelDatabase

# 连接数据库
db = ModelDatabase('models.db')
models = db.get_all_models()

print('数据库中的模特:')
for model in models:
    print(f'{model["name"]}: {model["url"]}')

# 检查是否有"测试模特1"
test_model = db.get_model("测试模特1")
if test_model:
    print(f'\n找到测试模特1: {test_model}')
else:
    print('\n未找到测试模特1')
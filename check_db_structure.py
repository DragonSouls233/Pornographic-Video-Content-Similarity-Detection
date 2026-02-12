import sqlite3

# 连接数据库
conn = sqlite3.connect('models.db')
cursor = conn.cursor()

# 查看所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('数据库表:', [table[0] for table in tables])

# 查看models表结构
cursor.execute("PRAGMA table_info(models)")
columns = cursor.fetchall()
print('\nmodels表结构:')
for col in columns:
    print(f'  {col[1]} ({col[2]})')

# 查看统计数据表结构
cursor.execute("PRAGMA table_info(model_stats)")
stats_columns = cursor.fetchall()
print('\nmodel_stats表结构:')
for col in stats_columns:
    print(f'  {col[1]} ({col[2]})')

conn.close()
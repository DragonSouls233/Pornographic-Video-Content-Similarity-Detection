#!/usr/bin/env python3
"""
命名规范检查脚本
检查代码库中的命名是否符合规范
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

class NamingChecker:
    """命名规范检查器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.violations = []
        
    def check_naming_conventions(self) -> List[Dict]:
        """检查命名规范"""
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            if 'venv' in str(file_path) or '__pycache__' in str(file_path):
                continue
                
            try:
                self._check_file(file_path)
            except Exception as e:
                print(f"检查文件时出错 {file_path}: {e}")
        
        return self.violations
    
    def _check_file(self, file_path: Path):
        """检查单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            visitor = NamingVisitor(file_path)
            visitor.visit(tree)
            
            self.violations.extend(visitor.violations)
            
        except SyntaxError as e:
            self.violations.append({
                'file': str(file_path),
                'line': e.lineno,
                'type': 'syntax_error',
                'message': f'语法错误: {e.msg}'
            })
    
    def print_report(self):
        """打印检查报告"""
        if not self.violations:
            print("[OK] 所有命名都符合规范！")
            return

        print("=" * 80)
        print("[报告] 命名规范检查报告")
        print("=" * 80)

        # 按文件分组
        violations_by_file = {}
        for violation in self.violations:
            file_path = violation['file']
            if file_path not in violations_by_file:
                violations_by_file[file_path] = []
            violations_by_file[file_path].append(violation)

        # 打印每个文件的违规情况
        for file_path, file_violations in violations_by_file.items():
            print(f"\n[文件] {file_path}")
            print("-" * 60)

            for violation in file_violations:
                line_info = f"行 {violation['line']}" if violation['line'] else ""
                print(f"  {line_info:>8} {violation['type']:<20} {violation['message']}")

        print("\n" + "=" * 80)
        print(f"总计发现 {len(self.violations)} 个命名规范问题")


class NamingVisitor(ast.NodeVisitor):
    """AST访问器，用于检查命名规范"""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.violations = []
        self.current_class = None
        
    def visit_FunctionDef(self, node):
        """检查函数命名"""
        # 跳过特殊方法（以双下划线开头结尾）
        if node.name.startswith('__') and node.name.endswith('__'):
            self.generic_visit(node)
            return
        
        # 跳过私有方法（以单下划线开头）
        if node.name.startswith('_'):
            self.generic_visit(node)
            return
        
        # 检查公共方法
        if not self._is_snake_case(node.name):
            self._add_violation(node, 'function_name', 
                              f"函数名 '{node.name}' 应使用 snake_case 格式")
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """检查类命名"""
        if not self._is_pascal_case(node.name):
            self._add_violation(node, 'class_name', 
                              f"类名 '{node.name}' 应使用 PascalCase 格式")
        
        # 记录当前类，用于检查类内变量
        old_class = self.current_class
        self.current_class = node
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_Name(self, node):
        """检查变量命名"""
        # 只检查赋值语句中的变量名
        if isinstance(node.ctx, ast.Store):
            # 跳过私有变量（以单下划线开头）
            if node.id.startswith('_'):
                self.generic_visit(node)
                return
            
            # 检查是否在Enum类中
            if self.current_class and self._is_enum_class(self.current_class):
                # Enum值应该使用 UPPER_SNAKE_CASE
                if not self._is_upper_snake_case(node.id):
                    self._add_violation(node, 'enum_value', 
                                      f"枚举值 '{node.id}' 应使用 UPPER_SNAKE_CASE 格式")
            elif node.id.isupper() and '_' in node.id:
                # 常量应该使用 UPPER_SNAKE_CASE
                if not self._is_upper_snake_case(node.id):
                    self._add_violation(node, 'constant_name', 
                                      f"常量名 '{node.id}' 应使用 UPPER_SNAKE_CASE 格式")
            else:
                if not self._is_snake_case(node.id):
                    self._add_violation(node, 'variable_name', 
                                      f"变量名 '{node.id}' 应使用 snake_case 格式")
        self.generic_visit(node)
    
    def _is_enum_class(self, class_node):
        """判断是否为枚举类"""
        # 检查基类是否包含Enum
        for base in class_node.bases:
            if isinstance(base, ast.Name) and 'Enum' in base.id:
                return True
            elif isinstance(base, ast.Attribute) and 'Enum' in base.attr:
                return True
        return False
    
    def _is_snake_case(self, name: str) -> bool:
        """检查是否为 snake_case"""
        if not name:
            return False
        # 允许数字，但不能以数字开头
        if name[0].isdigit():
            return False
        # 检查是否只包含小写字母、数字和下划线
        return bool(re.match(r'^[a-z][a-z0-9_]*$', name))
    
    def _is_pascal_case(self, name: str) -> bool:
        """检查是否为 PascalCase"""
        if not name:
            return False
        # 不能以下划线开头
        if name.startswith('_'):
            return False
        # 检查是否每个单词首字母大写
        return bool(re.match(r'^[A-Z][a-zA-Z0-9]*$', name))
    
    def _is_upper_snake_case(self, name: str) -> bool:
        """检查是否为 UPPER_SNAKE_CASE"""
        if not name:
            return False
        # 检查是否只包含大写字母、数字和下划线
        return bool(re.match(r'^[A-Z][A-Z0-9_]*$', name))
    
    def _add_violation(self, node, violation_type: str, message: str):
        """添加违规记录"""
        self.violations.append({
            'file': str(self.file_path),
            'line': getattr(node, 'lineno', None),
            'type': violation_type,
            'message': message
        })


def main():
    """主函数"""
    project_root = Path(__file__).parent.parent
    print(f"[检查] 项目命名规范: {project_root}")
    
    checker = NamingChecker(str(project_root))
    violations = checker.check_naming_conventions()
    checker.print_report()
    
    # 返回违规数量（用于CI/CD）
    return len(violations)


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
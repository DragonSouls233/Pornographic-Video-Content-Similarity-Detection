"""
批量导入导出模块
支持Excel/CSV格式的模特数据批量处理
"""

import os
import json
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import logging
from typing import Dict, List, Tuple, Any
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

class BatchModelProcessor:
    """批量模特数据处理器"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.supported_formats = {
            'excel': ['.xlsx', '.xls'],
            'csv': ['.csv'],
            'json': ['.json']
        }
        
        # 数据校验规则
        self.validation_rules = {
            'name': {
                'required': True,
                'max_length': 100,
                'pattern': r'^[a-zA-Z0-9\u4e00-\u9fa5\s\-_\.\(\)]+$',
                'error_msg': '模特名称只能包含中英文、数字、空格、横线、下划线、点号和括号'
            },
            'url': {
                'required': True,
                'max_length': 500,
                'pattern': r'^https?://[^\s/$.?#].[^\s]*$',
                'error_msg': 'URL格式不正确，必须以http://或https://开头'
            },
            'module': {
                'required': True,
                'allowed_values': ['PORN', 'JAVDB'],
                'error_msg': '模块类型必须是PORN或JAVDB'
            }
        }
    
    def validate_model_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证模特数据格式
        
        Args:
            data: 模特数据字典
            
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        for field, rule in self.validation_rules.items():
            value = data.get(field, '').strip() if isinstance(data.get(field), str) else data.get(field)
            
            # 检查必填字段
            if rule['required'] and not value:
                errors.append(f"{field} 是必填字段")
                continue
            
            # 如果值为空且非必填，跳过后续检查
            if not value:
                continue
            
            # 检查最大长度
            if 'max_length' in rule and len(str(value)) > rule['max_length']:
                errors.append(f"{field} 长度不能超过 {rule['max_length']} 个字符")
                continue
            
            # 检查正则表达式
            if 'pattern' in rule and not re.match(rule['pattern'], str(value)):
                errors.append(f"{field}: {rule['error_msg']}")
                continue
            
            # 检查允许值
            if 'allowed_values' in rule and value not in rule['allowed_values']:
                errors.append(f"{field}: {rule['error_msg']}")
                continue
        
        return len(errors) == 0, errors
    
    def auto_detect_module(self, url: str) -> str:
        """
        根据URL自动检测模块类型
        
        Args:
            url: 模特URL
            
        Returns:
            模块类型 (PORN/JAVDB)
        """
        url_lower = url.lower()
        if 'javdb' in url_lower:
            return 'JAVDB'
        else:
            return 'PORN'
    
    def import_from_excel(self, file_path: str, sheet_name: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        从Excel文件导入模特数据
        
        Args:
            file_path: Excel文件路径
            sheet_name: 工作表名称（可选）
            
        Returns:
            (是否成功, 结果字典)
        """
        try:
            # 读取Excel文件
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                df = pd.read_excel(file_path)
            
            return self._process_dataframe(df, "Excel")
            
        except Exception as e:
            self.logger.error(f"读取Excel文件失败: {e}")
            return False, {"error": f"读取Excel文件失败: {e}"}
    
    def import_from_csv(self, file_path: str, encoding: str = 'utf-8') -> Tuple[bool, Dict[str, Any]]:
        """
        从CSV文件导入模特数据
        
        Args:
            file_path: CSV文件路径
            encoding: 文件编码
            
        Returns:
            (是否成功, 结果字典)
        """
        try:
            # 尝试不同编码
            encodings = [encoding, 'utf-8', 'gbk', 'gb2312']
            df = None
            
            for enc in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                return False, {"error": "无法解码CSV文件，请尝试使用UTF-8或GBK编码"}
            
            return self._process_dataframe(df, "CSV")
            
        except Exception as e:
            self.logger.error(f"读取CSV文件失败: {e}")
            return False, {"error": f"读取CSV文件失败: {e}"}
    
    def _process_dataframe(self, df: pd.DataFrame, source_type: str) -> Tuple[bool, Dict[str, Any]]:
        """
        处理DataFrame数据
        
        Args:
            df: pandas DataFrame
            source_type: 数据源类型
            
        Returns:
            (是否成功, 结果字典)
        """
        try:
            # 标准化列名
            df.columns = df.columns.str.strip().str.lower()
            
            # 检查必要的列
            required_columns = ['name', 'url']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return False, {
                    "error": f"缺少必要的列: {', '.join(missing_columns)}",
                    "available_columns": list(df.columns)
                }
            
            # 数据处理结果
            result = {
                'total': len(df),
                'valid': 0,
                'invalid': 0,
                'duplicates': 0,
                'valid_models': {},
                'errors': []
            }
            
            # 处理每一行数据
            processed_names = set()
            
            for index, row in df.iterrows():
                try:
                    # 提取数据
                    name = str(row['name']).strip()
                    url = str(row['url']).strip()
                    
                    # 检查空值
                    if not name or name.lower() in ['nan', 'none', '']:
                        result['errors'].append(f"第{index+1}行: 模特名称为空")
                        result['invalid'] += 1
                        continue
                    
                    if not url or url.lower() in ['nan', 'none', '']:
                        result['errors'].append(f"第{index+1}行: URL为空")
                        result['invalid'] += 1
                        continue
                    
                    # 检查重复
                    if name in processed_names:
                        result['duplicates'] += 1
                        result['errors'].append(f"第{index+1}行: 模特名称重复 - {name}")
                        continue
                    
                    # 自动检测模块类型
                    module = self.auto_detect_module(url)
                    
                    # 如果有module列且不为空，使用指定值
                    if 'module' in df.columns and pd.notna(row['module']):
                        provided_module = str(row['module']).strip().upper()
                        if provided_module in ['PORN', 'JAVDB']:
                            module = provided_module
                    
                    # 构建数据
                    model_data = {
                        'name': name,
                        'url': url,
                        'module': module
                    }
                    
                    # 验证数据
                    is_valid, errors = self.validate_model_data(model_data)
                    
                    if is_valid:
                        result['valid_models'][name] = {
                            'module': module,
                            'url': url
                        }
                        result['valid'] += 1
                        processed_names.add(name)
                    else:
                        error_msg = f"第{index+1}行 ({name}): " + "; ".join(errors)
                        result['errors'].append(error_msg)
                        result['invalid'] += 1
                
                except Exception as e:
                    result['errors'].append(f"第{index+1}行: 处理失败 - {e}")
                    result['invalid'] += 1
            
            return True, result
            
        except Exception as e:
            self.logger.error(f"处理{source_type}数据失败: {e}")
            return False, {"error": f"处理{source_type}数据失败: {e}"}
    
    def export_to_excel(self, models: Dict[str, Any], file_path: str, 
                       include_stats: bool = False) -> Tuple[bool, str]:
        """
        导出模特数据到Excel文件
        
        Args:
            models: 模特数据字典
            file_path: 导出文件路径
            include_stats: 是否包含统计信息
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            # 准备数据
            data = []
            for name, info in models.items():
                if isinstance(info, dict):
                    row = {
                        '模特名称': name,
                        '模块类型': info.get('module', ''),
                        'URL链接': info.get('url', '')
                    }
                    
                    if include_stats:
                        # 添加统计信息（如果有）
                        row.update({
                            '本地视频数': info.get('local_video_count', 0),
                            '在线视频数': info.get('online_video_count', 0),
                            '缺失视频数': info.get('missing_video_count', 0),
                            '最后同步': info.get('last_sync', '')
                        })
                    
                    data.append(row)
                else:
                    # 兼容旧格式
                    row = {
                        '模特名称': name,
                        '模块类型': 'JAVDB' if 'javdb' in str(info).lower() else 'PORN',
                        'URL链接': info
                    }
                    
                    if include_stats:
                        row.update({
                            '本地视频数': 0,
                            '在线视频数': 0,
                            '缺失视频数': 0,
                            '最后同步': ''
                        })
                    
                    data.append(row)
            
            # 创建DataFrame
            df = pd.DataFrame(data)
            
            # 导出到Excel
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='模特数据', index=False)
                
                # 如果需要，添加统计工作表
                if include_stats:
                    stats_data = {
                        '统计项': ['总模特数', 'PORN模块', 'JAVDB模块'],
                        '数量': [
                            len(data),
                            len([d for d in data if d['模块类型'] == 'PORN']),
                            len([d for d in data if d['模块类型'] == 'JAVDB'])
                        ]
                    }
                    stats_df = pd.DataFrame(stats_data)
                    stats_df.to_excel(writer, sheet_name='统计信息', index=False)
            
            return True, ""
            
        except Exception as e:
            self.logger.error(f"导出到Excel失败: {e}")
            return False, f"导出到Excel失败: {e}"
    
    def export_to_csv(self, models: Dict[str, Any], file_path: str, 
                    encoding: str = 'utf-8-sig') -> Tuple[bool, str]:
        """
        导出模特数据到CSV文件
        
        Args:
            models: 模特数据字典
            file_path: 导出文件路径
            encoding: 文件编码
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            # 准备数据
            data = []
            for name, info in models.items():
                if isinstance(info, dict):
                    row = {
                        '模特名称': name,
                        '模块类型': info.get('module', ''),
                        'URL链接': info.get('url', '')
                    }
                else:
                    # 兼容旧格式
                    row = {
                        '模特名称': name,
                        '模块类型': 'JAVDB' if 'javdb' in str(info).lower() else 'PORN',
                        'URL链接': info
                    }
                
                data.append(row)
            
            # 创建DataFrame
            df = pd.DataFrame(data)
            
            # 导出到CSV
            df.to_csv(file_path, index=False, encoding=encoding)
            
            return True, ""
            
        except Exception as e:
            self.logger.error(f"导出到CSV失败: {e}")
            return False, f"导出到CSV失败: {e}"
    
    def batch_import_large_dataset(self, file_path: str, chunk_size: int = 1000) -> Tuple[bool, Dict[str, Any]]:
        """
        批量导入大数据集（分块处理）
        
        Args:
            file_path: 文件路径
            chunk_size: 分块大小
            
        Returns:
            (是否成功, 结果字典)
        """
        try:
            # 确定文件类型
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            start_time = time.time()
            total_result = {
                'total_processed': 0,
                'total_valid': 0,
                'total_invalid': 0,
                'total_duplicates': 0,
                'all_valid_models': {},
                'all_errors': [],
                'processing_time': 0
            }
            
            if ext in ['.xlsx', '.xls']:
                # Excel分块处理
                for chunk_df in pd.read_excel(file_path, chunksize=chunk_size):
                    success, chunk_result = self._process_dataframe(chunk_df, "Excel")
                    if success:
                        self._merge_chunk_result(total_result, chunk_result)
                    else:
                        return False, chunk_result
                        
            elif ext == '.csv':
                # CSV分块处理
                for chunk_df in pd.read_csv(file_path, chunksize=chunk_size, encoding='utf-8'):
                    success, chunk_result = self._process_dataframe(chunk_df, "CSV")
                    if success:
                        self._merge_chunk_result(total_result, chunk_result)
                    else:
                        return False, chunk_result
            else:
                return False, {"error": "不支持的文件格式"}
            
            total_result['processing_time'] = time.time() - start_time
            return True, total_result
            
        except Exception as e:
            self.logger.error(f"批量导入失败: {e}")
            return False, {"error": f"批量导入失败: {e}"}
    
    def _merge_chunk_result(self, total_result: Dict, chunk_result: Dict):
        """合并分块处理结果"""
        total_result['total_processed'] += chunk_result['total']
        total_result['total_valid'] += chunk_result['valid']
        total_result['total_invalid'] += chunk_result['invalid']
        total_result['total_duplicates'] += chunk_result['duplicates']
        total_result['all_valid_models'].update(chunk_result['valid_models'])
        total_result['all_errors'].extend(chunk_result['errors'])
    
    def get_import_template(self, format_type: str = 'excel') -> pd.DataFrame:
        """
        获取导入模板
        
        Args:
            format_type: 格式类型 ('excel' 或 'csv')
            
        Returns:
            模板DataFrame
        """
        template_data = [
            {
                'name': '示例模特1',
                'url': 'https://www.example.com/model1',
                'module': 'PORN'
            },
            {
                'name': '示例模特2',
                'url': 'https://javdb.com/model2',
                'module': 'JAVDB'
            },
            {
                'name': '示例模特3',
                'url': 'https://www.example.com/model3',
                'module': ''  # 留空将自动检测
            }
        ]
        
        df = pd.DataFrame(template_data)
        
        if format_type == 'excel':
            # 添加说明
            description = pd.DataFrame([
                {'name': '说明', 'url': '请填写实际的模特URL', 'module': 'PORN或JAVDB，留空自动检测'}
            ])
            return pd.concat([description, df], ignore_index=True)
        
        return df


class BatchImportDialog:
    """批量导入对话框"""
    
    def __init__(self, parent, models_dict: dict, logger=None):
        self.parent = parent
        self.models_dict = models_dict
        self.logger = logger or logging.getLogger(__name__)
        self.processor = BatchModelProcessor(logger)
        self.result = None
        
    def show_dialog(self) -> Dict[str, Any]:
        """显示导入对话框"""
        from tkinter import ttk
        
        dialog = tk.Toplevel(self.parent)
        dialog.title("批量导入模特")
        dialog.geometry("600x400")
        dialog.resizable(True, True)
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(dialog, text="选择文件", padding=10)
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(file_frame, text="文件路径:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=file_path_var, width=50).grid(row=0, column=1, sticky=tk.EW, padx=5)
        
        def browse_file():
            file_path = filedialog.askopenfilename(
                title="选择导入文件",
                filetypes=[
                    ("Excel文件", "*.xlsx *.xls"),
                    ("CSV文件", "*.csv"),
                    ("所有支持文件", "*.xlsx *.xls *.csv")
                ]
            )
            if file_path:
                file_path_var.set(file_path)
        
        ttk.Button(file_frame, text="浏览", command=browse_file).grid(row=0, column=2, padx=5)
        
        # 选项区域
        options_frame = ttk.LabelFrame(dialog, text="导入选项", padding=10)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 编码选择（仅CSV）
        ttk.Label(options_frame, text="编码格式:").grid(row=0, column=0, sticky=tk.W, pady=5)
        encoding_var = tk.StringVar(value="utf-8")
        encoding_combo = ttk.Combobox(options_frame, textvariable=encoding_var, 
                                     values=["utf-8", "gbk", "gb2312"], width=15)
        encoding_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 处理选项
        merge_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="合并到现有数据", variable=merge_var).grid(
            row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        skip_duplicates_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="跳过重复模特", variable=skip_duplicates_var).grid(
            row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 进度显示区域
        progress_frame = ttk.LabelFrame(dialog, text="导入进度", padding=10)
        progress_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        progress_text = tk.Text(progress_frame, height=10, wrap=tk.WORD)
        progress_text.pack(fill=tk.BOTH, expand=True)
        
        progress_scrollbar = ttk.Scrollbar(progress_frame, orient=tk.VERTICAL, command=progress_text.yview)
        progress_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        progress_text.config(yscrollcommand=progress_scrollbar.set)
        
        # 按钮区域
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def start_import():
            file_path = file_path_var.get().strip()
            if not file_path:
                messagebox.showwarning("提示", "请选择要导入的文件")
                return
            
            if not os.path.exists(file_path):
                messagebox.showerror("错误", "文件不存在")
                return
            
            # 清空进度显示
            progress_text.delete(1.0, tk.END)
            progress_text.insert(tk.END, "开始导入...\n\n")
            dialog.update()
            
            try:
                # 确定文件类型
                _, ext = os.path.splitext(file_path)
                ext = ext.lower()
                
                # 执行导入
                if ext in ['.xlsx', '.xls']:
                    success, result = self.processor.import_from_excel(file_path)
                elif ext == '.csv':
                    encoding = encoding_var.get()
                    success, result = self.processor.import_from_csv(file_path, encoding)
                else:
                    messagebox.showerror("错误", "不支持的文件格式")
                    return
                
                if success:
                    # 显示导入结果
                    total = result['total']
                    valid = result['valid']
                    invalid = result['invalid']
                    duplicates = result['duplicates']
                    
                    progress_text.insert(tk.END, f"导入完成！\n")
                    progress_text.insert(tk.END, f"总记录数: {total}\n")
                    progress_text.insert(tk.END, f"有效记录: {valid}\n")
                    progress_text.insert(tk.END, f"无效记录: {invalid}\n")
                    progress_text.insert(tk.END, f"重复记录: {duplicates}\n\n")
                    
                    if result['errors']:
                        progress_text.insert(tk.END, "错误详情:\n")
                        for error in result['errors'][:20]:  # 只显示前20个错误
                            progress_text.insert(tk.END, f"• {error}\n")
                        if len(result['errors']) > 20:
                            progress_text.insert(tk.END, f"... 还有 {len(result['errors']) - 20} 个错误\n")
                    
                    # 处理有效数据
                    if valid > 0:
                        valid_models = result['valid_models']
                        
                        # 检查重复
                        if merge_var.get():
                            existing_names = set(self.models_dict.keys())
                            duplicates = set(valid_models.keys()) & existing_names
                            
                            if skip_duplicates_var.get() and duplicates:
                                # 跳过重复
                                for dup_name in duplicates:
                                    valid_models.pop(dup_name, None)
                                progress_text.insert(tk.END, f"\n跳过了 {len(duplicates)} 个重复模特\n")
                            elif duplicates:
                                # 覆盖重复
                                progress_text.insert(tk.END, f"\n覆盖了 {len(duplicates)} 个重复模特\n")
                        
                        # 更新数据
                        self.models_dict.update(valid_models)
                        
                        progress_text.insert(tk.END, f"\n成功导入 {len(valid_models)} 个新模特！\n")
                        
                        # 保存结果
                        self.result = {
                            'success': True,
                            'imported_count': len(valid_models),
                            'total_processed': total,
                            'valid_count': valid,
                            'invalid_count': invalid,
                            'duplicate_count': duplicates
                        }
                    else:
                        progress_text.insert(tk.END, "\n没有有效数据可导入\n")
                        self.result = {'success': False, 'error': '没有有效数据'}
                else:
                    progress_text.insert(tk.END, f"导入失败: {result.get('error', '未知错误')}\n")
                    self.result = {'success': False, 'error': result.get('error', '未知错误')}
                
                progress_text.see(tk.END)
                
            except Exception as e:
                progress_text.insert(tk.END, f"导入过程中发生错误: {e}\n")
                self.result = {'success': False, 'error': str(e)}
        
        def download_template():
            """下载模板"""
            try:
                template_path = filedialog.asksaveasfilename(
                    title="保存模板",
                    defaultextension=".xlsx",
                    filetypes=[("Excel文件", "*.xlsx"), ("CSV文件", "*.csv")]
                )
                
                if template_path:
                    _, ext = os.path.splitext(template_path)
                    template_df = self.processor.get_import_template('excel' if ext in ['.xlsx', '.xls'] else 'csv')
                    
                    if ext in ['.xlsx', '.xls']:
                        template_df.to_excel(template_path, index=False)
                    else:
                        template_df.to_csv(template_path, index=False, encoding='utf-8-sig')
                    
                    messagebox.showinfo("成功", f"模板已保存到: {template_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存模板失败: {e}")
        
        ttk.Button(button_frame, text="下载模板", command=download_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="开始导入", command=start_import).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        file_frame.columnconfigure(1, weight=1)
        
        # 模态对话框
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.wait_window()
        
        return self.result


class BatchExportDialog:
    """批量导出对话框"""
    
    def __init__(self, parent, models_dict: dict, logger=None):
        self.parent = parent
        self.models_dict = models_dict
        self.logger = logger or logging.getLogger(__name__)
        self.processor = BatchModelProcessor(logger)
        
    def show_dialog(self) -> Dict[str, Any]:
        """显示导出对话框"""
        from tkinter import ttk
        
        dialog = tk.Toplevel(self.parent)
        dialog.title("批量导出模特")
        dialog.geometry("500x350")
        dialog.resizable(False, False)
        
        # 统计信息
        stats_frame = ttk.LabelFrame(dialog, text="数据统计", padding=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        total_count = len(self.models_dict)
        porn_count = len([name for name, info in self.models_dict.items() 
                         if isinstance(info, dict) and info.get('module') == 'PORN'])
        javdb_count = len([name for name, info in self.models_dict.items() 
                          if isinstance(info, dict) and info.get('module') == 'JAVDB'])
        
        ttk.Label(stats_frame, text=f"总模特数: {total_count}").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(stats_frame, text=f"PORN模块: {porn_count}").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(stats_frame, text=f"JAVDB模块: {javdb_count}").grid(row=2, column=0, sticky=tk.W, pady=2)
        
        # 导出选项
        options_frame = ttk.LabelFrame(dialog, text="导出选项", padding=10)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(options_frame, text="文件格式:").grid(row=0, column=0, sticky=tk.W, pady=5)
        format_var = tk.StringVar(value="Excel")
        format_combo = ttk.Combobox(options_frame, textvariable=format_var, 
                                   values=["Excel", "CSV", "JSON"], width=20, state="readonly")
        format_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        include_stats_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="包含统计信息", 
                       variable=include_stats_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 结果变量
        export_result = {'success': False, 'path': '', 'count': 0}
        
        def start_export():
            try:
                format_type = format_var.get().lower()
                include_stats = include_stats_var.get()
                
                if format_type == "excel":
                    file_path = filedialog.asksaveasfilename(
                        title="导出为Excel",
                        defaultextension=".xlsx",
                        filetypes=[("Excel文件", "*.xlsx")]
                    )
                    
                    if file_path:
                        success, error = self.processor.export_to_excel(
                            self.models_dict, file_path, include_stats
                        )
                        
                        if success:
                            export_result.update({'success': True, 'path': file_path, 'count': total_count})
                            messagebox.showinfo("成功", f"已导出 {total_count} 个模特到:\n{file_path}")
                            dialog.destroy()
                        else:
                            messagebox.showerror("错误", f"导出失败: {error}")
                
                elif format_type == "csv":
                    file_path = filedialog.asksaveasfilename(
                        title="导出为CSV",
                        defaultextension=".csv",
                        filetypes=[("CSV文件", "*.csv")]
                    )
                    
                    if file_path:
                        success, error = self.processor.export_to_csv(
                            self.models_dict, file_path
                        )
                        
                        if success:
                            export_result.update({'success': True, 'path': file_path, 'count': total_count})
                            messagebox.showinfo("成功", f"已导出 {total_count} 个模特到:\n{file_path}")
                            dialog.destroy()
                        else:
                            messagebox.showerror("错误", f"导出失败: {error}")
                
                elif format_type == "json":
                    file_path = filedialog.asksaveasfilename(
                        title="导出为JSON",
                        defaultextension=".json",
                        filetypes=[("JSON文件", "*.json")]
                    )
                    
                    if file_path:
                        import json
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(self.models_dict, f, ensure_ascii=False, indent=2)
                        
                        export_result.update({'success': True, 'path': file_path, 'count': total_count})
                        messagebox.showinfo("成功", f"已导出 {total_count} 个模特到:\n{file_path}")
                        dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("错误", f"导出过程中发生错误: {e}")
        
        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="开始导出", command=start_export).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # 模态对话框
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.wait_window()
        
        return export_result
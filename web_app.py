from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, make_response
import os
import json
import glob
from datetime import datetime
from drone_communication_analyzer import DroneCommAnalyzer
from visualization import DroneCommVisualizer, create_summary_dashboard
import plotly
import plotly.utils
import io
import zipfile
import tempfile
import pandas as pd
import shutil
from werkzeug.utils import secure_filename
import math

# 设置环境变量（用于生产部署）
os.environ.setdefault('FLASK_ENV', 'production')

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 全局变量存储当前分析器和可视化器
current_analyzer = None
current_visualizer = None
available_datasets = []

# 添加缓存控制装饰器
def add_cache_control(response):
    """添加缓存控制头"""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
    response.headers['ETag'] = str(hash(datetime.now().isoformat()))
    return response

@app.after_request
def after_request(response):
    """为所有响应添加缓存控制"""
    return add_cache_control(response)

def scan_available_datasets():
    """扫描可用的数据集"""
    global available_datasets
    available_datasets = []
    
    # 首先检查根目录下的数据集文件夹
    for item in os.listdir('.'):
        item_path = os.path.join('.', item)
        if os.path.isdir(item_path) and item not in ['data', 'uploads', 'templates', 'static', '__pycache__', '.git']:
            sender_path = os.path.join(item_path, 'sender')
            receiver_path = os.path.join(item_path, 'receiver')
            if os.path.exists(sender_path) and os.path.exists(receiver_path):
                # 检查是否包含必要的数据文件
                has_udp = (bool(glob.glob(os.path.join(sender_path, 'udp_sender_*.csv'))) and 
                          bool(glob.glob(os.path.join(receiver_path, 'udp_receiver_*.csv'))))
                has_nexfi = (bool(glob.glob(os.path.join(sender_path, 'nexfi_status_*.csv'))) or
                           bool(glob.glob(os.path.join(receiver_path, 'nexfi_status_*.csv'))))
                has_gps = (bool(glob.glob(os.path.join(sender_path, 'gps_logger_*.csv'))) or
                          bool(glob.glob(os.path.join(receiver_path, 'gps_logger_*.csv'))))
                
                dataset_info = {
                    'name': item,
                    'path': item_path,
                    'has_udp': has_udp,
                    'has_nexfi': has_nexfi,
                    'has_gps': has_gps,
                    'creation_time': datetime.fromtimestamp(os.path.getctime(item_path)).strftime('%Y-%m-%d %H:%M:%S'),
                    'source': 'local'
                }
                available_datasets.append(dataset_info)
    
    # 然后检查data目录下的数据集
    data_dir = 'data'
    if os.path.exists(data_dir):
        for item in os.listdir(data_dir):
            item_path = os.path.join(data_dir, item)
            if os.path.isdir(item_path):
                sender_path = os.path.join(item_path, 'sender')
                receiver_path = os.path.join(item_path, 'receiver')
                if os.path.exists(sender_path) and os.path.exists(receiver_path):
                    # 检查是否包含必要的数据文件
                    has_udp = (bool(glob.glob(os.path.join(sender_path, 'udp_sender_*.csv'))) and 
                              bool(glob.glob(os.path.join(receiver_path, 'udp_receiver_*.csv'))))
                    has_nexfi = (bool(glob.glob(os.path.join(sender_path, 'nexfi_status_*.csv'))) or
                               bool(glob.glob(os.path.join(receiver_path, 'nexfi_status_*.csv'))))
                    has_gps = (bool(glob.glob(os.path.join(sender_path, 'gps_logger_*.csv'))) or
                              bool(glob.glob(os.path.join(receiver_path, 'gps_logger_*.csv'))))
                    
                    dataset_info = {
                        'name': item,
                        'path': item_path,
                        'has_udp': has_udp,
                        'has_nexfi': has_nexfi,
                        'has_gps': has_gps,
                        'creation_time': datetime.fromtimestamp(os.path.getctime(item_path)).strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'data'
                    }
                    available_datasets.append(dataset_info)
    
    # 按创建时间排序
    available_datasets.sort(key=lambda x: x['creation_time'], reverse=True)


def validate_dataset_structure(dataset_path):
    """验证数据集结构是否正确"""
    sender_path = os.path.join(dataset_path, 'sender')
    receiver_path = os.path.join(dataset_path, 'receiver')
    
    if not os.path.exists(sender_path) or not os.path.exists(receiver_path):
        return False, "缺少sender或receiver文件夹"
    
    # 检查必要的文件
    required_files = {
        'udp_sender': glob.glob(os.path.join(sender_path, 'udp_sender_*.csv')),
        'udp_receiver': glob.glob(os.path.join(receiver_path, 'udp_receiver_*.csv')),
    }
    
    missing_files = []
    for file_type, files in required_files.items():
        if not files:
            missing_files.append(file_type)
    
    if missing_files:
        return False, f"缺少必要文件: {', '.join(missing_files)}"
    
    return True, "数据集结构正确"


def extract_zip_dataset(zip_path, extract_to):
    """解压ZIP文件并验证数据集结构"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 获取ZIP文件中的所有文件列表
            file_list = zip_ref.namelist()
            
            # 查找数据集根目录
            dataset_folders = set()
            for file_path in file_list:
                parts = file_path.split('/')
                if len(parts) >= 3:  # 至少包含 dataset/sender|receiver/file
                    if parts[1] in ['sender', 'receiver']:
                        dataset_folders.add(parts[0])
            
            if not dataset_folders:
                return None, "ZIP文件中未找到有效的数据集结构"
            
            if len(dataset_folders) > 1:
                return None, "ZIP文件中包含多个数据集，请确保只包含一个数据集"
            
            dataset_name = list(dataset_folders)[0]
            
            # 解压到临时目录
            temp_extract_path = os.path.join(extract_to, 'temp_extract')
            zip_ref.extractall(temp_extract_path)
            
            # 移动数据集到正确位置
            source_dataset_path = os.path.join(temp_extract_path, dataset_name)
            target_dataset_path = os.path.join(extract_to, dataset_name)
            
            if os.path.exists(target_dataset_path):
                # 如果目标已存在，添加时间戳
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                target_dataset_path = os.path.join(extract_to, f"{dataset_name}_{timestamp}")
            
            shutil.move(source_dataset_path, target_dataset_path)
            
            # 清理临时目录
            shutil.rmtree(temp_extract_path)
            
            # 验证数据集结构
            is_valid, message = validate_dataset_structure(target_dataset_path)
            if not is_valid:
                shutil.rmtree(target_dataset_path)
                return None, f"数据集结构验证失败: {message}"
            
            return os.path.basename(target_dataset_path), "数据集上传成功"
            
    except zipfile.BadZipFile:
        return None, "无效的ZIP文件"
    except Exception as e:
        return None, f"解压失败: {str(e)}"


@app.route('/')
def index():
    """主页面，显示可用数据集列表"""
    scan_available_datasets()
    return render_template('index.html', datasets=available_datasets)


@app.route('/upload', methods=['POST'])
def upload_dataset():
    """上传数据集ZIP文件"""
    if 'dataset_file' not in request.files:
        return jsonify({'error': '未选择文件'}), 400
    
    file = request.files['dataset_file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    if not file.filename.lower().endswith('.zip'):
        return jsonify({'error': '只支持ZIP格式文件'}), 400
    
    try:
        # 保存上传的文件
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{filename}"
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(zip_path)
        
        # 解压并验证数据集
        dataset_name, message = extract_zip_dataset(zip_path, 'data')
        
        # 删除上传的ZIP文件
        os.remove(zip_path)
        
        if dataset_name is None:
            return jsonify({'error': message}), 400
        
        # 重新扫描数据集
        scan_available_datasets()
        
        return jsonify({
            'success': True,
            'message': message,
            'dataset_name': dataset_name
        })
        
    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500


@app.route('/analyze/<dataset_name>')
def analyze_dataset(dataset_name):
    """分析指定数据集"""
    global current_analyzer, current_visualizer
    
    # 强制清理旧的分析结果
    current_analyzer = None
    current_visualizer = None
    
    # 查找数据集路径
    dataset_path = None
    for dataset in available_datasets:
        if dataset['name'] == dataset_name:
            dataset_path = dataset['path']
            break
    
    if not dataset_path or not os.path.exists(dataset_path):
        return jsonify({'error': f'数据集 {dataset_name} 不存在'}), 404
    
    try:
        print(f"开始分析数据集: {dataset_name}")
        print(f"数据集路径: {dataset_path}")
        
        # 创建分析器并运行分析
        current_analyzer = DroneCommAnalyzer(dataset_path)
        current_analyzer.run_full_analysis()
        
        print("数据分析完成，开始生成可视化...")
        
        # 创建可视化器并生成图表
        current_visualizer = DroneCommVisualizer(current_analyzer)
        current_visualizer.create_all_plots()
        
        print("可视化生成完成")
        
        # 创建响应并添加缓存控制
        response = make_response(redirect(url_for('dashboard', dataset_name=dataset_name)))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        print(f"分析错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'分析失败: {str(e)}'}), 500


@app.route('/dashboard/<dataset_name>')
def dashboard(dataset_name):
    """显示分析仪表板"""
    # 检查是否需要重新分析
    force_reanalyze = request.args.get('force', 'false').lower() == 'true'
    
    if current_analyzer is None or force_reanalyze:
        print(f"需要重新分析数据集: {dataset_name}")
        return redirect(url_for('analyze_dataset', dataset_name=dataset_name))
    
    # 创建响应并添加缓存控制
    response = make_response(render_template('dashboard.html', dataset_name=dataset_name))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


@app.route('/api/figures')
def get_figures():
    """API端点：获取所有图表的JSON数据"""
    if current_visualizer is None:
        return jsonify({'error': '尚未进行分析'}), 400
    
    try:
        figures_json = {}
        for name, fig in current_visualizer.figures.items():
            figures_json[name] = json.loads(fig.to_json())
        
        print(f"返回图表数据，包含 {len(figures_json)} 个图表")
        return jsonify(figures_json)
        
    except Exception as e:
        print(f"获取图表数据错误: {str(e)}")
        return jsonify({'error': f'获取图表数据失败: {str(e)}'}), 500


@app.route('/api/summary')
def api_summary():
    """返回分析结果摘要"""
    if not current_analyzer or not current_analyzer.analysis_results:
        return jsonify({'error': 'No analysis results available'}), 404
    
    summary = {
        'udp': None,
        'distance': None,
        'gps': {},
        'nexfi': {},
        'correlations': None,
        'time_range': None  # 添加时间范围信息
    }
    
    # UDP统计
    if 'udp' in current_analyzer.analysis_results:
        udp_stats = current_analyzer.analysis_results['udp']
        summary['udp'] = {
            'total_sent': udp_stats['total_sent'],
            'total_received': udp_stats['total_received'],
            'packet_loss_rate': f"{udp_stats['packet_loss_rate']:.2f}",
            'avg_delay': f"{udp_stats['delay_stats']['mean']:.2f}",
            'max_delay': f"{udp_stats['delay_stats']['max']:.2f}",
            'throughput': f"{udp_stats['throughput_kbps']:.2f}",
            'test_duration': f"{udp_stats['test_duration']:.1f}"
        }
    
    # 距离统计
    if 'inter_drone_distance' in current_analyzer.analysis_results:
        dist_stats = current_analyzer.analysis_results['inter_drone_distance']
        summary['distance'] = {
            'min_distance_3d': f"{dist_stats['min_distance_3d']:.2f}",
            'max_distance_3d': f"{dist_stats['max_distance_3d']:.2f}",
            'mean_distance_3d': f"{dist_stats['mean_distance_3d']:.2f}",
            'std_distance_3d': f"{dist_stats['std_distance_3d']:.2f}",
            'mean_distance_horizontal': f"{dist_stats['mean_distance_horizontal']:.2f}",
            'mean_distance_vertical': f"{dist_stats['mean_distance_vertical']:.2f}"
        }
    
    # GPS统计
    if 'gps' in current_analyzer.analysis_results:
        for role, stats in current_analyzer.analysis_results['gps'].items():
            summary['gps'][role] = {
                'data_points': stats['data_points'],
                'total_distance': f"{stats['total_distance']:.2f}",
                'altitude_change': f"{stats['altitude_change']:.2f}",
                'max_speed': f"{stats['max_speed']:.2f}",
                'flight_time': f"{stats['flight_time']:.1f}"
            }
    
    # NEXFI统计
    if 'nexfi' in current_analyzer.analysis_results:
        for role, stats in current_analyzer.analysis_results['nexfi'].items():
            summary['nexfi'][role] = {
                'avg_rssi': f"{stats['rssi']['mean']:.2f}",
                'avg_snr': f"{stats['snr']['mean']:.2f}",
                'avg_throughput': f"{stats['throughput']['mean']:.2f}",
                'avg_link_quality': f"{stats['link_quality']['mean']:.2f}"
            }
    
    # 相关性分析
    if 'correlations' in current_analyzer.analysis_results:
        summary['correlations'] = {}
        for key, corr in current_analyzer.analysis_results['correlations'].items():
            summary['correlations'][key] = {
                'correlation': f"{corr['correlation']:.3f}",
                'p_value': f"{corr['p_value']:.3f}",
                'significant': bool(corr['significant']),
                'data_points': corr['data_points']
            }
    
    # 时间范围信息
    time_ranges = {}
    
    # UDP时间范围
    if 'udp' in current_analyzer.sender_data and not current_analyzer.sender_data['udp'].empty:
        sender_udp = current_analyzer.sender_data['udp']
        time_ranges['udp_sender'] = {
            'start': sender_udp['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S'),
            'end': sender_udp['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    if 'udp' in current_analyzer.receiver_data and not current_analyzer.receiver_data['udp'].empty:
        receiver_udp = current_analyzer.receiver_data['udp']
        time_ranges['udp_receiver'] = {
            'start': receiver_udp['recv_timestamp'].min().strftime('%Y-%m-%d %H:%M:%S'),
            'end': receiver_udp['recv_timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    # GPS时间范围
    for role in ['sender', 'receiver']:
        if role in current_analyzer.gps_data and not current_analyzer.gps_data[role].empty:
            gps_data = current_analyzer.gps_data[role]
            time_ranges[f'gps_{role}'] = {
                'start': gps_data['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S'),
                'end': gps_data['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    # NEXFI时间范围
    for role in ['sender', 'receiver']:
        if role in current_analyzer.nexfi_data and not current_analyzer.nexfi_data[role].empty:
            nexfi_data = current_analyzer.nexfi_data[role]
            time_ranges[f'nexfi_{role}'] = {
                'start': nexfi_data['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S'),
                'end': nexfi_data['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    # 计算有效时间范围（所有数据的交集）
    if time_ranges:
        all_starts = []
        all_ends = []
        
        for key, range_info in time_ranges.items():
            all_starts.append(pd.to_datetime(range_info['start']))
            all_ends.append(pd.to_datetime(range_info['end']))
        
        effective_start = max(all_starts)
        effective_end = min(all_ends)
        
        summary['time_range'] = {
            'effective_start': effective_start.strftime('%Y-%m-%d %H:%M:%S'),
            'effective_end': effective_end.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_seconds': (effective_end - effective_start).total_seconds(),
            'individual_ranges': time_ranges
        }
    
    return jsonify(summary)


@app.route('/api/datasets')
def get_datasets():
    """API端点：获取可用数据集列表"""
    scan_available_datasets()
    return jsonify(available_datasets)


@app.route('/api/delete_dataset/<dataset_name>', methods=['DELETE'])
def delete_dataset(dataset_name):
    """API端点：删除指定数据集"""
    global current_analyzer, current_visualizer
    
    try:
        # 查找数据集路径
        dataset_path = None
        dataset_info = None
        for dataset in available_datasets:
            if dataset['name'] == dataset_name:
                dataset_path = dataset['path']
                dataset_info = dataset
                break
        
        if not dataset_path or not os.path.exists(dataset_path):
            return jsonify({'error': f'数据集 {dataset_name} 不存在'}), 404
        
        # 检查是否为当前正在分析的数据集
        if current_analyzer and hasattr(current_analyzer, 'dataset_path'):
            if os.path.abspath(current_analyzer.dataset_path) == os.path.abspath(dataset_path):
                # 清理当前分析器和可视化器
                current_analyzer = None
                current_visualizer = None
        
        # 删除数据集目录
        if os.path.exists(dataset_path):
            shutil.rmtree(dataset_path)
            print(f"已删除数据集: {dataset_path}")
        
        # 重新扫描数据集
        scan_available_datasets()
        
        return jsonify({
            'success': True,
            'message': f'数据集 {dataset_name} 已成功删除',
            'deleted_dataset': dataset_info
        })
        
    except Exception as e:
        print(f"删除数据集错误: {str(e)}")
        return jsonify({'error': f'删除失败: {str(e)}'}), 500


@app.route('/api/force_reanalyze/<dataset_name>', methods=['POST'])
def force_reanalyze(dataset_name):
    """强制重新分析数据集"""
    global current_analyzer, current_visualizer
    
    try:
        # 清理当前分析器和可视化器
        current_analyzer = None
        current_visualizer = None
        
        # 查找数据集路径
        dataset_path = None
        for dataset in available_datasets:
            if dataset['name'] == dataset_name:
                dataset_path = dataset['path']
                break
        
        if not dataset_path or not os.path.exists(dataset_path):
            return jsonify({'error': f'数据集 {dataset_name} 不存在'}), 404
        
        print(f"强制重新分析数据集: {dataset_name}")
        
        # 创建新的分析器并运行分析
        current_analyzer = DroneCommAnalyzer(dataset_path)
        current_analyzer.run_full_analysis()
        
        # 创建新的可视化器并生成图表
        current_visualizer = DroneCommVisualizer(current_analyzer)
        current_visualizer.create_all_plots()
        
        return jsonify({
            'success': True,
            'message': f'数据集 {dataset_name} 重新分析完成',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"强制重新分析错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'重新分析失败: {str(e)}'}), 500


@app.route('/api/clear_cache', methods=['POST'])
def clear_cache():
    """API端点：清理服务器端缓存"""
    global current_analyzer, current_visualizer
    
    try:
        # 清理当前分析器和可视化器
        current_analyzer = None
        current_visualizer = None
        
        # 清理临时文件
        temp_dirs = ['/tmp', tempfile.gettempdir()]
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for item in os.listdir(temp_dir):
                    if item.startswith('tmp') and 'drone' in item.lower():
                        try:
                            item_path = os.path.join(temp_dir, item)
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                        except:
                            pass
        
        # 重新扫描数据集
        scan_available_datasets()
        
        return jsonify({
            'success': True,
            'message': '服务器缓存已清理',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'清理缓存失败: {str(e)}'}), 500


@app.route('/api/download_report/<dataset_name>')
def download_report(dataset_name):
    """API端点：下载分析报告"""
    if current_analyzer is None or current_visualizer is None:
        return jsonify({'error': '尚未进行分析'}), 400
    
    try:
        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, f'{dataset_name}_analysis_report.zip')
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # 保存分析结果JSON
            results_json = json.dumps(current_analyzer.analysis_results, indent=2, default=str)
            zipf.writestr(f'{dataset_name}_analysis_results.json', results_json)
            
            # 保存摘要 - 直接调用api_summary的逻辑
            summary_response = api_summary()
            if summary_response.status_code == 200:
                summary_data = summary_response.get_json()
                summary_json = json.dumps(summary_data, indent=2, default=str)
                zipf.writestr(f'{dataset_name}_summary.json', summary_json)
            
            # 保存所有图表为HTML
            for name, fig in current_visualizer.figures.items():
                html_content = fig.to_html(include_plotlyjs='cdn')
                zipf.writestr(f'plots/{name}.html', html_content)
        
        return send_file(zip_path, as_attachment=True, 
                        download_name=f'{dataset_name}_analysis_report.zip')
    
    except Exception as e:
        return jsonify({'error': f'生成报告失败: {str(e)}'}), 500


@app.route('/compare')
def compare_datasets():
    """比较多个数据集的页面"""
    scan_available_datasets()
    return render_template('compare.html', datasets=available_datasets)


@app.route('/api/compare', methods=['POST'])
def compare_multiple_datasets():
    """API端点：比较多个数据集"""
    dataset_names = request.json.get('datasets', [])
    
    if len(dataset_names) < 2:
        return jsonify({'error': '至少需要选择两个数据集进行比较'}), 400
    
    comparison_results = {}
    
    for dataset_name in dataset_names:
        # 查找数据集路径
        dataset_path = None
        for dataset in available_datasets:
            if dataset['name'] == dataset_name:
                dataset_path = dataset['path']
                break
        
        if not dataset_path or not os.path.exists(dataset_path):
            comparison_results[dataset_name] = {'error': '数据集不存在'}
            continue
            
        try:
            analyzer = DroneCommAnalyzer(dataset_path)
            analyzer.run_full_analysis()
            
            # 提取关键指标
            metrics = {}
            if 'udp' in analyzer.analysis_results:
                metrics['packet_loss_rate'] = analyzer.analysis_results['udp']['packet_loss_rate']
                metrics['avg_delay'] = analyzer.analysis_results['udp']['delay_stats']['mean']
                metrics['max_delay'] = analyzer.analysis_results['udp']['delay_stats']['max']
                metrics['throughput'] = analyzer.analysis_results['udp']['throughput_kbps']
                metrics['total_sent'] = analyzer.analysis_results['udp']['total_sent']
                metrics['total_received'] = analyzer.analysis_results['udp']['total_received']
            
            if 'inter_drone_distance' in analyzer.analysis_results:
                metrics['avg_distance_3d'] = analyzer.analysis_results['inter_drone_distance']['mean_distance_3d']
                metrics['max_distance_3d'] = analyzer.analysis_results['inter_drone_distance']['max_distance_3d']
                metrics['min_distance_3d'] = analyzer.analysis_results['inter_drone_distance']['min_distance_3d']
            
            if 'nexfi' in analyzer.analysis_results:
                for role, stats in analyzer.analysis_results['nexfi'].items():
                    metrics[f'{role}_avg_rssi'] = stats['rssi']['mean']
                    metrics[f'{role}_avg_snr'] = stats['snr']['mean']
                    metrics[f'{role}_avg_link_quality'] = stats['link_quality']['mean']
            
            if 'gps' in analyzer.analysis_results:
                for role, stats in analyzer.analysis_results['gps'].items():
                    metrics[f'{role}_flight_distance'] = stats['total_distance']
                    metrics[f'{role}_flight_time'] = stats['flight_time']
                    metrics[f'{role}_max_speed'] = stats['max_speed']
            
            comparison_results[dataset_name] = metrics
            
        except Exception as e:
            comparison_results[dataset_name] = {'error': str(e)}
    
    return jsonify(comparison_results)


@app.route('/api/trajectory_data')
def get_trajectory_data():
    """API端点：获取轨迹回放数据"""
    if current_analyzer is None:
        return jsonify({'error': '尚未进行分析'}), 400
    
    try:
        # 添加详细的调试信息
        print("=== Trajectory Data API Debug ===")
        print(f"current_analyzer存在: {current_analyzer is not None}")
        
        if current_analyzer:
            print(f"current_analyzer类型: {type(current_analyzer)}")
            print(f"hasattr gps_data: {hasattr(current_analyzer, 'gps_data')}")
            print(f"hasattr sender_data: {hasattr(current_analyzer, 'sender_data')}")
            print(f"hasattr analysis_results: {hasattr(current_analyzer, 'analysis_results')}")
            
            if hasattr(current_analyzer, 'gps_data'):
                print(f"gps_data类型: {type(current_analyzer.gps_data)}")
                print(f"gps_data是否为None: {current_analyzer.gps_data is None}")
                if current_analyzer.gps_data:
                    print(f"gps_data键: {list(current_analyzer.gps_data.keys()) if isinstance(current_analyzer.gps_data, dict) else 'Not a dict'}")
                    for role in ['sender', 'receiver']:
                        if role in current_analyzer.gps_data:
                            df = current_analyzer.gps_data[role]
                            print(f"gps_data[{role}]形状: {df.shape if hasattr(df, 'shape') else 'No shape'}")
                            if hasattr(df, 'columns'):
                                print(f"gps_data[{role}]列: {list(df.columns)}")
                            if hasattr(df, 'empty'):
                                print(f"gps_data[{role}]是否为空: {df.empty}")
            
            if hasattr(current_analyzer, 'sender_data'):
                print(f"sender_data类型: {type(current_analyzer.sender_data)}")
                if isinstance(current_analyzer.sender_data, dict):
                    print(f"sender_data键: {list(current_analyzer.sender_data.keys())}")
                    if 'udp' in current_analyzer.sender_data:
                        udp_df = current_analyzer.sender_data['udp']
                        print(f"sender_data['udp']形状: {udp_df.shape if hasattr(udp_df, 'shape') else 'No shape'}")
        
        trajectory_data = {
            'sender': [],
            'receiver': [],
            'timestamps': [],
            'metrics': [],
            'overall_stats': {}
        }
        
        # 标记是否找到了真实数据
        has_real_data = False
        
        # 安全的GPS数据处理
        try:
            if (hasattr(current_analyzer, 'gps_data') and 
                current_analyzer.gps_data and 
                isinstance(current_analyzer.gps_data, dict)):
                
                print(f"GPS数据字典键: {list(current_analyzer.gps_data.keys())}")
                
                # 收集所有GPS点用于计算参考点
                all_lats = []
                all_lons = []
                
                for role in ['sender', 'receiver']:
                    if role in current_analyzer.gps_data:
                        gps_df = current_analyzer.gps_data[role]
                        print(f"GPS数据[{role}]: 类型={type(gps_df)}, 形状={gps_df.shape if hasattr(gps_df, 'shape') else '无形状'}")
                        
                        if (gps_df is not None and 
                            hasattr(gps_df, 'empty') and not gps_df.empty and
                            'latitude' in gps_df.columns and 'longitude' in gps_df.columns):
                            
                            # 过滤掉nan值
                            valid_rows = gps_df.dropna(subset=['latitude', 'longitude'])
                            print(f"GPS数据[{role}]: 有效行数={len(valid_rows)}/{len(gps_df)}")
                            
                            if len(valid_rows) > 0:
                                all_lats.extend(valid_rows['latitude'].tolist())
                                all_lons.extend(valid_rows['longitude'].tolist())
                
                print(f"收集到的坐标点数: {len(all_lats)} 个")
                
                if all_lats and all_lons:
                    ref_lat = sum(all_lats) / len(all_lats)
                    ref_lon = sum(all_lons) / len(all_lons)
                    
                    print(f"参考点设定为: lat={ref_lat:.6f}, lon={ref_lon:.6f}")
                    
                    # 处理每个角色的GPS数据
                    for role in ['sender', 'receiver']:
                        if role in current_analyzer.gps_data:
                            gps_df = current_analyzer.gps_data[role]
                            
                            if (gps_df is not None and 
                                hasattr(gps_df, 'empty') and not gps_df.empty):
                                
                                # 过滤掉nan值
                                valid_rows = gps_df.dropna(subset=['latitude', 'longitude', 'timestamp'])
                                
                                # 限制数据量以避免过载，但取更多数据点
                                sample_df = valid_rows.head(100) if len(valid_rows) > 100 else valid_rows
                                
                                points_added = 0
                                for index, row in sample_df.iterrows():
                                    try:
                                        lat = float(row['latitude'])
                                        lon = float(row['longitude'])
                                        alt = float(row.get('altitude', 0))
                                        
                                        # 简化的坐标转换（近似）
                                        x = (lon - ref_lon) * 111320 * math.cos(math.radians(ref_lat))
                                        y = (lat - ref_lat) * 111320
                                        
                                        trajectory_data[role].append({
                                            'x': round(x, 2),
                                            'y': round(y, 2),
                                            'z': round(alt, 2),
                                            'timestamp': row['timestamp'].isoformat()
                                        })
                                        
                                        points_added += 1
                                        has_real_data = True
                                        
                                    except Exception as e:
                                        print(f"处理{role} GPS数据行错误: {e}")
                                        continue
                                
                                print(f"为{role}添加了{points_added}个GPS点")
                else:
                    print("没有找到有效的GPS坐标数据")
                    
        except Exception as e:
            print(f"GPS数据处理错误: {e}")
            import traceback
            traceback.print_exc()
        
        # 安全的UDP指标数据处理
        try:
            metrics_added = 0
            
            # 优先使用接收方数据，因为它包含延迟信息
            if (hasattr(current_analyzer, 'receiver_data') and 
                isinstance(current_analyzer.receiver_data, dict) and
                'udp' in current_analyzer.receiver_data and 
                current_analyzer.receiver_data['udp'] is not None and
                not current_analyzer.receiver_data['udp'].empty):
                
                udp_df = current_analyzer.receiver_data['udp']
                print(f"使用接收方UDP数据，形状: {udp_df.shape}")
                print(f"接收方UDP列: {list(udp_df.columns)}")
                
                # 限制数据量，取前50个数据点
                sample_df = udp_df.head(50) if len(udp_df) > 50 else udp_df
                
                for index, row in sample_df.iterrows():
                    try:
                        if pd.notna(row.get('recv_timestamp')):
                            delay_value = None
                            if pd.notna(row.get('delay')):
                                delay_value = float(row['delay']) * 1000  # 转换为毫秒
                            
                            trajectory_data['metrics'].append({
                                'timestamp': row['recv_timestamp'].isoformat(),
                                'delay': delay_value,
                                'packet_loss': 0
                            })
                            metrics_added += 1
                            has_real_data = True
                    except Exception as e:
                        print(f"处理接收方UDP数据行错误: {e}")
                        continue
                
                print(f"从接收方添加了{metrics_added}个UDP指标数据点")
                
            # 如果接收方数据不可用，尝试发送方数据
            elif (hasattr(current_analyzer, 'sender_data') and 
                  isinstance(current_analyzer.sender_data, dict) and
                  'udp' in current_analyzer.sender_data and 
                  current_analyzer.sender_data['udp'] is not None and
                  not current_analyzer.sender_data['udp'].empty):
                
                udp_df = current_analyzer.sender_data['udp']
                print(f"使用发送方UDP数据，形状: {udp_df.shape}")
                
                # 限制数据量，取前50个数据点
                sample_df = udp_df.head(50) if len(udp_df) > 50 else udp_df
                
                for index, row in sample_df.iterrows():
                    try:
                        if pd.notna(row.get('timestamp')):
                            trajectory_data['metrics'].append({
                                'timestamp': row['timestamp'].isoformat(),
                                'delay': None,  # 发送方数据通常没有延迟信息
                                'packet_loss': 0
                            })
                            metrics_added += 1
                            has_real_data = True
                    except Exception as e:
                        print(f"处理发送方UDP数据行错误: {e}")
                        continue
                
                print(f"从发送方添加了{metrics_added}个UDP指标数据点")
                        
        except Exception as e:
            print(f"UDP数据处理错误: {e}")
            import traceback
            traceback.print_exc()
        
        # 安全的统计信息处理
        try:
            if (hasattr(current_analyzer, 'analysis_results') and 
                current_analyzer.analysis_results and 
                'udp' in current_analyzer.analysis_results):
                
                udp_stats = current_analyzer.analysis_results['udp']
                trajectory_data['overall_stats'] = {
                    'packet_loss_rate': udp_stats.get('packet_loss_rate', 0),
                    'avg_delay': udp_stats.get('delay_stats', {}).get('mean', 0),
                    'max_delay': udp_stats.get('delay_stats', {}).get('max', 0)
                }
                print(f"添加了UDP统计信息: {trajectory_data['overall_stats']}")
        except Exception as e:
            print(f"统计信息处理错误: {e}")
        
        # 如果没有找到真实数据，返回示例数据，但标记为示例
        if not has_real_data:
            print("没有找到真实数据，返回示例数据")
            trajectory_data = {
                'sender': [
                    {'x': 0, 'y': 0, 'z': 0, 'timestamp': '2025-01-01T00:00:00'},
                    {'x': 10, 'y': 10, 'z': 5, 'timestamp': '2025-01-01T00:01:00'}
                ],
                'receiver': [
                    {'x': 100, 'y': 0, 'z': 0, 'timestamp': '2025-01-01T00:00:00'},
                    {'x': 90, 'y': 10, 'z': 5, 'timestamp': '2025-01-01T00:01:00'}
                ],
                'timestamps': ['2025-01-01T00:00:00', '2025-01-01T00:01:00'],
                'metrics': [
                    {'timestamp': '2025-01-01T00:00:00', 'delay': 50, 'packet_loss': 0},
                    {'timestamp': '2025-01-01T00:01:00', 'delay': 75, 'packet_loss': 0}
                ],
                'overall_stats': {
                    'packet_loss_rate': 0,
                    'avg_delay': 62.5,
                    'max_delay': 75
                },
                'is_sample_data': True
            }
        else:
            trajectory_data['is_sample_data'] = False
            print(f"返回真实数据: sender={len(trajectory_data['sender'])}点, receiver={len(trajectory_data['receiver'])}点, metrics={len(trajectory_data['metrics'])}点")
        
        return jsonify(trajectory_data)
        
    except Exception as e:
        print(f"轨迹数据API总体错误: {str(e)}")
        import traceback
        traceback.print_exc()
        # 返回基本响应而不是错误
        return jsonify({
            'sender': [],
            'receiver': [],
            'timestamps': [],
            'metrics': [],
            'overall_stats': {},
            'error': f'数据处理错误: {str(e)}',
            'is_sample_data': False
        })


if __name__ == '__main__':
    # 创建必要的目录
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    
    # 获取端口配置（支持Render部署）
    port = int(os.environ.get('PORT', 6500))
    host = '0.0.0.0'
    
    print("🚁 无人机通信数据分析系统正在启动...")
    print(f"📊 系统将在 http://{host}:{port} 启动")
    print("🌐 请在浏览器中访问上述地址")
    
    # 扫描可用数据集
    scan_available_datasets()
    print(f"📂 发现 {len(available_datasets)} 个数据集")
    
    # 根据环境判断是否启用调试模式
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    
    app.run(debug=debug_mode, host=host, port=port) 
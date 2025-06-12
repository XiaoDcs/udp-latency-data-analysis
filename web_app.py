from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import json
import glob
from datetime import datetime
from drone_communication_analyzer import DroneCommAnalyzer
from visualization import DroneCommVisualizer, create_summary_dashboard
import plotly
import plotly.utils

app = Flask(__name__)

# 全局变量存储当前分析器和可视化器
current_analyzer = None
current_visualizer = None
available_datasets = []

def scan_available_datasets():
    """扫描可用的数据集"""
    global available_datasets
    available_datasets = []
    
    # 确保data目录存在
    data_dir = 'data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        return
    
    # 查找data目录下所有包含sender和receiver子文件夹的目录
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
                    'path': item_path,  # 完整路径
                    'has_udp': has_udp,
                    'has_nexfi': has_nexfi,
                    'has_gps': has_gps,
                    'creation_time': datetime.fromtimestamp(os.path.getctime(item_path)).strftime('%Y-%m-%d %H:%M:%S')
                }
                available_datasets.append(dataset_info)
    
    # 按创建时间排序
    available_datasets.sort(key=lambda x: x['creation_time'], reverse=True)


@app.route('/')
def index():
    """主页面，显示可用数据集列表"""
    scan_available_datasets()
    return render_template('index.html', datasets=available_datasets)


@app.route('/analyze/<dataset_name>')
def analyze_dataset(dataset_name):
    """分析指定数据集"""
    global current_analyzer, current_visualizer
    
    # 构建完整的数据集路径
    dataset_path = os.path.join('data', dataset_name)
    
    if not os.path.exists(dataset_path):
        return jsonify({'error': f'数据集 {dataset_name} 不存在'}), 404
    
    try:
        # 创建分析器并运行分析
        current_analyzer = DroneCommAnalyzer(dataset_path)
        current_analyzer.run_full_analysis()
        
        # 创建可视化器并生成图表
        current_visualizer = DroneCommVisualizer(current_analyzer)
        current_visualizer.create_all_plots()
        
        return redirect(url_for('dashboard', dataset_name=dataset_name))
        
    except Exception as e:
        return jsonify({'error': f'分析失败: {str(e)}'}), 500


@app.route('/dashboard/<dataset_name>')
def dashboard(dataset_name):
    """显示分析仪表板"""
    if current_analyzer is None:
        return redirect(url_for('analyze_dataset', dataset_name=dataset_name))
    
    # 获取分析结果摘要
    summary = get_analysis_summary()
    
    return render_template('dashboard.html', 
                         dataset_name=dataset_name,
                         summary=summary)


@app.route('/api/figures')
def get_figures():
    """API端点：获取所有图表的JSON数据"""
    if current_visualizer is None:
        return jsonify({'error': '尚未进行分析'}), 400
    
    figures_json = {}
    for name, fig in current_visualizer.figures.items():
        figures_json[name] = json.loads(fig.to_json())
    
    return jsonify(figures_json)


@app.route('/api/summary')
def get_analysis_summary():
    """API端点：获取分析结果摘要"""
    if current_analyzer is None:
        return jsonify({'error': '尚未进行分析'}), 400
    
    summary = {}
    
    # UDP性能摘要
    if 'udp' in current_analyzer.analysis_results:
        udp_results = current_analyzer.analysis_results['udp']
        summary['udp'] = {
            'total_sent': udp_results['total_sent'],
            'total_received': udp_results['total_received'],
            'packet_loss_rate': round(udp_results['packet_loss_rate'], 2),
            'avg_delay': round(udp_results['delay_stats']['mean'], 2),
            'p95_delay': round(udp_results['delay_stats']['p95'], 2),
            'throughput': round(udp_results['throughput_kbps'], 2),
            'test_duration': round(udp_results['test_duration'], 1)
        }
    
    # NEXFI摘要
    if 'nexfi' in current_analyzer.analysis_results:
        summary['nexfi'] = {}
        for role, stats in current_analyzer.analysis_results['nexfi'].items():
            summary['nexfi'][role] = {
                'avg_rssi': round(stats['rssi']['mean'], 1),
                'avg_snr': round(stats['snr']['mean'], 1),
                'avg_throughput': round(stats['throughput']['mean'], 2),
                'avg_link_quality': round(stats['link_quality']['mean'], 1)
            }
    
    # GPS摘要
    if 'gps' in current_analyzer.analysis_results:
        summary['gps'] = {}
        for role, stats in current_analyzer.analysis_results['gps'].items():
            summary['gps'][role] = {
                'total_distance': round(stats['total_distance'], 2),
                'altitude_change': round(stats['altitude_change'], 2),
                'max_speed': round(stats['max_speed'], 2),
                'flight_time': round(stats['flight_time'], 1)
            }
    
    # 距离摘要
    if 'inter_drone_distance' in current_analyzer.analysis_results:
        dist_stats = current_analyzer.analysis_results['inter_drone_distance']
        summary['distance'] = {
            'mean_distance': round(dist_stats['mean_distance'], 2),
            'max_distance': round(dist_stats['max_distance'], 2),
            'min_distance': round(dist_stats['min_distance'], 2),
            'std_distance': round(dist_stats['std_distance'], 2)
        }
    
    # 相关性摘要
    if 'correlations' in current_analyzer.analysis_results:
        summary['correlations'] = {}
        for key, corr in current_analyzer.analysis_results['correlations'].items():
            summary['correlations'][key] = {
                'correlation': round(corr['correlation'], 3),
                'p_value': round(corr['p_value'], 3),
                'significant': corr['significant']
            }
    
    return summary


@app.route('/api/datasets')
def get_datasets():
    """API端点：获取可用数据集列表"""
    scan_available_datasets()
    return jsonify(available_datasets)


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
        # 构建完整的数据集路径
        dataset_path = os.path.join('data', dataset_name)
        
        if not os.path.exists(dataset_path):
            continue
            
        try:
            analyzer = DroneCommAnalyzer(dataset_path)
            analyzer.run_full_analysis()
            
            # 提取关键指标
            metrics = {}
            if 'udp' in analyzer.analysis_results:
                metrics['packet_loss_rate'] = analyzer.analysis_results['udp']['packet_loss_rate']
                metrics['avg_delay'] = analyzer.analysis_results['udp']['delay_stats']['mean']
                metrics['throughput'] = analyzer.analysis_results['udp']['throughput_kbps']
            
            if 'inter_drone_distance' in analyzer.analysis_results:
                metrics['avg_distance'] = analyzer.analysis_results['inter_drone_distance']['mean_distance']
            
            if 'nexfi' in analyzer.analysis_results:
                for role, stats in analyzer.analysis_results['nexfi'].items():
                    metrics[f'{role}_avg_rssi'] = stats['rssi']['mean']
                    metrics[f'{role}_avg_snr'] = stats['snr']['mean']
            
            comparison_results[dataset_name] = metrics
            
        except Exception as e:
            comparison_results[dataset_name] = {'error': str(e)}
    
    return jsonify(comparison_results)


if __name__ == '__main__':
    # 创建templates目录如果不存在
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("🚁 无人机通信数据分析系统正在启动...")
    print("📊 系统将在 http://127.0.0.1:6500 启动")
    print("🌐 请在浏览器中访问上述地址")
    
    app.run(debug=True, host='0.0.0.0', port=6500) 
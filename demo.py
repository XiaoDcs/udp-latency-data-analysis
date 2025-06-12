#!/usr/bin/env python3
"""
无人机通信数据分析系统演示脚本

这个脚本演示了如何使用无人机通信数据分析系统进行数据分析和可视化。
运行前请确保已安装所有依赖包：pip install -r requirements.txt
"""

import os
import sys

def check_dependencies():
    """检查依赖包是否已安装"""
    required_packages = [
        'pandas', 'numpy', 'matplotlib', 'plotly', 'scipy', 'flask'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} 未安装")
    
    if missing_packages:
        print(f"\n缺少以下依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    print("\n所有依赖包已正确安装！")
    return True

def check_data_structure():
    """检查数据文件夹结构"""
    print("\n=== 检查数据文件夹结构 ===")
    
    # 确保data目录存在
    data_dir = 'data'
    if not os.path.exists(data_dir):
        print("❌ data目录不存在，正在创建...")
        os.makedirs(data_dir, exist_ok=True)
        print("✓ data目录已创建")
    
    # 查找data目录下的数据文件夹
    data_folders = []
    for item in os.listdir(data_dir):
        item_path = os.path.join(data_dir, item)
        if os.path.isdir(item_path):
            sender_path = os.path.join(item_path, 'sender')
            receiver_path = os.path.join(item_path, 'receiver')
            if os.path.exists(sender_path) and os.path.exists(receiver_path):
                data_folders.append(item_path)
    
    if not data_folders:
        print("❌ 在data目录下未找到符合格式的数据文件夹")
        print("\n期望的文件夹结构:")
        print("data/")
        print("└── 数据集文件夹名称（如：20250612190350）/")
        print("    ├── sender/")
        print("    │   ├── udp_sender_*.csv")
        print("    │   ├── nexfi_status_*.csv")
        print("    │   └── gps_logger_*.csv")
        print("    └── receiver/")
        print("        ├── udp_receiver_*.csv")
        print("        ├── nexfi_status_*.csv")
        print("        └── gps_logger_*.csv")
        return False
    
    print(f"✓ 在data目录下找到 {len(data_folders)} 个数据文件夹:")
    for folder in data_folders:
        print(f"  - {folder}")
    
    return True, data_folders

def demo_command_line_analysis():
    """演示命令行分析"""
    print("\n=== 命令行分析演示 ===")
    
    print("""
# 基本使用方法
from drone_communication_analyzer import DroneCommAnalyzer
from visualization import DroneCommVisualizer

# 1. 创建分析器（数据现在在data目录下）
analyzer = DroneCommAnalyzer("data/20250612190350")

# 2. 运行完整分析
analyzer.run_full_analysis()

# 3. 保存分析结果
analyzer.save_results("analysis_results.json")

# 4. 创建可视化图表
visualizer = DroneCommVisualizer(analyzer)
visualizer.create_all_plots()

# 5. 保存图表为HTML文件
visualizer.save_plots_as_html("output_plots")
    """)

def demo_web_interface():
    """演示Web界面使用"""
    print("\n=== Web界面演示 ===")
    
    print("""
# 启动Web服务
python3 web_app.py

# 然后在浏览器中访问：
http://localhost:5000

# Web界面功能：
1. 首页 - 查看所有可用的数据集
2. 分析 - 选择数据集进行自动分析
3. 仪表板 - 查看详细的分析结果和图表
4. 比较 - 对比多个数据集的测试结果
    """)

def show_analysis_capabilities():
    """展示分析能力"""
    print("\n=== 系统分析能力 ===")
    
    capabilities = {
        "UDP通信性能分析": [
            "延迟统计（平均值、中位数、95%分位数等）",
            "丢包率计算",
            "吞吐量分析",
            "时间序列分析"
        ],
        "NEXFI通信质量分析": [
            "RSSI信号强度分析",
            "SNR信噪比分析", 
            "链路质量评估",
            "通信吞吐量统计"
        ],
        "GPS轨迹分析": [
            "3D飞行轨迹可视化",
            "飞行速度计算",
            "高度变化分析",
            "飞行距离统计"
        ],
        "距离与相关性分析": [
            "双机间距离实时计算",
            "通信质量与距离相关性",
            "延迟与距离关系分析",
            "统计显著性检验"
        ]
    }
    
    for category, features in capabilities.items():
        print(f"\n📊 {category}:")
        for feature in features:
            print(f"  • {feature}")

def main():
    print("🚁 无人机通信数据分析系统演示")
    print("=" * 50)
    
    # 检查依赖
    print("\n=== 步骤1: 检查依赖包 ===")
    deps_ok = check_dependencies()
    
    # 检查数据
    print("\n=== 步骤2: 检查数据文件 ===")
    data_result = check_data_structure()
    
    # 展示分析能力
    show_analysis_capabilities()
    
    # 演示使用方法
    demo_command_line_analysis()
    demo_web_interface()
    
    print("\n=== 系统特色功能 ===")
    print("✨ 交互式3D轨迹可视化")
    print("✨ 实时性能监控仪表板")
    print("✨ 多数据集对比分析")
    print("✨ 自动相关性统计分析")
    print("✨ 现代化Web界面")
    print("✨ 可扩展的分析框架")
    
    print("\n=== 快速开始 ===")
    if deps_ok and isinstance(data_result, tuple) and data_result[0]:
        print("✅ 系统已准备就绪！")
        print("📁 数据文件夹位置: data/")
        print("🚀 运行 'python3 web_app.py' 启动Web界面")
        print("🔗 或者使用命令行API进行自定义分析")
        
        # 显示找到的数据集
        if len(data_result[1]) > 0:
            print(f"\n📊 发现的数据集:")
            for dataset_path in data_result[1]:
                dataset_name = os.path.basename(dataset_path)
                print(f"  - {dataset_name} (位置: {dataset_path})")
    else:
        print("⚠️  请先安装依赖包和准备数据文件")
        print("📁 请将测试数据放入 data/ 文件夹")
        print("📝 详细说明请查看 README.md")
    
    print("\n感谢使用无人机通信数据分析系统！")
    print("项目地址: https://github.com/XiaoDcs/udp-latency")

if __name__ == "__main__":
    main() 
# 无人机通信数据分析系统

基于 [udp-latency 项目](https://github.com/XiaoDcs/udp-latency) 开发的无人机通信测试数据分析系统，提供全面的数据分析和可视化功能。

## 🚀 功能特性

### 数据分析能力
- **UDP通信性能分析**：延迟统计、丢包率、吞吐量分析
- **NEXFI通信质量分析**：RSSI、SNR、链路质量、吞吐量分析
- **GPS轨迹分析**：3D飞行轨迹、速度、高度变化分析
- **距离分析**：双机间距离变化及统计分析
- **相关性分析**：通信质量与距离的相关性分析

### 可视化展示
- 交互式3D轨迹图
- 实时性能指标仪表板
- 多维度统计图表
- 相关性散点图和趋势分析

### Web界面
- 现代化响应式Web界面
- 多数据集管理和比较
- 实时数据加载和展示
- 分析报告导出功能

## 📦 安装要求

### Python环境
```bash
Python >= 3.8
```

### 虚拟环境安装（推荐）
```bash
# 创建虚拟环境
python3 -m venv drone_analysis_env

# 激活虚拟环境
# macOS/Linux:
source drone_analysis_env/bin/activate
# Windows:
# drone_analysis_env\Scripts\activate

# 安装依赖包
pip install pandas numpy matplotlib seaborn plotly scipy flask
```

## 📂 项目结构

```
udp-latency-data-analysis/
├── drone_communication_analyzer.py  # 核心分析引擎
├── visualization.py                 # 可视化模块
├── web_app.py                      # Flask Web应用
├── demo.py                         # 演示脚本
├── requirements.txt                # 依赖列表
├── README.md                       # 项目文档
├── .gitignore                      # Git忽略文件
├── templates/                      # Web模板
│   ├── base.html
│   ├── index.html
│   └── dashboard.html
└── data/                          # 数据存储目录
    └── 数据集文件夹（如：20250612190350）/
        ├── sender/                # 发送方数据
        │   ├── udp_sender_*.csv
        │   ├── nexfi_status_*.csv
        │   └── gps_logger_*.csv
        └── receiver/              # 接收方数据
            ├── udp_receiver_*.csv
            ├── nexfi_status_*.csv
            └── gps_logger_*.csv
```

## 📂 数据格式要求

系统支持分析包含以下结构的数据文件夹，**所有数据集应放在 `data/` 目录下**：

```
data/
└── 数据集文件夹名称（如：20250612190350）/
    ├── sender/                    # 发送方数据
    │   ├── udp_sender_*.csv      # UDP发送数据
    │   ├── nexfi_status_*.csv    # NEXFI通信状态
    │   └── gps_logger_*.csv      # GPS位置数据
    └── receiver/                 # 接收方数据
        ├── udp_receiver_*.csv    # UDP接收数据
        ├── nexfi_status_*.csv    # NEXFI通信状态
        └── gps_logger_*.csv      # GPS位置数据
```

### 文件格式说明

#### UDP发送方数据 (udp_sender_*.csv)
```csv
seq_num,timestamp,packet_size
1,1749726272.1257734,1000
2,1749726272.2251344,1000
...
```

#### UDP接收方数据 (udp_receiver_*.csv)
```csv
seq_num,send_timestamp,recv_timestamp,delay,src_ip,src_port,packet_size
2,1749726272.224993,1749726272.35602,0.1310269832611084,192.168.104.112,20002,1000
...
```

#### NEXFI通信状态 (nexfi_status_*.csv)
```csv
timestamp,mesh_enabled,channel,frequency_band,tx_power,work_mode,node_id,connected_nodes,avg_rssi,avg_snr,throughput,cpu_usage,memory_usage,uptime,firmware_version,topology_nodes,link_quality
1749726241.37493,True,2A,10,33,adhoc,12,1,-38.0,57.0,6.408,0.60,0.419986,5479,MC1.0.127,2,191.0
...
```

#### GPS数据 (gps_logger_*.csv)
```csv
timestamp,latitude,longitude,altitude,local_x,local_y,local_z,connected,armed,offboard
1749726239.493269,34.03433114686528,108.76448924146617,397.0210266113281,2.7077839374542236,0.6664539575576782,-0.01397705078125,True,False,False
...
```

## 🖥️ 使用方法

### 1. 快速开始

#### 数据准备
1. 将测试数据文件夹放入 `data/` 目录
2. 确保数据文件夹包含 `sender/` 和 `receiver/` 子目录
3. 运行演示脚本检查数据结构：
```bash
python3 demo.py
```

#### 启动Web界面
```bash
# 激活虚拟环境（如果使用）
source drone_analysis_env/bin/activate

# 启动Web应用
python3 web_app.py
```

然后在浏览器中访问：`http://localhost:6500`

### 2. 命令行分析

#### 基础分析
```python
from drone_communication_analyzer import DroneCommAnalyzer

# 创建分析器（注意：数据在data目录下）
analyzer = DroneCommAnalyzer("data/20250612190350")

# 运行完整分析
analyzer.run_full_analysis()

# 保存结果
analyzer.save_results("analysis_results.json")
```

#### 生成可视化图表
```python
from visualization import DroneCommVisualizer

# 创建可视化器
visualizer = DroneCommVisualizer(analyzer)
visualizer.create_all_plots()

# 保存图表为HTML文件
visualizer.save_plots_as_html("output_plots")
```

### 3. Web界面使用

#### 使用流程
1. **首页**：查看可用的数据集列表
2. **选择数据集**：点击"开始分析"按钮
3. **查看结果**：在仪表板中浏览分析结果
4. **切换标签**：查看不同类型的分析和图表
5. **数据集比较**：对比多个测试结果

## 📊 分析结果说明

### UDP性能指标
- **丢包率**：(发送包数 - 接收包数) / 发送包数 × 100%
- **延迟统计**：平均值、中位数、95%分位数、99%分位数
- **吞吐量**：有效数据传输速率 (kbps)

### NEXFI通信质量
- **RSSI**：接收信号强度指示 (dBm)
- **SNR**：信噪比 (dB)
- **链路质量**：通信链路质量评分
- **吞吐量**：NEXFI层面的数据吞吐量 (Mbps)

### GPS轨迹分析
- **飞行距离**：总飞行路径长度
- **高度变化**：最大/最小高度及变化范围
- **飞行速度**：最大/平均飞行速度
- **双机距离**：两架无人机之间的实时距离

### 相关性分析
- **延迟-距离相关性**：UDP延迟与双机距离的相关关系
- **RSSI-距离相关性**：信号强度与距离的相关关系
- **统计显著性**：相关系数的p值检验

## 🔧 系统扩展

### 添加新的数据集
1. 将新的测试数据按照标准格式放入 `data/` 目录
2. 重新启动Web服务或点击"刷新"按钮
3. 系统会自动识别新的数据集

### 自定义分析
```python
# 自定义分析指标
class CustomAnalyzer(DroneCommAnalyzer):
    def custom_analysis(self):
        # 添加自定义分析逻辑
        pass

# 使用自定义分析器
analyzer = CustomAnalyzer("data/your_dataset_folder")
analyzer.run_full_analysis()
analyzer.custom_analysis()
```

### 扩展可视化
```python
# 自定义图表
class CustomVisualizer(DroneCommVisualizer):
    def create_custom_plot(self):
        # 添加自定义图表生成逻辑
        pass

visualizer = CustomVisualizer(analyzer)
visualizer.create_all_plots()
visualizer.create_custom_plot()
```

## ⚠️ 注意事项

1. **数据位置**：所有测试数据必须放在 `data/` 目录下
2. **数据格式**：确保CSV文件格式与示例一致
3. **时间同步**：GPS和通信数据需要时间同步以进行准确的相关性分析
4. **文件大小**：大型数据集可能需要较长的处理时间
5. **内存使用**：建议在内存充足的环境下运行大规模数据分析

## 🐛 故障排除

### 常见问题

#### 1. 数据加载失败
- 检查数据是否放在 `data/` 目录下
- 确认文件路径和格式正确
- 检查CSV文件包含必要的列
- 验证文件编码（建议使用UTF-8）

#### 2. 分析结果异常
- 验证时间戳格式和范围
- 检查数据完整性
- 确认坐标系统一致性

#### 3. Web界面无法访问
- 确认端口6500未被占用
- 检查防火墙设置
- 验证所有依赖包已正确安装
- 尝试使用不同的浏览器或清除缓存

## 📁 Git版本控制

项目已配置 `.gitignore` 文件，会自动忽略：
- Python缓存文件和虚拟环境
- 数据文件（`data/` 目录）
- 分析结果文件
- 系统临时文件
- IDE配置文件

如需分享数据，请单独提供数据文件。

## 📄 开源协议

本项目基于 MIT 协议开源，详见 [LICENSE](LICENSE) 文件。

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进这个项目。

## 📧 联系方式

如有问题或建议，请通过以下方式联系：
- GitHub Issues: [项目Issue页面]
- 原始项目: https://github.com/XiaoDcs/udp-latency

---

**注意**: 本系统基于 [XiaoDcs/udp-latency](https://github.com/XiaoDcs/udp-latency) 项目开发，用于无人机通信测试数据的分析和可视化。 
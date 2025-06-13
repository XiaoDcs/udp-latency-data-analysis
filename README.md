# 无人机通信数据分析系统

一个专业的无人机通信性能分析工具，支持UDP通信延迟、NEXFI通信质量、GPS轨迹等多维度数据分析和可视化。

## 🚁 项目概述

本系统专门用于分析双无人机之间的通信性能，通过对UDP数据包传输、NEXFI通信质量、GPS轨迹等数据的综合分析，提供全面的通信性能评估报告。

## ✨ 主要功能

### 📊 数据分析功能
- **UDP通信性能分析**：延迟统计、丢包率计算、吞吐量分析
- **NEXFI通信质量分析**：RSSI、SNR、链路质量、吞吐量监控
- **GPS轨迹分析**：3D飞行轨迹、速度分析、高度变化
- **双机距离分析**：实时3D距离计算、水平/垂直距离分解
- **相关性分析**：通信质量与距离的相关性统计

### 🎯 可视化功能
- **3D轨迹回放**：支持时间轴控制的三维轨迹动画
- **实时数据面板**：显示当前时刻的无人机状态和通信指标
- **交互式图表**：基于Plotly的高质量交互式图表
- **多维度统计**：综合仪表板展示所有关键指标

### 🌐 Web界面功能
- **数据集管理**：自动扫描和管理多个测试数据集
- **在线分析**：基于Web的实时数据分析
- **报告导出**：支持分析结果和图表的批量导出
- **数据上传**：支持ZIP格式数据包上传和解析

## 🛠️ 技术栈

- **后端**：Python Flask
- **数据处理**：Pandas, NumPy, SciPy
- **可视化**：Plotly, Three.js
- **前端**：Bootstrap 5, jQuery
- **数学计算**：Haversine公式（GPS距离计算）

## 📦 安装说明

### 环境要求
- Python 3.8+
- 现代浏览器（支持WebGL）

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/yourusername/udp-latency-data-analysis.git
cd udp-latency-data-analysis
```

2. **创建虚拟环境**
```bash
python -m venv drone_analysis_env
source drone_analysis_env/bin/activate  # Linux/Mac
# 或
drone_analysis_env\Scripts\activate     # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **启动系统**
```bash
python web_app.py
```

5. **访问系统**
打开浏览器访问：http://127.0.0.1:6500

## 📁 数据格式要求

### 数据集结构
```
数据集名称（如：20250612190350）/
├── sender/                 # 发送方数据
│   ├── udp_sender_*.csv   # UDP发送记录
│   ├── nexfi_status_*.csv # NEXFI状态数据
│   └── gps_logger_*.csv   # GPS轨迹数据
└── receiver/              # 接收方数据
    ├── udp_receiver_*.csv # UDP接收记录
    ├── nexfi_status_*.csv # NEXFI状态数据
    └── gps_logger_*.csv   # GPS轨迹数据
```

### CSV文件格式

#### UDP发送方数据 (udp_sender_*.csv)
```csv
timestamp,seq_num,packet_size
1718188470.123,1,1024
1718188470.223,2,1024
```

#### UDP接收方数据 (udp_receiver_*.csv)
```csv
send_timestamp,recv_timestamp,seq_num,delay,packet_size
1718188470.123,1718188470.145,1,0.022,1024
1718188470.223,1718188470.248,2,0.025,1024
```

#### NEXFI状态数据 (nexfi_status_*.csv)
```csv
timestamp,avg_rssi,avg_snr,throughput,link_quality
1718188470.123,-45.2,25.8,150.5,85
1718188470.223,-46.1,24.9,148.2,83
```

#### GPS数据 (gps_logger_*.csv)
```csv
timestamp,latitude,longitude,altitude,local_x,local_y,local_z
1718188470.123,39.123456,116.654321,450.2,0.0,0.0,0.0
1718188470.223,39.123457,116.654322,451.1,1.2,1.1,0.9
```

## 🚀 使用指南

### 1. 数据准备
- 将测试数据按照上述格式整理
- 可以直接放在项目根目录或`data/`目录下
- 支持上传ZIP压缩包格式的数据

### 2. 开始分析
1. 启动系统后访问主页
2. 选择要分析的数据集
3. 点击"开始分析"按钮
4. 等待分析完成后查看结果

### 3. 查看结果
- **汇总统计**：查看关键性能指标
- **3D轨迹回放**：观看无人机飞行轨迹动画
- **详细图表**：分析各项通信指标的时间序列
- **相关性分析**：了解距离与通信质量的关系

### 4. 导出报告
- 点击"下载报告"按钮
- 获得包含所有分析结果和图表的ZIP文件

## 📈 分析结果说明

### 关键指标
- **丢包率**：UDP数据包丢失百分比
- **平均延迟**：端到端通信延迟（毫秒）
- **3D距离**：双机之间的实时空间距离
- **RSSI**：接收信号强度指示器
- **SNR**：信噪比
- **吞吐量**：数据传输速率

### 相关性分析
系统会自动计算以下相关性：
- 延迟与距离的相关性
- RSSI与距离的相关性
- 通信质量随距离变化的趋势

## 🔧 高级功能

### GPS坐标系统
- 使用Haversine公式计算精确的球面距离
- 支持经纬度到相对坐标的转换
- 考虑地球曲率的真实距离计算

### 时间同步
- 自动对齐不同数据源的时间戳
- 支持中国时区(UTC+8)的时间转换
- 智能处理数据时间范围重叠

### 3D可视化
- 基于Three.js的高性能3D渲染
- 支持鼠标交互控制视角
- 实时轨迹回放和时间轴控制

## 🐛 故障排除

### 常见问题

1. **端口占用错误**
```bash
# 查找占用端口的进程
lsof -i :6500
# 或更改端口
python web_app.py --port 6501
```

2. **数据格式错误**
- 检查CSV文件是否包含必需的列
- 确认时间戳格式为Unix时间戳
- 验证数据文件路径结构

3. **图表显示问题**
- 确保浏览器支持WebGL
- 检查网络连接（需要加载Plotly.js）
- 清除浏览器缓存

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发环境设置
1. Fork本项目
2. 创建功能分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -am 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至：[your-email@example.com]

## 🙏 致谢

感谢所有为本项目做出贡献的开发者和测试人员！

---

**注意**：本系统专为无人机通信测试设计，请确保在合法合规的环境下使用。 
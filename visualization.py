import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo
import pandas as pd
import numpy as np
from datetime import datetime
import json


class DroneCommVisualizer:
    def __init__(self, analyzer):
        """
        初始化可视化器
        
        Args:
            analyzer: DroneCommAnalyzer实例
        """
        self.analyzer = analyzer
        self.figures = {}
        
    def create_udp_performance_plots(self):
        """创建UDP性能相关图表"""
        if 'udp' not in self.analyzer.receiver_data:
            return
            
        receiver_udp = self.analyzer.receiver_data['udp']
        
        # 创建子图
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('UDP延迟时间序列', '延迟分布直方图', '延迟累积分布', '包序号vs延迟'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # 延迟时间序列
        fig.add_trace(
            go.Scatter(
                x=receiver_udp['recv_timestamp'],
                y=receiver_udp['delay'] * 1000,
                mode='lines+markers',
                name='UDP延迟',
                line=dict(color='blue', width=1),
                marker=dict(size=3)
            ),
            row=1, col=1
        )
        
        # 延迟分布直方图
        fig.add_trace(
            go.Histogram(
                x=receiver_udp['delay'] * 1000,
                nbinsx=50,
                name='延迟分布',
                marker_color='lightblue'
            ),
            row=1, col=2
        )
        
        # 延迟累积分布
        sorted_delays = np.sort(receiver_udp['delay'] * 1000)
        cumulative_prob = np.arange(1, len(sorted_delays) + 1) / len(sorted_delays)
        fig.add_trace(
            go.Scatter(
                x=sorted_delays,
                y=cumulative_prob * 100,
                mode='lines',
                name='累积分布',
                line=dict(color='red', width=2)
            ),
            row=2, col=1
        )
        
        # 包序号vs延迟
        fig.add_trace(
            go.Scatter(
                x=receiver_udp['seq_num'],
                y=receiver_udp['delay'] * 1000,
                mode='markers',
                name='延迟vs序号',
                marker=dict(color='green', size=4, opacity=0.6)
            ),
            row=2, col=2
        )
        
        # 更新布局
        fig.update_layout(
            title='UDP通信性能分析',
            height=800,
            showlegend=True
        )
        
        # 更新x轴和y轴标签
        fig.update_xaxes(title_text="时间", row=1, col=1)
        fig.update_yaxes(title_text="延迟 (ms)", row=1, col=1)
        fig.update_xaxes(title_text="延迟 (ms)", row=1, col=2)
        fig.update_yaxes(title_text="频次", row=1, col=2)
        fig.update_xaxes(title_text="延迟 (ms)", row=2, col=1)
        fig.update_yaxes(title_text="累积概率 (%)", row=2, col=1)
        fig.update_xaxes(title_text="包序号", row=2, col=2)
        fig.update_yaxes(title_text="延迟 (ms)", row=2, col=2)
        
        self.figures['udp_performance'] = fig
        
    def create_nexfi_quality_plots(self):
        """创建NEXFI通信质量图表"""
        if not self.analyzer.nexfi_data:
            return
            
        # 创建子图
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('RSSI时间序列', 'SNR时间序列', '吞吐量时间序列', '链路质量时间序列')
        )
        
        colors = {'sender': 'blue', 'receiver': 'red'}
        
        for role, data in self.analyzer.nexfi_data.items():
            if data.empty:
                continue
                
            # RSSI
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=data['avg_rssi'],
                    mode='lines+markers',
                    name=f'{role} RSSI',
                    line=dict(color=colors[role], width=2),
                    marker=dict(size=4)
                ),
                row=1, col=1
            )
            
            # SNR
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=data['avg_snr'],
                    mode='lines+markers',
                    name=f'{role} SNR',
                    line=dict(color=colors[role], width=2),
                    marker=dict(size=4)
                ),
                row=1, col=2
            )
            
            # 吞吐量
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=data['throughput'],
                    mode='lines+markers',
                    name=f'{role} 吞吐量',
                    line=dict(color=colors[role], width=2),
                    marker=dict(size=4)
                ),
                row=2, col=1
            )
            
            # 链路质量
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=data['link_quality'],
                    mode='lines+markers',
                    name=f'{role} 链路质量',
                    line=dict(color=colors[role], width=2),
                    marker=dict(size=4)
                ),
                row=2, col=2
            )
        
        # 更新布局
        fig.update_layout(
            title='NEXFI通信质量分析',
            height=800,
            showlegend=True
        )
        
        # 更新轴标签
        fig.update_xaxes(title_text="时间", row=1, col=1)
        fig.update_yaxes(title_text="RSSI (dBm)", row=1, col=1)
        fig.update_xaxes(title_text="时间", row=1, col=2)
        fig.update_yaxes(title_text="SNR (dB)", row=1, col=2)
        fig.update_xaxes(title_text="时间", row=2, col=1)
        fig.update_yaxes(title_text="吞吐量 (Mbps)", row=2, col=1)
        fig.update_xaxes(title_text="时间", row=2, col=2)
        fig.update_yaxes(title_text="链路质量", row=2, col=2)
        
        self.figures['nexfi_quality'] = fig
        
    def create_gps_trajectory_plots(self):
        """创建GPS轨迹图表"""
        if not self.analyzer.gps_data:
            return
            
        # 3D轨迹图 - 使用经纬度转换为相对坐标
        fig_3d = go.Figure()
        
        colors = {'sender': 'blue', 'receiver': 'red'}
        
        # 找到所有GPS点的中心作为参考点
        all_lats = []
        all_lons = []
        for role, data in self.analyzer.gps_data.items():
            if not data.empty:
                all_lats.extend(data['latitude'].tolist())
                all_lons.extend(data['longitude'].tolist())
        
        if not all_lats:
            return
            
        # 使用中心点作为参考
        ref_lat = np.mean(all_lats)
        ref_lon = np.mean(all_lons)
        
        # 将经纬度转换为相对米坐标的函数
        def latlon_to_meters(lat, lon, ref_lat, ref_lon):
            """将经纬度转换为相对于参考点的米坐标"""
            from math import radians, cos
            
            # 地球半径（米）
            R = 6371000
            
            # 纬度差转换为米
            y = (lat - ref_lat) * (np.pi / 180) * R
            
            # 经度差转换为米（考虑纬度的影响）
            x = (lon - ref_lon) * (np.pi / 180) * R * cos(radians(ref_lat))
            
            return x, y
        
        for role, data in self.analyzer.gps_data.items():
            if data.empty:
                continue
                
            # 按时间排序
            data_sorted = data.sort_values('timestamp')
            
            # 转换经纬度为相对米坐标
            x_coords = []
            y_coords = []
            for _, row in data_sorted.iterrows():
                x, y = latlon_to_meters(row['latitude'], row['longitude'], ref_lat, ref_lon)
                x_coords.append(x)
                y_coords.append(y)
            
            # 使用高度数据
            z_coords = data_sorted['altitude'].tolist()
            
            # 创建颜色梯度以显示时间进程
            n_points = len(data_sorted)
            color_scale = np.linspace(0, 1, n_points)
            
            # 完整轨迹线
            fig_3d.add_trace(
                go.Scatter3d(
                    x=x_coords,
                    y=y_coords,
                    z=z_coords,
                    mode='lines+markers',
                    name=f'{role} 轨迹',
                    line=dict(
                        color=colors[role], 
                        width=4,
                        colorscale='Viridis' if role == 'sender' else 'Plasma'
                    ),
                    marker=dict(
                        size=3, 
                        opacity=0.8,
                        color=color_scale,
                        colorscale='Viridis' if role == 'sender' else 'Plasma',
                        showscale=True,
                        colorbar=dict(title=f"{role} 时间进程")
                    ),
                    text=[f"时间: {t.strftime('%H:%M:%S')}<br>高度: {h:.1f}m<br>经度: {lon:.6f}<br>纬度: {lat:.6f}" 
                          for t, h, lat, lon in zip(data_sorted['timestamp'], z_coords, 
                                                   data_sorted['latitude'], data_sorted['longitude'])],
                    hovertemplate="%{text}<extra></extra>"
                )
            )
            
            # 添加起始点（绿色大圆点）
            fig_3d.add_trace(
                go.Scatter3d(
                    x=[x_coords[0]],
                    y=[y_coords[0]],
                    z=[z_coords[0]],
                    mode='markers',
                    name=f'{role} 起点',
                    marker=dict(color='green', size=12, symbol='circle')
                )
            )
            
            # 添加结束点（红色大方块）
            fig_3d.add_trace(
                go.Scatter3d(
                    x=[x_coords[-1]],
                    y=[y_coords[-1]],
                    z=[z_coords[-1]],
                    mode='markers',
                    name=f'{role} 终点',
                    marker=dict(color='red', size=12, symbol='square')
                )
            )
        
        fig_3d.update_layout(
            title='无人机3D飞行轨迹（基于GPS经纬度）',
            scene=dict(
                xaxis_title='东西向 (m)',
                yaxis_title='南北向 (m)',
                zaxis_title='高度 (m)',
                aspectmode='data'
            ),
            height=700,
            showlegend=True
        )
        
        self.figures['gps_3d_trajectory'] = fig_3d
        
        # 高度时间序列（修复直线问题）
        fig_alt = go.Figure()
        
        for role, data in self.analyzer.gps_data.items():
            if data.empty:
                continue
                
            # 按时间排序
            data_sorted = data.sort_values('timestamp')
            
            # 使用local_z字段，这是相对高度变化
            alt_data = data_sorted['local_z']
            alt_range = alt_data.max() - alt_data.min()
            print(f"{role} 高度(local_z)变化范围: {alt_range:.2f} m")
            
            fig_alt.add_trace(
                go.Scatter(
                    x=data_sorted['timestamp'],
                    y=alt_data,
                    mode='lines+markers',
                    name=f'{role} 高度',
                    line=dict(color=colors[role], width=2),
                    marker=dict(size=4),
                    text=[f"时间: {t.strftime('%H:%M:%S')}<br>高度: {h:.2f}m" 
                          for t, h in zip(data_sorted['timestamp'], alt_data)],
                    hovertemplate="%{text}<extra></extra>"
                )
            )
        
        fig_alt.update_layout(
            title='高度变化时间序列',
            xaxis_title='时间',
            yaxis_title='相对高度 (m)',
            height=400,
            showlegend=True
        )
        
        self.figures['altitude_timeline'] = fig_alt
        
        # 速度时间序列
        fig_speed = go.Figure()
        
        for role, data in self.analyzer.gps_data.items():
            if data.empty or len(data) < 2:
                continue
                
            data_sorted = data.sort_values('timestamp')
            
            # 计算速度
            speeds = []
            timestamps = []
            
            for i in range(1, len(data_sorted)):
                prev_row = data_sorted.iloc[i-1]
                curr_row = data_sorted.iloc[i]
                
                # 计算3D距离
                distance = np.sqrt(
                    (curr_row['local_x'] - prev_row['local_x'])**2 +
                    (curr_row['local_y'] - prev_row['local_y'])**2 +
                    (curr_row['local_z'] - prev_row['local_z'])**2
                )
                
                # 计算时间差
                time_diff = (curr_row['timestamp'] - prev_row['timestamp']).total_seconds()
                
                if time_diff > 0:
                    speed = distance / time_diff
                    speeds.append(speed)
                    timestamps.append(curr_row['timestamp'])
            
            if speeds:
                fig_speed.add_trace(
                    go.Scatter(
                        x=timestamps,
                        y=speeds,
                        mode='lines+markers',
                        name=f'{role} 速度',
                        line=dict(color=colors[role], width=2),
                        marker=dict(size=4)
                    )
                )
        
        fig_speed.update_layout(
            title='飞行速度时间序列',
            xaxis_title='时间',
            yaxis_title='速度 (m/s)',
            height=400,
            showlegend=True
        )
        
        self.figures['speed_timeline'] = fig_speed
        
    def create_distance_analysis_plots(self):
        """创建距离分析图表"""
        if 'inter_drone_distance' not in self.analyzer.analysis_results:
            return
            
        distance_data = self.analyzer.analysis_results['inter_drone_distance']
        timestamps = distance_data['timestamps']
        distances_3d = distance_data['distances_3d']
        distances_horizontal = distance_data['distances_horizontal']
        distances_vertical = distance_data['distances_vertical']
        
        # 距离时间序列（3D、水平、垂直）
        fig_dist = make_subplots(
            rows=2, cols=1,
            subplot_titles=('双机距离时间序列', '距离分布统计'),
            specs=[[{"secondary_y": False}], [{"type": "box"}]]
        )
        
        # 3D距离时间序列
        fig_dist.add_trace(
            go.Scatter(
                x=timestamps,
                y=distances_3d,
                mode='lines+markers',
                name='3D距离',
                line=dict(color='purple', width=2),
                marker=dict(size=4)
            ),
            row=1, col=1
        )
        
        # 水平距离
        fig_dist.add_trace(
            go.Scatter(
                x=timestamps,
                y=distances_horizontal,
                mode='lines+markers',
                name='水平距离',
                line=dict(color='blue', width=2),
                marker=dict(size=4)
            ),
            row=1, col=1
        )
        
        # 垂直距离
        fig_dist.add_trace(
            go.Scatter(
                x=timestamps,
                y=distances_vertical,
                mode='lines+markers',
                name='垂直距离',
                line=dict(color='green', width=2),
                marker=dict(size=4)
            ),
            row=1, col=1
        )
        
        # 添加平均距离线
        mean_dist_3d = np.mean(distances_3d)
        fig_dist.add_hline(
            y=mean_dist_3d,
            line_dash="dash",
            line_color="red",
            annotation_text=f"平均3D距离: {mean_dist_3d:.2f}m",
            row=1, col=1
        )
        
        # 距离分布箱线图
        fig_dist.add_trace(
            go.Box(y=distances_3d, name='3D距离分布', marker_color='purple'),
            row=2, col=1
        )
        fig_dist.add_trace(
            go.Box(y=distances_horizontal, name='水平距离分布', marker_color='blue'),
            row=2, col=1
        )
        fig_dist.add_trace(
            go.Box(y=distances_vertical, name='垂直距离分布', marker_color='green'),
            row=2, col=1
        )
        
        fig_dist.update_layout(
            title='双机距离分析',
            height=800,
            showlegend=True
        )
        
        fig_dist.update_xaxes(title_text="时间", row=1, col=1)
        fig_dist.update_yaxes(title_text="距离 (m)", row=1, col=1)
        fig_dist.update_yaxes(title_text="距离 (m)", row=2, col=1)
        
        self.figures['distance_timeline'] = fig_dist
        
        # 创建距离统计摘要图表
        stats_data = {
            '统计指标': ['最小值', '最大值', '平均值', '标准差'],
            '3D距离 (m)': [
                distance_data['min_distance_3d'],
                distance_data['max_distance_3d'],
                distance_data['mean_distance_3d'],
                distance_data['std_distance_3d']
            ],
            '水平距离 (m)': [
                distance_data['min_distance_horizontal'],
                distance_data['max_distance_horizontal'],
                distance_data['mean_distance_horizontal'],
                np.std(distances_horizontal)
            ],
            '垂直距离 (m)': [
                distance_data['min_distance_vertical'],
                distance_data['max_distance_vertical'],
                distance_data['mean_distance_vertical'],
                np.std(distances_vertical)
            ]
        }
        
        fig_stats = go.Figure(data=[go.Table(
            header=dict(values=list(stats_data.keys()),
                       fill_color='lightblue',
                       align='center',
                       font_size=12),
            cells=dict(values=[stats_data[k] for k in stats_data.keys()],
                      fill_color='white',
                      align='center',
                      format=[None, '.2f', '.2f', '.2f'],
                      font_size=11)
        )])
        
        fig_stats.update_layout(
            title='距离统计摘要',
            height=300
        )
        
        self.figures['distance_statistics'] = fig_stats
        
    def create_correlation_plots(self):
        """创建相关性分析图表"""
        if 'correlations' not in self.analyzer.analysis_results:
            return
            
        correlations = self.analyzer.analysis_results['correlations']
        
        if not correlations:
            return
            
        # 如果有延迟-距离相关性数据，创建散点图
        if 'delay_distance' in correlations:
            # 重新获取对齐的数据进行绘图
            if 'inter_drone_distance' in self.analyzer.analysis_results and 'udp' in self.analyzer.receiver_data:
                distance_data = self.analyzer.analysis_results['inter_drone_distance']
                distances = distance_data['distances_3d']
                timestamps = distance_data['timestamps']
                udp_data = self.analyzer.receiver_data['udp']
                
                aligned_delays = []
                aligned_distances = []
                
                for _, udp_row in udp_data.iterrows():
                    time_diffs = [abs((ts - udp_row['recv_timestamp']).total_seconds()) for ts in timestamps]
                    if not time_diffs:
                        continue
                    closest_idx = time_diffs.index(min(time_diffs))
                    
                    if min(time_diffs) < 5:
                        aligned_delays.append(udp_row['delay'] * 1000)
                        aligned_distances.append(distances[closest_idx])
                
                if aligned_delays:
                    fig_corr = go.Figure()
                    
                    fig_corr.add_trace(
                        go.Scatter(
                            x=aligned_distances,
                            y=aligned_delays,
                            mode='markers',
                            name='延迟vs距离',
                            marker=dict(color='blue', size=6, opacity=0.6)
                        )
                    )
                    
                    # 添加趋势线
                    z = np.polyfit(aligned_distances, aligned_delays, 1)
                    p = np.poly1d(z)
                    x_trend = np.linspace(min(aligned_distances), max(aligned_distances), 100)
                    y_trend = p(x_trend)
                    
                    fig_corr.add_trace(
                        go.Scatter(
                            x=x_trend,
                            y=y_trend,
                            mode='lines',
                            name='趋势线',
                            line=dict(color='red', width=2)
                        )
                    )
                    
                    corr_val = correlations['delay_distance']['correlation']
                    p_val = correlations['delay_distance']['p_value']
                    
                    fig_corr.update_layout(
                        title=f'UDP延迟与双机距离相关性分析<br>相关系数: r={corr_val:.3f}, p={p_val:.3f}',
                        xaxis_title='距离 (m)',
                        yaxis_title='延迟 (ms)',
                        height=500
                    )
                    
                    self.figures['delay_distance_correlation'] = fig_corr
        
        # RSSI-距离相关性
        for role in ['sender', 'receiver']:
            if f'rssi_distance_{role}' in correlations and role in self.analyzer.nexfi_data:
                distance_data = self.analyzer.analysis_results['inter_drone_distance']
                distances = distance_data['distances_3d']
                timestamps = distance_data['timestamps']
                nexfi_data = self.analyzer.nexfi_data[role]
                
                aligned_rssi = []
                aligned_distances = []
                
                for _, nexfi_row in nexfi_data.iterrows():
                    time_diffs = [abs((ts - nexfi_row['timestamp']).total_seconds()) for ts in timestamps]
                    if not time_diffs:
                        continue
                    closest_idx = time_diffs.index(min(time_diffs))
                    
                    if min(time_diffs) < 10:
                        aligned_rssi.append(nexfi_row['avg_rssi'])
                        aligned_distances.append(distances[closest_idx])
                
                if aligned_rssi:
                    fig_rssi_corr = go.Figure()
                    
                    fig_rssi_corr.add_trace(
                        go.Scatter(
                            x=aligned_distances,
                            y=aligned_rssi,
                            mode='markers',
                            name=f'{role} RSSI vs 距离',
                            marker=dict(color='green', size=6, opacity=0.6)
                        )
                    )
                    
                    # 添加趋势线
                    z = np.polyfit(aligned_distances, aligned_rssi, 1)
                    p = np.poly1d(z)
                    x_trend = np.linspace(min(aligned_distances), max(aligned_distances), 100)
                    y_trend = p(x_trend)
                    
                    fig_rssi_corr.add_trace(
                        go.Scatter(
                            x=x_trend,
                            y=y_trend,
                            mode='lines',
                            name='趋势线',
                            line=dict(color='red', width=2)
                        )
                    )
                    
                    corr_val = correlations[f'rssi_distance_{role}']['correlation']
                    p_val = correlations[f'rssi_distance_{role}']['p_value']
                    
                    fig_rssi_corr.update_layout(
                        title=f'{role} RSSI与双机距离相关性分析<br>相关系数: r={corr_val:.3f}, p={p_val:.3f}',
                        xaxis_title='距离 (m)',
                        yaxis_title='RSSI (dBm)',
                        height=500
                    )
                    
                    self.figures[f'rssi_distance_correlation_{role}'] = fig_rssi_corr
        
    def create_all_plots(self):
        """创建所有图表"""
        print("生成可视化图表...")
        self.create_udp_performance_plots()
        self.create_nexfi_quality_plots()
        self.create_gps_trajectory_plots()
        self.create_distance_analysis_plots()
        self.create_correlation_plots()
        print(f"已生成 {len(self.figures)} 个图表")
        
    def save_plots_as_html(self, output_dir="plots"):
        """将所有图表保存为HTML文件"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        for name, fig in self.figures.items():
            output_file = os.path.join(output_dir, f"{name}.html")
            pyo.plot(fig, filename=output_file, auto_open=False)
            print(f"图表已保存: {output_file}")
            
    def get_figures_json(self):
        """将图表转换为JSON格式，用于Web展示"""
        figures_json = {}
        for name, fig in self.figures.items():
            figures_json[name] = fig.to_json()
        return figures_json


def create_summary_dashboard(analyzer):
    """创建综合仪表板"""
    if not analyzer.analysis_results:
        return None
        
    # 创建综合仪表板的多子图布局
    fig = make_subplots(
        rows=3, cols=3,
        subplot_titles=[
            'UDP延迟统计', '丢包率指示器', 'RSSI分布',
            '3D距离分布', '吞吐量对比', '高度变化范围',
            '链路质量', '速度统计', '测试时长'
        ],
        specs=[
            [{"type": "bar"}, {"type": "indicator"}, {"type": "box"}],
            [{"type": "histogram"}, {"type": "bar"}, {"type": "scatter"}],
            [{"type": "scatter"}, {"type": "box"}, {"type": "indicator"}]
        ]
    )
    
    # 1. UDP延迟统计
    if 'udp' in analyzer.analysis_results:
        udp_stats = analyzer.analysis_results['udp']['delay_stats']
        fig.add_trace(
            go.Bar(
                x=['平均值', '中位数', '95%', '99%'],
                y=[udp_stats['mean'], udp_stats['median'], udp_stats['p95'], udp_stats['p99']],
                name='延迟统计',
                marker_color='lightblue'
            ),
            row=1, col=1
        )
    
    # 2. 丢包率指示器
    if 'udp' in analyzer.analysis_results:
        packet_loss = analyzer.analysis_results['udp']['packet_loss_rate']
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=packet_loss,
                title={'text': "丢包率 (%)"},
                gauge={'axis': {'range': [None, 50]},
                       'bar': {'color': "red" if packet_loss > 10 else "orange" if packet_loss > 5 else "green"},
                       'steps': [{'range': [0, 5], 'color': "lightgray"},
                                {'range': [5, 10], 'color': "yellow"},
                                {'range': [10, 50], 'color': "red"}],
                       'threshold': {'line': {'color': "red", 'width': 4},
                                   'thickness': 0.75, 'value': 10}}
            ),
            row=1, col=2
        )
    
    # 3. 添加更多子图...
    # (其他子图内容类似，根据需要添加)
    
    fig.update_layout(
        title='无人机通信测试综合仪表板',
        height=900,
        showlegend=False
    )
    
    return fig 
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
            
        # 3D轨迹图
        fig_3d = go.Figure()
        
        colors = {'sender': 'blue', 'receiver': 'red'}
        
        for role, data in self.analyzer.gps_data.items():
            if data.empty:
                continue
                
            fig_3d.add_trace(
                go.Scatter3d(
                    x=data['local_x'],
                    y=data['local_y'],
                    z=data['local_z'],
                    mode='lines+markers',
                    name=f'{role} 轨迹',
                    line=dict(color=colors[role], width=4),
                    marker=dict(size=3, opacity=0.8)
                )
            )
            
            # 添加起始点
            fig_3d.add_trace(
                go.Scatter3d(
                    x=[data['local_x'].iloc[0]],
                    y=[data['local_y'].iloc[0]],
                    z=[data['local_z'].iloc[0]],
                    mode='markers',
                    name=f'{role} 起点',
                    marker=dict(color=colors[role], size=10, symbol='diamond')
                )
            )
            
            # 添加结束点
            fig_3d.add_trace(
                go.Scatter3d(
                    x=[data['local_x'].iloc[-1]],
                    y=[data['local_y'].iloc[-1]],
                    z=[data['local_z'].iloc[-1]],
                    mode='markers',
                    name=f'{role} 终点',
                    marker=dict(color=colors[role], size=10, symbol='square')
                )
            )
        
        fig_3d.update_layout(
            title='无人机3D飞行轨迹',
            scene=dict(
                xaxis_title='X (m)',
                yaxis_title='Y (m)',
                zaxis_title='Z (m)',
                aspectmode='data'
            ),
            height=700
        )
        
        self.figures['gps_3d_trajectory'] = fig_3d
        
        # 高度时间序列
        fig_alt = go.Figure()
        
        for role, data in self.analyzer.gps_data.items():
            if data.empty:
                continue
                
            fig_alt.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=data['altitude'],
                    mode='lines+markers',
                    name=f'{role} 高度',
                    line=dict(color=colors[role], width=2),
                    marker=dict(size=4)
                )
            )
        
        fig_alt.update_layout(
            title='高度变化时间序列',
            xaxis_title='时间',
            yaxis_title='高度 (m)',
            height=400
        )
        
        self.figures['altitude_timeline'] = fig_alt
        
    def create_distance_analysis_plots(self):
        """创建距离分析图表"""
        if 'inter_drone_distance' not in self.analyzer.analysis_results:
            return
            
        distance_data = self.analyzer.analysis_results['inter_drone_distance']
        timestamps = distance_data['timestamps']
        distances = distance_data['distances']
        
        # 距离时间序列
        fig_dist = go.Figure()
        
        fig_dist.add_trace(
            go.Scatter(
                x=timestamps,
                y=distances,
                mode='lines+markers',
                name='双机距离',
                line=dict(color='purple', width=2),
                marker=dict(size=4)
            )
        )
        
        # 添加平均距离线
        mean_dist = np.mean(distances)
        fig_dist.add_hline(
            y=mean_dist,
            line_dash="dash",
            line_color="red",
            annotation_text=f"平均距离: {mean_dist:.2f}m"
        )
        
        fig_dist.update_layout(
            title='双机距离时间序列',
            xaxis_title='时间',
            yaxis_title='距离 (m)',
            height=400
        )
        
        self.figures['distance_timeline'] = fig_dist
        
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
                distances = distance_data['distances']
                timestamps = distance_data['timestamps']
                udp_data = self.analyzer.receiver_data['udp']
                
                aligned_delays = []
                aligned_distances = []
                
                for _, udp_row in udp_data.iterrows():
                    time_diffs = [abs((ts - udp_row['recv_timestamp']).total_seconds()) for ts in timestamps]
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
                distances = distance_data['distances']
                timestamps = distance_data['timestamps']
                nexfi_data = self.analyzer.nexfi_data[role]
                
                aligned_rssi = []
                aligned_distances = []
                
                for _, nexfi_row in nexfi_data.iterrows():
                    time_diffs = [abs((ts - nexfi_row['timestamp']).total_seconds()) for ts in timestamps]
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
        
    # 创建综合仪表板
    fig = make_subplots(
        rows=3, cols=3,
        subplot_titles=[
            'UDP延迟统计', '丢包率', 'RSSI统计',
            '双机距离统计', '吞吐量对比', '高度变化',
            '链路质量', 'SNR统计', '性能指标总览'
        ],
        specs=[[{"type": "bar"}, {"type": "indicator"}, {"type": "box"}],
               [{"type": "histogram"}, {"type": "bar"}, {"type": "scatter"}],
               [{"type": "scatter"}, {"type": "box"}, {"type": "table"}]]
    )
    
    # UDP延迟统计
    if 'udp' in analyzer.analysis_results:
        delay_stats = analyzer.analysis_results['udp']['delay_stats']
        fig.add_trace(
            go.Bar(
                x=['平均', '中位数', '95%', '99%'],
                y=[delay_stats['mean'], delay_stats['median'], 
                   delay_stats['p95'], delay_stats['p99']],
                name='延迟统计',
                marker_color='lightblue'
            ),
            row=1, col=1
        )
        
        # 丢包率指示器
        packet_loss = analyzer.analysis_results['udp']['packet_loss_rate']
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=packet_loss,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "丢包率 (%)"},
                gauge={'axis': {'range': [None, 50]},
                       'bar': {'color': "darkblue"},
                       'steps': [{'range': [0, 5], 'color': "lightgray"},
                                {'range': [5, 20], 'color': "gray"}],
                       'threshold': {'line': {'color': "red", 'width': 4},
                                   'thickness': 0.75, 'value': 10}}
            ),
            row=1, col=2
        )
    
    # RSSI统计（如果有NEXFI数据）
    if 'nexfi' in analyzer.analysis_results:
        rssi_data = []
        roles = []
        for role, stats in analyzer.analysis_results['nexfi'].items():
            rssi_data.extend([stats['rssi']['mean']] * 10)  # 简化显示
            roles.extend([role] * 10)
            
        if rssi_data:
            fig.add_trace(
                go.Box(y=rssi_data, name='RSSI分布', marker_color='lightgreen'),
                row=1, col=3
            )
    
    # 距离统计
    if 'inter_drone_distance' in analyzer.analysis_results:
        distances = analyzer.analysis_results['inter_drone_distance']['distances']
        fig.add_trace(
            go.Histogram(x=distances, name='距离分布', marker_color='orange'),
            row=2, col=1
        )
        
    fig.update_layout(
        title='无人机通信测试综合仪表板',
        height=1000,
        showlegend=False
    )
    
    return fig 
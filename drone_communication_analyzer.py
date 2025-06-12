import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
import glob
import json
from pathlib import Path
import seaborn as sns
from scipy.spatial.distance import euclidean
from scipy import stats
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo


class DroneCommAnalyzer:
    def __init__(self, data_folder):
        """
        初始化无人机通信数据分析器
        
        Args:
            data_folder (str): 测试数据文件夹路径
        """
        self.data_folder = data_folder
        self.sender_data = {}
        self.receiver_data = {}
        self.nexfi_data = {}
        self.gps_data = {}
        self.analysis_results = {}
        
    def load_data(self):
        """加载所有数据文件"""
        sender_folder = os.path.join(self.data_folder, 'sender')
        receiver_folder = os.path.join(self.data_folder, 'receiver')
        
        # 加载UDP发送方数据
        udp_sender_files = glob.glob(os.path.join(sender_folder, 'udp_sender_*.csv'))
        if udp_sender_files:
            self.sender_data['udp'] = pd.read_csv(udp_sender_files[0])
            self.sender_data['udp']['timestamp'] = pd.to_datetime(self.sender_data['udp']['timestamp'], unit='s')
            
        # 加载UDP接收方数据
        udp_receiver_files = glob.glob(os.path.join(receiver_folder, 'udp_receiver_*.csv'))
        if udp_receiver_files:
            self.receiver_data['udp'] = pd.read_csv(udp_receiver_files[0])
            self.receiver_data['udp']['send_timestamp'] = pd.to_datetime(self.receiver_data['udp']['send_timestamp'], unit='s')
            self.receiver_data['udp']['recv_timestamp'] = pd.to_datetime(self.receiver_data['udp']['recv_timestamp'], unit='s')
            
        # 加载NEXFI数据
        nexfi_sender_files = glob.glob(os.path.join(sender_folder, 'nexfi_status_*.csv'))
        nexfi_receiver_files = glob.glob(os.path.join(receiver_folder, 'nexfi_status_*.csv'))
        
        if nexfi_sender_files:
            self.nexfi_data['sender'] = pd.read_csv(nexfi_sender_files[0])
            self.nexfi_data['sender']['timestamp'] = pd.to_datetime(self.nexfi_data['sender']['timestamp'], unit='s')
            
        if nexfi_receiver_files:
            self.nexfi_data['receiver'] = pd.read_csv(nexfi_receiver_files[0])
            self.nexfi_data['receiver']['timestamp'] = pd.to_datetime(self.nexfi_data['receiver']['timestamp'], unit='s')
            
        # 加载GPS数据
        gps_sender_files = glob.glob(os.path.join(sender_folder, 'gps_logger_drone*_*.csv'))
        gps_receiver_files = glob.glob(os.path.join(receiver_folder, 'gps_logger_drone*_*.csv'))
        
        if gps_sender_files:
            self.gps_data['sender'] = pd.read_csv(gps_sender_files[0])
            self.gps_data['sender']['timestamp'] = pd.to_datetime(self.gps_data['sender']['timestamp'], unit='s')
            
        if gps_receiver_files:
            self.gps_data['receiver'] = pd.read_csv(gps_receiver_files[0])
            self.gps_data['receiver']['timestamp'] = pd.to_datetime(self.gps_data['receiver']['timestamp'], unit='s')
            
        print(f"数据加载完成:")
        print(f"  发送方UDP数据: {len(self.sender_data.get('udp', []))} 条记录")
        print(f"  接收方UDP数据: {len(self.receiver_data.get('udp', []))} 条记录")
        print(f"  发送方NEXFI数据: {len(self.nexfi_data.get('sender', []))} 条记录")
        print(f"  接收方NEXFI数据: {len(self.nexfi_data.get('receiver', []))} 条记录")
        print(f"  发送方GPS数据: {len(self.gps_data.get('sender', []))} 条记录")
        print(f"  接收方GPS数据: {len(self.gps_data.get('receiver', []))} 条记录")
        
    def analyze_udp_performance(self):
        """分析UDP通信性能"""
        if 'udp' not in self.sender_data or 'udp' not in self.receiver_data:
            print("缺少UDP数据，跳过UDP性能分析")
            return
            
        sender_udp = self.sender_data['udp']
        receiver_udp = self.receiver_data['udp']
        
        # 计算基本统计
        total_sent = len(sender_udp)
        total_received = len(receiver_udp)
        packet_loss_rate = (total_sent - total_received) / total_sent * 100
        
        # 延迟统计
        delay_stats = {
            'mean': receiver_udp['delay'].mean() * 1000,  # 转换为毫秒
            'median': receiver_udp['delay'].median() * 1000,
            'std': receiver_udp['delay'].std() * 1000,
            'min': receiver_udp['delay'].min() * 1000,
            'max': receiver_udp['delay'].max() * 1000,
            'p95': receiver_udp['delay'].quantile(0.95) * 1000,
            'p99': receiver_udp['delay'].quantile(0.99) * 1000
        }
        
        # 计算吞吐量
        test_duration = (sender_udp['timestamp'].max() - sender_udp['timestamp'].min()).total_seconds()
        throughput_kbps = (total_received * sender_udp['packet_size'].iloc[0] * 8) / (test_duration * 1000)
        
        self.analysis_results['udp'] = {
            'total_sent': total_sent,
            'total_received': total_received,
            'packet_loss_rate': packet_loss_rate,
            'delay_stats': delay_stats,
            'throughput_kbps': throughput_kbps,
            'test_duration': test_duration
        }
        
        print(f"\nUDP性能分析结果:")
        print(f"  发送包数: {total_sent}")
        print(f"  接收包数: {total_received}")
        print(f"  丢包率: {packet_loss_rate:.2f}%")
        print(f"  平均延迟: {delay_stats['mean']:.2f} ms")
        print(f"  延迟标准差: {delay_stats['std']:.2f} ms")
        print(f"  95%延迟: {delay_stats['p95']:.2f} ms")
        print(f"  吞吐量: {throughput_kbps:.2f} kbps")
        
    def analyze_nexfi_performance(self):
        """分析NEXFI通信质量"""
        nexfi_results = {}
        
        for role, data in self.nexfi_data.items():
            if data.empty:
                continue
                
            stats = {
                'rssi': {
                    'mean': data['avg_rssi'].mean(),
                    'std': data['avg_rssi'].std(),
                    'min': data['avg_rssi'].min(),
                    'max': data['avg_rssi'].max()
                },
                'snr': {
                    'mean': data['avg_snr'].mean(),
                    'std': data['avg_snr'].std(),
                    'min': data['avg_snr'].min(),
                    'max': data['avg_snr'].max()
                },
                'throughput': {
                    'mean': data['throughput'].mean(),
                    'std': data['throughput'].std(),
                    'min': data['throughput'].min(),
                    'max': data['throughput'].max()
                },
                'link_quality': {
                    'mean': data['link_quality'].mean(),
                    'std': data['link_quality'].std(),
                    'min': data['link_quality'].min(),
                    'max': data['link_quality'].max()
                }
            }
            nexfi_results[role] = stats
            
        self.analysis_results['nexfi'] = nexfi_results
        
        print(f"\nNEXFI通信质量分析结果:")
        for role, stats in nexfi_results.items():
            print(f"  {role}:")
            print(f"    平均RSSI: {stats['rssi']['mean']:.1f} dBm")
            print(f"    平均SNR: {stats['snr']['mean']:.1f} dB")
            print(f"    平均吞吐量: {stats['throughput']['mean']:.2f} Mbps")
            print(f"    平均链路质量: {stats['link_quality']['mean']:.1f}")
            
    def analyze_gps_trajectory(self):
        """分析GPS轨迹"""
        gps_results = {}
        
        for role, data in self.gps_data.items():
            if data.empty:
                continue
                
            # 计算距离
            distances = []
            if len(data) > 1:
                for i in range(1, len(data)):
                    dist = euclidean(
                        [data.iloc[i]['local_x'], data.iloc[i]['local_y'], data.iloc[i]['local_z']],
                        [data.iloc[i-1]['local_x'], data.iloc[i-1]['local_y'], data.iloc[i-1]['local_z']]
                    )
                    distances.append(dist)
                    
            # 计算速度
            speeds = []
            if len(data) > 1:
                for i in range(1, len(data)):
                    time_diff = (data.iloc[i]['timestamp'] - data.iloc[i-1]['timestamp']).total_seconds()
                    if time_diff > 0 and i-1 < len(distances):
                        speed = distances[i-1] / time_diff
                        speeds.append(speed)
                        
            # 计算航迹统计
            stats = {
                'total_distance': sum(distances) if distances else 0,
                'max_altitude': data['altitude'].max(),
                'min_altitude': data['altitude'].min(),
                'altitude_change': data['altitude'].max() - data['altitude'].min(),
                'max_speed': max(speeds) if speeds else 0,
                'avg_speed': np.mean(speeds) if speeds else 0,
                'flight_time': (data['timestamp'].max() - data['timestamp'].min()).total_seconds()
            }
            
            gps_results[role] = stats
            
        self.analysis_results['gps'] = gps_results
        
        print(f"\nGPS轨迹分析结果:")
        for role, stats in gps_results.items():
            print(f"  {role}:")
            print(f"    总飞行距离: {stats['total_distance']:.2f} m")
            print(f"    高度变化: {stats['altitude_change']:.2f} m")
            print(f"    最大速度: {stats['max_speed']:.2f} m/s")
            print(f"    平均速度: {stats['avg_speed']:.2f} m/s")
            print(f"    飞行时间: {stats['flight_time']:.1f} s")
            
    def calculate_inter_drone_distance(self):
        """计算双机之间的距离"""
        if 'sender' not in self.gps_data or 'receiver' not in self.gps_data:
            print("缺少GPS数据，无法计算双机距离")
            return
            
        sender_gps = self.gps_data['sender']
        receiver_gps = self.gps_data['receiver']
        
        # 时间对齐
        distances = []
        timestamps = []
        
        for _, sender_row in sender_gps.iterrows():
            # 找到最接近的接收方GPS点
            time_diffs = abs(receiver_gps['timestamp'] - sender_row['timestamp'])
            closest_idx = time_diffs.idxmin()
            receiver_row = receiver_gps.loc[closest_idx]
            
            # 计算3D距离
            distance = euclidean(
                [sender_row['local_x'], sender_row['local_y'], sender_row['local_z']],
                [receiver_row['local_x'], receiver_row['local_y'], receiver_row['local_z']]
            )
            
            distances.append(distance)
            timestamps.append(sender_row['timestamp'])
            
        # 保存结果
        self.analysis_results['inter_drone_distance'] = {
            'timestamps': timestamps,
            'distances': distances,
            'mean_distance': np.mean(distances),
            'max_distance': max(distances),
            'min_distance': min(distances),
            'std_distance': np.std(distances)
        }
        
        print(f"\n双机距离分析结果:")
        print(f"  平均距离: {np.mean(distances):.2f} m")
        print(f"  最大距离: {max(distances):.2f} m")
        print(f"  最小距离: {min(distances):.2f} m")
        print(f"  距离标准差: {np.std(distances):.2f} m")
        
    def analyze_correlation(self):
        """分析通信质量与距离的相关性"""
        if 'inter_drone_distance' not in self.analysis_results:
            print("缺少距离数据，无法进行相关性分析")
            return
            
        # 获取距离数据
        distance_data = self.analysis_results['inter_drone_distance']
        distances = distance_data['distances']
        timestamps = distance_data['timestamps']
        
        correlations = {}
        
        # 与UDP延迟的相关性
        if 'udp' in self.receiver_data:
            udp_data = self.receiver_data['udp']
            aligned_delays = []
            aligned_distances = []
            
            for _, udp_row in udp_data.iterrows():
                # 找到最接近的距离数据点
                time_diffs = [abs((ts - udp_row['recv_timestamp']).total_seconds()) for ts in timestamps]
                closest_idx = time_diffs.index(min(time_diffs))
                
                if min(time_diffs) < 5:  # 5秒内的数据才考虑
                    aligned_delays.append(udp_row['delay'] * 1000)  # 转换为毫秒
                    aligned_distances.append(distances[closest_idx])
                    
            if len(aligned_delays) > 10:
                correlation, p_value = stats.pearsonr(aligned_distances, aligned_delays)
                correlations['delay_distance'] = {
                    'correlation': correlation,
                    'p_value': p_value,
                    'significant': p_value < 0.05
                }
                
        # 与NEXFI RSSI的相关性
        for role in ['sender', 'receiver']:
            if role in self.nexfi_data:
                nexfi_data = self.nexfi_data[role]
                aligned_rssi = []
                aligned_distances = []
                
                for _, nexfi_row in nexfi_data.iterrows():
                    time_diffs = [abs((ts - nexfi_row['timestamp']).total_seconds()) for ts in timestamps]
                    closest_idx = time_diffs.index(min(time_diffs))
                    
                    if min(time_diffs) < 10:  # 10秒内的数据才考虑
                        aligned_rssi.append(nexfi_row['avg_rssi'])
                        aligned_distances.append(distances[closest_idx])
                        
                if len(aligned_rssi) > 5:
                    correlation, p_value = stats.pearsonr(aligned_distances, aligned_rssi)
                    correlations[f'rssi_distance_{role}'] = {
                        'correlation': correlation,
                        'p_value': p_value,
                        'significant': p_value < 0.05
                    }
                    
        self.analysis_results['correlations'] = correlations
        
        print(f"\n相关性分析结果:")
        for key, corr in correlations.items():
            print(f"  {key}: r={corr['correlation']:.3f}, p={corr['p_value']:.3f} {'(显著)' if corr['significant'] else '(不显著)'}")
            
    def run_full_analysis(self):
        """运行完整分析流程"""
        print("开始数据分析...")
        self.load_data()
        self.analyze_udp_performance()
        self.analyze_nexfi_performance()
        self.analyze_gps_trajectory()
        self.calculate_inter_drone_distance()
        self.analyze_correlation()
        print("\n数据分析完成!")
        
    def save_results(self, output_file):
        """保存分析结果到JSON文件"""
        # 处理datetime对象，转换为字符串
        results_copy = self.analysis_results.copy()
        
        if 'inter_drone_distance' in results_copy:
            timestamps = results_copy['inter_drone_distance']['timestamps']
            results_copy['inter_drone_distance']['timestamps'] = [ts.isoformat() for ts in timestamps]
            
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_copy, f, ensure_ascii=False, indent=2)
        print(f"分析结果已保存到: {output_file}")


def main():
    # 测试分析器
    data_folder = "20250612190350"
    if not os.path.exists(data_folder):
        print(f"数据文件夹 {data_folder} 不存在")
        return
        
    analyzer = DroneCommAnalyzer(data_folder)
    analyzer.run_full_analysis()
    
    # 保存结果
    output_file = f"analysis_results_{os.path.basename(data_folder)}.json"
    analyzer.save_results(output_file)


if __name__ == "__main__":
    main() 